# role: `base_hardening`

> Надстройка над `baseline`. Применяется на **тенант-хостах** (клиентских серверах), где нужна более жёсткая hardening-политика, чем на нашей инфре.

## Что делает

1. Отключает неиспользуемые firewall-порты (оставляет только SSH + явно разрешённые).
2. Выключает и `mask` сервисы: `avahi-daemon`, `cups`, `rpcbind`, `nfs-common` (если клиенту они не нужны — проверяй `host_vars`).
3. `sysctl`: `net.ipv4.conf.all.rp_filter=1`, `net.ipv4.tcp_syncookies=1`, `kernel.dmesg_restrict=1`, `kernel.kptr_restrict=2`.
4. `/etc/login.defs`: `PASS_MAX_DAYS=90`, `PASS_MIN_LEN=14`.
5. Удаляет unused users (`games`, `news`, `uucp`) — если включён флаг `base_hardening_remove_unused_users`.
6. Audit-rules для PCI-like: `-w /etc/passwd -p wa -k identity`, exec-monitoring и т.д. (дополняет baseline).

## Переменные

- `base_hardening_disable_services` (list) — сервисы под `systemctl disable --now` + `mask`
- `base_hardening_sysctl` (dict) — ключ/значение в `/etc/sysctl.d/99-mspshield.conf`
- `base_hardening_remove_unused_users` (bool, default false) — опасно включать на prod без теста

## Почему отдельная роль, а не в baseline

Baseline — «одинаково у всех, включая нашу инфру». Base_hardening — то, что нельзя применять на bastion/landing (сломает функциональность: landing.nginx слушает 443, monitoring — 9090, итд.). Поэтому играется только по тенантам.
