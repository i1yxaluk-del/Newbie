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

## 2. Доставить артефакты на новую VM

```bash
# на новой VM:
sudo bash -c 'source /etc/restic/env.sh && restic restore latest --target /tmp/restore --path /opt/msp-backups/current'
sudo mkdir -p /tmp/migration/volumes
sudo cp -r /tmp/restore/opt/msp-backups/current/* /tmp/migration/
sudo ls -la /tmp/migration /tmp/migration/volumes
```

## 3. Новая VM — восстановить

```bash
cd /opt/msp/Newbie
sudo MIGRATION_DIR=/tmp/migration bash migration/restore-on-vm.sh
```

Скрипт: mongo → `mongorestore --drop` → тома (`msp_vaultwarden-data`, `msp_stalwart-etc`, `msp_stalwart-data`) → `max-session` → стек → healthcheck (backend/AM/max-alerter).

## 4. MAX (если сессия протухла)

```bash
sudo docker exec -it msp-max-alerter python -m max_alerter.auth --authorize
# SMS на +79990703823 → ввести код
```

Проверка без SMS: `sudo docker exec msp-max-alerter python -m max_alerter.auth` (exit 0 = сессия есть).

## 5. TLS Stalwart

Импортировать сертификаты Caddy для `mail.<domain>` (bind-mount `/var/lib/caddy → /etc/stalwart-certs`), либо настроить отдельный ACME.
Авто-ACME Stalwart (TLS-ALPN-01) недоступен — 443 занят Caddy.

## 6. DNS switch

У регистратора: `A` (@/mail/mon) → новый IP. SPF/DKIM/DMARC — проверить значения (SPF с `include:postbox.cloud.yandex.net`).

## 7. Верификация

- Письмо внутрь: с Яндекса на `admin@<domain>` → появилось в ящике.
- Письмо наружу: из ящика на Gmail/Яндекс → доставлено, не в спаме.
- Тестовый P1-алерт → MAX + email (+ Telegram, если доступен с ВМ).
- `restic snapshots` на новой VM содержит новый снапшот.
- `sudo bash scripts/deployment/preflight.sh` → PRE-FLIGHT OK.

## 8. Старая VM

После подтверждения: остановить/удалить (грант/биллинг), проверить, что бэкапы ведутся с новой VM.
