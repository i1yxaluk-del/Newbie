# Онбординг клиента — маршрут

1. [`pre_onboarding_checklist.md`](pre_onboarding_checklist.md) — договор, scope, доступы, ПДн, окно.
2. [`day_1_7_runbook.md`](day_1_7_runbook.md) — безопасное подключение по дням.
3. [`welcome_package.md`](welcome_package.md) — правила коммуникации клиента.
4. [`../operations/CLIENT_LIFECYCLE.md`](../operations/CLIENT_LIFECYCLE.md) — переход в регулярную эксплуатацию.

## Обязательный technical gate

- read-only discovery до изменений;
- отдельные Vaultwarden credentials и MFA;
- backup не считается готовым без test restore;
- alert test должен дойти минимум в MAX и email;
- dashboard не публикуется анонимно;
- production change содержит owner, timestamp, команды, ожидаемый результат и rollback;
- клиентские файлы и ПДн не попадают в этот репозиторий.

Срок 3–7 дней является ориентиром. Onboarding завершается по evidence, а не по календарю.
