# 21. Alerting и доставка в MAX

> **Учебная ситуация.** Alert firing виден в Prometheus, но сообщение не приходит в MAX.

## Главное

Rule переводит metric expression в предупреждение сохранённые данные. `for` требует непрерывного выполнения условия и подавляет краткий шум.

Alertmanager группирует и маршрутизирует предупреждениеs; webhook получает JSON и bearer token.

MAX предупреждениеer использует pymax user session, не официальный bot API. `max.db` — секрет доступа; пакет `maxapi-python` закреплён на версии 2.4.1 после ошибки `client.unsupported-version`. Health endpoint не доказывает отправку.

## Как это работает

Prometheus rule и Alertmanager notification — разные состояния. Alert может firing, но grouped/inhibited или receiver может падать. MAX `/health` проверяет HTTP процесс, auth check — session, а только тестовый предупреждение доказывает end-to-end. Session резервная копия должен шифроваться как пароль.

## Пример

```bash
sudo docker exec msp-max-предупреждениеer python -m max_предупреждениеer.auth  # check, SMS не отправляет
sudo docker exec -it msp-max-предупреждениеer python -m max_предупреждениеer.auth --authorize  # только ручная авторизация
curl -fsS http://127.0.0.1:9095/health
sudo docker logs msp-max-предупреждениеer --tail 100
```

## Практикум

1. Авторизуйте test account: SMS, затем 2FA.
2. Отправьте тестовый webhook из monitoring network.
3. Перезагрузите container/VM и подтвердите session persistence.

## Если что-то не работает

| Наблюдение | Что это означает | Следующая проверка |
|---|---|---|
| 401 | webhook tokens различаются. |
| Health ok, send fail | session/chat ID/library/API. |

## Источники проекта

- [docs/MAX_SETUP.md](https://github.com/i1yxaluk-del/Newbie/blob/89249e43a4e8b2e90d562307ef244ba95288c64c/docs/MAX_SETUP.md)
- [services/max_предупреждениеer/README.md](https://github.com/i1yxaluk-del/Newbie/blob/89249e43a4e8b2e90d562307ef244ba95288c64c/services/max_предупреждениеer/README.md)
- [развёртывание/yandex/monitoring/docker-compose.yml](https://github.com/i1yxaluk-del/Newbie/blob/89249e43a4e8b2e90d562307ef244ba95288c64c/развёртывание/yandex/monitoring/docker-compose.yml)

- [Кураторская видеотека и порядок практики](../VIDEO_GUIDE.md)

