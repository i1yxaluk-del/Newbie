# Post-mortem: миграция MSPShield → Cloud.ru Evolution

**Дата:** 2026-10-05 · **Статус:** выполнено · **Автор:** DevOps-агент + оператор

## Итог

Production перенесён с single-VM Yandex Cloud на Cloud.ru Evolution. Сайт, API,
мониторинг, Vaultwarden и Stalwart работают на новой ВМ под управлением домена
`msp-claude.online` с TLS Let's Encrypt. Данные (Mongo, Vaultwarden, Stalwart)
восстановлены из локального migration-кита. **Почта переведена на прямую доставку
по MX — без Yandex Cloud Postbox.**

| Компонент | Результат |
|---|---|
| ВМ | `msp-cloud-vm`, 2 vCPU / 4 GB, Ubuntu 22.04, 30 GB SSD, `ru.AZ-3` |
| Публичный IP | **`45.132.176.143`** (постоянный, direct-IP) |
| Лендинг / API | `200` / `{"status":"ok","db":"connected"}` |
| Grafana / Vaultwarden | `200` / `200` |
| Почта | SMTP 25 (вход/исход), SMTPS 465, IMAPS 993, Sieve 4190, LE-сертификат |
| Данные | Mongo 10 лидов, тома Vaultwarden/Stalwart восстановлены |

## Хронология

1. Анализ репозитория: найдены канонические runbook'и (`migration/README.md`,
   `docs/deployment/MIGRATION_RUNBOOK.md`, `DEPLOY_RUNBOOK.md`) и автоматизация
   (`migrate.ps1`, `restore-on-vm.sh`, `restic-backup.sh`, `cloud-init.yaml`).
2. Изучен API Cloud.ru Evolution; получен токен (`iam.api.cloud.ru/api/v1/auth/token`).
3. Созданы ресурсы через API: диск из `ubuntu-22.04`, ВМ `lowcost10-2-4`, интерфейсы,
   публичный IP; в SG открыты нужные порты.
4. Bootstrap ВМ (Docker/Caddy/Node/restic/ufw), деплой кода и env, `preflight` → OK.
5. Восстановление данных из `migration/` (`restore-on-vm.sh`): mongo, vaultwarden,
   stalwart (+ проверка «не bootstrap»).
6. Переключение на постоянный direct-IP, **диагностика и фикс асимметричной
   маршрутизации**, выпуск TLS.
7. Почта переведена на прямую доставку (удалён релей Postbox, импортирован
   актуальный сертификат).

## Уроки (главные)

### 1. Два интерфейса — асимметричная маршрутизация (самый дорогой урок)
ВМ получила `enp3s0` (внутренний, 10.0.0.6) и `enp8s0` (direct-IP). DHCP выдал
**два default-маршрута с одинаковой metric 100** — ответные пакеты уходили через
`enp3s0` с чужим source-IP, и соединения рвались: SSH/HTTP таймаутили, почтовые
порты были недоступны, хотя сервисы слушали и SG/ufw всё разрешали.

**Диагностика:** `ip route get 8.8.8.8` показал `dev enp3s0`, хотя входящие шли на
`enp8s0`. Симптом «TCP SYN-ACK есть, а данные не идут» — классическая асимметрия.

**Фикс (персистентно):**
```bash
ip route replace default via 45.132.176.1 dev enp8s0 metric 50
```
в `msp-policy-route.service`. Важно: **не** решать это policy-rule'ом
`from <docker-subnet> lookup <table>` — такая таблица не содержит маршрутов бриджей,
и связь host↔контейнер рвётся (проверено, откатили).

### 2. Direct-IP интерфейс ≠ Floating IP
Direct-IP даёт публичный адрес прямо на интерфейсе ВМ (нужен PTR/своя маршрутизация),
floating IP — NAT на внутренний адрес. У нас работали оба, но direct-IP потребовал
фикса из п.1. Для админ-доступа удобно временно повесить floating IP на основной
интерфейс (и потом удалить).

