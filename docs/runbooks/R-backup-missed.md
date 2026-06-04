# R-backup-missed — Backup Missed 24h

| | |
|---|---|
| **Alert** | `BackupMissed24h` |
| **Severity** | P1 |
| **Expression** | `(time() - restic_backup_last_timestamp_seconds) > 93600` for 10m |
| **Summary** | Бэкап не запускался более 26 часов |

## Диагностика

1. `systemctl status restic-backup.timer`
2. `sudo journalctl -u restic-backup --since "26 hours ago"`
3. `sudo systemctl list-timers | grep restic`
4. Проверить что timer enabled: `sudo systemctl is-enabled restic-backup.timer`

## Устранение

1. Если timer disabled: `sudo systemctl enable --now restic-backup.timer`
2. Запустить вручную: `sudo systemctl start restic-backup`
3. Проверить: `sudo systemctl status restic-backup`
4. Проверить метрику обновилась в Prometheus
