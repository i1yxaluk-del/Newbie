# R-smtp-down · SMTP недоступен

| | |
|---|---|
| **Alert** | `StalwartSmtpDown` |
| **Severity** | P1 |
| **Expression** | `probe_success{job="blackbox-smtp"} == 0` for 3m |
| **Summary** | Stalwart SMTP недоступен — отправка почты не работает |

## Диагностика

1. `docker ps | grep stalwart`
2. `nc -zv 127.0.0.1 465` — SMTPS порт
3. `nc -zv 127.0.0.1 25` — SMTP inbound
4. Проверить Caddy не занял ли порт 443 вместо Stalwart
5. UFW rules для 25, 465

## Устранение

1. Рестарт: `cd /opt/msp/Newbie/deploy/yandex && docker compose restart stalwart`
2. Если port conflict: Caddy и Stalwart оба на 443 — проверить Caddyfile
3. Проверить UFW: `sudo ufw status`
4. Проверить MX записи: `dig MX msp-claude.online`
5. Тест: `swaks --to alert@msp-claude.online --server msp-claude.online:25`
