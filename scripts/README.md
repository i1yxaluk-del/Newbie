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
| [`backup_calendar.py`](backup_calendar.py) | реальные наблюдения backup → textfile → календарь внутри существующего Backups |
| [`audit_junior_readability.py`](audit_junior_readability.py) | реестр пояснений в исходниках; численные признаки для ручного разбора, не автоматический допуск |
| [`deployment/publish_landing.py`](deployment/publish_landing.py) | публикация готовой сборки со старой версией для rollback |
| [`deployment/integrate_backup_calendar.py`](deployment/integrate_backup_calendar.py) | точечная замена панели live Backups с backup JSON |
| [`deployment/verify_calendar.py`](deployment/verify_calendar.py) | проверка Grafana provisioning и серий без вывода credentials |

Перед запуском откройте связанный runbook. Не выводите `.env`, токены и session data в терминал или CI-log.
