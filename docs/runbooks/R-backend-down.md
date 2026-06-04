# R-backend-down · Backend недоступен

| | |
|---|---|
| **Alert** | `BackendHealthFail` |
| **Severity** | P1 |
| **Expression** | `up{job="mspshield-backend"} == 0` for 2m |
| **Summary** | MSPShield backend /metrics недоступен более 2 минут |

## Диагностика

1. `docker ps | grep backend` — статус контейнера
2. `docker logs msp-backend-1 --tail 100` — причина падения
3. `curl -s http://127.0.0.1:8080/metrics` — ответ /metrics
4. `docker exec msp-mongo-1 mongosh --eval "db.runCommand({ping:1})"` — Mongo жива?

## Устранение

1. Если контейнер exited: `cd /opt/msp/Newbie/deploy/yandex && docker compose up -d backend`
2. Если Mongo down: `docker compose up -d mongo`
3. Если OOM Killed: увеличить memory limit в compose
4. Проверить ADMIN_TOKEN и .env
5. После рестарта: `curl -s http://backend:8080/metrics | head`
