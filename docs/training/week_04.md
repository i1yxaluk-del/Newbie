# Week 4 · Backup & Recovery (restic + DR)

## Цель

Уметь установить restic на новый tenant, настроить расписание, провести
smoke DR, объяснить клиенту RTO/RPO.

## Задачи

- [ ] Прочитать `technical/0_Common/ansible/playbooks/backup_install.yml`.
- [ ] Прочитать `technical/0_Common/scripts/dr_drill.sh`.
- [ ] Развернуть restic на своей test-VM от нуля:
      - init repo к S3 (тестовый bucket);
      - написать systemd-timer;
      - сделать первый бэкап;
      - ВОССТАНОВИТЬ один файл.
- [ ] Сессия с owner: 30 мин про restic internals (pack files,
      snapshots, prune).
- [ ] Провести DR-drill на одном из клиентов вместе с owner (ты
      ведёшь, owner слушает).

## Production

- [ ] Пройти R-03 (backup failed) на тестовом scenario: симулируй
      ошибку, исправь по runbook'у.
- [ ] Подготовить следующий monthly_report для 1 Bronze-клиента
      (`monthly_report.py`), сдать owner на ревью.

## Read

- [Restic docs: "Operations"](https://restic.readthedocs.io/en/latest/060_forget.html) — forget + prune политики.
- Note: наша retention policy описана в `docs/onboarding/day_1_7_runbook.md`.

## Check-in

1. Что такое `restic prune` и почему он дорогой?
2. RTO и RPO — формулируй для Bronze / Silver / Gold.
3. Что делать, если `restic check` показал `repository broken`?

## DoD

- Самостоятельно провёл DR smoke-test одного клиента.
- Monthly report сдан и принят.
- Понимает политику forget/prune.
