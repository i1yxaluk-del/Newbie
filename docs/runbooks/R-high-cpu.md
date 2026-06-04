# R-high-cpu · CPU >90%

| | |
|---|---|
| **Alert** | `HighCPU` |
| **Severity** | P2 |
| **Expression** | `100 - avg by(instance)(rate(node_cpu_seconds_total{mode="idle"}[5m])) * 100 > 90` for 10m |
| **Summary** | CPU >90% на node-01 в течение 10 минут |

## Диагностика

1. `top -bn1 | head -20` — топ процессов
2. `docker stats --no-stream` — по контейнерам
3. `iotop` — IO wait?
4. Проверить cron задачи: `crontab -l`

## Устранение

1. Определить процесс-нарушитель через top/docker stats
2. Если контейнер: `docker logs <name> --tail 100`
3. Если утечка CPU: рестарт `docker restart <name>`
4. Если cron задача — дождаться завершения или убить
5. Мониторинг 15 мин, если повторяется — масштабировать VM
