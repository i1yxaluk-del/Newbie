# R-container-mem — Container High Memory

| | |
|---|---|
| **Alert** | `ContainerHighMemory` |
| **Severity** | P2 |
| **Expression** | `container_memory_working_set_bytes / container_spec_memory_limit_bytes > 0.9` for 5m |
| **Summary** | Контейнер использует >90% memory limit |

## Диагностика

1. `docker stats --no-stream` — текущее потребление
2. `docker inspect <name> --format='{{.HostConfig.Memory}}'` — limit
3. `docker logs <name> --tail 100` — leak indicators
4. Для Mongo: `db.stats()` и `db.currentOp()`

## Устранение

1. Увеличить memory limit в docker-compose.yml
2. Для Mongo: запустить compact на больших коллекциях
3. Для backend: проверить на leak в /metrics heap stats
4. Применить: `docker compose up -d <service>`
5. Мониторинг 30 мин
