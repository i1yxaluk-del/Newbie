# Миграция MSPShield на Cloud.ru Evolution — пошаговая инструкция

Документ для инженера (в том числе **junior**): что делать по шагам, зачем именно так,
как проверить результат и что делать, если сломалось. Все скрипты лежат в
[`migration/`](../../migration/) и **содержат такие же пояснения в шапке файла**.

Сопутствующие документы:
- [`POSTMORTEM_CLOUDRU_MIGRATION.md`](POSTMORTEM_CLOUDRU_MIGRATION.md) — что пошло не так и почему;
- [`JAMI_MIGRATION_CLOUDRU.md`](JAMI_MIGRATION_CLOUDRU.md) — отдельно про Jami/JAMS;
- [`../../migration/CLOUDRU_MIGRATION.md`](../../migration/CLOUDRU_MIGRATION.md) — плейбук-конспект;
- [`../../migration/CLOUDRU_RESOURCES.md`](../../migration/CLOUDRU_RESOURCES.md) — созданные ресурсы и API.

---

## 0. Что должно получиться

Одна ВМ в Cloud.ru Evolution, на которой живёт весь пилот:

| Слой | Что | Как проверяется |
|---|---|---|
| Веб | Caddy (TLS) + лендинг + FastAPI + Mongo | `https://msp-claude.online` → 200, `/api/health` → `{"status":"ok"}` |
| Секреты | Vaultwarden | `https://vault.msp-claude.online` → 200 |
| Наблюдаемость | Prometheus + Grafana + Alertmanager | `https://mon.msp-claude.online` → 200 |
| Почта | Stalwart (прямая доставка по MX, без Postbox) | `openssl s_client -connect mail…:465` → LE-сертификат |
| VPN | AmneziaWG (UDP/443) | `awg show` → `latest handshake`, SSH только через туннель |
| Мессенджер | JAMS + coturn + OpenDHT + jami-services | `https://m.msp-claude.online` → 200 |
| Бэкапы | restic + метрики в Prometheus | Grafana → `MSPShield — Backups`, `restic_backup_success = 1` |

**Ключевые принципы, которые сэкономят вам день:**
1. Нигде не хардкодить имя сетевого интерфейса — оно меняется после перезагрузки (см. §3.1).
2. Изменения, которые могут отрезать доступ (SSH), применять **через VPN-туннель**, а не снаружи.
3. Тяжёлые сборки запускать только при наличии swap (§3.3).

---

## 1. Что подготовить заранее

| Что | Где взять | Зачем |
|---|---|---|
| OAuth-ключ Cloud.ru (`keyId`, `secret`) | консоль Cloud.ru → IAM | создание ВМ и управление ресурсами |
| SSH-ключ (публичная часть) | ваша станция `~/.ssh/id_ed25519_yc_new.pub` | доступ к ВМ |
| Локальный migration-кит | `migration/*.tar.gz` | восстановление данных |
| Доступ к DNS (Namecheap) | — | A-записи, DKIM/SPF/DMARC |
| Swaks/curl/openssl | на ВМ | проверки почты и TLS |

Получить токен Cloud.ru (живёт 1 час):
```bash
echo '{"keyId":"<KEY_ID>","secret":"<SECRET>"}' > /tmp/tok.json
curl -s -X POST https://iam.api.cloud.ru/api/v1/auth/token \
  -H 'Content-Type: application/json' --data-binary @/tmp/tok.json
# → {"access_token":"…"} — дальше везде Authorization: Bearer <token>
```

---

## 2. Ресурсы Cloud.ru

Скрипт-пример: [`cloudru-create-vm.sh`](../../migration/) · подробности API — в
[`CLOUDRU_RESOURCES.md`](../../migration/CLOUDRU_RESOURCES.md).

Порядок: **диск → ВМ → второй интерфейс (direct-IP) → публичный IP → SG**.

Особенности API (спотыкались все):
- создание ВМ принимает **массив**, а не объект;
- `disks: [{"disk_id": "…"}]`;
- SSH-ключ передаётся через `image_metadata` **простыми строками**:
  `{"public_key":"ssh-ed25519 …","name":"ubuntu","hostname":"msp-cloud-vm"}`;
- в SG правила добавляются отдельным вызовом `POST /api/v1/security-groups/{id}/rules`,
  а **читаются без `project_id`** (иначе `extra_forbidden`).

**Проверка:** `GET /api/v1/vms/{id}?project_id=…` → `state: "running"`.

Открыть в SG: 22 (потом закроем), 80, 443, 465, 993, 4190, 25, 3478, 5349, 4222,
49160-49250, **udp/443** (AmneziaWG).

