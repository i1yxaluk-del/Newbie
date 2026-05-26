# role: `monitoring_agent`

> node_exporter + promtail на клиентских хостах (и на нашем landing/bastion).
> Prometheus на нашем monitoring-VM скрейпит через WireGuard.

## Что делает

1. Ставит `prometheus-node-exporter` (apt).
2. bind = 127.0.0.1:9100 + firewall allow только из `monitoring_agent_scraper_cidrs` (наш WG-mgmt).
3. Разворачивает `promtail` (binary из GH-releases) → читает `/var/log/syslog`, `/var/log/auth.log`, `/var/log/mspshield/*.log`.
4. `promtail` шлёт на `{{ monitoring_agent_loki_url }}` (наш Loki на monitoring-VM).

## Переменные

- `monitoring_agent_scraper_cidrs` (default `["10.9.0.0/24"]`) — откуда пустить на 9100
- `monitoring_agent_loki_url` (default `http://10.9.0.20:3100/loki/api/v1/push`)
- `monitoring_agent_extra_logs` (list, default `[]`) — дополнительные файлы для promtail

## Telegraf?

Не используем. Один node_exporter + promtail достаточно для Bronze-Silver. Gold может добавить `collectd` / `wazuh-agent` — но это отдельные роли.
