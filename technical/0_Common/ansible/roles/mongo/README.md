# role: `mongo`

> MongoDB 7 для landing-бэкенда. Одиночная нода (не реплика) — нагрузка landing минимальная, RPO-12ч закрывается `backup_agent`.

## Что делает

1. Добавляет официальный APT-репо MongoDB 7.0
2. `apt install mongodb-org`
3. bind_ip = `127.0.0.1` (только localhost; FastAPI подключается через `MONGO_URL=mongodb://localhost:27017`)
4. auth enabled, создаёт admin-user из vault
5. systemd enabled + started
6. smoke: `mongosh --quiet --eval 'db.runCommand({ping:1}).ok'` == 1

## Переменные

- `mongo_admin_user` (default `mspshield_admin`)
- `mongo_admin_password` (required, vault)
- `mongo_version` (default `7.0`)
- `mongo_bind_ip` (default `127.0.0.1`)

## Бэкапы

Не в этой роли — см. `restic_client` (снимает `mongodump` в object storage, см. `technical/0_Common/backup/`).