---

## 3. Первичная настройка ВМ (делать ДО деплоя приложения)

Скрипты: [`cloudru-bootstrap.sh`](../../migration/cloudru-bootstrap.sh) (Docker/Caddy/Node 20/restic/ufw),
[`cloudru-fix-iface-name.sh`](../../migration/cloudru-fix-iface-name.sh), [`cloudru-fix-route-swap.sh`](../../migration/cloudru-fix-route-swap.sh).

### 3.1 Маршрутизация — и почему нельзя хардкодить имя интерфейса
У ВМ два интерфейса: внутренний (`enp3s0`, 10.0.0.6) и direct-IP. DHCP выдаёт **два
default-маршрута с одинаковой метрикой** → ответные пакеты уходят «не туда», соединения
рвутся: SSH и HTTP таймаутят, хотя сервисы слушают и firewall всё разрешает.

Фикс — приоритетный default через интерфейс с публичным IP:
```bash
IFACE=$(ip -4 -o addr show | awk -v ip=45.132.176.143 'index($4, ip"/")==1 {print $2; exit}')
GW=$(ip route | awk -v i="$IFACE" '$1=="default" && $5==i {print $3; exit}')
ip route replace default via "$GW" dev "$IFACE" metric 50
```
> ⚠️ **Имя интерфейса меняется после перезагрузки** (наблюдали `enp8s0` → `enp4s0`: имена
> зависят от порядка PCI). Поэтому ищем по IP. Симптом ошибки: служба `msp-policy-route`
> падает с `Cannot find device "enp8s0"`.

**Проверка:** `ip route get 8.8.8.8` → должен показать `dev <интерфейс с публичным IP>`.

### 3.2 HELO/имя хоста
Stalwart берёт **hostname ВМ** как HELO при исходящей доставке. Односложное имя
(`msp-cloud-vm`) — нарушение RFC 5321 и плюс к спам-скору. Делаем FQDN:
```bash
hostnamectl set-hostname mail.msp-claude.online
sed -i 's/^127\.0\.1\.1.*/127.0.1.1 mail.msp-claude.online mail/' /etc/hosts
```

### 3.3 Swap — обязателен
На инстансе 4 ГБ **без swap** сборка фронтенда уходит в thrash: процесс жив, но SSH не
отвечает, сборка не завершается. Один раз:
```bash
fallocate -l 4G /swapfile && chmod 600 /swapfile && mkswap /swapfile && swapon /swapfile
echo '/swapfile none swap sw 0 0' >> /etc/fstab && sysctl -w vm.swappiness=10
```

### 3.4 DNS для Docker — иначе сборки «висят»
Провайдер отдаёт в DHCP `8.8.4.4`/`8.8.8.8`, но **`8.8.8.8` из cloud.ru не отвечает**
(`1.1.1.1`, `77.88.8.8` работают). Docker раздаёт контейнерам нерабочий резолвер →
`pip install` висит до таймаута, Stalwart пишет `DNS error: Server Failure`.
```bash
python3 -c "import json;p='/etc/docker/daemon.json';d=json.load(open(p)) if __import__('os').path.exists(p) else {};d['dns']=['1.1.1.1','8.8.4.4'];json.dump(d,open(p,'w'),indent=2)"
systemctl restart docker
# ⚠️ Docker перезапустит ВСЕ контейнеры — после этого поднять прод-стек:
cd /opt/msp/Newbie/deploy/yandex && docker compose --profile mail up -d
```
Скрипт: [`cloudru-docker-dns-fix.sh`](../../migration/cloudru-docker-dns-fix.sh).

---

## 4. Деплой приложения и восстановление данных

1. Код: `git clone <repo> /opt/msp/Newbie` (или rsync с локальной машины).
2. Секреты: `deploy/yandex/.env`, `backend/.env` — из кита/секретов.
3. `docker compose --profile mail up -d` + стек мониторинга.
4. Восстановление данных: [`restore-on-vm.sh`](../../migration/restore-on-vm.sh) (Mongo, Vaultwarden, Stalwart, MAX).

**Проверка:** `curl -s localhost:8001/api/health` → `{"status":"ok","db":"connected"}`;
`docker compose ps` — все healthy.

---

## 5. TLS и сайт (Caddy)

