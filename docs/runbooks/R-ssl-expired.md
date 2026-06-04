# R-ssl-expired · SSL-сертификат истёк

| | |
|---|---|
| **Alert** | `SSLExpired` |
| **Severity** | P1 |
| **Expression** | `(probe_ssl_earliest_cert_expiry - time()) < 0` for 5m |
| **Summary** | SSL-сертификат ИСТЁК — сайт недоступен для пользователей |

## Диагностика

1. `echo | openssl s_client -connect msp-claude.online:443 2>/dev/null | openssl x509 -noout -dates`
2. `docker logs msp-caddy --tail 100 | grep -iE 'cert|tls|acme'`
3. Caddy auto-TLS должен был обновить — почему не обновился?
4. Проверить /var/lib/caddy/.local/share/caddy/ — cert storage

## Устранение

1. Немедленно: `docker restart msp-caddy` — Caddy попробует renew
2. Если не помогло: `docker exec msp-caddy caddy reload --config /etc/caddy/Caddyfile`
3. Если ACME fail: проверить порт 80 для HTTP challenge
4. Если Let's Encrypt rate limit: использовать staging cert временно
5. Экстренный план: CloudFlare или другой CDN с auto-TLS
6. После: проверить `curl -sI https://msp-claude.online`
