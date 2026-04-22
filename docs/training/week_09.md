# Week 9 · Ansible + IaC

## Цель

Писать свои Ansible playbooks / roles. Работать с Terraform в режиме
read-and-modify (не полный design-from-scratch).

## Задачи

- [ ] Прочитать все наши playbook'и (`technical/0_Common/ansible/`).
- [ ] Сессия с owner: Ansible roles, variables, facts, handlers — 2
      часа.
- [ ] Написать свою роль `ssh_hardening` и применить на test-VM.
- [ ] Прочитать `infra/terraform/main.tf` построчно, разобрать с
      owner каждый ресурс.

## Production

- [ ] Пройти `patch_nondisruptive.yml` на 2-3 Bronze-клиентах без
      supervision.
- [ ] Добавить в существующую роль новую task (например, установка
      node_exporter).

## Read

- [Ansible best practices](https://docs.ansible.com/ansible/latest/tips_tricks/ansible_tips_tricks.html).
- Official Terraform tutorials (1-2 quickstarts).

## Check-in

1. Разница `when:` vs `failed_when:` vs `changed_when:`?
2. Что такое `handlers` и когда они срабатывают?
3. Почему Terraform требует backend (S3/local)?

## DoD

- Написал и применил свою Ansible-роль.
- Применил patch-playbook на 2+ клиентах.
- Понимает структуру Terraform main + variables.
