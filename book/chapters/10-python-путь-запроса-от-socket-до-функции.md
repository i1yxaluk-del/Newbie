# 10. Python-путь запроса: от сетевое подключение до функции

> **Учебная ситуация.** Нужно понять, что именно происходит между POST `/api/leads` и записью в Mongo.

## Главное

Uvicorn принимает сетевое подключение и вызывает ASGI application. FastAPI сопоставляет method/path с route, выполняет dependencies и validation.

`async def` позволяет уступать event loop во время I/O, но CPU-heavy код всё равно блокирует процесс.

Middleware оборачивает application. В `secure_server.py` body читается, проверяется consent и воспроизводится для FastAPI.

## Слова, которые встретятся дальше

### ASGI

Контракт вызовов между Python web server и asynchronous application. Uvicorn владеет сетевое подключение, FastAPI обрабатывает границы услуги/events.

### middleware

Обёртка вокруг application, которая может проверить или изменить запрос/ответ. Ошибка в чтении body способна лишить downstream исходных данных.

### процесс

Запущенный экземпляр программы: address space, PID, секрет доступаs, environment и file descriptors. Service может породить несколько процессов.

## Как это работает

Uvicorn превращает bytes из сетевое подключение в ASGI events. Middleware читает `http.request`; если body потреблён, downstream нужно вернуть его через replay. FastAPI после middleware выбирает route и валидирует model. Затем handler пишет Mongo и создаёт outbox, поэтому status ответа надо связывать с фактическим commit данных.

## Пример

```python
if границы услуги["method"] == "POST" and границы услуги["path"] == "/api/leads":
    body = b"".join(chunks)
    payload = json.loads(body or b"{}")
    if payload.get("consent") is not True:
        return JSONResponse({"detail": "consent_required"}, status_code=400)
```

### Что здесь происходит

- `if границы услуги["method"] == "POST" and границы услуги["path"] == "/api/leads":` — Разделите строку на программу/оператор, options и operands; затем по документации установите side effect и exit semantics.
- `body = b"".join(chunks)` — Разделите строку на программу/оператор, options и operands; затем по документации установите side effect и exit semantics.
- `payload = json.loads(body or b"{}")` — Разделите строку на программу/оператор, options и operands; затем по документации установите side effect и exit semantics.
- `if payload.get("consent") is not True:` — Разделите строку на программу/оператор, options и operands; затем по документации установите side effect и exit semantics.
- `return JSONResponse({"detail": "consent_required"}, status_code=400)` — Разделите строку на программу/оператор, options и operands; затем по документации установите side effect и exit semantics.

## Практикум

1. Проследите один запрос по логам.
2. Напишите минимальный endpoint и Pydantic model.
3. Проверьте malformed JSON, отсутствие consent и корректный payload.

## Если что-то не работает

| Наблюдение | Что это означает | Следующая проверка |
|---|---|---|
| 422 | schema validation, 400 здесь — policy middleware. |
| 500 | необработанное исключение; искать traceback и request correlation. |


## Проверьте себя

1. Объясните `ASGI` через механизм и приведите пример из этой главы, а не словарную формулировку.
1. Объясните `middleware` через механизм и приведите пример из этой главы, а не словарную формулировку.
1. Объясните `процесс` через механизм и приведите пример из этой главы, а не словарную формулировку.
1. Почему симптом «422» ещё не доказывает единственную причину?
1. Какая независимая проверка отличает выполненную команду от достигнутого результата?

## Источники проекта

- [backend/secure_server.py](https://github.com/i1yxaluk-del/Newbie/blob/89249e43a4e8b2e90d562307ef244ba95288c64c/backend/secure_server.py)
- [backend/server.py](https://github.com/i1yxaluk-del/Newbie/blob/89249e43a4e8b2e90d562307ef244ba95288c64c/backend/server.py)
- [backend/tests/](https://github.com/i1yxaluk-del/Newbie/blob/89249e43a4e8b2e90d562307ef244ba95288c64c/backend/tests/)

- [Кураторская видеотека и порядок практики](../VIDEO_GUIDE.md)

