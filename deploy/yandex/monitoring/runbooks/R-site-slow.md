# R-site-slow — Site Slow Response

| | |
|---|---|
| **Alert** | `SiteSlowResponse` |
| **Severity** | P3 |
| **Expression** | `probe_duration_seconds{job=~"blackbox-http.*"} > 5` for 5m |
| **Summary** | Сайт отвечает >5 секунд более 5 минут |

## Диагностика

1. `curl -sw '%{time_total}' -o /dev/null https://msp-claude.online` — время ответа
2. `docker stats --no-stream` — CPU/IO нагрузка
3. `docker logs msp-caddy --tail 30` — Caddy upstream timing
4. `iostat 1 5` — IO wait

## Устранение

1. Высокий IO: проверить backup/restic не запущен ли
2. Высокий CPU: смотреть R-high-cpu
3. Caddy proxy timeout: проверить upstream response time
4. Если временная — дождаться завершения
5. Если постоянная — масштабировать VM
