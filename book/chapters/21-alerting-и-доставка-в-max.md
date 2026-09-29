# 21. Alerting и доставка в MAX

> **Учебная ситуация.** Alert firing виден в Prometheus, но сообщение не приходит в MAX.

Предыдущая глава: [глава 20](./20-метрики-и-prometheus.md).

## Модель, которую нужно построить

Rule переводит metric expression в alert state. `for` требует непрерывного выполнения условия и подавляет краткий шум.

Alertmanager группирует и маршрутизирует alerts; webhook получает JSON и bearer token.

MAX alerter использует pymax user session, не официальный bot API. `max.db` — credential; пакет `maxapi-python` закреплён на версии 2.4.1 после ошибки `client.unsupported-version`. Health endpoint не доказывает отправку.

## Термины в рабочем смысле

### alert rule

PromQL condition, labels, annotations и необязательное `for`. Alert state существует отдельно от доставки notification.

### grouping

Объединение alerts Alertmanager по labels для снижения шума; слишком широкая группа может скрыть отдельные impacts.

### session

Состояние авторизации MAX в `max.db`, функционально равное credential. Bind mount сохраняет его при recreate container.

## Что происходит внутри

Prometheus rule и Alertmanager notification — разные состояния. Alert может firing, но grouped/inhibited или receiver может падать. MAX `/health` проверяет HTTP process, auth check — session, а только тестовый alert доказывает end-to-end. Session backup должен шифроваться как пароль.

## Разобранный пример

```bash
sudo docker exec msp-max-alerter python -m max_alerter.auth
curl -fsS http://127.0.0.1:9095/health
sudo docker logs msp-max-alerter --tail 100
```

### Как читать пример

- `sudo docker exec msp-max-alerter python -m max_alerter.auth` — `sudo` запускает следующую программу с повышенной effective identity; shell уже обработал кавычки, glob и redirection.
- `curl -fsS http://127.0.0.1:9095/health` — `curl` создаёт реальный HTTP/TLS request. `-f` делает HTTP 4xx/5xx ненулевым exit, `-sS` скрывает progress, но оставляет ошибки.
- `sudo docker logs msp-max-alerter --tail 100` — `sudo` запускает следующую программу с повышенной effective identity; shell уже обработал кавычки, glob и redirection.

## Практикум

1. Авторизуйте test account: SMS, затем 2FA.
2. Отправьте тестовый webhook из monitoring network.
3. Перезагрузите container/VM и подтвердите session persistence.

## Если результат не совпал с ожиданием

| Наблюдение | Что это означает | Следующая проверка |
|---|---|---|
| 401 | Это сужает область поиска, но не доказывает единственную причину | webhook tokens различаются. |
| Health ok, send fail | Это сужает область поиска, но не доказывает единственную причину | session/chat ID/library/API. |

## Самостоятельная работа

Решите изменённый вариант исходной ситуации: **Alert firing виден в Prometheus, но сообщение не приходит в MAX.** Измените один существенный параметр — host, port, credential, dataset, пакет или ограничение клиента — и сначала письменно предскажите результат. Затем выполните проверку на безопасном стенде. В отчёте оставьте исходное предположение, фактическое наблюдение, причину расхождения и способ восстановления.

## Проверка понимания

1. Объясните `alert rule` через механизм и приведите пример из этой главы, а не словарную формулировку.
1. Объясните `grouping` через механизм и приведите пример из этой главы, а не словарную формулировку.
1. Объясните `session` через механизм и приведите пример из этой главы, а не словарную формулировку.
1. Почему симптом «401» ещё не доказывает единственную причину?
1. Какая независимая проверка отличает выполненную команду от достигнутого результата?

## Источники проекта

- [docs/MAX_SETUP.md](https://github.com/i1yxaluk-del/Newbie/blob/89249e43a4e8b2e90d562307ef244ba95288c64c/docs/MAX_SETUP.md)
- [services/max_alerter/README.md](https://github.com/i1yxaluk-del/Newbie/blob/89249e43a4e8b2e90d562307ef244ba95288c64c/services/max_alerter/README.md)
- [deploy/yandex/monitoring/docker-compose.yml](https://github.com/i1yxaluk-del/Newbie/blob/89249e43a4e8b2e90d562307ef244ba95288c64c/deploy/yandex/monitoring/docker-compose.yml)

- [Кураторская видеотека и порядок практики](../VIDEO_GUIDE.md)

## Условие перехода

Глава завершена, если вы можете связно объяснить `alert rule`, `grouping`, `session`, выполнить практикум без копирования команд и восстановить систему после описанного отказа. Запишите в `learning-log.md`, что осталось непонятным; неизвестность не заменяйте догадкой.
