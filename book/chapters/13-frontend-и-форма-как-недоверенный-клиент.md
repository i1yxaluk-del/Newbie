# 13. Frontend и форма как недоверенный клиент

> **Учебная ситуация.** Пользователь может вызвать API напрямую, минуя checkbox и JavaScript.

## Главное

SPA выполняется на машине пользователя: код и значения bundle доступны для чтения и изменения. Поэтому frontend validation улучшает UX, но не обеспечивает policy.

Build-time environment встраивается в assets; секрет, попавший туда, становится публичным.

Consent и CAPTCHA проверяются server-side. Fail-closed отклоняет запрос при недоступности verifier; fail-open — явное риск-решение.

## Как это работает

Browser может изменить JavaScript, удалить required attribute и отправить собственный HTTP. Поэтому backend повторяет validation, consent и CAPTCHA policy. Build создаёт статические public files: любое значение, попавшее в bundle, нужно считать раскрытым.

## Пример

```bash
cd frontend
yarn install --frozen-lockfile
yarn сборка
grep -R "ADMIN_TOKEN\|PASSWORD" сборка/ || true
curl -i -X POST http://127.0.0.1:8001/api/leads -H 'Content-Type: application/json' -d '{}'
```

## Практикум

1. Соберите frontend.
2. Отправьте запрос без UI.
3. Проверьте отсутствие secrets и поведение consent/CAPTCHA.

## Если что-то не работает

| Наблюдение | Что это означает | Следующая проверка |
|---|---|---|
| Работает в dev, не в сборка | различие runtime/сборка config. |
| Checkbox есть, backend принимает false | UI не является control. |

## Источники проекта

- [frontend/](https://github.com/i1yxaluk-del/Newbie/blob/89249e43a4e8b2e90d562307ef244ba95288c64c/frontend/)
- [backend/secure_server.py](https://github.com/i1yxaluk-del/Newbie/blob/89249e43a4e8b2e90d562307ef244ba95288c64c/backend/secure_server.py)

- [Кураторская видеотека и порядок практики](../VIDEO_GUIDE.md)

