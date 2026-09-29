# 10. Python-путь запроса: от socket до функции

> **Учебная ситуация.** Нужно понять, что именно происходит между POST `/api/leads` и записью в Mongo.

Предыдущая глава: [глава 9](./09-yaml-и-env-как-разные-языки.md).

## Модель, которую нужно построить

Uvicorn принимает socket и вызывает ASGI application. FastAPI сопоставляет method/path с route, выполняет dependencies и validation.

`async def` позволяет уступать event loop во время I/O, но CPU-heavy код всё равно блокирует процесс.

Middleware оборачивает application. В `secure_server.py` body читается, проверяется consent и воспроизводится для FastAPI.

## Термины в рабочем смысле

### ASGI

Контракт вызовов между Python web server и asynchronous application. Uvicorn владеет socket, FastAPI обрабатывает scope/events.

### middleware

Обёртка вокруг application, которая может проверить или изменить запрос/ответ. Ошибка в чтении body способна лишить downstream исходных данных.

### process

Запущенный экземпляр программы: address space, PID, credentials, environment и file descriptors. Service может породить несколько процессов.

## Что происходит внутри

Uvicorn превращает bytes из socket в ASGI events. Middleware читает `http.request`; если body потреблён, downstream нужно вернуть его через replay. FastAPI после middleware выбирает route и валидирует model. Затем handler пишет Mongo и создаёт outbox, поэтому status ответа надо связывать с фактическим commit данных.

## Разобранный пример

```python
if scope["method"] == "POST" and scope["path"] == "/api/leads":
    body = b"".join(chunks)
    payload = json.loads(body or b"{}")
    if payload.get("consent") is not True:
        return JSONResponse({"detail": "consent_required"}, status_code=400)
```

### Как читать пример

- `if scope["method"] == "POST" and scope["path"] == "/api/leads":` — Разделите строку на программу/оператор, options и operands; затем по документации установите side effect и exit semantics.
- `body = b"".join(chunks)` — Разделите строку на программу/оператор, options и operands; затем по документации установите side effect и exit semantics.
- `payload = json.loads(body or b"{}")` — Разделите строку на программу/оператор, options и operands; затем по документации установите side effect и exit semantics.
- `if payload.get("consent") is not True:` — Разделите строку на программу/оператор, options и operands; затем по документации установите side effect и exit semantics.
- `return JSONResponse({"detail": "consent_required"}, status_code=400)` — Разделите строку на программу/оператор, options и operands; затем по документации установите side effect и exit semantics.

## Практикум

1. Проследите один запрос по логам.
2. Напишите минимальный endpoint и Pydantic model.
3. Проверьте malformed JSON, отсутствие consent и корректный payload.

## Если результат не совпал с ожиданием

| Наблюдение | Что это означает | Следующая проверка |
|---|---|---|
| 422 | Это сужает область поиска, но не доказывает единственную причину | schema validation, 400 здесь — policy middleware. |
| 500 | Это сужает область поиска, но не доказывает единственную причину | необработанное исключение; искать traceback и request correlation. |

## Самостоятельная работа

Решите изменённый вариант исходной ситуации: **Нужно понять, что именно происходит между POST `/api/leads` и записью в Mongo.** Измените один существенный параметр — host, port, credential, dataset, пакет или ограничение клиента — и сначала письменно предскажите результат. Затем выполните проверку на безопасном стенде. В отчёте оставьте исходное предположение, фактическое наблюдение, причину расхождения и способ восстановления.

## Проверка понимания

1. Объясните `ASGI` через механизм и приведите пример из этой главы, а не словарную формулировку.
1. Объясните `middleware` через механизм и приведите пример из этой главы, а не словарную формулировку.
1. Объясните `process` через механизм и приведите пример из этой главы, а не словарную формулировку.
1. Почему симптом «422» ещё не доказывает единственную причину?
1. Какая независимая проверка отличает выполненную команду от достигнутого результата?

## Источники проекта

- [backend/secure_server.py](https://github.com/i1yxaluk-del/Newbie/blob/89249e43a4e8b2e90d562307ef244ba95288c64c/backend/secure_server.py)
- [backend/server.py](https://github.com/i1yxaluk-del/Newbie/blob/89249e43a4e8b2e90d562307ef244ba95288c64c/backend/server.py)
- [backend/tests/](https://github.com/i1yxaluk-del/Newbie/blob/89249e43a4e8b2e90d562307ef244ba95288c64c/backend/tests/)

- [Русскоязычный видеопоиск: Python-путь запроса: от socket до функции](https://www.youtube.com/results?search_query=Python-%D0%BF%D1%83%D1%82%D1%8C+%D0%B7%D0%B0%D0%BF%D1%80%D0%BE%D1%81%D0%B0%3A+%D0%BE%D1%82+socket+%D0%B4%D0%BE+%D1%84%D1%83%D0%BD%D0%BA%D1%86%D0%B8%D0%B8+%D0%BD%D0%B0+%D1%80%D1%83%D1%81%D1%81%D0%BA%D0%BE%D0%BC)

## Условие перехода

Глава завершена, если вы можете связно объяснить `ASGI`, `middleware`, `process`, выполнить практикум без копирования команд и восстановить систему после описанного отказа. Запишите в `learning-log.md`, что осталось непонятным; неизвестность не заменяйте догадкой.
