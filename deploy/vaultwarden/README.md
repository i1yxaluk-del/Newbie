# Vaultwarden — единый secret store

Хранит: пароли админов клиентов, SSH-ключи, API-токены, WireGuard-конфиги.
Организация в виде Collections: `client/<name>`, `internal/infra`,
`internal/billing`.

## Развёртывание

1. Отдельная VM (2 vCPU / 4 GB / 40 GB) в Yandex Cloud, отдельная security-group.
2. DNS: `vault.mspshield.ru` → А-запись на публичный IP VM.
3. Let's Encrypt: `certbot --nginx -d vault.mspshield.ru`.
4. `docker compose up -d`.
5. Сгенерировать `ADMIN_TOKEN`: `openssl rand -base64 48`.
6. Зайти в `/admin`, пригласить первого пользователя (владельца).
7. Отключить `SIGNUPS_ALLOWED=false` навсегда.

## Политики

- **Все секреты через Vaultwarden**. Пароли в мессенджерах / заметках — запрещены.
- **2FA обязательна** для всех пользователей.
- **Sharing по Collections**, не по organization целиком.
- **Bitwarden send** для временной передачи секретов клиенту (с истечением).
- **Аудит доступа**: раз в квартал пересматриваем, кто к чему имеет доступ.

## Бэкапы

- `./data/db.sqlite3` → daily restic → S3 (отдельный бакет от landing).
- Retention: 90 дней.
- Test-restore: ежемесячно.
