# Развёртывание — оглавление

## Канонический pilot path

| Шаг | Документ / инструмент |
|---:|---|
| 1 | [`local_dev.md`](local_dev.md) — локальная проверка приложения |
| 1 | [`SERVICE_MAP.md`](SERVICE_MAP.md) — границы сервисов, зависимости и evidence |
| 2 | [DEPLOY_RUNBOOK.md](DEPLOY_RUNBOOK.md) — пошаговое развёртывание VM с нуля |
| 2 | [`../../deploy/yandex/README.md`](../../deploy/yandex/README.md) — одна production VM |
| 3 | [`../../scripts/deployment/preflight.sh`](../../scripts/deployment/preflight.sh) — env/Compose/security gate |
| 4 | [`DEPLOYMENT_LESSONS.md`](DEPLOYMENT_LESSONS.md) — уроки, превращённые в controls |
| 5 | [`../../migration/README.md`](../../migration/README.md) — перенос VM |
| 5 | [MIGRATION_RUNBOOK.md](MIGRATION_RUNBOOK.md) — пошаговая миграция на новую VM |
| 6 | [`disaster_recovery.md`](disaster_recovery.md) — восстановление |
| 7 | [`troubleshooting.md`](troubleshooting.md) — диагностика |

## Другие сценарии

- [Применение landing, календаря и учебного Wazuh 15.10.2026](ROLLOUT_2026-10-15.md) — фактически проверенные результаты и откат.
- [Прикладные правила и панели Wazuh 16.10.2026](WAZUH_BUSINESS_ROLLOUT_2026-10-16.md) — конкретный прогон, штатные SSH/FIM и ограничения.

- [`landing_production.md`](landing_production.md) — Terraform/Ansible вариант; использовать только после отдельного решения перейти с single-VM pilot.
- [`tenant_onboarding.md`](tenant_onboarding.md) — подключение клиентского tenant после подписанного scope.
- [`secrets_management.md`](secrets_management.md) — секреты и ротация.
- [VAULTWARDEN_ORG_RUNBOOK.md](VAULTWARDEN_ORG_RUNBOOK.md)

## Не смешивать

- backend MAX Bot API для лидов и `msp-max-alerter` для monitoring alerts;
- infrastructure deployment и client onboarding;
- snapshot/backup и доказанный restore;
- исторические команды из postmortem и текущий runbook.

При конфликте источников приоритет у кода и CI, затем канонического документа и профильного index. Название каталога `deploy/yandex/` не доказывает текущего облачного провайдера: есть конфигурация/журнал перехода на Cloud.ru; используйте подтверждённый inventory среды.
