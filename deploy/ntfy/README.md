# ntfy (UnifiedPush) — push.msp-claude.online

Стек push-уведомлений для XMPP-клиентов (Conversations/Monal, UnifiedPush).

Раньше контейнер жил внутри `jami-services` (как `jami-ntfy`). После де-комиссии Jami
(06.10.2026) вынесен в отдельный compose — **`/opt/ntfy`** на VM, контейнер `msp-ntfy`.

## Деплой

```bash
cd /opt/ntfy && docker compose up -d
```

Systemd-юнит не нужен (`restart: unless-stopped`). Caddy: `push.msp-claude.online` → `127.0.0.1:8891`.
Данные: `/opt/ntfy/cache` (перенесены из `/opt/jami-services/ntfy-cache`).
