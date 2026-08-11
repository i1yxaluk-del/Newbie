# R-node-down · Node Exporter недоступен

| | |
|---|---|
| **Alert** | `NodeDown` |
| **Severity** | P1 |
| **Expression** | `up{job="node"} == 0` for 3m |
| **Summary** | Node exporter не отвечает более 3 минут |

## Диагностика

1. SSH на node-01: `docker ps -a | grep node-exporter`
2. `systemctl status docker` — работает ли Docker
3. `uptime` — жив ли хост вообще
4. `dmesg | tail -50` — OOM / kernel panic

## Устранение

1. Если хост жив, Docker упал: `sudo systemctl restart docker`
2. Если node-exporter упал: `cd /opt/msp/Newbie/deploy/yandex/monitoring && docker compose up -d node-exporter`
3. Если хост недоступен — проверить статус VM в Yandex Cloud Console
4. После восстановления проверить http://127.0.0.1:9090 → targets → node

## Проверка

- Grafana → msp-vm dashboard
- Алёрт перешёл в resolved
- Если повторяется — эскалация
