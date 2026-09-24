# MSPShield / «МСП Облако»

Управляемый IT-сервис для малого и среднего бизнеса в РФ: мониторинг, резервное копирование, защищённый доступ и реакция в согласованное рабочее окно.

> Monitoring 24/7 означает круглосуточную автоматику, а не круглосуточное дежурство инженера. Gold и 24/7 engineer on-call закрыты до отдельного operational gate.

## Быстрый маршрут

| Задача | Начать здесь | Затем |
|---|---|---|
| понять проект | [`docs/README.md`](docs/README.md) | [`docs/PROJECT_8_OF_10.md`](docs/PROJECT_8_OF_10.md) |
| развернуть production | [`docs/deployment/README.md`](docs/deployment/README.md) | [`docs/deployment/DEPLOYMENT_LESSONS.md`](docs/deployment/DEPLOYMENT_LESSONS.md) |
| перенести VM | [`migration/README.md`](migration/README.md) | [`migration/restore-on-vm.sh`](migration/restore-on-vm.sh) |
| работать с клиентом | [`docs/operations/CLIENT_LIFECYCLE.md`](docs/operations/CLIENT_LIFECYCLE.md) | [`docs/onboarding/README.md`](docs/onboarding/README.md) |
| продавать и считать цену | [`commercial/README.md`](commercial/README.md) | [`commercial/PRICING.md`](commercial/PRICING.md) |
| подготовить договор | [`contracts/README.md`](contracts/README.md) | [`contracts/MSP_SERVICE_AGREEMENT.md`](contracts/MSP_SERVICE_AGREEMENT.md) |
| обучить Junior | [`docs/training/README.md`](docs/training/README.md) | [`docs/training/DEPLOYMENT_MIGRATION_LABS.md`](docs/training/DEPLOYMENT_MIGRATION_LABS.md) |
| настроить MAX | [`docs/MAX_SETUP.md`](docs/MAX_SETUP.md) | [`services/max_alerter/README.md`](services/max_alerter/README.md) |

## Структура

| Каталог | Назначение |
|---|---|
| `commercial/` | единственные актуальные прайс, воронка, скрипты, КП и объявления |
| `contracts/` | один полный договор, приложения и DOCX builder |
| `backend/`, `frontend/` | приложение и тесты |
| `deploy/`, `migration/`, `infra/` | production, перенос и IaC |
| `services/` | MAX alerter и VM watcher |
| `technical/`, `docs/` | эксплуатация, обучение и runbooks |
| `scripts/` | проверки и bootstrap |

## Production flow

```text
Изменение → preflight → backup/rollback → deploy → health checks
→ test alert → restore evidence → change record → наблюдение
```

```bash
bash scripts/deployment/preflight.sh
```

## Безопасные правила

- Не коммитить `.env`, state, session DB, токены и backup credentials.
- Не копировать старые `.env` на новую VM.
- Не отключать SSH host-key verification.
- Не считать snapshot доказанным backup без restore evidence.
- Junior не меняет production вне уровня допуска и change record.
- Активное обследование клиента выполняется только после письменного разрешения.
