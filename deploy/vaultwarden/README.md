# Vaultwarden — единый secret store

**Что это.** Бесплатная open-source альтернатива Bitwarden Cloud
(`github.com/dani-garcia/vaultwarden`, AGPL-3.0). API-совместима с
оригинальными клиентами Bitwarden (desktop / mobile / browser extension) —
меняется только `Server URL` в настройках клиента. Bitwarden Send,
Organizations, Collections, 2FA, attachments — всё доступно без подписки
(в Bitwarden Cloud Free лимит — 2 пользователя на Organization).

Хранит: пароли админов клиентов, SSH-ключи, API-токены, AmneziaWG-конфиги.
Организация в виде Collections: `client/<name>`, `internal/infra`,
`internal/billing`.

## Развёртывание

1. Развёрнут на той же VM, что и landing-стек, за Caddy reverse proxy (единая VM в Yandex Cloud).
2. DNS: `vault.msp-claude.online` → А-запись на публичный IP VM.
3. Caddy auto-HTTPS: reverse-proxy vault.msp-claude.online → 127.0.0.1:8180.
4. Added to `deploy/yandex/docker-compose.yml` as `vaultwarden` service (port 127.0.0.1:8180).
5. Сгенерировать `ADMIN_TOKEN`: `openssl rand -base64 48`.
6. Зайти в `/admin`, пригласить первого пользователя (владельца).
7. Отключить `SIGNUPS_ALLOWED=false` навсегда.

## Политики

- **Все секреты через Vaultwarden**. Пароли в мессенджерах / заметках — запрещены.
- **2FA обязательна** для всех пользователей.
- **Sharing по Collections**, не по organization целиком.
- **Bitwarden Send** для временной передачи секретов клиенту (TTL,
  опциональный пароль на ссылку, max access count). Поддерживается
  Vaultwarden с v1.21.0 — у нас актуальная 1.32+, фича включена.
- **Аудит доступа**: раз в квартал пересматриваем, кто к чему имеет доступ.

## Бэкапы

- `./data/db.sqlite3` → daily restic → S3 (отдельный бакет от landing).
- Retention: 90 дней.
- Test-restore: ежемесячно.
