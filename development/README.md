# Разработка

[← Главная](../README.md) · [Документация](../docs/README.md) · [Маркетинг](../marketing/README.md)

## Приложение

| Задача | Рабочий каталог | Особенность |
|---|---|---|
| API и интеграции | [`backend/`](../backend/) | local `server:app`, production `secure_server:app`, MongoDB, один outbox worker |
| Landing и админка | [`frontend/`](../frontend/) | CRA/CRACO, Yarn 1.22.22, Node 20 в CI; контент `src/content/landing.ru.json` |
| Отдельные сервисы | [`services/`](../services/README.md) | MAX Bot API backend и MAX userbot — разные контуры |

## Инфраструктура и инструменты

- [Deployment-код](../deploy/README.md) → [карта сервисов](../docs/deployment/SERVICE_MAP.md) → [runbook](../docs/deployment/README.md).
- [Backup и миграция](../migration/README.md).
- [Скрипты и валидаторы](../scripts/README.md); источник CI — [quality.yml](../.github/workflows/quality.yml).
- [Wazuh lab: конфигурации и инструменты](../deploy/wazuh-lab/README.md); [курс Junior](../docs/training/wazuh/README.md).
- [Технические шаблоны тарифов](../technical/README.md), [альтернативный IaC](../infra/README.md).

Исполняемые каталоги сохранены на прежних путях: Docker build contexts, CI, bind mounts и remote runbooks используют их напрямую. Этот раздел — единая точка входа разработки, а не второй экземпляр кода.

## Проверки из корня

```text
python scripts/validate_markdown_links.py
python scripts/validate_business_consistency.py
python scripts/validate_max_consistency.py
python scripts/validate_operational_consistency.py
python scripts/validate_deployment_freshness.py
pytest -q backend/tests/test_kaiten_integration.py backend/tests/test_alertmanager.py backend/tests/test_max_integration.py backend/tests/test_secure_delivery.py scripts/tests/test_backup_calendar.py
python -m compileall -q backend scripts deploy/wazuh-lab
```

Frontend из `frontend/`: `yarn install --frozen-lockfile`, затем `CI=true yarn build` (PowerShell: сначала `$env:CI='true'`). Live HTTP suite `test_mspshield_api.py` пишет данные: отдельно проверить target и разрешение. Production-публикация не выполняется автоматически после изменения файлов или Git push.

## Локально, GitHub и VM

Это три независимых состояния. Проверить `git status`, diff и результаты проверок; затем отдельное решение на commit/push. Публикация frontend — готовая сборка, backup и проверка через [publish_landing.py](../scripts/deployment/publish_landing.py). Доставка на VM не отправляет изменения на GitHub.
