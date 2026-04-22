# Week 6 · Security (hardening, SIEM basics)

## Цель

Применять security-хrategies осознанно. Уметь поднять minimal SIEM
(Wazuh или Loki+Alerts). Понимать 152-ФЗ в контексте нашей работы.

## Задачи

- [ ] Прочитать `deploy/nginx/mspshield.conf` (внимательно к CSP и
      security headers).
- [ ] Сессия с owner: 1 час про SSH hardening, fail2ban, ufw. 1 час
      про 152-ФЗ baseline.
- [ ] На test-VM: провести full hardening (SSH config, PAM, auditd,
      fail2ban), сравни до/после через `lynis audit system`.
- [ ] Прочитать R-01 (Ransomware) и обсудить с owner: что самое
      сложное в этом runbook'е.

## Production

- [ ] Провести security-audit одного Bronze-клиента: SSH-конфиги,
      fail2ban-логи, updates, firewall; зафиксировать findings в Kaiten.
- [ ] Закрыть 1-2 P3 security-related (force password rotation,
      revoke user access).

## Read

- [NIST SSH config guidelines](https://www.ssh.com/academy/ssh/sshd_config).
- Briefly: [Wazuh intro](https://wazuh.com/documentation/ossec/getting-started/) для Gold (опционально).

## Check-in

1. Что входит в твой SSH hardening checklist (5+ пунктов)?
2. Зачем `audit` логи кроме journalctl?
3. Как мы защищаем персональные данные в 152-ФЗ (основные принципы)?

## DoD

- Lynis-score test-VM поднят до 80+ после hardening.
- Security-audit одного Bronze подан.
- Может запустить R-01 по шагам.
