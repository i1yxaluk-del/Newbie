# MSPShield / «МСП Облако»

Управляемый IT-сервис для малого и среднего бизнеса: monitoring, backup, защищённый доступ и реакция в договорное окно.

> **Начинайте не с поиска файлов, а с нужного маршрута ниже.** Полная карта: [`docs/NAVIGATION.md`](docs/NAVIGATION.md).

## Маршруты работы

| Что нужно сделать | Точка входа | Дальше по маршруту |
|---|---|---|
| Продать услугу | [`commercial/README.md`](commercial/README.md) | цена → квалификация → discovery → КП → договор |
| Подготовить договор | [`contracts/README.md`](contracts/README.md) | единый MSA → Order Form → DOCX |
| Развернуть production | [`docs/deployment/README.md`](docs/deployment/README.md) | preflight → deploy → health → alert → restore evidence |
| Перенести VM | [`migration/README.md`](migration/README.md) | backup → restore → gates → DNS switch |
| Подключить клиента | [`docs/operations/README.md`](docs/operations/README.md) | Won → onboarding → steady state → offboarding |
| Разобрать инцидент | [`docs/runbooks/README.md`](docs/runbooks/README.md) | severity → runbook → evidence → postmortem |
| Настроить MAX | [`docs/MAX_SETUP.md`](docs/MAX_SETUP.md) | webhook → ручная авторизация → test alert |
| Обучить Junior | [`docs/training/README.md`](docs/training/README.md) | guide → weeks → labs → допуск |
| Разрабатывать приложение | [`docs/NAVIGATION.md#разработка`](docs/NAVIGATION.md#разработка) | backend/frontend → tests → PR |
| Понять готовность | [`docs/PROJECT_8_OF_10.md`](docs/PROJECT_8_OF_10.md) | gates → evidence → ограничения |

## По ролям

- **Owner / инженер:** [`docs/deployment/README.md`](docs/deployment/README.md) → [`docs/operations/README.md`](docs/operations/README.md).
- **Product / Service Manager:** [`commercial/README.md`](commercial/README.md) → [`docs/operations/CLIENT_LIFECYCLE.md`](docs/operations/CLIENT_LIFECYCLE.md).
- **Junior Engineer:** [`docs/training/README.md`](docs/training/README.md) → [`docs/runbooks/README.md`](docs/runbooks/README.md).
- **Разработчик:** [`docs/NAVIGATION.md#разработка`](docs/NAVIGATION.md#разработка).

## Структура без путаницы

| Каталог | Что внутри | Читать или выполнять |
|---|---|---|
| [`commercial/`](commercial/README.md) | прайс, воронка, scripts, объявления, КП | читать и копировать в сделку |
| [`contracts/`](contracts/README.md) | один договор и DOCX builder | заполнять после КП |
| [`docs/`](docs/README.md) | оглавления, runbooks, обучение, процессы | начинать с index-файлов |
| [`deploy/`](deploy/README.md) | Compose/Docker/Nginx production-код | выполнять только через deploy runbook |
| [`migration/`](migration/README.md) | backup/restore/migration scripts | выполнять только по migration gate |
| [`services/`](services/README.md) | MAX alerter и VM watcher | код сервисов и их README |
| [`scripts/`](scripts/README.md) | preflight и validators | инструменты, не бизнес-документация |
| [`technical/`](technical/README.md) | технический состав тарифов | reference после прайса |
| [`infra/`](infra/README.md) | Terraform/IaC альтернативного контура | не основной pilot path |
| `backend/`, `frontend/` | приложение и тесты | разработка |
| `analysis/`, `marketing/`, `docs/sales/` | исторические материалы/redirects | не источник истины |

## Приоритет при конфликте

1. код и CI-инварианты;
2. канонический документ из [`docs/README.md`](docs/README.md);
3. профильный index/README;
4. исторические audit, analysis и postmortem.

Gold On Demand доступен только после capacity gate. Monitoring 24/7 не означает 24/7 реакцию, если это отдельно не активировано в Gold Order Form.

## Проверка ссылок

```bash
python scripts/validate_markdown_links.py
```

CI не позволит слить изменение с тупиковой ссылкой в основных оглавлениях.
