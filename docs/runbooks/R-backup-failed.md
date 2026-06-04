# R-backup-failed · Бэкап завершился с ошибкой

| | |
|---|---|
| **Alert** | `BackupFailed` |
| **Severity** | P1 |
| **Expression** | `restic_backup_last_status == 0` for 5m |
| **Summary** | Последний restic-бэкап завершился с ошибкой |

## Диагностика

1. `sudo tail -100 /var/log/restic-backup.log`
2. Типовые причины:
   - **Auth** — IAM-ключи протухли → обновить `/etc/restic/env.sh`
   - **Network** — нет связи с S3 → `curl -I https://storage.yandexcloud.net`
   - **Disk** — закончилось место в `/tmp`
   - **Lock** — предыдущий запуск завис → `sudo bash -c 'source /etc/restic/env.sh && restic unlock'`

## Устранение

1. Устранить root cause (auth/network/disk/lock)
2. Перезапустить вручную: `sudo systemctl start restic-backup`
3. Проверить: `sudo journalctl -u restic-backup --since "5 min ago"`
4. Метрика обновится автоматически
