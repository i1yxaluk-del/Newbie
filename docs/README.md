# Документация MSPShield — оглавление

Эта страница — единая точка входа. Если два документа противоречат друг другу, приоритет имеют отмеченные ниже источники истины.

## Источники истины

| Область | Канонический документ |
|---|---|
| цены, лимиты, маржа | [`PRICING_SOURCE_OF_TRUTH.md`](PRICING_SOURCE_OF_TRUTH.md) |
| readiness и незакрытые gate | [`PROJECT_8_OF_10.md`](PROJECT_8_OF_10.md) |
| договоры | [`../contracts/canonical/`](../contracts/canonical/) |
| production deployment | [`deployment/README.md`](deployment/README.md) |
| фактические уроки deployment | [`deployment/DEPLOYMENT_LESSONS.md`](deployment/DEPLOYMENT_LESSONS.md) |
| миграция | [`../migration/README.md`](../migration/README.md) |
| MAX alerts | [`MAX_SETUP.md`](MAX_SETUP.md) |
| обучение и допуск | [`training/README.md`](training/README.md) |
| клиентский lifecycle | [`operations/CLIENT_LIFECYCLE.md`](operations/CLIENT_LIFECYCLE.md) |

## По ролям

### Owner / инженер

1. [`deployment/README.md`](deployment/README.md)
2. [`deployment/DEPLOYMENT_LESSONS.md`](deployment/DEPLOYMENT_LESSONS.md)
3. [`runbooks/README.md`](runbooks/README.md)
4. [`checklists/README.md`](checklists/README.md)

### Product / Service Manager

1. [`operations/PILOT_OPERATING_MODEL.md`](operations/PILOT_OPERATING_MODEL.md)
2. [`sales/new_lead_workflow.md`](sales/new_lead_workflow.md)
3. [`onboarding/README.md`](onboarding/README.md)
4. [`operations/CLIENT_LIFECYCLE.md`](operations/CLIENT_LIFECYCLE.md)

### Junior Engineer

1. [`training/JUNIOR_OPERATIONS_GUIDE.md`](training/JUNIOR_OPERATIONS_GUIDE.md)
2. [`training/README.md`](training/README.md)
3. [`training/DEPLOYMENT_MIGRATION_LABS.md`](training/DEPLOYMENT_MIGRATION_LABS.md)
4. [`runbooks/README.md`](runbooks/README.md)

## Статус уроков сентября 2026

| Урок | Реализация | Документация | Junior practice |
|---|---|---|---|
| BOM/CRLF и обязательные env | deploy preflight | deployment lessons | Lab 1 |
| Postbox SMTP credentials | Compose override + fail-fast entrypoint | monitoring section | Lab 2 |
| согласованный backup Docker volumes | staging archives, не raw live-copy | backup section | Lab 3 |
| перенос MAX session | backup/restore scripts | MAX guide | Lab 4 |
| dynamic Mongo container ID | backup/restore scripts | migration guide | Lab 3 |
| TCP/443 вместо ICMP | VM watcher | deployment lessons | Lab 5 |
| YC config из user profile | VM watcher | deployment lessons | Lab 5 |
| host-key verification | migration uploader | migration guide | security gate |

## Правило обновления

Новый production-урок нельзя оставлять только в README. Он должен попасть минимум в:

1. код или автоматическую проверку;
2. canonical runbook;
3. backup/rollback, если меняются данные;
4. Junior lab или стоп-условие;
5. CI validator, если правило можно проверить статически.
