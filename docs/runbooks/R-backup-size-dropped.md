# R-backup-size-dropped · Размер бэкапа упал >50%

| | |
|---|---|
| **Alert** | `BackupSizeDropped` |
| **Severity** | P2 |
| **Expression** | `restic_backup_size_bytes < avg_over_time(restic_backup_size_bytes[7d]) * 0.5` for 15m |
| **Summary** | Размер бэкапа упал более чем на 50% от среднего за 7 дней |

## Диагностика

1. `sudo bash -c 'source /etc/restic/env.sh && restic snapshots --latest 5'`
2. Проверить excludes: `sudo cat /opt/restic-scripts/excludes.txt`
3. Проверить что бэкапимые директории на месте: `df -h /opt /var/www /etc`
4. Возможно: Docker volume отвалился → часть данных не видна

## Устранение

1. Проверить `/opt/restic-scripts/backup.sh` — BACKUP_PATHS актуальны?
2. Проверить что Docker volumes смонтированы: `docker volume ls`
3. Добавить пропущенные пути в backup.sh
4. Запустить вручную: `sudo systemctl start restic-backup`
