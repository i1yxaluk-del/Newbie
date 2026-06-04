# R-backup-long — Backup Running Too Long

| | |
|---|---|
| **Alert** | `BackupInProgress` |
| **Severity** | P3 |
| **Expression** | `restic_backup_last_status == 2` for 30m |
| **Summary** | Бэкап выполняется более 30 минут |

## Диагностика

1. `sudo journalctl -u restic-backup --since "30 min ago" -f`
2. `sudo systemctl status restic-backup`
3. Проверить IO: `iostat 1 3`
4. Проверить network to S3: `curl -w '%{time_total}' -o /dev/null https://storage.yandexcloud.net`

## Устранение

1. Если IO bottleneck — дождаться (nighttime backup)
2. Если завис: `sudo systemctl kill restic-backup` затем `sudo bash -c 'source /etc/restic/env.sh && restic unlock'`
3. Перезапустить: `sudo systemctl start restic-backup`
4. Если постоянно — увеличить TimeoutStartSec в systemd unit
