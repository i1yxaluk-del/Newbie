# Скрипты и проверки

[← Главная](../README.md) · [Карта](../docs/NAVIGATION.md)

| Раздел | Назначение |
|---|---|
| [`deployment/`](deployment/) | preflight production-среды |
| [`production-readiness/`](production-readiness/) | внешний scan и readiness evidence |
| `validate_*` | CI-инварианты business/MAX/operations |
| `validate_markdown_links.py` | проверка переходов в основных MD-оглавлениях |
| `kaiten_bootstrap.py` | начальная настройка Kaiten |
| `max_setup_webhook.py` | настройка webhook, не авторизация userbot |

Перед запуском откройте связанный runbook. Не выводите `.env`, токены и session data в терминал или CI-log.
