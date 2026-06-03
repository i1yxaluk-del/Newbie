# R-site-down — Site Down

| | |
|---|---|
| **Alert** | `SiteDown` |
| **Severity** | P1 |
| **Expression** | `probe_success{job=~"blackbox-http|blackbox-https-strict"} == 0` for 2m |
| **Summary** | Сайт недоступен более 2 минут |

## Диагностика

1. `curl -sI https://msp-claude.online` — что отвечает Caddy?
2. `docker logs msp-caddy --tail 50` — логи Caddy
3. `docker ps | grep caddy` — жив ли Caddy
4. Проверить DNS: `dig msp-claude.online`

## Устранение

1. Если Caddy упал: `docker restart msp-caddy`
2. Если SSL ошибка: `caddy validate --config /etc/caddy/Caddyfile`
3. Если upstream недоступен: проверить backend контейнер
4. Проверить UFW: `sudo ufw status`
5. Проверить AmneziaWG: `awg show`
