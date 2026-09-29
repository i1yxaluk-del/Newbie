# 19. SMTP, DNS и Stalwart/Postbox

> **Учебная ситуация.** Письма принимаются локально, но наружу копятся с 535.

Предыдущая глава: [глава 18](./18-полный-deploy-mspshield.md).

## Модель, которую нужно построить

SMTP envelope MAIL FROM/RCPT TO управляет доставкой и отличается от видимых From/To headers. Relay требует authentication и policy.

MX указывает принимающий host; SPF разрешает senders; DKIM подписывает письмо; DMARC задаёт policy и alignment. В Postbox DKIM публикуется CNAME из консоли.

Stalwart хранит route credentials в собственной БД. Восстановление старой БД может вернуть старый ключ, даже если `.env` обновлён. Очередь JMAP показывает реальную 535.

## Термины в рабочем смысле

### SMTP

Store-and-forward протокол передачи почты между clients/servers. Успешная submission ещё не доказывает final delivery.

### DKIM

Криптографическая подпись выбранных headers/body, проверяемая public key из DNS. В Postbox проект публикует выданные CNAME delegation records.

### bootstrap mode

Начальное состояние Stalwart без восстановленной рабочей конфигурации. Process может быть healthy, но service для клиента фактически потерян.

## Что происходит внутри

Stalwart принимает local mail и/или отправляет через Postbox relay. Route credentials могут жить в restored RocksDB, поэтому environment не является единственным source. JMAP queue показывает recipient-level last error. После route update restart нужен, чтобы runtime перечитал состояние.

## Разобранный пример

```bash
curl -s -u "admin:$PW" -H 'Content-Type: application/json' \
 -d '{"using":["urn:ietf:params:jmap:core","urn:stalwart:jmap"],"methodCalls":[["x:QueuedMessage/get",{},"0"]]}' \
 http://127.0.0.1:8080/jmap/
```

### Как читать пример

- `curl -s -u "admin:$PW" -H 'Content-Type: application/json' \` — `curl` создаёт реальный HTTP/TLS request. `-f` делает HTTP 4xx/5xx ненулевым exit, `-sS` скрывает progress, но оставляет ошибки.
- `-d '{"using":["urn:ietf:params:jmap:core","urn:stalwart:jmap"],"methodCalls":[["x:QueuedMessage/get",{},"0"]]}' \` — Разделите строку на программу/оператор, options и operands; затем по документации установите side effect и exit semantics.
- `http://127.0.0.1:8080/jmap/` — Разделите строку на программу/оператор, options и operands; затем по документации установите side effect и exit semantics.

## Практикум

1. Проверьте DNS records.
2. Получите очередь JMAP.
3. Обновите route на тестовом стенде и restart Stalwart.

## Если результат не совпал с ожиданием

| Наблюдение | Что это означает | Следующая проверка |
|---|---|---|
| 535 | Это сужает область поиска, но не доказывает единственную причину | credential/identity, не сетевой timeout. |
| Bootstrap mode | Это сужает область поиска, но не доказывает единственную причину | не восстановлен `stalwart-data` или `stalwart-etc`. |

## Самостоятельная работа

Решите изменённый вариант исходной ситуации: **Письма принимаются локально, но наружу копятся с 535.** Измените один существенный параметр — host, port, credential, dataset, пакет или ограничение клиента — и сначала письменно предскажите результат. Затем выполните проверку на безопасном стенде. В отчёте оставьте исходное предположение, фактическое наблюдение, причину расхождения и способ восстановления.

## Проверка понимания

1. Объясните `SMTP` через механизм и приведите пример из этой главы, а не словарную формулировку.
1. Объясните `DKIM` через механизм и приведите пример из этой главы, а не словарную формулировку.
1. Объясните `bootstrap mode` через механизм и приведите пример из этой главы, а не словарную формулировку.
1. Почему симптом «535» ещё не доказывает единственную причину?
1. Какая независимая проверка отличает выполненную команду от достигнутого результата?

## Источники проекта

- [docs/deployment/MIGRATION_RUNBOOK.md](https://github.com/i1yxaluk-del/Newbie/blob/89249e43a4e8b2e90d562307ef244ba95288c64c/docs/deployment/MIGRATION_RUNBOOK.md)
- [deploy/yandex/docker-compose.yml](https://github.com/i1yxaluk-del/Newbie/blob/89249e43a4e8b2e90d562307ef244ba95288c64c/deploy/yandex/docker-compose.yml)

- [Русскоязычный видеопоиск: SMTP, DNS и Stalwart/Postbox](https://www.youtube.com/results?search_query=SMTP%2C+DNS+%D0%B8+Stalwart%2FPostbox+%D0%BD%D0%B0+%D1%80%D1%83%D1%81%D1%81%D0%BA%D0%BE%D0%BC)

## Условие перехода

Глава завершена, если вы можете связно объяснить `SMTP`, `DKIM`, `bootstrap mode`, выполнить практикум без копирования команд и восстановить систему после описанного отказа. Запишите в `learning-log.md`, что осталось непонятным; неизвестность не заменяйте догадкой.