Caddy сам выпускает сертификаты по HTTP-01. Важные детали (все проверены на практике):
- **A-запись должна существовать ДО** первого запуска Caddy, иначе ACME не пройдёт;
- глобальный блок `acme_ca https://acme-v02…` — иначе Caddy уйдёт на staging;
- `servers :443 { protocols h1 h2 }` — **отключаем HTTP/3**, потому что UDP/443 занят AmneziaWG;
- `header { -Server }` **в одну строку невалиден** — либо `header -Server`, либо многострочный блок.

**Проверка:** `curl -I https://msp-claude.online` → 200; сертификаты в
`/var/lib/caddy/.local/share/caddy/certificates/`.

---

## 6. Почта (Stalwart) — без Yandex Postbox

Главное отличие Cloud.ru: **порт 25 открыт в обе стороны**, поэтому внешний релей не нужен.

1. Удалить релей Postbox: `x:MtaRoute/set` → `destroy` для маршрута `BaseYandex`
   (конфиг Stalwart живёт в RocksDB; **env-переменные применяются только при первом запуске**).
2. TLS: импортировать сертификат Caddy в `x:Certificate` и **перезапустить** контейнер —
   без рестарта listener продолжает отдавать старый/self-signed.
   Скрипт: [`cloudru-mail-cert.sh`](../../migration/cloudru-mail-cert.sh).
3. DNS: 5 записей + PTR. Разбор — [`../../deploy/yandex/DNS_RECORDS.md`](../../deploy/yandex/DNS_RECORDS.md),
   пошагово для Namecheap — [`../../deploy/yandex/NAMECHEAP_DNS_SETUP.md`](../../deploy/yandex/NAMECHEAP_DNS_SETUP.md).
   > ⚠️ DKIM-RSA (420 символов) вставлять **одной строкой без кавычек**: если вписать
   > `"фрагмент1" "фрагмент2"`, панель сохранит пробел внутри base64 → `dkim=fail`.
4. Ящик `postmaster@` (RFC 5321) — [`cloudru-create-postmaster.sh`](../../migration/cloudru-create-postmaster.sh).
5. Логи Stalwart: по умолчанию путь `/var/log/stalwart/` в контейнере недоступен
   непривилегированному пользователю, и **логи не пишутся вообще**. Перевести на
   `/var/lib/stalwart/logs/` (том `stalwart-data`) — [`cloudru-stalwart-logs.sh`](../../migration/cloudru-stalwart-logs.sh).

**Проверка:** `openssl s_client -connect 127.0.0.1:465 -servername mail.msp-claude.online` → LE-сертификат;
письмо наружу доставляется; `nslookup -type=TXT v1-rsa-20260521._domainkey.msp-claude.online` — без пробелов.

**Спам:** при корректных SPF/DKIM/DMARC главный оставшийся фактор — **PTR**. Через API
Cloud.ru обратную зону создать не удалось (Evolution DNS API отвечает `Not Found`);
менять в консоли (**Evolution DNS → Обратные зоны**) или тикетом в поддержку.

---

## 7. VPN (AmneziaWG) и доступ по SSH только через туннель

Порядок **критичен**: сначала поднять туннель и убедиться, что SSH через него работает,
и только потом закрывать 22 снаружи.

1. Установка: `ppa:amnezia/ppa` → `amneziawg-dkms amneziawg-tools qrencode`.
2. Bootstrap сервера: [`awg_bootstrap.sh`](../../technical/0_Common/amneziawg/awg_bootstrap.sh)
   (`awg0` = 10.9.0.1/24, **UDP/443**, обфускация Jc/Jmin/Jmax/S1/S2/H1..H4).
3. Пир админа: [`cloudru-awg-add-admin-peer.sh`](../../migration/cloudru-awg-add-admin-peer.sh).
4. Клиент: [`../../migration/awg-admin.conf.example`](../../migration/awg-admin.conf.example) →
   `amneziawg.exe /installtunnelservice` (**файл без BOM!**).
5. Закрытие SSH: [`cloudru-ssh-lockdown-ufw.sh`](../../migration/cloudru-ssh-lockdown-ufw.sh) —
   ufw пускает 22 только из `10.9.0.0/24`; из SG удалить правило `tcp 22:22 from 0.0.0.0/0`.
6. `PostUp` AmneziaWG должен делать MASQUERADE **через интерфейс с публичным IP**
   (см. §3.1) — иначе VPN-клиенты не выйдут в интернет.

**Проверка:** `Test-NetConnection 45.132.176.143 -Port 22` → False; `ssh ubuntu@10.9.0.1` → работает.
**Аварийный доступ** — веб-консоль Cloud.ru (`is_serial_ready: true`).

---

## 8. Jami / JAMS

