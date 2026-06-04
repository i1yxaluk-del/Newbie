# R-high-mem — High Memory

| | |
|---|---|
| **Alert** | `HighMemory` |
| **Severity** | P2 |
| **Expression** | `(1 - node_memory_MemAvailable_bytes / node_memory_MemTotal_bytes) > 0.95` for 10m |
| **Summary** | RAM >95% на node-01 в течение 10 минут |

## Диагностика

1. `free -h` — общее использование
2. `docker stats --no-stream` — по контейнерам
3. `ps aux --sort=-%mem | head -20` — топ процессов
4. `cat /proc/meminfo | grep -i slab` — kernel slab

## Устранение

1. Определить контейнер-нарушитель
2. Рестарт: `docker restart <name>`
3. Если Mongo — проверить `db.stats()`, при необходимости compact
4. Проверить limits в docker-compose.yml — установить memory limits
5. Мониторинг 15 мин
