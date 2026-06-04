# R-vault-down — Vaultwarden Down

| | |
|---|---|
| **Alert** | `VaultwardenDown` |
| **Severity** | P1 |
| **Expression** | `probe_success{job="blackbox-internal", instance="http://vaultwarden:80"} == 0` for 3m |
| **Summary** | Менеджер паролей Vaultwarden недоступен более 3 минут |

## Диагностика

1. `docker ps | grep vaultwarden`
2. `docker logs msp-vaultwarden-1 --tail 50`
3. `curl -s http://127.0.0.1:8180/alive` — health check
4. Проверить attached volume для data

## Устранение

1. Рестарт: `cd /opt/msp/Newbie/deploy/yandex && docker compose restart vaultwarden`
2. Если data volume повреждён: восстановить из restic backup
3. Проверить SIGNUPS_ALLOWED и ADMIN_TOKEN в compose
4. Проверить Caddy route: vault.msp-claude.online → :8180
5. После рестарта: `curl -sI https://vault.msp-claude.online/alive`
