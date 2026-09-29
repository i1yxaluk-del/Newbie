# 13. Frontend и форма как недоверенный клиент

> **Учебная ситуация.** Пользователь может вызвать API напрямую, минуя checkbox и JavaScript.

## Главное

SPA выполняется на машине пользователя: код и значения bundle доступны для чтения и изменения. Поэтому frontend validation улучшает UX, но не обеспечивает policy.

Build-time environment встраивается в assets; секрет, попавший туда, становится публичным.

Consent и CAPTCHA проверяются server-side. Fail-closed отклоняет запрос при недоступности verifier; fail-open — явное риск-решение.

## Слова, которые встретятся дальше

### SPA

Приложение, где browser загружает bundle и меняет UI без полной перезагрузки страницы. Код работает в недоверенной среде пользователя.

### fail-closed

При невозможности проверить разрешение операция отклоняется. Повышает безопасность, но требует продуманного UX и fallback для legitimate users.

### schema

Набор допустимых ключей, типов и ограничений поверх синтаксически корректных данных. YAML parser не знает правил Docker Compose.

## Как это работает

Browser может изменить JavaScript, удалить required attribute и отправить собственный HTTP. Поэтому backend повторяет validation, consent и CAPTCHA policy. Build создаёт статические public files: любое значение, попавшее в bundle, нужно считать раскрытым.

## Пример

```bash
cd frontend
yarn install --frozen-lockfile
yarn build
grep -R "ADMIN_TOKEN\|PASSWORD" build/ || true
curl -i -X POST http://127.0.0.1:8001/api/leads -H 'Content-Type: application/json' -d '{}'
```

### Что здесь происходит

- `cd frontend` — Разделите строку на программу/оператор, options и operands; затем по документации установите side effect и exit semantics.
- `yarn install --frozen-lockfile` — Разделите строку на программу/оператор, options и operands; затем по документации установите side effect и exit semantics.
- `yarn build` — Разделите строку на программу/оператор, options и operands; затем по документации установите side effect и exit semantics.
- `grep -R "ADMIN_TOKEN\|PASSWORD" build/ || true` — Разделите строку на программу/оператор, options и operands; затем по документации установите side effect и exit semantics.
- `curl -i -X POST http://127.0.0.1:8001/api/leads -H 'Content-Type: application/json' -d '{}'` — `curl` создаёт реальный HTTP/TLS request. `-f` делает HTTP 4xx/5xx ненулевым exit, `-sS` скрывает progress, но оставляет ошибки.

## Практикум

1. Соберите frontend.
2. Отправьте запрос без UI.
3. Проверьте отсутствие secrets и поведение consent/CAPTCHA.

## Если что-то не работает

| Наблюдение | Что это означает | Следующая проверка |
|---|---|---|
| Работает в dev, не в build | различие runtime/build config. |
| Checkbox есть, backend принимает false | UI не является control. |


## Проверьте себя

1. Объясните `SPA` через механизм и приведите пример из этой главы, а не словарную формулировку.
1. Объясните `fail-closed` через механизм и приведите пример из этой главы, а не словарную формулировку.
1. Объясните `schema` через механизм и приведите пример из этой главы, а не словарную формулировку.
1. Почему симптом «Работает в dev, не в build» ещё не доказывает единственную причину?
1. Какая независимая проверка отличает выполненную команду от достигнутого результата?

## Источники проекта

- [frontend/](https://github.com/i1yxaluk-del/Newbie/blob/89249e43a4e8b2e90d562307ef244ba95288c64c/frontend/)
- [backend/secure_server.py](https://github.com/i1yxaluk-del/Newbie/blob/89249e43a4e8b2e90d562307ef244ba95288c64c/backend/secure_server.py)

- [Кураторская видеотека и порядок практики](../VIDEO_GUIDE.md)

