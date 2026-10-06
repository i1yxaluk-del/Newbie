# Matrix-стек MSPShield (Synapse + PostgreSQL + Element Web)

Параллельный мессенджер к XMPP: **Matrix** — homeserver `m.msp-claude.online`,
веб-клиент `e.msp-claude.online`. Развёрнут 06.10.2026 на VM `msp-cloud-vm` (cloud.ru).

## Состав

| Компонент | Образ | Порт (локально) | Домен |
|---|---|---|---|
| Synapse | matrixdotorg/synapse | 127.0.0.1:8008 | m.msp-claude.online |
| PostgreSQL 16 | postgres:16-alpine | — (внутренний) | — |
| Element Web | vectorim/element-web | 127.0.0.1:8082 | e.msp-claude.online |

Caddy: `m.` → 8008 (+ `/.well-known/matrix/client`), `e.` → 8082. Наружу только 443.
Федерация выключена, публичная регистрация выключена (аккаунты создаёт администратор).

## Деплой (как разворачивалось)

1. `/opt/matrix/`: `docker-compose.yml` + `homeserver.yaml` (из шаблона, `__...__` заменяются
   секретами) + `element-config.json`. Порты — только на 127.0.0.1 (наружу через Caddy).
2. Секреты: DB password, registration_shared_secret, macaroon/form — генерируются;
   `turn_shared_secret` — **тот же**, что у coturn (`static-auth-secret` в `/etc/turnserver.conf`).
3. Сид: `docker run --rm -v /opt/matrix/data:/data -e SYNAPSE_SERVER_NAME=m.msp-claude.online \
   -e SYNAPSE_REPORT_STATS=no matrixdotorg/synapse:latest generate` — создаёт `log.config`,
   signing key и т.д.; затем `chown -R 991:991 /opt/matrix/data`.
4. **Грабли:** в сгенерированном `log.config` файловый обработчик пишет в `/homeserver.log`
   (корень контейнера, туда нет прав) → контейнер падает в рестарт-цикл с `PermissionError`.
   Лечится заменой на `/data/homeserver.log`.
5. `cd /opt/matrix && docker compose up -d`.

## Пользователи

Публичная регистрация выключена. Новый пользователь:

```bash
docker exec msp-synapse register_new_matrix_user -u ИМЯ -p ПАРОЛЬ [-a] \
  -c /data/homeserver.yaml http://localhost:8008
```

(без `-a` спросит «Make admin [no]:» — в скриптах отвечать `echo no |`).

Аккаунты на 06.10.2026: `admin` (администратор), `test1` — пароли в
`~/msp-deploy-secrets.txt` раздел `[MATRIX]` на VM.

## Проверка

```bash
curl -s https://m.msp-claude.online/_matrix/client/versions
curl -s -o /dev/null -w '%{http_code}\n' https://e.msp-claude.online/
```

## Дальше

- Push-уведомления: UnifiedPush через наш ntfy (https://push.msp-claude.online).
- Интеграция приглашений в портал (создание Matrix-аккаунтов из админки/XMPP-кабинета).
- Медиа: лимит 100 МБ, автоочистка (30 дней локальные, 7 дней удалённые).
- Звонки: через общий coturn (turn_uris в homeserver.yaml).

## Приватность каталога пользователей

- В поиске (Element → «Начать чат») видны **только пользователи, с которыми есть общая комната** —
  то есть те, кого вы добавили или кто добавил вас. «Всех подряд» сервер не показывает.
- За это отвечает `user_directory.search_all_users: false` в `homeserver.yaml`.
  Не включать `true` на приватном сервере — иначе в каталоге видны все аккаунты.
- Изменение применяется после перезапуска контейнера `msp-synapse`.