### 3. Формат API Cloud.ru Evolution (документация куцая, всё через опыт)
- Токен: `POST https://iam.api.cloud.ru/api/v1/auth/token` `{"keyId","secret"}`.
- **OAuth-ключи API не равны S3-ключам**: для Object Storage нужны отдельные
  статические ключи (`InvalidAccessKeyId` иначе).
- Service endpoints: `compute.api.cloud.ru`, `vpc.api.cloud.ru`, `dns.api.cloud.ru`,
  `s3.cloud.ru` (регион `ru-central-1`).
- Создание ВМ: тело — **массив**; `disks:[{"disk_id": …}]`; SSH-ключ через
  `image_metadata:{public_key, name, hostname}` **простыми строками** (не `{string_value}`).
- Интерфейс ВМ при создании создаётся автоматически в дефолтной подсети AZ.

### 4. Cloud.ru НЕ блокирует порт 25 (в отличие от Yandex Cloud)
Проверено: исходящий 25 к Gmail/Яндекс — OK; входящий 25 — Stalwart отвечает баннером.
Это открывает **полную самостоятельную почту без Postbox**: Stalwart доставляет по MX
напрямую. Postbox был обходом блокировки 25 в YC.
Для доставляемости обязательны: PTR (в Evolution DNS есть PTR-зоны), DKIM
(Stalwart генерирует), SPF, DMARC, MX.

### 5. Stalwart: маршрутизация и сертификаты
- Маршрут прямой доставки `mx` уже был; релей Postbox (`BaseYandex`) удалён через
  JMAP `x:MtaRoute/set`. Конфиг Stalwart живёт в RocksDB (том `stalwart-data`),
  **env-переменные применяются только при первом запуске** — правки только через API/UI.
- Полный набор DNS-записей Stalwart генерирует сам: `x:Domain/get` → `dnsZoneFile`
  (сохранён в `deploy/yandex/dns-zone-stalwart.txt`).
- После восстановления из бэкапа Stalwart отдавал **просроченный** self-signed
  сертификат; лечится импортом сертификата Caddy в `x:Certificate` + **рестарт**
  контейнера (без рестарта listener продолжает отдавать старое).

### 6. Прочее
- `docs/deployment/MIGRATION_RUNBOOK.md` §9.2 (доступность IP) подтвердился —
  проверять TCP до DNS-switch обязательно.
- `max-session.tar.gz` не было в ките → MAX требует ручной авторизации (штатно).
- Снаружи доступны `465`/`993`/`4190`; `587`/`143` (STARTTLS) фильтруются облаком —
  клиентам указывать implicit-TLS порты.
- На операторской станции `pwsh` может падать с `0xC0000142` (DLL init) — лечится
  перезапуском Harness; работать через PowerShell 5.1.

## Что улучшить в следующий раз

1. Сразу после создания ВМ с двумя интерфейсами — проверить `ip route get 8.8.8.8`
   и при двух default-маршрутах сразу выставить приоритет.
2. Держать DNS-зону (SPF/DKIM/DMARC/MX/PTR) в IaC рядом с репозиторием, а не собирать
   руками — Stalwart уже отдаёт готовый zone file.
3. Заранее заготавливать `max-session` в ките, чтобы не терять MAX-сессию.
4. Проверять PTR до включения прямой отправки почты.

## Артефакты

- Плейбук: [`migration/CLOUDRU_MIGRATION.md`](../../migration/CLOUDRU_MIGRATION.md)
- Ресурсы и API: [`migration/CLOUDRU_RESOURCES.md`](../../migration/CLOUDRU_RESOURCES.md)
- Скрипты: `cloudru-bootstrap.sh`, `cloudru-fix-routing.sh`, `cloudru-mail-cert.sh`
- DNS-зона: [`deploy/yandex/dns-zone-stalwart.txt`](../../deploy/yandex/dns-zone-stalwart.txt)
