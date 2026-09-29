# 15. Dockerfile, cache и attack surface

> **Учебная ситуация.** Нужно собрать backend воспроизводимо и не запускать его как root без причины.

## Главное

`FROM` задаёт базовый filesystem. `COPY` и `RUN` создают layers; изменение раннего layer инвалидирует последующий cache.

Build context определяет, какие файлы доступны `COPY`; секреты не должны попадать в context или layer history.

`CMD` задаёт default процесс. Production image проекта запускает `secure_server:app`, чтобы consent/CAPTCHA/outbox policy нельзя было обойти.

## Слова, которые встретятся дальше

### build context

Набор файлов, отправляемый builder. `.dockerignore` уменьшает размер и риск случайно включить secrets.

### layer

Неизменяемый результат инструкции image build. Удаление секрета следующим RUN не гарантирует его исчезновение из предыдущего layer.

### image

Неизменяемый шаблон root filesystem и metadata для container. Image не содержит runtime volume data.

## Как это работает

Builder вычисляет cache key инструкции и её inputs. Копирование всего repository до install делает любое изменение source причиной повторной установки dependencies. Secrets нельзя исправить простым `rm` в следующем layer: предыдущий layer остаётся доступным в image history.

## Пример

```dockerfile
FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
CMD ["uvicorn", "secure_server:app", "--host", "0.0.0.0", "--port", "8001"]
```

### Что здесь происходит

- `FROM python:3.12-slim` — Стрелка показывает направление зависимости; подпись на стрелке задаёт протокол или тип передачи.
- `WORKDIR /app` — Стрелка показывает направление зависимости; подпись на стрелке задаёт протокол или тип передачи.
- `COPY requirements.txt .` — Стрелка показывает направление зависимости; подпись на стрелке задаёт протокол или тип передачи.
- `RUN pip install --no-cache-dir -r requirements.txt` — Стрелка показывает направление зависимости; подпись на стрелке задаёт протокол или тип передачи.
- `COPY . .` — Стрелка показывает направление зависимости; подпись на стрелке задаёт протокол или тип передачи.
- `CMD ["uvicorn", "secure_server:app", "--host", "0.0.0.0", "--port", "8001"]` — Стрелка показывает направление зависимости; подпись на стрелке задаёт протокол или тип передачи.

## Практикум

1. Соберите image дважды и сравните cache.
2. Добавьте non-root user.
3. Проверьте image history на secrets.

## Если что-то не работает

| Наблюдение | Что это означает | Следующая проверка |
|---|---|---|
| Сборка всегда долгая | часто requirements копируются после всего source. |
| Container стартует, policy нет | указан `server:app` вместо wrapper. |


## Проверьте себя

1. Объясните `build context` через механизм и приведите пример из этой главы, а не словарную формулировку.
1. Объясните `layer` через механизм и приведите пример из этой главы, а не словарную формулировку.
1. Объясните `image` через механизм и приведите пример из этой главы, а не словарную формулировку.
1. Почему симптом «Сборка всегда долгая» ещё не доказывает единственную причину?
1. Какая независимая проверка отличает выполненную команду от достигнутого результата?

## Источники проекта

- [развёртывание/yandex/Dockerfile.backend](https://github.com/i1yxaluk-del/Newbie/blob/89249e43a4e8b2e90d562307ef244ba95288c64c/развёртывание/yandex/Dockerfile.backend)
- [backend/secure_server.py](https://github.com/i1yxaluk-del/Newbie/blob/89249e43a4e8b2e90d562307ef244ba95288c64c/backend/secure_server.py)

- [Кураторская видеотека и порядок практики](../VIDEO_GUIDE.md)

