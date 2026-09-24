# Deployment-код

[← Главная](../README.md) · [Deployment runbooks](../docs/deployment/README.md) · [Карта](../docs/NAVIGATION.md)

Этот каталог содержит Dockerfiles, Compose, Nginx и production-конфигурацию. **Не начинайте deployment с файлов этого каталога.**

## Правильный порядок

1. Открыть [`../docs/deployment/README.md`](../docs/deployment/README.md).
2. Выполнить [`../scripts/deployment/preflight.sh`](../scripts/deployment/preflight.sh).
3. Для текущей single-VM схемы использовать [`yandex/README.md`](yandex/README.md).
4. После deploy выполнить health, test alert и restore gates.
5. Для переноса перейти в [`../migration/README.md`](../migration/README.md).

Корневой `docker-compose.yml` не подменяет production runbook; текущий pilot path зафиксирован в `deploy/yandex/`.
