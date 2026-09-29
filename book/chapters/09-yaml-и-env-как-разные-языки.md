# 9. YAML и .env как разные языки

> **Учебная ситуация.** Compose принял YAML, но service получил пустой пароль.

## Главное

YAML задаёт дерево данных: mapping, sequence и scalar. Валидный YAML может быть невалидным Compose, потому что schema — второй уровень проверки.

`.env` — пары KEY=VALUE, не YAML и не shell script. Compose interpolation выполняется до запуска container.

`${VAR:?message}` требует значение; `${VAR:-default}` разрешает fallback. Для security-параметров безопаснее обязательность, чем тихий default.

## Как это работает

YAML parser строит типизированное дерево, Compose проверяет допустимость ключей, затем подставляет environment и объединяет files. Только итоговая модель становится containers/networks/volumes. Поэтому `docker compose config` полезен, но его вывод может содержать подставленные secrets.

## Пример

```yaml
services:
  backend:
    env_file: ../../backend/.env
    environment:
      MONGO_URL: mongodb://mongo:27017
    ports:
      - "127.0.0.1:8001:8001"
```

## Практикум

1. Проверьте `docker compose config`.
2. Сломайте indentation и затем schema key.
3. Добавьте обязательную переменную и убедитесь, что пустая конфигурация не запускается.

## Если что-то не работает

| Наблюдение | Что это означает | Следующая проверка |
|---|---|---|
| Parser error указывает синтаксис; unknown property | schema. |
| Значение выглядит числом/boolean | кавычки фиксируют строку. |

## Источники проекта

- [развёртывание/yandex/docker-compose.yml](https://github.com/i1yxaluk-del/Newbie/blob/89249e43a4e8b2e90d562307ef244ba95288c64c/развёртывание/yandex/docker-compose.yml)
- [scripts/deployment/preflight.sh](https://github.com/i1yxaluk-del/Newbie/blob/89249e43a4e8b2e90d562307ef244ba95288c64c/scripts/deployment/preflight.sh)

- [Кураторская видеотека и порядок практики](../VIDEO_GUIDE.md)

