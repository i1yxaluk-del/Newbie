# Работа с секретами

Где хранятся ключи, пароли, токены — и как с ними работать, чтобы **ничего не утекло в git и не оказалось на диске в открытом виде**.

## TL;DR

| Секрет | Где хранится | Кто имеет доступ |
|--------|--------------|------------------|
| SSH-ключи владельца (личные) | `~/.ssh/` на личной машине | Только владелец |
| WireGuard peer-keys (клиентов) | `/etc/wireguard/tenants/<client>.conf` на bastion | `root` на bastion |
| `ADMIN_TOKEN` backend | `/etc/mspshield/backend.env` (chmod 600) | `root` на landing-VM |
| `TG_BOT_TOKEN` | `/etc/mspshield/backend.env` + `/etc/alertmanager/tg_bot_token` | `root` |
| `MAX_BOT_TOKEN` | `/etc/mspshield/backend.env` (бот из `@MasterBot` MAX) | `root` |
| `MAX_WEBHOOK_SECRET` | `/etc/mspshield/backend.env` (верификация `X-Max-Bot-Api-Secret`) | `root` |
| `ALERTMANAGER_WEBHOOK_TOKEN` | `/etc/mspshield/backend.env` + `/etc/alertmanager/max_webhook_token` | `root` |
| `SMARTCAPTCHA_SERVER_KEY` | `/etc/mspshield/backend.env` | `root` |
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

## Vaultwarden (self-hosted Bitwarden)

Разворачивается как отдельный docker-compose на bastion. Конфиг: [`../../deploy/vaultwarden/`](../../deploy/vaultwarden/).

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

Ежедневный `restic backup /opt/vaultwarden/data/` в отдельный S3-бакет `mspshield-vaultwarden-backup`. Проверка — квартальный DR-drill.

## Ротация секретов

| Секрет | Периодичность | Триггер ротации |
|--------|---------------|-----------------|
| `ADMIN_TOKEN` backend | Каждые 6 мес | Или при любом подозрении |
| `TG_BOT_TOKEN` | По необходимости | При увольнении Junior (если у него был доступ к чату) |
| `MAX_BOT_TOKEN` | По необходимости | При увольнении Junior, при компрометации webhook'а |
| `ALERTMANAGER_WEBHOOK_TOKEN` | 12 мес | При увольнении Junior — `openssl rand -hex 32` в `backend/.env` + `/etc/alertmanager/max_webhook_token` |
| WireGuard peer-keys клиента | 12 мес | Или по договорённости с клиентом |
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
