# Migration Runbook — перенос MSPShield на новую VM

Короткий порядок переноса со старой VM на новую. Артефакты создаёт `migration/restic-backup.sh` (mongodump + тома с остановленными writer'ами).
Подробности и подводные камни: [`../../migration/README.md`](../../migration/README.md).

## 0. Пререквизиты

- Новая VM развёрнута по [DEPLOY_RUNBOOK.md](DEPLOY_RUNBOOK.md) **шаги 0–6** (без DNS switch и Stalwart-wizard), `preflight` → PRE-FLIGHT OK.
- `restic` на новой VM настроен (`/etc/restic/env.sh`, тот же S3-репозиторий).

## 1. Старая VM — снять артефакты

```bash
sudo bash /opt/restic-scripts/backup.sh
# артефакты: /opt/msp-backups/current/{mongodump.archive.gz, volumes/*.tar.gz} + restic-снапшот
sudo bash -c 'source /etc/restic/env.sh && restic snapshots --latest 1'
```

Скрипт сам останавливает vaultwarden/stalwart/max-alerter на время копии томов и поднимает их обратно.

> Урок 28.09: артефакты удобно сразу складывать плоско — `restore-on-vm.sh` умеет искать и в `volumes/`, но плоская раскладка исключает сюрпризы (см. §9.4).

## 2. Доставить артефакты на новую VM

```bash
# на новой VM:
sudo bash -c 'source /etc/restic/env.sh && restic restore latest --target /tmp/restore --path /opt/msp-backups/current'
sudo mkdir -p /tmp/migration/volumes
sudo cp -r /tmp/restore/opt/msp-backups/current/* /tmp/migration/
sudo ls -la /tmp/migration /tmp/migration/volumes
```

> Копирование из root-only каталогов — только `sudo sh -c 'cp ...'` (glob раскрывается в пользовательском шелле до sudo и молча не находит файлы — урок 28.09, §9.4).

## 3. Новая VM — восстановить

```bash
cd /opt/msp/Newbie
sudo MIGRATION_DIR=/tmp/migration bash migration/restore-on-vm.sh
```

Скрипт: mongo → `mongorestore --drop` → тома (`msp_vaultwarden-data`, `msp_stalwart-etc`, `msp_stalwart-data`) → `max-session` → стек → healthcheck (backend/AM/max-alerter).

> Скрипт сам ищет артефакты во всех типовых раскладках и падает, если том пустой после восстановления; после рестарта проверяет, что Stalwart не в bootstrap (урок 28.09, §9.4). Если что-то пропущено — в логе будет `ИТОГ: пропущено …` и `WARN`/`ERROR`.
>
> Контроль самостоятельно: `docker logs msp-stalwart-1 | grep -c 'bootstrap mode'` → `0`; `du -sh /var/lib/docker/volumes/msp_*` ≈ размер бэкапа.

## 4. MAX (если сессия протухла)

```bash
sudo docker exec -it msp-max-alerter python -m max_alerter.auth --authorize
# 1) ввести SMS-код; 2) если включён 2FA — ввести пароль MAX (ввод скрыт)
# неинтерактивно: MAX_SMS_CODE / MAX_PASSWORD в monitoring/.env (после использования — удалить)
```

Проверка без SMS: `sudo docker exec msp-max-alerter python -m max_alerter.auth` (exit 0 = сессия есть).

## 5. TLS Stalwart

Импортировать сертификаты Caddy для `mail.<domain>` (bind-mount `/var/lib/caddy → /etc/stalwart-certs`), либо настроить отдельный ACME.
Авто-ACME Stalwart (TLS-ALPN-01) недоступен — 443 занят Caddy.

## 6. DNS switch

У регистратора: `A` (@/mail/mon) → новый IP. SPF/DKIM/DMARC — проверить значения (SPF с `include:postbox.cloud.yandex.net`; для Postbox — TXT `postbox._domainkey`, иначе отправка получит `550 identity not verified`, §9.5).

**Сначала проверь TCP-доступность нового IP из целевой сети (из РФ)** — `nc -vz <IP> 22`; если TCP не проходит, а ICMP ок, меняй зарезервированный адрес, не переключай DNS (урок 28.09, §9.2).

## 7. Верификация

- Письмо внутрь: с Яндекса на `admin@<domain>` → появилось в ящике.
- Письмо наружу: из ящика на Gmail/Яндекс → доставлено, не в спаме.
- Тестовый P1-алерт → MAX + email (+ Telegram, если доступен с ВМ).
- `restic snapshots` на новой VM содержит новый снапшот.
- `sudo bash scripts/deployment/preflight.sh` → PRE-FLIGHT OK.

## 8. Старая VM

После подтверждения: остановить/удалить (грант/биллинг), проверить, что бэкапы ведутся с новой VM.


## 9. Журнал фактической миграции 28.09.2026 (новый YC-аккаунт)

Перенос выполнен 28.09.2026 на новую ВМ (`msp-cloud-vm`, публичный `130.193.49.21`, внутренний `10.128.0.25`). Ниже — все проблемы, с которыми столкнулись по ходу, и проверенные решения — дополнение к шагам выше для следующего переноса.

### 9.1 Инфраструктура / аккаунт

- **`key.json` нового аккаунта был невалидным** (посторонний текст `PLEASE DO NOT REMOVE…` перед PEM) → `yc` CLI не принимал профиль. Решение: валидный JSON-ключ сервисного аккаунта; проверять формат до автоматизации.
- **cloud-init на свежей ВМ падал**: apt ходил через IPv6-зеркала (недоступны), ufw мешал ранним этапам. Решение: пересоздать ВМ с исправленным cloud-init — `Acquire::ForceIPv4`, ufw не ставится на этапе bootstrap (настраивается позже явно).
- **Битый NodeSource-репозиторий** от cloud-init (недействительный gpg-ключ) ломал `apt-get update`. Решение: удалить `sources.list.d/nodesource.list` + ключ; Node 20 — тарболом в `/usr/local`, симлинки в `/usr/local/bin`.
- **На ВМ не было `unzip`** → распаковка репозитория падала. Решение: `apt-get install -y unzip` (добавить в cloud-init).

### 9.2 Сеть и доступ

- **Главная причина «сайт не работает»: зарезервированный IP `111.88.253.222` недостижим по TCP из РФ** (ICMP проходит, TCP — таймаут). Симптом: `ERR_CONNECTION_TIMED_OUT` у всех из России. Решение: новый зарезервированный адрес `130.193.49.21` (другой пул — доступен, проверено TCP 22/80/443), переключение NAT, DNS у Namecheap.
  - **Новый обязательный gate**: перед DNS switch — smoke-тест TCP-доступности нового публичного IP **из целевого региона** (из РФ). Если недоступен — пересоздавать адрес, не переключать DNS.
- Пока основной IP не отвечал, доступ был только через промежуточную ВМ-бастион (`msp-test`). После переключения на доступный IP бастион удалён — держать одну ВМ.
- В security group **не было UDP/443** для AmneziaWG. Решение: `msp-sg` += INGRESS UDP 443; в ufw — `allow 443/udp`; плюс ufw-правило SSH из `10.9.0.0/24`.

### 9.3 Развёртывание

- **Caddy от cloud-init стоял с заглушкой** (`:80 → respond 503 "provisioning"`) → сайт 503. Решение: боевой `deploy/yandex/Caddyfile`.
- **Caddyfile не стартовал без `MSP_DOMAIN`** (`server block without any key`) — для systemd-юнита нет env из compose. Решение: override `Environment=MSP_DOMAIN=msp-claude.online` (`/etc/systemd/system/caddy.service.d/override.conf`).
- **Фронтенд не был собран** (пустой webroot). Решение: `yarn install --frozen-lockfile && yarn build`, выкладка в `/var/www/landing`.

### 9.4 Данные (главная ловушка)

- **`restore-on-vm.sh` ожидает артефакты плоско в `MIGRATION_DIR`**, а в полном ките они лежат в `opt/msp-backups/current/` + `.../volumes/`. Без раскладки — тома молча не восстанавливаются.
- **Ловушка `sudo cp root-only/*.tar.gz`**: glob раскрывается в шелле пользователя, root-only каталог не читается — копирование молча падает. Копировать так: `sudo sh -c 'cp .../volumes/*.tar.gz /tmp/migration/'`.
- **Пустой том `stalwart-etc` + `stalwart-data` → Stalwart стартует в bootstrap-режиме** («No configuration file found. Port 8080 open for initial setup»). Важно понимать: `config.json` — только указатель на RocksDB (`/var/lib/stalwart`), вся конфигурация (маршруты, ящики) — в `stalwart-data`. Восстанавливать **оба тома**, иначе bootstrap.
- Проверка после восстановления: размеры томов (`du -sh`) ≈ бэкап; в логе Stalwart нет «bootstrap mode»; Vaultwarden открывает сохранённые аккаунты.

### 9.5 Почта / Postbox

- **При смене аккаунта Postbox ключи и домен не переносятся**: старый API-ключ не работает, идентичность требует повторной верификации. Заново: создать API-ключ (`yc iam api-key create … --scope yc.postbox.send`), обновить `POSTBOX_API_KEY_*` в deploy `.env` и `SMTP_AUTH_*` / `SMTP_*` / `GF_SMTP_*` в monitoring `.env`, перезапустить Stalwart / Alertmanager / Grafana.
- **DKIM у Postbox — через CNAME-делегирование, не TXT** (проверено 28.09): в консоли Postbox (страница адреса → «Email signature configuration (DKIM)») публикуются записи вида `egtn...-1._domainkey.<домен> → egtn...-1.dkim.pstbx.ru` (и `-2`). TXT `postbox._domainkey` у нового Postbox нет — не искать его (частая ошибка диагностики).
- Пока домен не verified — Postbox отклоняет отправку: `550 "identity not verified"`.
- **Маршрут Stalwart `postbox-outbound` не обновляется при смене `deploy/.env`** — после восстановления БД из бэкапа в нём остаются креды СТАРОГО аккаунта; письма молча копятся в очереди с `535 Authentication failed`. Диагностика и лечение — §9.9.
- Быстрая проверка ключей: python-smtplib login на `postbox.cloud.yandex.net:465` (без отправки письма).

### 9.6 Бэкапы / restic

- **restic не был установлен** на свежей ВМ (`apt-get install -y restic`).
- **Креды restic привязаны к аккаунту**: старый `AWS_ACCESS_KEY_ID` даёт `SignatureDoesNotMatch` на новый бакет. Создать новый статический ключ SA `restic-backup` (`yc iam access-key create`), обновить `/etc/restic/env.sh`, `restic init` в новом бакете, проверить `restic snapshots` + тестовый снапшот, вернуть cron/timer (03:30).

### 9.7 AmneziaWG

- **Amnezia PPA «not signed»** после переноса gpg-ключа: ключ должен лежать в `/etc/apt/trusted.gpg.d/`, и в `.list` не должно быть лишнего `signed-by`. Только после этого ставится `amneziawg` / `amneziawg-tools`.
- **Клиентские конфиги привязаны к IP сервера**: серверные ключи сохранили, поэтому достаточно заменить `Endpoint` на новый IP — клиентам обновить один туннель. Новый конфиг: `migration/awg-admin.conf`.
- После восстановления сервера: `awg-quick@awg0` enabled, `net.ipv4.ip_forward=1`, PostUp-MASQUERADE на eth0, ufw allow 443/udp + SSH из `10.9.0.0/24`.

### 9.8 Обновление gate «до DNS switch» (по итогам)

Добавить в проверки перед переключением DNS:
- [ ] TCP-доступность нового IP из целевого региона (22/80/443);
- [ ] `du -sh` восстановленных томов ≈ размер до бэкапа; Stalwart не в bootstrap;
- [ ] `curl https://<domain>/api/health` — ok (локально, до DNS);
- [ ] `restic snapshots` в новом бакете — ok; cron/timer на месте;
- [ ] DKIM TXT опубликован, домен в Postbox «verified» (иначе письма не уйдут).

### 9.9 Очередь Stalwart: письма копятся, наружу не уходят (535 Authentication failed)

Симптом: письма из ящиков (`admin@`/`sales@`) не доходят; `docker logs msp-stalwart-1` пуст (в этом конфиге логирование в stdout выключено). Реальная причина видна только в очереди: Postbox отвечает `535 Authentication failed` — маршрут с устаревшими кредами.

Управляющая учётка Stalwart — **`admin` (без домена!)**, пароль — `STALWART_ADMIN_PASSWORD` из `deploy/yandex/.env`. Логин `admin@<домен>` — обычный ящик; на `x:*-методах` он получает `forbidden`.

```bash
PW=$(grep '^STALWART_ADMIN_PASSWORD=' /opt/msp/Newbie/deploy/yandex/.env | cut -d= -f2-)

# 1) Очередь — по каждому получателю видна последняя ошибка:
curl -s -u "admin:$PW" -H 'Content-Type: application/json' \
  -d '{"using":["urn:ietf:params:jmap:core","urn:stalwart:jmap"],"methodCalls":[["x:QueuedMessage/get",{},"0"]]}' \
  http://127.0.0.1:8080/jmap/

# 2) Маршрут — найти id у name=postbox-outbound:
curl -s -u "admin:$PW" -H 'Content-Type: application/json' \
  -d '{"using":["urn:ietf:params:jmap:core","urn:stalwart:jmap"],"methodCalls":[["x:MtaRoute/get",{},"0"]]}' \
  http://127.0.0.1:8080/jmap/

# 3) Обновить креды маршрута на актуальный Postbox-ключ (POSTBOX_API_KEY_ID/SECRET из deploy/.env):
curl -s -u "admin:$PW" -H 'Content-Type: application/json' \
  -d '{"using":["urn:ietf:params:jmap:core","urn:stalwart:jmap"],"methodCalls":[["x:MtaRoute/set",{"update":{"<ROUTE_ID>":{"authUsername":"<KEY_ID>","authSecret":{"@type":"Value","secret":"<SECRET>"}}}},"0"]]}' \
  http://127.0.0.1:8080/jmap/

# 4) ОБЯЗАТЕЛЬНО перезапустить Stalwart — маршрут применяется только после рестарта:
sudo docker restart msp-stalwart-1
```

Проверка: письмо с `admin@` на `check-auth@verifier.port25.com`; через пару минут в ящик `admin@` вернётся автоотчёт с результатами SPF/DKIM/DMARC. Зависшие ранее письма до-отправятся на ближайших retry.
