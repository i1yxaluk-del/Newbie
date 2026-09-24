# Жизненный цикл клиента и инструменты

## Сквозной путь

| Этап | Вход | Инструменты | Evidence / выход | Owner |
|---|---|---|---|---|
| Lead | заявка/контакт | landing, backend outbox, Kaiten | карточка с source и next action | Product Manager |
| Qualification | подтверждённая потребность | BANT-скрипт, pre-audit | scope, ограничения, риски | Owner + PM |
| Contract | согласованный scope | canonical MSA/SLA/DPA | подписанные приложения | Owner |
| Pre-onboarding | оплата и доступы | checklist, Vaultwarden | access matrix без секретов в тикете | PM |
| Technical onboarding | change window | Ansible, VPN, restic, Prometheus | baseline, alert test, restore evidence | Engineer |
| Operation | onboarded tenant | Kaiten, Grafana, runbooks, weekly/monthly checklists | tickets, reports, evidence | Service Manager |
| Incident | alert/client report | Alertmanager, MAX/email, P1 runbook | timeline, resolution, postmortem | Incident owner |
| Change | approved request | change record, backup, rollback | before/after evidence | Engineer + reviewer |
| Offboarding | termination notice | access revocation, export, deletion schedule | signed handover | Owner |

## Разделение систем

- **Kaiten** — задачи, SLA timestamps, approvals и next action; не секреты.
- **Vaultwarden** — пароли, токены и recovery codes; не client reports.
- **Git** — templates, code, runbooks; не client-specific inventory и credentials.
- **Grafana/Prometheus** — telemetry; не договорные обещания.
- **MAX/email** — оповещение; source of truth остаётся ticket/change record.
- **Restic/S3** — backup; восстановление подтверждается отдельным evidence.

## Минимальный client dossier

Хранится в приватном клиентском пространстве, не в публичном репозитории:

1. подписанный scope и contact matrix;
2. inventory с владельцем каждого сервиса;
3. data classification и ПДн-периметр;
4. backup policy, RPO/RTO и последнее restore evidence;
5. monitoring targets и alert routes;
6. access matrix с датами ревизии;
7. список open risks/technical debt;
8. change/incident history;
9. offboarding и deletion policy.

## Стоп-условия

Не начинать onboarding или изменение, если нет scope, ответственного клиента, окна, rollback, backup evidence либо законного основания обработки данных.
