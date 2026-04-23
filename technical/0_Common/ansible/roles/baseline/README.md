# role: `baseline`

> Применяется на **всех** хостах (первое `site.yml`-play). Это «всё что должно быть у любой машины до появления ролей-специализаций».

## Что делает

1. `apt update` + `unattended-upgrades` (auto security updates)
2. Базовые пакеты: `curl`, `git`, `htop`, `tmux`, `ufw`, `fail2ban`, `jq`, `dnsutils`, `net-tools`
3. SSH hardening (PermitRootLogin no, PasswordAuthentication no, AllowUsers ubuntu)
4. `ufw` default deny incoming / allow outgoing + SSH (22) + tenant-scoped ports через `ufw_extra_ports`
5. `fail2ban` с sshd-jail
6. Таймзона Europe/Moscow + NTP (systemd-timesyncd)
7. auditd включён с минимальными правилами (execve, identity, privileged)

## Переменные (`defaults/main.yml`)

- `baseline_timezone` (default `Europe/Moscow`)
- `baseline_ufw_allowed_ports` (list, default `[22]`)
- `baseline_ufw_extra_ports` (list, default `[]`) — добавь в host_vars для конкретного хоста
- `baseline_admin_user` (default `ubuntu`)

## Handlers

- `restart ssh`, `restart fail2ban`, `restart auditd`

## Как использовать

В `site.yml` уже подключён для `hosts: all`. Точечно: `ansible-playbook site.yml --tags baseline`.

## Known limitations (v4.3)

- На Astra Linux ветка `apt unattended-upgrades` может отличаться — тестировалось на Ubuntu 22.04. При развёртывании на Astra заменить pkgname на astra-specific, либо добавить `when: ansible_distribution != 'Astra Linux'`.
- SELinux/AppArmor не трогаем — предполагаем дефолт AppArmor на Ubuntu.
