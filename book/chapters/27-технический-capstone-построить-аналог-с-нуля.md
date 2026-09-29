# 27. Технический capstone: построить аналог с нуля

> **Учебная ситуация.** Теперь нельзя копировать готовый Compose целиком: нужно доказать перенос модели.

## Главное

Минимальный аналог: public TLS proxy, API, persistent DB, metrics, предупреждение webhook и encrypted резервная копия. Компоненты можно заменить, если объяснены точка связиs и recovery.

Architecture decision сравнивает варианты по требованиям, общая точка отказаs, операционной цене и обратимости. «Популярнее» не является достаточным критерием.

Definition of done включает clean восстановление и handover другому человеку.

## Как это работает

В capstone сначала фиксируются requirements: число пользователей, допустимый downtime, данные, угрозы и budget. Только затем выбираются components. Замена Mongo на PostgreSQL допустима, если перепроектированы schema, резервная копия, health и application доступы, а не просто изменено имя image.

## Пример

```text
Пустая VM → hardening исходное состояние → app/data → TLS → metrics/предупреждениеs
→ резервная копия → destructive test → clean восстановление → handover
```

## Практикум

1. Напишите design до развёртывание.
2. Разверните без копирования project compose.
3. Передайте runbook другому человеку и исправьте непонятные места.

## Если что-то не работает

| Наблюдение | Что это означает | Следующая проверка |
|---|---|---|
| Работает только у автора | нет воспроизводимости. |
| Есть резервная копия, нет восстановление | capstone не принят. |

## Источники проекта

- [docs/deployment/DEPLOY_RUNBOOK.md](https://github.com/i1yxaluk-del/Newbie/blob/89249e43a4e8b2e90d562307ef244ba95288c64c/docs/deployment/DEPLOY_RUNBOOK.md)
- [docs/training/DEPLOYMENT_MIGRATION_LABS.md](https://github.com/i1yxaluk-del/Newbie/blob/89249e43a4e8b2e90d562307ef244ba95288c64c/docs/training/DEPLOYMENT_MIGRATION_LABS.md)

- [Кураторская видеотека и порядок практики](../VIDEO_GUIDE.md)

