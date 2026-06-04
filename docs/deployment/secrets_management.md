# Работа с секретами

Где хранятся ключи, пароли, токены — и как с ними работать, чтобы **ничего не утекло в git и не оказалось на диске в открытом виде**.

## Архитектура

Все сервисы работают на одной Yandex Cloud VM (внешний IP: `93.77.184.219`). Доступ — только через AmneziaWG туннель (`10.9.0.1`, UDP/443). SSH: `ssh -i ~/.ssh/id_ed25519_yc ubuntu@10.9.0.1`.

Два Docker-стека:
- **Приложение**: `/opt/msp/Newbie/deploy/yandex/` (сеть `msp_default`) — MongoDB, backend, Stalwart, Vaultwarden
- **Мониторинг**: `/opt/msp-monitoring/` (сеть `msp-monitoring`, 172.20.0.0/24) — Prometheus, Grafana, Alertmanager, exporters, max-alerter, telegram-webhook

## TL;DR

| Секрет | Где хранится | Примечание |
|--------|--------------|------------|
| SSH-ключ `id_ed25519_yc` | `~/.ssh/` на рабочей машине (Windows) | Доступ к VM только через AWG |
| `ADMIN_TOKEN` backend | `/opt/msp/Newbie/backend/.env` | SHA-256 хеш, 64 hex-символа |
| Stalwart admin password | Vaultwarden → Infrastructure | WebUI: `mail.msp-claude.online/admin` |
| Stalwart mail passwords (admin@, sales@, alert@) | Vaultwarden → Infrastructure | SMTP AUTH + IMAP |
| Postbox API key (ID + secret) | Vaultwarden → Infrastructure + Stalwart route | SMTP relay `postbox.cloud.yandex.net:465` |
| `ALERTMANAGER_WEBHOOK_TOKEN` | `/opt/msp-monitoring/.env` + backend `.env` | Bearer token для webhook receivers |
| `MAX_WEBHOOK_SECRET` | `/opt/msp-monitoring/.env` | Верификация входящих webhook |
| Telegram Bot token | `/opt/msp-monitoring/.env` | `@Alertmsp_bot` |
| Telegram group chat_id | `/opt/msp-monitoring/.env` | MSPShield Alerts group |
| MAX alerter phone + session | `/opt/msp-monitoring/max-session/max.db` | pymax userbot, интерактивная SMS-авторизация |
| MAX group chat_id | `/opt/msp-monitoring/.env` | Группа «Msptest» |
| Grafana admin password | `/opt/msp-monitoring/.env` (`GRAFANA_ADMIN_PASSWORD`) | Доступ: SSH tunnel → 127.0.0.1:3000 |
| Vaultwarden admin password | Vaultwarden → Infrastructure | Панель: `vault.msp-claude.online/admin` |
| Vaultwarden ADMIN_TOKEN (Argon2id) | `deploy/yandex/docker-compose.yml` | Argon2id хеш, НЕ plain text |
| Restic encryption password | Vaultwarden → Infrastructure | AES-256, шифрование бэкапов |
| Restic S3 keys (Yandex Object Storage) | Vaultwarden → Infrastructure | Бакет `mspshield-backups-prod` |
| Restic env | `/etc/restic/env.sh` на VM | S3 + пароль для cron-бэкапов |
| Restic backup script | `/opt/restic-scripts/backup.sh` | mongodump → restic → S3 |
| Backend `.env` | `/opt/msp/Newbie/backend/.env` | ADMIN_TOKEN + SMTP + все env vars |
| Vaultwarden CSV (18 entries) | `secrets/vaultwarden-import.csv` (локально, НЕ в git) + VM `/opt/msp/secrets/` | Для импорта в org MSPShield |

## Файлы секретов на VM

```
/opt/msp/Newbie/backend/.env          # backend: ADMIN_TOKEN, SMTP, env
/opt/msp-monitoring/.env              # мониторинг: все токены, chat_id
/opt/msp-monitoring/max-session/max.db # pymax session (SMS auth)
/etc/restic/env.sh                    # restic: S3 keys, encryption pw
/opt/msp/secrets/vaultwarden-import.csv # CSV для импорта (вне git)
```

## Запрещено

- **Коммитить в git** любой файл с реальными значениями токенов/паролей. GitHub push protection блокирует.
- **Хранить секреты в репозитории** — даже в `secrets/`. Файл `.gitignore` исключает `secrets/`.
- **Отправлять секреты через Telegram / MAX** (сохраняется в истории клиентского устройства).
- **Логгировать секреты** в прод-сервисах.
- **Пушить Argon2id хеш Vaultwarden ADMIN_TOKEN** — даже хеш считается секретом GitHub.

## Vaultwarden

Адрес: `vault.msp-claude.online` (через Caddy reverse proxy).

### Организация MSPShield

- Хранилище: **MSPShield**
- Коллекция: **Infrastructure** (создаётся при импорте CSV)
- Доступ: владелец org (admin)

### Структура коллекций

