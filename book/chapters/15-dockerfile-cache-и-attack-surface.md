# 15. Dockerfile, cache и attack surface

> **Учебная ситуация.** Нужно собрать backend воспроизводимо и не запускать его как root без причины.

## Главное

`FROM` задаёт базовый filesystem. `COPY` и `RUN` создают layers; изменение раннего layer инвалидирует последующий cache.

Build context определяет, какие файлы доступны `COPY`; секреты не должны попадать в context или layer history.

`CMD` задаёт default процесс. Production image проекта запускает `secure_server:app`, чтобы consent/CAPTCHA/outbox policy нельзя было обойти.

## Как это работает

Builder вычисляет cache key инструкции и её исходное значениеs. Копирование всего repository до install делает любое изменение source причиной повторной установки dependencies. Secrets нельзя исправить простым `rm` в следующем layer: предыдущий layer остаётся доступным в image history.

## Пример

```dockerfile
FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
CMD ["uvicorn", "secure_server:app", "--host", "0.0.0.0", "--port", "8001"]
```

## Практикум

1. Соберите image дважды и сравните cache.
2. Добавьте non-root user.
3. Проверьте image history на secrets.

## Если что-то не работает

| Наблюдение | Что это означает | Следующая проверка |
|---|---|---|
| Сборка всегда долгая | часто requirements копируются после всего source. |
| Container стартует, policy нет | указан `server:app` вместо wrapper. |

## Источники проекта

- [развёртывание/yandex/Dockerfile.backend](https://github.com/i1yxaluk-del/Newbie/blob/89249e43a4e8b2e90d562307ef244ba95288c64c/развёртывание/yandex/Dockerfile.backend)
- [backend/secure_server.py](https://github.com/i1yxaluk-del/Newbie/blob/89249e43a4e8b2e90d562307ef244ba95288c64c/backend/secure_server.py)

- [Кураторская видеотека и порядок практики](../VIDEO_GUIDE.md)

