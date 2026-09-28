# R-site-down · Сайт недоступен

| | |
|---|---|
| **Alert** | `SiteDown` |
| **Severity** | P1 |
| **Expression** | `probe_success{job=~"blackbox-http|blackbox-https-strict"} == 0` for 2m |
| **Summary** | Сайт недоступен более 2 минут |

## Диагностика

1. `curl -sI https://msp-claude.online` — что отвечает Caddy?
2. `sudo journalctl -u caddy -n 50` — логи Caddy
3. `systemctl status caddy` — жив ли Caddy
4. Проверить DNS: `dig msp-claude.online`
5. Если из одной сети 200, а из другой timeout: `nc -vz <IP> 443` из обеих сетей. ICMP при этом может работать — это блокировка/маршрут, а не сервис (см. `../deployment/MIGRATION_RUNBOOK.md` §9.2).

## Устранение

1. Если Caddy упал: `sudo systemctl restart caddy`
2. Если SSL ошибка: `caddy validate --config /etc/caddy/Caddyfile`
3. Если upstream недоступен: проверить backend контейнер
4. Проверить UFW: `sudo ufw status`
5. Проверить AmneziaWG: `awg show`
6. Если IP недостижим из сети клиента — пересоздать зарезервированный адрес и переключить DNS (см. MIGRATION_RUNBOOK §9.2).
