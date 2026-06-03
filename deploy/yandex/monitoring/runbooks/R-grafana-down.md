# R-grafana-down — Grafana Down

| | |
|---|---|
| **Alert** | `GrafanaDown` |
| **Severity** | P2 |
| **Expression** | `probe_success{job="blackbox-internal", instance="http://grafana:3000/api/health"} == 0` for 3m |
| **Summary** | Grafana мониторинг недоступна более 3 минут |

## Диагностика

1. `docker ps | grep grafana`
2. `docker logs msp-grafana --tail 50`
3. `curl -s http://127.0.0.1:3000/api/health`
4. Проверить grafana_data volume

## Устранение

1. Рестарт: `cd /opt/msp-monitoring && docker compose restart grafana`
2. Если DB corruption: проверить volume `sudo ls /var/lib/docker/volumes/msp-grafana-data/_data/`
3. Переустановить CSS theme после рестарта
4. После: SSH tunnel + http://localhost:3000
