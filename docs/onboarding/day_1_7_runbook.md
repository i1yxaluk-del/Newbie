# Day 1–7 onboarding runbook

Срок ориентировочный; завершение определяется acceptance evidence.

## Day 1 — discovery без изменений

- подтвердить tenant/hostname/contact matrix;
- собрать read-only inventory и baseline;
- сохранить credentials в Vaultwarden;
- завести risks/technical debt в Kaiten;
- не ротировать и не отключать ничего без отдельного change.

## Day 2 — backup

- внедрить policy по согласованному RPO/retention;
- выполнить первый backup;
- восстановить выборочный файл в отдельный target;
- записать RTO/RPO, команды и evidence.

## Day 3 — monitoring

- подключить exporters и dashboards;
- проверить backup freshness metric;
- выполнить контролируемый alert;
- подтвердить доставку в MAX и email;
- не публиковать Grafana анонимно.

## Day 4 — security baseline

- SSH/root/MFA/firewall/time sync/updates;
- каждое изменение — change record и rollback;
- findings, выходящие за тариф, не исправлять скрытно: оформить recommendation/add-on.

## Day 5 — service-specific checks

- Bronze: OS, storage, certificates, key services;
- Silver: AD/GPO/database только в согласованном scope;
- Gold не активировать до отдельного operational gate.

## Day 6 — handover

- передать клиенту support route и escalation matrix;
- показать dashboard и test restore result;
- проверить, что client owner умеет открыть P1;
- провести внутренний handover Junior → reviewer.

## Day 7 — acceptance

- закрыть gaps или согласовать deadlines;
- клиент подтверждает dashboard, alert и restore evidence;
- перевести Kaiten в operation;
- SLA начинает измеряться с явно указанного времени.

## Acceptance criteria

1. inventory и scope подтверждены;
2. least-privilege access и MFA;
3. backup + clean restore evidence;
4. MAX/email alert test;
5. клиентский support drill;
6. open risks имеют owner и due date;
7. change history заполнена.
