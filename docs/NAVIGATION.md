# Карта репозитория

[← Главная](../README.md) · [Оглавление документации](README.md)

Эта карта разделяет **документы**, **исполняемый код** и **историю**. В каждой работе сначала открывается index, затем конкретная инструкция.

## Продажи

```text
commercial/README.md
  → PRICING.md
  → SALES_FUNNEL.md
  → SALES_PLAYBOOK.md
  → PROPOSAL.md
  → contracts/README.md
  → MSP_SERVICE_AGREEMENT.md
```

- [Коммерческое оглавление](../commercial/README.md)
- [Единый договор](../contracts/README.md)
- После оплаты: [клиентский lifecycle](operations/CLIENT_LIFECYCLE.md)

## Развёртывание

```text
docs/deployment/README.md
  → DEPLOY_RUNBOOK.md
  → scripts/deployment/preflight.sh
  → deploy/yandex/README.md
  → health/test alert/restore evidence
```

- [Оглавление deployment](deployment/README.md)
- [Что является кодом deployment](../deploy/README.md)
- [Уроки deployment](deployment/DEPLOYMENT_LESSONS.md)

## Миграция и восстановление

```text
migration/README.md
  → restic-backup.sh
  → restore-on-vm.sh
  → health/alert/restore gates
  → DNS switch
```

- [Миграция VM](../migration/README.md)
- [Пошаговый migration runbook](deployment/MIGRATION_RUNBOOK.md)
- [Disaster recovery](deployment/disaster_recovery.md)

## Эксплуатация клиента

```text
Won
  → operations/CLIENT_LIFECYCLE.md
  → onboarding/README.md
  → runbooks/README.md
  → checklists/README.md
  → report / renewal / offboarding
```

- [Оглавление operations](operations/README.md)
- [Onboarding](onboarding/README.md)
- [Runbooks](runbooks/README.md)
- [Регулярные проверки](checklists/README.md)

## Monitoring и MAX

```text
Prometheus → Alertmanager → msp-max-alerter:9095/alert
→ pymax userbot → /session/max.db → MAX
```

- [MAX setup](MAX_SETUP.md)
- [Сервисы](../services/README.md)
- [MAX alerter](../services/max_alerter/README.md)
- [Monitoring runbooks](runbooks/README.md)

## Обучение и допуск

- [Программа Junior](training/README.md)
- [Как работать с production](training/JUNIOR_OPERATIONS_GUIDE.md)
- [Deployment/migration labs](training/DEPLOYMENT_MIGRATION_LABS.md)
- [Runbooks](runbooks/README.md)

## Разработка

| Зона | Путь | Перед PR |
|---|---|---|
| Backend/API/integrations | [`../backend/`](../backend/) | unit tests, compileall, env example |
| Landing/admin | [`../frontend/`](../frontend/) | yarn build, контент и consent |
| MAX/VM services | [`../services/`](../services/) | service tests и README |
| Compose/Nginx | [`../deploy/`](../deploy/) | preflight и production-config |
| CI/validators | [`../scripts/`](../scripts/) | локальный запуск validator |

## Что не является источником истины

`analysis/`, старые `marketing/`, `docs/sales/`, audit reports и postmortem объясняют историю, но не определяют текущие цену, SLA или deployment-команды. Их ссылки должны вести обратно в канонический index.

## Если ссылка сломана

1. Не угадывать соседний файл.
2. Вернуться в этот index.
3. Запустить `python scripts/validate_markdown_links.py`.
4. Исправить ссылку и ближайший index в одном PR.
