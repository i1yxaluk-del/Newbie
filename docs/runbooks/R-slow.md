# R-slow — Service Slow Response

| | |
|---|---|
| **Alert** | `ServiceSlowResponse` |
| **Severity** | P3 |
| **Expression** | `probe_duration_seconds{job=~"blackbox-http|blackbox-internal"} > 3` for 5m |
| **Summary** | Внутренний сервис отвечает >3 секунд более 5 минут |

## Диагностика

1. `docker stats --no-stream` — нагрузка по контейнерам
2. `curl -sw '%{time_total}' <service_url>` — замер
3. `docker logs <name> --tail 30` — ошибки
4. `iostat 1 5` — IO wait на хосте

## Устранение

1. Если IO wait: проверить restic backup не запущен ли
2. Если CPU: смотреть R-high-cpu
3. Рестарт тяжёлого контейнера: `docker restart <name>`
4. Масштабировать VM если постоянно
5. Мониторинг 15 мин
