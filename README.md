# MSPShield / «МСП Облако»

Управляемый IT-сервис для малого и среднего бизнеса в РФ: мониторинг, резервное копирование, защищённый доступ и реакция в согласованное рабочее окно.

> «Мониторинг 24/7» означает круглосуточную автоматику, а не круглосуточное дежурство инженера. Gold и гарантированное 24/7-реагирование закрыты до отдельного operational gate.

## Быстрый маршрут по репозиторию

| Я хочу… | Начать здесь | Затем |
|---|---|---|
| понять проект и ограничения | [`docs/README.md`](docs/README.md) | [`docs/PROJECT_8_OF_10.md`](docs/PROJECT_8_OF_10.md) |
| развернуть production | [`docs/deployment/README.md`](docs/deployment/README.md) | [`docs/deployment/DEPLOYMENT_LESSONS.md`](docs/deployment/DEPLOYMENT_LESSONS.md) |
| перенести VM | [`migration/README.md`](migration/README.md) | [`migration/restore-on-vm.sh`](migration/restore-on-vm.sh) |
| проверить backup/restore | [`docs/deployment/disaster_recovery.md`](docs/deployment/disaster_recovery.md) | [`technical/0_Common/scripts/dr_drill.sh`](technical/0_Common/scripts/dr_drill.sh) |
| настроить MAX | [`docs/MAX_SETUP.md`](docs/MAX_SETUP.md) | [`services/max_alerter/README.md`](services/max_alerter/README.md) |
| принять нового клиента | [`docs/operations/CLIENT_LIFECYCLE.md`](docs/operations/CLIENT_LIFECYCLE.md) | [`docs/onboarding/README.md`](docs/onboarding/README.md) |
| обучить Junior | [`docs/training/README.md`](docs/training/README.md) | [`docs/training/DEPLOYMENT_MIGRATION_LABS.md`](docs/training/DEPLOYMENT_MIGRATION_LABS.md) |
| нанять инженера | [`docs/hiring/test_task.md`](docs/hiring/test_task.md) | [`docs/hiring/technical_interview.md`](docs/hiring/technical_interview.md) |
| работать с тарифами | [`technical/README.md`](technical/README.md) | [`docs/PRICING_SOURCE_OF_TRUTH.md`](docs/PRICING_SOURCE_OF_TRUTH.md) |
| подготовить договор | [`contracts/README.md`](contracts/README.md) | [`contracts/canonical/`](contracts/canonical/) |

## Структура верхнего уровня

| Каталог | Что в нём | Не хранить |
|---|---|---|
| `backend/`, `frontend/` | приложение и тесты | реальные `.env` |
| `deploy/`, `infra/` | production compose, IaC, установка | state, cloud IDs и ключи |
| `migration/` | перенос данных и проверка новой VM | архивы и credentials |
| `services/` | MAX alerter, VM watcher | session database и токены |
| `technical/` | роли, playbook, тарифные реализации | клиентские секреты |
| `docs/` | процессы, обучение, runbook, продажи | неподтверждённые обещания |
| `contracts/` | канонические шаблоны договоров | подписанные клиентские копии |
| `scripts/` | проверки и bootstrap | некомментированные destructive scripts |

## Канонический production flow

```text
Изменение → preflight → backup/rollback → deploy → health checks
→ тестовый alert → restore evidence → change record → наблюдение
```

```bash
bash scripts/deployment/preflight.sh
```

## Безопасные правила

- Не коммитить `.env`, `.deploy-state.json`, session DB, токены, ключи и backup credentials.
- Не копировать старые `.env` на новую VM: создать новые и проверить обязательные ключи.
- Не использовать `StrictHostKeyChecking=no`; изменение host key проверять через консоль провайдера.
- Не считать snapshot backup успешным без test restore и evidence.
- Junior не меняет production вне уровня допуска и change record.
- Каждый operational script должен иметь русскую шапку: назначение, место запуска, входы, побочные эффекты, проверка и откат.

## Локальный запуск

```bash
git clone https://github.com/i1yxaluk-del/Newbie.git
cd Newbie
cp backend/.env.example backend/.env
docker compose -f deploy/docker-compose.yml up -d mongo
cd backend && pip install -r requirements.txt && uvicorn server:app --reload --port 8001
```

Production запускает `secure_server:app`; порт backend доступен только через reverse proxy.
