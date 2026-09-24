# Документация MSPShield — оглавление

[← Главная](../README.md) · [Полная карта](NAVIGATION.md)

## Источники истины

| Область | Канонический документ |
|---|---|
| цены, лимиты, маржа | [`../commercial/PRICING.md`](../commercial/PRICING.md) |
| воронка и sales scripts | [`../commercial/README.md`](../commercial/README.md) |
| договор | [`../contracts/MSP_SERVICE_AGREEMENT.md`](../contracts/MSP_SERVICE_AGREEMENT.md) |
| readiness и gates | [`PROJECT_8_OF_10.md`](PROJECT_8_OF_10.md) |
| production deployment | [`deployment/README.md`](deployment/README.md) |
| миграция | [`../migration/README.md`](../migration/README.md) |
| операции клиента | [`operations/README.md`](operations/README.md) |
| MAX alerts | [`MAX_SETUP.md`](MAX_SETUP.md) |
| обучение и допуск | [`training/README.md`](training/README.md) |

## По задаче

- Продажи: [`../commercial/README.md`](../commercial/README.md)
- Договор: [`../contracts/README.md`](../contracts/README.md)
- Deploy: [`deployment/README.md`](deployment/README.md)
- Migration/DR: [`../migration/README.md`](../migration/README.md)
- Клиент: [`operations/README.md`](operations/README.md)
- Инцидент: [`runbooks/README.md`](runbooks/README.md)
- Регулярные работы: [`checklists/README.md`](checklists/README.md)
- Junior: [`training/README.md`](training/README.md)

## По ролям

### Owner / инженер

1. [`deployment/README.md`](deployment/README.md)
2. [`operations/README.md`](operations/README.md)
3. [`runbooks/README.md`](runbooks/README.md)
4. [`checklists/README.md`](checklists/README.md)

### Product / Service Manager

1. [`../commercial/README.md`](../commercial/README.md)
2. [`operations/PILOT_OPERATING_MODEL.md`](operations/PILOT_OPERATING_MODEL.md)
3. [`operations/CLIENT_LIFECYCLE.md`](operations/CLIENT_LIFECYCLE.md)
4. [`onboarding/README.md`](onboarding/README.md)

### Junior Engineer

1. [`training/JUNIOR_OPERATIONS_GUIDE.md`](training/JUNIOR_OPERATIONS_GUIDE.md)
2. [`training/README.md`](training/README.md)
3. [`training/DEPLOYMENT_MIGRATION_LABS.md`](training/DEPLOYMENT_MIGRATION_LABS.md)
4. [`runbooks/README.md`](runbooks/README.md)

## Правило обновления

Новый production-урок должен попасть в код/control, canonical runbook, backup/rollback, Junior lab и CI validator, если правило проверяется статически. Новая ветка документации обязана иметь README/index и ссылку из `NAVIGATION.md`.
