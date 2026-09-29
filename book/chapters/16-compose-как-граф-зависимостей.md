# 16. Compose как граф зависимостей

> **Учебная ситуация.** Backend должен ждать Mongo, но restart policy не исправляет логическую ошибку приложения.

## Главное

Compose project объединяет services, networks и volumes. Service — шаблон container, а не сам процесс.

`depends_on: condition: service_healthy` регулирует порядок старта, но не лечит будущий отказ зависимости. Приложению нужны timeout/retry.

Два Compose-проекта связываются через external network `msp_default`; имя должно уже существовать.

## Как это работает

Compose сначала создаёт networks/volumes, затем containers. `depends_on` с health condition ждёт initial health, но после запуска backend должен сам переживать краткий отказ Mongo. External network — контракт между двумя projects и не создаётся вторым Compose автоматически.

## Пример

```yaml
backend:
  depends_on:
    mongo:
      condition: service_healthy
  ports:
    - "127.0.0.1:8001:8001"
```

## Практикум

1. Поднимите Mongo+backend.
2. Сделайте Mongo unhealthy после старта.
3. Сравните `restart` и `up -d --force-recreate` после изменения env.

## Если что-то не работает

| Наблюдение | Что это означает | Следующая проверка |
|---|---|---|
| Compose config ok, external network missing | runtime prerequisite. |
| `restart` не перечитал env | нужен recreate. |

## Источники проекта

- [развёртывание/yandex/docker-compose.yml](https://github.com/i1yxaluk-del/Newbie/blob/89249e43a4e8b2e90d562307ef244ba95288c64c/развёртывание/yandex/docker-compose.yml)
- [развёртывание/yandex/monitoring/docker-compose.yml](https://github.com/i1yxaluk-del/Newbie/blob/89249e43a4e8b2e90d562307ef244ba95288c64c/развёртывание/yandex/monitoring/docker-compose.yml)

- [Кураторская видеотека и порядок практики](../VIDEO_GUIDE.md)

