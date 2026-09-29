# 19. SMTP, DNS и Stalwart/Postbox

> **Учебная ситуация.** Письма принимаются локально, но наружу копятся с 535.

## Главное

SMTP envelope MAIL FROM/RCPT TO управляет доставкой и отличается от видимых From/To headers. Relay требует authentication и policy.

MX указывает принимающий host; SPF разрешает senders; DKIM подписывает письмо; DMARC задаёт policy и alignment. В Postbox DKIM публикуется CNAME из консоли.

Stalwart хранит route секрет доступаs в собственной БД. Восстановление старой БД может вернуть старый ключ, даже если `.env` обновлён. Очередь JMAP показывает реальную 535.

## Как это работает

Stalwart принимает local mail и/или отправляет через Postbox relay. Route секрет доступаs могут жить в восстановлениеd RocksDB, поэтому environment не является единственным source. JMAP queue показывает recipient-level last error. После route update restart нужен, чтобы runtime перечитал состояние.

## Пример

```bash
curl -s -u "admin:$PW" -H 'Content-Type: application/json' \
 -d '{"using":["urn:ietf:params:jmap:core","urn:stalwart:jmap"],"methodCalls":[["x:QueuedMessage/get",{},"0"]]}' \
 http://127.0.0.1:8080/jmap/
```

## Практикум

1. Проверьте DNS records.
2. Получите очередь JMAP.
3. Обновите route на тестовом стенде и restart Stalwart.

## Если что-то не работает

| Наблюдение | Что это означает | Следующая проверка |
|---|---|---|
| 535 | секрет доступа/identity, не сетевой timeout. |
| Bootstrap mode | не восстановлен `stalwart-data` или `stalwart-etc`. |

## Источники проекта

- [docs/deployment/MIGRATION_RUNBOOK.md](https://github.com/i1yxaluk-del/Newbie/blob/89249e43a4e8b2e90d562307ef244ba95288c64c/docs/deployment/MIGRATION_RUNBOOK.md)
- [развёртывание/yandex/docker-compose.yml](https://github.com/i1yxaluk-del/Newbie/blob/89249e43a4e8b2e90d562307ef244ba95288c64c/развёртывание/yandex/docker-compose.yml)

- [Кураторская видеотека и порядок практики](../VIDEO_GUIDE.md)