Полная процедура и 12 граблей — в [`JAMI_MIGRATION_CLOUDRU.md`](JAMI_MIGRATION_CLOUDRU.md).
Кратко: Caddy-блоки → coturn + dhtnode → JDK 26 + сборка JAMS → мастер установки
(свой CA + **`signingAlgorithm`!**) → jami-services → blueprint/группа → always-online демон.

Два места, где спотыкаются чаще всего:
- в `install/settings` **обязателен** `signingAlgorithm` (иначе создание пользователей → 500);
- фронтенд JAMS собирать из коммита `ee62171~1` (в `ee62171` MUI разъехался по мажорам).

**Проверка:** `https://m.msp-claude.online` → 200, вход админом, создание пользователя → 201.

---

## 9. Бэкапы и мониторинг

Скрипт: [`cloudru-backup-setup.sh`](../../migration/cloudru-backup-setup.sh)
(ставит [`restic-backup.sh`](../../migration/restic-backup.sh) в `/opt/restic-scripts`, создаёт
`/etc/restic/env.sh`, инициализирует репозиторий, делает первый бэкап, включает cron 03:00).

Метрики бэкапа уходят в Prometheus через node-exporter **textfile collector** — важно
писать именно в `/var/lib/node_exporter/textfile_collector` (именно этот каталог смонтирован
в контейнер). Дашборд `MSPShield — Backups` и 4 алерта уже есть в репозитории.

> Пока нет статических ключей Object Storage, репозиторий **локальный**
> (`/var/backups/restic`). Для off-site: создать бакет + статические ключи в консоли cloud.ru
> и заменить `RESTIC_REPOSITORY` в `/etc/restic/env.sh` на `s3:https://s3.cloud.ru/<bucket>`
> (OAuth-ключи API для S3 **не подходят** — нужны отдельные статические).

**Проверка:**
```bash
restic snapshots                                  # есть снапшот
cat /var/lib/node_exporter/textfile_collector/restic_backup.prom
curl -s 'http://127.0.0.1:9090/api/v1/query?query=restic_backup_success'   # значение 1
```
Grafana → папка MSPShield → **MSPShield — Backups**.

---

## 10. Приёмка (acceptance checklist)

- [ ] `https://msp-claude.online` → 200; `https://msp-claude.online/api/health` → `{"status":"ok"}`
- [ ] `https://vault.` → 200; вход в Vaultwarden
- [ ] `https://mon.` → 200; все таргеты Prometheus `up`
- [ ] `https://m.` → 200; создание пользователя JAMS → 201
- [ ] `openssl s_client -connect 127.0.0.1:465` → валидный LE-сертификат
- [ ] `nslookup -type=TXT v1-rsa-20260521._domainkey.msp-claude.online` → без пробелов
- [ ] `Test-NetConnection <IP> -Port 22` → False; `ssh ubuntu@10.9.0.1` → OK
- [ ] `restic snapshots` → снапшот; Grafana → Backups показывает успех
- [ ] `awg show` → `latest handshake`
- [ ] `ip route get 8.8.8.8` → интерфейс с публичным IP

---

## 11. Если что-то сломалось

| Симптом | Причина | Что делать |
|---|---|---|
| Сайт недоступен, сервисы слушают | два default-маршрута | §3.1, `ip route get 8.8.8.8` |
| `msp-policy-route failed: Cannot find device enp8s0` | интерфейс переименовался | перезапустить `msp-policy-route` (§3.1) |
| Сборка/`npm` висит, SSH не отвечает | нет swap / thrash | добавить swap (§3.3), проверить `free -m` |
| `pip` в сборке: `No matching distribution` | контейнерам раздан 8.8.8.8 | §3.4, `daemon.json` |
| JAMS: создание пользователя → 500 | нет `signingAlgorithm` | [`cloudru-jams-signfix.sh`](../../migration/cloudru-jams-signfix.sh) |
| JAMS UI: `theme.spacing is not a function` | MUI v9 vs `@mui/styles` v6 | [`cloudru-jams-frontend-rollback.sh`](../../migration/cloudru-jams-frontend-rollback.sh) |
| Письма в спаме | PTR не FQDN/не подтверждается | PTR в консоли Evolution DNS + тикет |
| Grafana: бэкапов нет | метрики в неверном textfile-каталоге | писать в `.../textfile_collector` |
| Потерян SSH | 22 закрыт, туннель упал | веб-консоль Cloud.ru, затем поднять `awg-quick@awg0` |

**Откат миграции:** старую ВМ не удалять до конца периода наблюдения; DNS возвращается
сменой A-записей; данные восстанавливаются из restic-репозитория (`restic restore latest --target /`).
