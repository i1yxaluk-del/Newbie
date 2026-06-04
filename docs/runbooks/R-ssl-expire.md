# R-ssl-expire — SSL Expiring Soon

| | |
|---|---|
| **Alert** | `SSLExpiringSoon` |
| **Severity** | P2 |
| **Expression** | `(probe_ssl_earliest_cert_expiry - time()) / 86400 < 14` for 1h |
| **Summary** | SSL-сертификат истекает менее чем через 14 дней |

## Диагностика

1. `echo | openssl s_client -connect msp-claude.online:443 2>/dev/null | openssl x509 -noout -dates`
2. `curl -sI https://msp-claude.online` — проверить сертификат
3. Caddy auto-TLS обычно обновляет автоматически
4. `docker logs msp-caddy | grep -i cert`

## Устранение

1. Caddy должен автообновить — проверить почему не обновился
2. Force renew: `docker exec msp-caddy caddy reload --config /etc/caddy/Caddyfile`
3. Если Caddy не управляет доменом: certbot вручную
4. Проверить что порт 80 доступен для ACME challenge
5. После обновления: проверить даты сертификата
