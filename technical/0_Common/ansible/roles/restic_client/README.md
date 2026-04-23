# role: `restic_client`

> Ежедневные бэкапы на клиентских хостах (+ mongodump на landing). Репозиторий — Yandex Object Storage (s3-compatible), шифрование restic-паролем, retention 14d+4w+6m.

## Что делает

1. `apt install restic` (>=0.16)
2. `/etc/restic/env` из vault (`RESTIC_REPOSITORY`, `RESTIC_PASSWORD`, `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`)
3. Кладёт `/usr/local/bin/mspshield-backup.sh` (template) — делает snapshot `restic_paths` + retention
4. systemd timer `mspshield-backup.timer` (daily 02:30 + RandomizedDelaySec=30m)
5. Если есть mongo (landing) — дополнительно `mongodump` перед snapshot'ом

## Переменные

- `restic_repository` (vault)
- `restic_password` (vault)
- `restic_s3_key_id` (vault)
- `restic_s3_key_secret` (vault)
- `restic_paths` (list, default `["/etc", "/home", "/var/log"]`)
- `restic_include_mongodump` (bool, default false)

## Retention policy

`--keep-daily 14 --keep-weekly 4 --keep-monthly 6` — соответствует checklists/monthly.md.

## Smoke

`restic --repo <repo> snapshots | head -5` — показывает последний snapshot младше 24ч.
