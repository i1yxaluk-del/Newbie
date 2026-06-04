# R-container-down · Контейнер не работает

| | |
|---|---|
| **Alert** | `ContainerDown` |
| **Severity** | P1 |
| **Expression** | `absent(container_last_seen) or time() - container_last_seen > 120` for 3m |
| **Summary** | Контейнер не виден в cAdvisor более 2 минут |

## Диагностика

1. `docker ps -a` — статус всех контейнеров
2. `docker logs <name> --tail 50` — причина падения
3. `docker inspect <name> --format='{{.State}}'`
4. Проверить OOM: `dmesg | grep -i oom`

## Устранение

1. Если exited: `docker start <name>` или `docker compose up -d <service>`
2. Если OOM Killed: увеличить memory limit
3. Если restart loop: смотреть R-restart-loop
4. Проверить зависимости (mongo, network)
5. После рестарта: `docker ps | grep <name>`
