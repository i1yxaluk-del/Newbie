# 14. Что Docker изолирует, а что нет

> **Учебная ситуация.** Container удалили и потеряли данные; ожидали, что image хранит runtime state.

Предыдущая глава: [глава 13](./13-frontend-и-форма-как-недоверенный-клиент.md).

## Модель, которую нужно построить

Image — неизменяемый набор слоёв; container — процесс с writable layer и namespaces. Удаление container удаляет его writable layer.

Volume живёт отдельно и предназначен для состояния. Bind mount показывает container конкретный host path и наследует его permissions.

Container не VM: ядро общее с host. Privileged/cAdvisor и docker.sock расширяют доверие и attack surface.

## Термины в рабочем смысле

### image

Неизменяемый шаблон root filesystem и metadata для container. Image не содержит runtime volume data.

### namespace

Механизм Linux, дающий процессу отдельное представление PID, mount, network и других ресурсов; ядро остаётся общим.

### cgroup

Механизм учёта и ограничения CPU, memory и других ресурсов группы процессов.

### volume

Storage с lifecycle отдельно от container. Backup volume всё равно должен учитывать consistency приложения.

## Что происходит внутри

При `docker run` kernel запускает обычный process, но Docker настраивает namespaces, cgroups, root filesystem и network. Port publishing создаёт host forwarding. Named volume монтируется поверх path внутри image: исходное содержимое этого path может стать невидимым.

## Разобранный пример

```bash
docker run --name demo alpine sh -c 'echo x >/state && sleep 300'
docker rm -f demo
docker volume create demo-data
docker run --rm -v demo-data:/data alpine sh -c 'echo y >/data/state'
docker run --rm -v demo-data:/data alpine cat /data/state
```

### Как читать пример

- `docker run --name demo alpine sh -c 'echo x >/state && sleep 300'` — Разделите строку на программу/оператор, options и operands; затем по документации установите side effect и exit semantics.
- `docker rm -f demo` — Разделите строку на программу/оператор, options и operands; затем по документации установите side effect и exit semantics.
- `docker volume create demo-data` — Разделите строку на программу/оператор, options и operands; затем по документации установите side effect и exit semantics.
- `docker run --rm -v demo-data:/data alpine sh -c 'echo y >/data/state'` — Разделите строку на программу/оператор, options и operands; затем по документации установите side effect и exit semantics.
- `docker run --rm -v demo-data:/data alpine cat /data/state` — Разделите строку на программу/оператор, options и operands; затем по документации установите side effect и exit semantics.

## Практикум

1. Сравните writable layer и volume.
2. Исследуйте PID и network namespace.
3. Объясните host binding `127.0.0.1:8001:8001`.

## Если результат не совпал с ожиданием

| Наблюдение | Что это означает | Следующая проверка |
|---|---|---|
| Данные пропали | Это сужает область поиска, но не доказывает единственную причину | состояние было не в volume. |
| Порт недоступен извне | Это сужает область поиска, но не доказывает единственную причину | это может быть намеренный loopback binding. |

## Самостоятельная работа

Решите изменённый вариант исходной ситуации: **Container удалили и потеряли данные; ожидали, что image хранит runtime state.** Измените один существенный параметр — host, port, credential, dataset, пакет или ограничение клиента — и сначала письменно предскажите результат. Затем выполните проверку на безопасном стенде. В отчёте оставьте исходное предположение, фактическое наблюдение, причину расхождения и способ восстановления.

## Проверка понимания

1. Объясните `image` через механизм и приведите пример из этой главы, а не словарную формулировку.
1. Объясните `namespace` через механизм и приведите пример из этой главы, а не словарную формулировку.
1. Объясните `cgroup` через механизм и приведите пример из этой главы, а не словарную формулировку.
1. Почему симптом «Данные пропали» ещё не доказывает единственную причину?
1. Какая независимая проверка отличает выполненную команду от достигнутого результата?

## Источники проекта

- [deploy/yandex/docker-compose.yml](https://github.com/i1yxaluk-del/Newbie/blob/89249e43a4e8b2e90d562307ef244ba95288c64c/deploy/yandex/docker-compose.yml)

- [Русскоязычный видеопоиск: Что Docker изолирует, а что нет](https://www.youtube.com/results?search_query=%D0%A7%D1%82%D0%BE+Docker+%D0%B8%D0%B7%D0%BE%D0%BB%D0%B8%D1%80%D1%83%D0%B5%D1%82%2C+%D0%B0+%D1%87%D1%82%D0%BE+%D0%BD%D0%B5%D1%82+%D0%BD%D0%B0+%D1%80%D1%83%D1%81%D1%81%D0%BA%D0%BE%D0%BC)

## Условие перехода

Глава завершена, если вы можете связно объяснить `image`, `namespace`, `cgroup`, выполнить практикум без копирования команд и восстановить систему после описанного отказа. Запишите в `learning-log.md`, что осталось непонятным; неизвестность не заменяйте догадкой.
