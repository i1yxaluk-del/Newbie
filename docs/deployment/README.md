# Развёртывание — оглавление

## Канонический pilot path

| Шаг | Документ / инструмент |
|---:|---|
| 1 | [`local_dev.md`](local_dev.md) — локальная проверка приложения |
| 2 | [DEPLOY_RUNBOOK.md](DEPLOY_RUNBOOK.md) — пошаговое развёртывание VM с нуля |
| 2 | [`../../deploy/yandex/README.md`](../../deploy/yandex/README.md) — одна production VM |
| 3 | [`../../scripts/deployment/preflight.sh`](../../scripts/deployment/preflight.sh) — env/Compose/security gate |
| 4 | [`DEPLOYMENT_LESSONS.md`](DEPLOYMENT_LESSONS.md) — уроки, превращённые в controls |
| 5 | [`../../migration/README.md`](../../migration/README.md) — перенос VM |
| 5 | [MIGRATION_RUNBOOK.md](MIGRATION_RUNBOOK.md) — пошаговая миграция на новую VM |
| 6 | [`disaster_recovery.md`](disaster_recovery.md) — восстановление |
| 7 | [`troubleshooting.md`](troubleshooting.md) — диагностика |

## Другие сценарии

- [`landing_production.md`](landing_production.md) — Terraform/Ansible вариант; использовать только после отдельного решения перейти с single-VM pilot.
- [`tenant_onboarding.md`](tenant_onboarding.md) — подключение клиентского tenant после подписанного scope.
- [`secrets_management.md`](secrets_management.md) — секреты и ротация.
- [VAULTWARDEN_ORG_RUNBOOK.md](VAULTWARDEN_ORG_RUNBOOK.md) — организация, коллекции и импорт секретов Vaultwarden

## Не смешивать

- backend MAX Bot API для лидов и `msp-max-alerter` для monitoring alerts;
- infrastructure deployment и client onboarding;
- snapshot/backup и доказанный restore;
- исторические команды из postmortem и текущий runbook.

При конфликте документации приоритет: root `README` → этот index → canonical runbook → code/CI.
