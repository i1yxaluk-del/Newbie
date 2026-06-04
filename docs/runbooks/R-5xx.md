# R-5xx — High 5xx Error Rate

| | |
|---|---|
| **Alert** | `HighErrorRate5xx` |
| **Severity** | P3 |
| **Expression** | `rate(mspshield_leads_rejected_total[5m]) > 0.1` for 5m |
| **Summary** | Высокий процент отклонений лидов на backend |

## Диагностика

1. `docker logs msp-backend-1 --tail 200 | grep -i error`
2. `curl -s http://backend:8080/metrics | grep rejected`
3. Проверить webhook URL и ключи в .env
4. Проверить доступность внешних API (MAX, Telegram)

## Устранение

1. Определить причину rejection в логах
2. Если webhook fail: проверить ADMIN_TOKEN / WEBHOOK_SECRET
3. Если внешнее API недоступно — эскалация
4. Добавить retry / dead letter если отсутствует
5. Мониторинг 15 мин
