# ntfy (UnifiedPush) — push.msp-claude.online

Стек push-уведомлений для XMPP-клиентов (Conversations/Monal, UnifiedPush).

Контейнер `msp-ntfy` живёт в отдельном compose — **`/opt/ntfy`** на VM.

## Деплой

```bash
cd /opt/ntfy && docker compose up -d
```

Systemd-юнит не нужен (`restart: unless-stopped`). Caddy: `push.msp-claude.online` → `127.0.0.1:8891`.
Данные: `/opt/ntfy/cache`.
