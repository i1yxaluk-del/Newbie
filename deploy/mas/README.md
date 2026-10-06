# MSPShield: Matrix Authentication Service (MAS)

Делегированная авторизация Matrix (OAuth 2.0 / OIDC) для homeserver `m.msp-claude.online`.
Публичный адрес сервиса: **https://bastion.msp-claude.online/** (листенер 127.0.0.1:8899, за Caddy).

## Состав (на ВМ)

- `/opt/mas/docker-compose.yml` — контейнеры `msp-mas` (ghcr.io/element-hq/matrix-authentication-service,
  пин по digest; v1.26.0) и `msp-mas-db` (postgres:16-alpine), сеть `msp-matrix`.
- `/opt/mas/config.yaml` — конфиг MAS (600, владелец 65532; внутри `secrets`, `matrix.secret`).
- `/opt/mas/.env` — `MAS_DB_PASSWORD`, `MAS_PORTAL_CLIENT_ID`, `MAS_PORTAL_CLIENT_SECRET`
  (тот же client прокинут в портал приглашений: `/opt/matrix-invite/.env` → `MAS_CLIENT_ID/MAS_CLIENT_SECRET`).
- Порта для портала (только локально): `127.0.0.1:8898` → adminapi+health (внутренний листенер).

## Эксплуатация

```bash
cd /opt/mas
sudo docker compose ps
sudo docker compose run --rm --no-deps mas config check --config /config.yaml
sudo docker compose run --rm --no-deps mas doctor --config /config.yaml
sudo docker compose run --rm --no-deps mas database migrate --config /config.yaml
```

Admin API для портала: `http://127.0.0.1:8898/api/admin/v1` (Bearer = client_credentials c scope `urn:mas:admin`).

## Миграция пользователей (выполнена 06.10.2026)

```bash
# проверка и сухой прогон (Synapse может работать)
sudo docker run --rm -u 65532:65532 --network msp-matrix \
  -v /opt/mas/config.yaml:/config.yaml:ro \
  -v /opt/matrix/homeserver.yaml:/synapse-hs.yaml:ro \
  ghcr.io/element-hq/matrix-authentication-service@sha256:e089f1048a1d4a9a492ed17b9fe759100f1bd619407b001f5927928d88b780c4 \
  syn2mas check --config /config.yaml --synapse-config /synapse-hs.yaml

# боевая миграция — Synapse ОСТАНОВЛЕН, конфиг Synapse уже с matrix_authentication_service
# (см. deploy/matrix/homeserver.yaml), пароли переносятся (bcrypt v1 + unicode_normalization)
```

## Откат (если понадобится вернуть локальную авторизацию Synapse)

1. Бэкапы конфигов: `/opt/matrix/homeserver.yaml.pre-mas-*`, `/etc/caddy/Caddyfile.bak-flip-*`.
2. В homeserver.yaml: убрать блок `matrix_authentication_service`, вернуть `password_config.enabled: true`.
3. Caddy: убрать маршрут `@mas` на m.* (login/logout/refresh → Synapse), перезагрузить.
4. `sudo docker compose stop mas mas-db` (в /opt/mas), рестарт Synapse.

## Безопасность

- Секреты — только в `/opt/mas/*` (600) и `/home/ubuntu/msp-deploy-secrets.txt` ([MAS]).
- adminapi не выставлен в интернет (только 127.0.0.1:8898).
- rate_limiting MAS включён (логин/регистрация/восстановление — дефолтные лимиты).
- Для серверных операций портала используются короткоживущие personal-sessions с немедленным revoke.
- Регистрация — только по инвайт-токенам (`password_registration_token_required: true`).

## purge-user.sh (06.10.2026)

`/opt/mas/purge-user.sh <login>` — полное удаление записи (MAS + Synapse) с освобождением логина:
удаляет пользователя во всех связанных таблицах MAS и Synapse, чистит профиль/директорию/девайсы;
если в Synapse была «живая» запись — перезапускает Synapse для сброса кэшей.

## Русские/упрощённые страницы MAS (06.10.2026)

- Шаблоны и переводы монтируются из /opt/mas/templates и /opt/mas/translations (см. compose).
- base.html форсирует русский язык; consent.html упрощён: «Вход» + кнопка «Войти», без ссылок на приложение.
- Пересборка оверрайдов: deploy/mas/overrides/apply-overrides.sh.
