# 16. Compose как граф зависимостей

> **Учебная ситуация.** Backend должен ждать Mongo, но restart policy не исправляет логическую ошибку приложения.

Предыдущая глава: [глава 15](./15-dockerfile-cache-и-attack-surface.md).

## Модель, которую нужно построить

Compose project объединяет services, networks и volumes. Service — шаблон container, а не сам process.

`depends_on: condition: service_healthy` регулирует порядок старта, но не лечит будущий отказ зависимости. Приложению нужны timeout/retry.

Два Compose-проекта связываются через external network `msp_default`; имя должно уже существовать.

## Термины в рабочем смысле

### service-compose

Compose-описание желаемого container: image/build, env, mounts, networks, health и restart. Это не systemd service.

### healthcheck

Команда, оценивающая выбранный признак внутри/рядом с service. Она доказывает только то, что действительно проверяет.

### volume

Storage с lifecycle отдельно от container. Backup volume всё равно должен учитывать consistency приложения.

## Что происходит внутри

Compose сначала создаёт networks/volumes, затем containers. `depends_on` с health condition ждёт initial health, но после запуска backend должен сам переживать краткий отказ Mongo. External network — контракт между двумя projects и не создаётся вторым Compose автоматически.

## Разобранный пример

```yaml
backend:
  depends_on:
    mongo:
      condition: service_healthy
  ports:
    - "127.0.0.1:8001:8001"
```

### Как читать пример

- `backend:` — Стрелка показывает направление зависимости; подпись на стрелке задаёт протокол или тип передачи.
- `depends_on:` — Разделите строку на программу/оператор, options и operands; затем по документации установите side effect и exit semantics.
- `mongo:` — Стрелка показывает направление зависимости; подпись на стрелке задаёт протокол или тип передачи.
- `condition: service_healthy` — Разделите строку на программу/оператор, options и operands; затем по документации установите side effect и exit semantics.
- `ports:` — Разделите строку на программу/оператор, options и operands; затем по документации установите side effect и exit semantics.
- `- "127.0.0.1:8001:8001"` — Эта строка является частью конфигурации или формулы; смысл определяется родительским блоком и отступом.

## Практикум

1. Поднимите Mongo+backend.
2. Сделайте Mongo unhealthy после старта.
3. Сравните `restart` и `up -d --force-recreate` после изменения env.

## Если результат не совпал с ожиданием

| Наблюдение | Что это означает | Следующая проверка |
|---|---|---|
| Compose config ok, external network missing | Это сужает область поиска, но не доказывает единственную причину | runtime prerequisite. |
| `restart` не перечитал env | Это сужает область поиска, но не доказывает единственную причину | нужен recreate. |

## Самостоятельная работа

Решите изменённый вариант исходной ситуации: **Backend должен ждать Mongo, но restart policy не исправляет логическую ошибку приложения.** Измените один существенный параметр — host, port, credential, dataset, пакет или ограничение клиента — и сначала письменно предскажите результат. Затем выполните проверку на безопасном стенде. В отчёте оставьте исходное предположение, фактическое наблюдение, причину расхождения и способ восстановления.

## Проверка понимания

1. Объясните `service-compose` через механизм и приведите пример из этой главы, а не словарную формулировку.
1. Объясните `healthcheck` через механизм и приведите пример из этой главы, а не словарную формулировку.
1. Объясните `volume` через механизм и приведите пример из этой главы, а не словарную формулировку.
1. Почему симптом «Compose config ok, external network missing» ещё не доказывает единственную причину?
1. Какая независимая проверка отличает выполненную команду от достигнутого результата?

## Источники проекта

- [deploy/yandex/docker-compose.yml](https://github.com/i1yxaluk-del/Newbie/blob/89249e43a4e8b2e90d562307ef244ba95288c64c/deploy/yandex/docker-compose.yml)
- [deploy/yandex/monitoring/docker-compose.yml](https://github.com/i1yxaluk-del/Newbie/blob/89249e43a4e8b2e90d562307ef244ba95288c64c/deploy/yandex/monitoring/docker-compose.yml)

- [Кураторская видеотека и порядок практики](../VIDEO_GUIDE.md)

## Условие перехода

Глава завершена, если вы можете связно объяснить `service-compose`, `healthcheck`, `volume`, выполнить практикум без копирования команд и восстановить систему после описанного отказа. Запишите в `learning-log.md`, что осталось непонятным; неизвестность не заменяйте догадкой.
