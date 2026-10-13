# matrix_alerter — уведомления Alertmanager в Element X

Production webhook: Alertmanager → `msp-matrix-alerter:9096/alert` → сообщения от
пользователя **alert** (Matrix) в его личные чаты (куда добавлены ilya и admin).

## Как это работает

1. Prometheus-правила (Grafana-стек) → **Alertmanager**.
2. Маршруты Alertmanager дублируют алерты (P1/P2/P3) в receiver `matrix-alert`.
3. `matrix-alerter` логинится как пользователь `alert` (MAS compat login), кэширует
   токен и шлёт сообщения в комнаты из `MATRIX_ALERT_ROOMS` (при 401 — перелогин).
4. В Element X у ilya и admin это личный чат с контактом «MSPShield Alert».

## Деплой (VM)

```bash
cd /opt/msp/Newbie/deploy/yandex/monitoring
sudo docker compose up -d --build matrix-alerter alertmanager
```

## Переменные (monitoring/.env, вне Git)

- `MATRIX_ALERT_USER` — пользователь-бот (по умолчанию `alert`).
- `MATRIX_ALERT_PASSWORD` — его пароль (генерируется при создании).
- `MATRIX_ALERT_ROOMS` — комнаты-получатели через запятую (`!id:server`).
- `ALERTMANAGER_WEBHOOK_TOKEN` — Bearer-токен вебхука (тот же, что у MAX-алертера).

## Проверка

```bash
curl -fsS http://127.0.0.1:9096/health
curl -X POST http://127.0.0.1:9093/api/v2/alerts -H 'Content-Type: application/json' \
  -d '[{"labels":{"alertname":"Test","severity":"P2"},"annotations":{"summary":"Проверка"}}]'
sudo docker logs msp-matrix-alerter --tail 50
```
