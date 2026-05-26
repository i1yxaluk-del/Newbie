# Работа с секретами

Где хранятся ключи, пароли, токены — и как с ними работать, чтобы **ничего не утекло в git и не оказалось на диске в открытом виде**.

## TL;DR

| Секрет | Где хранится | Кто имеет доступ |
|--------|--------------|------------------|
| SSH-ключи владельца (личные) | `~/.ssh/` на личной машине | Только владелец |
| AmneziaWG peer-keys (клиентов) | `/etc/amnezia/amneziawg/tenants/<client>.conf` на bastion | `root` на bastion |
| `ADMIN_TOKEN` backend | `/etc/mspshield/backend.env` (chmod 600) | `root` на landing-VM |
| `TG_BOT_TOKEN` | `/etc/mspshield/backend.env` + `/etc/alertmanager/tg_bot_token` | `root` |
| `MAX_BOT_TOKEN` | `/etc/mspshield/backend.env` (бот из `@MasterBot` MAX) | `root` |
| `MAX_WEBHOOK_SECRET` | `/etc/mspshield/backend.env` (верификация `X-Max-Bot-Api-Secret`) | `root` |
| `ALERTMANAGER_WEBHOOK_TOKEN` | `/etc/mspshield/backend.env` + `/etc/alertmanager/max_webhook_token` | `root` |
| `SMARTCAPTCHA_SERVER_KEY` | `/etc/mspshield/backend.env` | `root` |
| `POSTBOX_API_KEY_ID` + `POSTBOX_API_KEY_SECRET` (Yandex Cloud Postbox — outbound SMTP smarthost для Stalwart) | `/etc/mspshield/backend.env` + Stalwart route config (`/etc/stalwart/`); см. [`deploy/yandex/STALWART_RELAY_MODE.md`](../../deploy/yandex/STALWART_RELAY_MODE.md) §2 · Вариант A | `root` |
| Restic S3-ключи (клиент → бэкап бакет) | `/etc/restic/env` на каждом клиентском хосте (chmod 600) | `root` |
| Пароли клиентов (RDP, админки, сайтов) | **Vaultwarden** на bastion | Владелец + Junior (после приёма на работу) |
| Terraform state | S3-бакет `mspshield-tfstate` (зашифрован на стороне Yandex Object Storage) | Владелец |
| Yandex Cloud ключ (terraform, restic) | `~/.yc/` на личной машине + сервис-аккаунты в Terraform | Владелец |
| `.env` для локального dev | `backend/.env` (в `.gitignore`) | Только владелец на своей машине |

## Запрещено

- **Коммитить в git** любой файл, содержащий строки вида `TOKEN`, `PASSWORD`, `SECRET`, `PRIVATE KEY`, `ADMIN_TOKEN=<значение>`.
- **Отправлять секреты через Telegram / MAX** (даже в личку — сохраняется в истории клиентского устройства).
- **Хранить пароли клиентов в Excel/Google Docs** — только Vaultwarden.
- **Логгировать секреты** в прод-сервисах (проверять `grep -r SECRET /var/log/`).
- **Давать Junior полный доступ к Vaultwarden** — только конкретные коллекции после подписания NDA (см. `contracts/junior_nda.md` при его создании).

## Vaultwarden (бесплатная open-source альтернатива Bitwarden Cloud)

Vaultwarden — это **отдельный проект** (`github.com/dani-garcia/vaultwarden`,
лицензия AGPL-3.0), написанный с нуля на Rust и **полностью API-совместимый**
с серверами Bitwarden. Поэтому:

- **Бесплатно и навсегда** — никаких подписок, никаких лимитов по
  пользователям/Collections (в Bitwarden Cloud Free лимит — 2 человека
  на Organization).
- **Все «платные» фичи Bitwarden включены by-default**: Organizations,
  Collections, **Bitwarden Send** (одноразовая передача секрета с TTL
  и опциональным паролем), 2FA (TOTP/FIDO2/YubiKey), attachments,
  Emergency Access, audit log в `/admin`.
- **Клиенты — родные Bitwarden** (desktop, mobile, browser extensions);
  меняется только `Server URL` в настройках → `https://vault.msp-claude.online`.
