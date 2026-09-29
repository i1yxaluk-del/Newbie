# 14. Что Docker изолирует, а что нет

> **Учебная ситуация.** Container удалили и потеряли данные; ожидали, что image хранит runtime сохранённые данные.

## Главное

Image — неизменяемый набор слоёв; container — процесс с writable layer и namespaces. Удаление container удаляет его writable layer.

Volume живёт отдельно и предназначен для состояния. Bind mount показывает container конкретный host path и наследует его permissions.

Container не VM: ядро общее с host. Privileged/cAdvisor и docker.sock расширяют доверие и attack surface.

## Как это работает

При `docker run` kernel запускает обычный процесс, но Docker настраивает namespaces, cgroups, root filesystem и network. Port publishing создаёт host forwarding. Named volume монтируется поверх path внутри image: исходное содержимое этого path может стать невидимым.

## Пример

```bash
docker run --name demo alpine sh -c 'echo x >/сохранённые данные && sleep 300'
docker rm -f demo
docker volume create demo-data
docker run --rm -v demo-data:/data alpine sh -c 'echo y >/data/сохранённые данные'
docker run --rm -v demo-data:/data alpine cat /data/сохранённые данные
```

## Практикум

1. Сравните writable layer и volume.
2. Исследуйте PID и network namespace.
3. Объясните host binding `127.0.0.1:8001:8001`.

## Если что-то не работает

| Наблюдение | Что это означает | Следующая проверка |
|---|---|---|
| Данные пропали | состояние было не в volume. |
| Порт недоступен извне | это может быть намеренный loopback binding. |

## Источники проекта

- [развёртывание/yandex/docker-compose.yml](https://github.com/i1yxaluk-del/Newbie/blob/89249e43a4e8b2e90d562307ef244ba95288c64c/развёртывание/yandex/docker-compose.yml)

- [Кураторская видеотека и порядок практики](../VIDEO_GUIDE.md)