- **Infrastructure** — доступы к инфраструктуре (SSH, Grafana, Stalwart, бэкапы, API ключи, боты)
- **Clients / <client>** — пароли конкретного клиента (будущее)
- **Shared-Work** — маркетинг (Yandex.Метрика, Kaiten, email)

### Импорт CSV

Формат для организации (по официальной документации Bitwarden):

```csv
collections,type,name,notes,fields,reprompt,login_uri,login_username,login_password,login_totp
Infrastructure,login,Example,description,,0,https://example.com,user,password,
```

Ключевые требования:
- Заголовок: `collections,type,name,notes,fields,reprompt,login_uri,login_username,login_password,login_totp`
- Колонка `collections` (не `folder`, не `collection`) — для организации
- `reprompt` обязателен (0 = нет, 1 = требовать master password)
- При импорте: Хранилище = **MSPShield**, формат = **Bitwarden (csv)**
- Коллекции создаются автоматически из значений в `collections`

### Бэкапы Vaultwarden

Ежедневный `restic backup` volume `vaultwarden-data` → S3. Проверка — квартальный DR-drill.

## Мониторинг — потоки алёртов

```
Prometheus rules (P1/P2/P3)
  → Alertmanager :9093
    → email (Stalwart :25, AUTH=none, EHLO=msp-claude.online)
    → webhook → backend /api/alerts/alertmanager
    → webhook → max-alerter :9095
      → MAX group «Msptest» (pymax userbot)
      → Telegram MSPShield Alerts group (Bot API fallback)
```

### Alertmanager SMTP

- Relay: Stalwart `:25` (не Postbox `:465` — встроенный SMTP AM не поддерживает implicit TLS)
- AUTH: нет (EHLO hostname = `msp-claude.online` → Stalwart доверяет)
- From: `alert@msp-claude.online`, имя `MSPShield` (не «Alert» — триггерит спам-фильтры)

### Grafana SMTP

- Relay: Stalwart `:25` (AUTH=none, hostname=`msp-claude.online`)
- Сеть: Grafana подключена к `msp_default` для доступа к Stalwart

## Ротация секретов

| Секрет | Периодичность | Триггер ротации |
|--------|---------------|-----------------|
| `ADMIN_TOKEN` backend | 6 мес | Или при подозрении на утечку |
| `ALERTMANAGER_WEBHOOK_TOKEN` | 12 мес | `openssl rand -hex 32` → обновить в обоих `.env` |
| Telegram Bot token | По необходимости | Через @BotFather → revoke |
| MAX session | При истечении | `python3 auth.py --phone +79990703823 --session /opt/msp-monitoring/max-session/max.db` |
| Postbox API key | 6 мес | Новый ключ в YC → обновить Stalwart route |
| Restic encryption password | 12 мес | `restic key passwd` (требует старый пароль) |
| Restic S3 keys | 12 мес | Новый ключ в YC → `/etc/restic/env.sh` |
| Stalwart passwords | По необходимости | Через Stalwart WebUI или JMAP API |
| Grafana admin password | По необходимости | Через Grafana API или env var |
| SSH-ключ | 12 мес | `ssh-keygen -t ed25519` → обновить на VM `~/.ssh/authorized_keys` |
| AmneziaWG peer keys | 12 мес | Перегенерация конфига клиента |
| Vaultwarden admin password | По необходимости | Через `/admin` панель |

## DNS (Namecheap)

DNS управляется через Namecheap (НЕ Yandex Cloud DNS — платно).

| Запись | Тип | Значение |
|--------|-----|----------|
| `msp-claude.online` | A | `93.77.184.219` |
| `vault.msp-claude.online` | CNAME | `msp-claude.online` |
| `mail.msp-claude.online` | CNAME | `msp-claude.online` |
| `mon.msp-claude.online` | CNAME | `msp-claude.online` |
| `MX` | MX | `10 mail.msp-claude.online` |
| `_dmarc.msp-claude.online` | TXT | `v=DMARC1; p=none; rua=mailto:alert@msp-claude.online` |
| `msp-claude.online` | TXT | SPF (через Postbox include) |
| `stalwart._domainkey` | TXT | DKIM public key |

**TODO**: Обновить DMARC `p=none` → `p=quarantine` (DKIM alignment стабилен).

## Если секрет утёк в git

1. **Ротировать секрет** немедленно (создать новый, инвалидировать старый).
2. GitHub push protection заблокирует пуш — это защита, не ошибка.
3. Если репо публичный — считать прошлое значение скомпрометированным навсегда.

## Связанные документы

- [`landing_production.md`](landing_production.md) — деплой лендинга
- [`troubleshooting.md`](troubleshooting.md) — решение проблем
- [`disaster_recovery.md`](disaster_recovery.md) — восстановление после аварии
- [`../runbooks/README.md`](../runbooks/README.md) — каталог ранбуков
- [`../../services/max_alerter/`](../../services/max_alerter/) — MAX alerter код и auth.py