- **SaaS-стоимость для нашей команды:** на Bitwarden Cloud Teams = $4/user/мес
  ≈ $20/мес для 5 человек ≈ $240/год. Наш Vaultwarden на отдельной VM
  Yandex Cloud ≈ **300-450 ₽/мес = $3-5/мес**, окупается уже на двух
  пользователях.

Разворачивается как отдельный docker-compose на bastion. Конфиг:
[`../../deploy/vaultwarden/`](../../deploy/vaultwarden/).

### Первый запуск

```bash
ssh ubuntu@mspshield-bastion
cd /opt/vaultwarden
# Отредактировать .env (ADMIN_TOKEN для панели админа, SMTP для восстановления пароля)
sudo docker compose up -d
```

Открыть через SSH-туннель (НЕ пускать Vaultwarden в публичный интернет):

```bash
# На своей машине:
ssh -L 8443:localhost:8443 ubuntu@<bastion_public_ip>
# В браузере: http://localhost:8443
```

### Структура коллекций

- **MSPShield / Personal** — личные пароли владельца (только он).
- **MSPShield / Clients / <client>** — пароли конкретного клиента (владелец + Junior после доступа).
- **MSPShield / Infra** — доступы к Yandex Cloud, DNS-регистратору, бухгалтерии (только владелец).
- **MSPShield / Shared-Work** — то, что супруга использует в маркетинге (Yandex.Метрика, Kaiten, email).

### Бэкапы Vaultwarden

Ежедневный `restic backup /var/lib/docker/volumes/msp_vaultwarden-data/_data/` в отдельный S3-бакет `mspshield-vaultwarden-backup`. Проверка — квартальный DR-drill.

## Ротация секретов

| Секрет | Периодичность | Триггер ротации |
|--------|---------------|-----------------|
| `ADMIN_TOKEN` backend | Каждые 6 мес | Или при любом подозрении |
| `TG_BOT_TOKEN` | По необходимости | При увольнении Junior (если у него был доступ к чату) |
| `MAX_BOT_TOKEN` | По необходимости | При увольнении Junior, при компрометации webhook'а |
| `ALERTMANAGER_WEBHOOK_TOKEN` | 12 мес | При увольнении Junior — `openssl rand -hex 32` в `backend/.env` + `/etc/alertmanager/max_webhook_token` |
| `POSTBOX_API_KEY_*` (Yandex Cloud) | 6 мес | При увольнении сотрудника с доступом, при компрометации, при смене service account: создать новый API key в YC консоли → обновить `backend/.env` → пересоздать Stalwart route (`stalwart-cli mta route update postbox-outbound …`) → инвалидировать старый ключ |
| AmneziaWG peer-keys клиента | 12 мес | Или по договорённости с клиентом |
| Restic S3-ключи | Каждые 12 мес | — |
| SSH-ключи Junior | При уходе / повышении | См. [`../../technical/0_Common/scripts/rotate_junior_access.sh`](../../technical/0_Common/scripts/rotate_junior_access.sh) |
| Пароли в Vaultwarden | По ситуации | При компрометации / уходе сотрудника |

## Если секрет уже утёк в git

Немедленно:

1. **Ротировать сам секрет** (создать новый, инвалидировать старый у провайдера).
2. `git filter-repo --invert-paths --path <файл>` → force-push (координируя с тем, кто ещё работает с репо).
3. Если репо публичный — считать, что прошлое значение скомпрометировано **навсегда**. Нет смысла пытаться «удалить из истории».

Для защиты от случайных коммитов — `pre-commit` хук с `detect-secrets` или `gitleaks`. Поставить локально:

```bash
pip install pre-commit detect-secrets
pre-commit install
```

## Связанные документы

- [`../../contracts/wife_nda.md`](../../contracts/wife_nda.md) — что супруга подписывает про доступ к клиентским данным.
- Junior NDA появится в спринте 11 Этапа 4.
- [`../../technical/0_Common/scripts/rotate_junior_access.sh`](../../technical/0_Common/scripts/rotate_junior_access.sh) — автоматизация ротации.
