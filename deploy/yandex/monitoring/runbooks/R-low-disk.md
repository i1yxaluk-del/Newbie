# R-low-disk — Low Disk Space

| | |
|---|---|
| **Alert** | `LowDisk` |
| **Severity** | P2 |
| **Expression** | `(node_filesystem_avail_bytes / node_filesystem_size_bytes) < 0.1` for 15m |
| **Summary** | Свободное место на диске <10% |

## Диагностика

1. `df -h` — по разделам
2. `du -sh /var/lib/docker/volumes/*` — Docker volumes
3. `du -sh /var/log/*` — логи
4. `docker system df` — Docker disk usage

## Устранение

1. Очистить Docker: `docker system prune -af --volumes` (ВНИМАНИЕ: удалит unused volumes)
2. Удалить старые логи: `journalctl --vacuum-size=100M`
3. Проверить restic-бэкапы не занимают ли локально
4. Увеличить диск YC если >80% постоянно
