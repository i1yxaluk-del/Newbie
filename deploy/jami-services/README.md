# jami-services — вспомогательные сервисы Jami (пилот)

Стек (docker compose) для self-hosted Jami: **Name Service**, **портал приглашений**, **UnifiedPush (ntfy)**.

## Состав

| Сервис | Код | Порт (локально) | Домен |
|---|---|---|---|
| nameservice | `nameservice/` (FastAPI + Postgres) | 8889 | `names.msp-claude.online` |
| invite | `invite/` (FastAPI + SQLite + QR) | 8890 | `invite.msp-claude.online` |
| ntfy | образ binwiederhier/ntfy | 8891 | `push.msp-claude.online` |
| jami-exporter | `exporter/` (метрики JAMS/DHT для Prometheus) | 8892 | — (внутр., сеть `msp-monitoring`) |
| postgres | postgres:16-alpine (БД `names`) | — | — |

## Развёртывание на ВМ

```bash
sudo mkdir -p /opt/jami-services
sudo cp -r <этот каталог>/. /opt/jami-services/
cd /opt/jami-services
# .env (root:root 600) — PGPASSWORD/NAMES_ADMIN_TOKEN/INVITE_ADMIN_TOKEN
# сгенерён на ВМ; значения — в ~/msp-deploy-secrets.txt [JamiServices]
sudo docker compose up -d --build
```

## Админ-операции

```bash
# Зарегистрировать короткое имя (только админ):
sudo /opt/jami-services/bin/jami-name-add <username> <jami_id_40hex>

# Создать одноразовое приглашение:
# (можно передать JAMS-логин и пароль нового пользователя — покажутся на странице приглашения)
sudo /opt/jami-services/bin/jami-invite-create "Имя приглашающего" <jami_id_40hex> [ttl_hours] [note] [jams_username] [jams_password]
```

## Заметки

- Все данные — в `/opt/jami-services/{pgdata,invite-data,ntfy-cache}` (входят в restic-бэкап по `/opt`; `backup.sh` дополнительно делает `pg_dump` nameservice).
- ntfy на пилоте открыт (чтение/подписка); ACL/токены — на этапе эксплуатации.
- Веб-админка приглашений: `/admin?token=…` (создание/список/удаление); карточки контактов: `/c/<jami-id>`, QR: `/qr/<jami-id>.png` (payload `jami:<id>`).
- Name Service отдаёт `text/plain` (протокол Jami), `?json=1` — JSON.
