# R-imap-down · IMAP недоступен

| | |
|---|---|
| **Alert** | `StalwartImapDown` |
| **Severity** | P1 |
| **Expression** | `probe_success{job="blackbox-imap"} == 0` for 3m |
| **Summary** | Stalwart IMAP недоступен — почта не работает |

## Диагностика

1. `docker ps | grep stalwart`
2. `nc -zv 127.0.0.1 993` — IMAPS порт открыт?
3. `docker logs msp-stalwart-1 --tail 50`
4. Проверить port mappings в compose

## Устранение

1. Рестарт: `cd /opt/msp/Newbie/deploy/yandex && docker compose restart stalwart`
2. Если порт не проброшен: проверить ports section в compose
3. Проверить UFW: `sudo ufw status | grep 993`
4. Если RocksDB повреждён: восстановить volume из restic
5. Тест: `openssl s_client -connect msp-claude.online:993`
