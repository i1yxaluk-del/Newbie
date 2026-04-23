# role: `ad_health_check`

> Silver-only. Проверяет здоровье AD-леса клиента: `dcdiag`-аналог под Linux (cross-platform) + синхронизация `samba-tool`.
> Для Windows DC — роль ставит агента, который раз в час гоняет `dcdiag /c /v` и шлёт в Prometheus text-file collector.

## Что делает (Linux-target, Samba-AD сценарий)

1. Ставит `samba-tool` утилиты
2. Кладёт `/usr/local/bin/ad_health_check.sh` — проверяет: `samba-tool drs showrepl`, `samba-tool dbcheck --cross-ncs`, DNS-SRV-записи, Kerberos-clock skew
3. systemd timer hourly → пишет `/var/lib/node_exporter/textfile/ad_health.prom`
4. Prometheus metric: `ad_health_errors_count{check="replication"}`, `ad_health_last_success_ts`

## Windows-target

Не через Ansible — используется Puppet-агент или RMM (Silver+). См. `docs/runbooks/silver/ad-dc-health.md`.

## Переменные

- `ad_realm` (например `corp.acme.ru`)
- `ad_admin_user` (default `administrator`) — только для dry-run, пароль **не** передаётся (read-only проверки)

## Dependency

`monitoring_agent` должен быть уже раскатан, иначе метрика не уедет в Prometheus.
