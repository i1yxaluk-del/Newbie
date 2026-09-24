# Pre-onboarding checklist

Day 1 не начинается, пока обязательные пункты не подтверждены evidence.

## Contract и scope

- [ ] подписаны MSA, SLA/tariff appendix и DPA при обработке ПДн;
- [ ] оплачены согласованные setup работы;
- [ ] зафиксированы in-scope hosts/services и исключения;
- [ ] определены owner клиента, P1 contacts и change window;
- [ ] monitoring 24/7 не назван engineer on-call 24/7.

## Доступ и данные

- [ ] inventory получен через защищённый канал;
- [ ] credentials хранятся в Vaultwarden, MFA включена;
- [ ] выданы минимальные роли; Domain Admin не является default-требованием;
- [ ] определены ПДн-периметр, retention и право обработки;
- [ ] доступ MSP можно отозвать без потери клиентского доступа.

## Backup/monitoring readiness

- [ ] согласованы RPO/RTO и restore target;
- [ ] известны объём, окна и стоимость хранения;
- [ ] подготовлены Prometheus targets/labels без клиентских секретов в Git;
- [ ] согласованы alert channels: MAX + email, Telegram не единственный канал;
- [ ] создан Kaiten tenant/project с next action и due date.

## Gate

Если нет scope, backup target, ответственного клиента, окна или rollback — onboarding откладывается. Ответственный за gate: owner; Junior только собирает evidence.
