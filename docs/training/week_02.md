# Week 2 · Linux deep-dive + наш baseline

## Цель

Понимать наш production baseline (Ubuntu 22.04 + конкретные роли).
Уметь провести первичную диагностику без помощи.

## Задачи

- [ ] Прочитать `technical/0_Common/ansible/playbooks/site.yml` и
      explain back: что делают какие роли.
- [ ] Развернуть локальную копию baseline в VM (Vagrant / VirtualBox),
      запустить playbook вручную.
- [ ] Сессия с owner: 1 час про systemd, 1 час про networking в Linux.
- [ ] Пройти checklist из R-06 (disk space critical) на своей VM:
      создать проблему, решить по runbook'у.

## Задачи на production (под supervision)

- [ ] Провести patch-проверку одного Bronze-клиента (`patch_nondisruptive.yml`
      в dry-run, затем apply).
- [ ] Закрыть 2-3 P3 тикета (password reset, add user, disk cleanup).

## Read

- `man systemd.service` (обзорно).
- `man journalctl` (разбор примеров).
- Briefly: Ubuntu release notes 22.04.

## Check-in

1. Можешь объяснить словами, чем `sshd` отличается от `systemd-sshd@`
   (обслуживающих).
2. Что делает `journalctl --vacuum-time=7d`?
3. Зачем `sudo systemctl daemon-reload` после правки unit-файла?

## DoD

- Baseline playbook разворачивается локально из твоих рук.
- Закрыл 2 P3 самостоятельно (без pairing).
- Обновил свой bluebook.
