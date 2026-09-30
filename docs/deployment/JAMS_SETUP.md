# JAMS / Jami-инфраструктура (пилот)

Развёрнуто 30.09.2026 на ВМ `msp-cloud-vm` (130.193.49.21). Self-hosted Jami:
**JAMS** (управление аккаунтами) + **coturn** (TURN) + **OpenDHT** (bootstrap + DHT Proxy),
всё за стандартным **Caddy** (вместо nginx из типового плана).

## Хосты (Namecheap: A → 130.193.49.21)

| Хост | Назначение | Сейчас отдаёт |
|---|---|---|
| `m.msp-claude.online` | JAMS Web UI | JAMS (127.0.0.1:8081) |
| `dht.msp-claude.online` | DHT Proxy REST | dhtnode (127.0.0.1:8888) |
| `turn.msp-claude.online` | coturn | сертификат для TLS; TURN 3478/5349 |
| `names.msp-claude.online` | Name Service (этап 2) | заглушка (сертификат выпущен) |
| `invite.msp-claude.online` | Портал приглашений (этап 2) | заглушка |
| `push.msp-claude.online` | UnifiedPush (этап 3) | заглушка |

## Порты (SG `msp-sg` + ufw)

- TURN: `3478` tcp/udp, `5349` tcp/udp, ретрансляция `49160-49250/udp`;
- OpenDHT: `4222` tcp/udp;
- 8081/8888 наружу НЕ открыты — только через Caddy.

## JAMS

- Исходники: `https://git.jami.net/savoirfairelinux/jami-jams` (на GitHub зеркала нет).
- Требования сборки: **JDK 26** (Temurin в `/opt/jdk26`), Maven, Node.js (использован Node 20).
- Сборка:
  ```bash
  cd /opt/jams-src/jams-react-client
  npm ci --legacy-peer-deps
  NODE_OPTIONS=--openssl-legacy-provider npm run build
  mkdir -p ../jams-server/src/main/resources/webapp
  cp -r build/* ../jams-server/src/main/resources/webapp/
  cd .. && JAVA_HOME=/opt/jdk26 mvn clean package -DskipTests
  ```
- Дистрибутив `jams/` → `/opt/jams` (пользователь `jams`); служба `jams.service`; порт **8081** (8080 занят админкой Stalwart).
- Грабли (уже учтены):
  - лаунчер JAMS запускает сервер дочерним `java` из PATH — в unit обязательны `Environment=JAVA_HOME=/opt/jdk26` и PATH с JDK 26;
  - `npm ci` требует `--legacy-peer-deps` (React 19 в зависимостях);
  - `react-dropzone@20` требует Node ≥22 — на Node 20 собирается с предупреждением EBADENGINE (работает).
- Первичный мастер пройден **программно** (эндпоинты UI): `PUT /api/install/start` {username,password} → `POST /api/install/ca` (self-signed, 10 лет) → `POST /api/install/auth` (`type: LOCAL`) → `POST /api/install/settings` (`serverDomain=https://m.msp-claude.online`, `reverseProxy=true`, `crlLifetime=3600000`, `deviceLifetime`/`userLifetime` = 1 год).
- Проверка: `curl -s http://127.0.0.1:8081/api/info` → `{"installed":"true"}`; логин `POST /api/login`.
- Артефакты установки: `/opt/jams/{CA.pem, keystore.jks, config.json, oauth.key, jams.crl}` — в бэкап!
- Пароль администратора — в `~/msp-deploy-secrets.txt` на ВМ (секция [JAMS]).

## coturn

- `/etc/turnserver.conf`: realm/server-name `turn.msp-claude.online`, `external-ip=130.193.49.21`, relay-порты 49160-49250, fingerprint.
- Пользователь: `sudo turnadmin -a -u jami -p '<пароль>' -r turn.msp-claude.online` (пароль — в secrets).
- Сертификат: копируется из хранилища Caddy скриптом `/usr/local/bin/coturn-cert-sync.sh` (cron 04:30; рестарт только при изменении).
- Проверка: `turnadmin -l -r turn.msp-claude.online` → `jami[turn.msp-claude.online]`.

## OpenDHT (dhtnode)

- Установка: `apt install dhtnode` (2.3.1), пользователь `dht`.
- Служба `dhtnode.service`:
  `tail -f /dev/null | /usr/bin/dhtnode -v -p 4222 -b bootstrap.jami.net --proxyserver 8888`
  - **`tail -f /dev/null |` обязателен**: без stdin dhtnode выходит по EOF (проверено);
  - `--proxyserver 8888` — REST API DHT Proxy для мобильных клиентов.
- Проверка: `curl http://127.0.0.1:8888/` → JSON (node_id, пиры); публично — `https://dht.msp-claude.online`.

## Caddy

- Блоки `m.`/`dht.`/`turn.`/`names.`/`invite.`/`push.` добавлены в `/etc/caddy/Caddyfile` (стиль `{$MSP_DOMAIN}`, сертификаты выпускаются автоматически).
- `turn.*` — блок-«заглушка» нужен только для выпуска сертификата (его использует coturn).

## Настройка клиентов Jami (пилот)

1. JAMS: `https://m.msp-claude.online` — вход под выданной учёткой.
2. Bootstrap: `dht.msp-claude.online:4222` (или `130.193.49.21:4222`).
3. DHT Proxy: `https://dht.msp-claude.online`.
4. TURN: `turn.msp-claude.online:3478` (user `jami`, пароль из secrets; TLS 5349).

## Сервисы этапа 2–3 (реализовано 30.09.2026)

Стек `jami-services` (docker compose; код — `deploy/jami-services/`, развёрнут в `/opt/jami-services`):

| Компонент | Порт (локально) | Домен |
|---|---|---|
| nameservice (FastAPI + Postgres) | 8889 | https://names.msp-claude.online |
| invite portal (FastAPI + SQLite + QR) | 8890 | https://invite.msp-claude.online |
| ntfy (UnifiedPush для Android) | 8891 | https://push.msp-claude.online |

- **Name Service**: `GET /name/{username}` → Jami ID (`text/plain`; `?json=1` → JSON). Регистрация — только админом: `sudo /opt/jami-services/bin/jami-name-add <username> <jami-id>`. Аудит в таблице `audit`; rate-limit 60 req/min на GET и 10/min на записи.
- **Invite portal**: `sudo /opt/jami-services/bin/jami-invite-create "Имя" <jami-id> [ttl_hours] [note]` → ссылка `/i/<token>`: детект iOS/Android, кнопки App Store / Google Play, QR (`/i/<token>/qr.png`, содержимое `jami:<id>`; см. также «Приглашения v2»), кнопка «Я добавил(а) контакт» помечает токен использованным; истёкшие/использованные токены показывают понятный статус.
- **UnifiedPush**: ntfy-сервер на `push.` — для Android-сборок Jami с UnifiedPush; дистрибутор ntfy указывает на `https://push.msp-claude.online`. На пилоте доступ открыт; ACL/токены — на этапе эксплуатации.
- Креды: `~/msp-deploy-secrets.txt` → [JamiServices]. Данные: `/opt/jami-services/{pgdata,invite-data,ntfy-cache}` (в restic через `/opt`; `backup.sh` делает `pg_dump` nameservice).

## Always-online Jami daemon (реализовано 30.09.2026)

- Пакет `jami-daemon` из официального репо (`dl.jami.net/stable/ubuntu_22.04`, ключ 64CD5FA175348F84 с keyserver.ubuntu.com).
- Пользователь `jamiserver`; служба `jamiserver.service` (`launchjami`: `dbus-launch` → `/usr/libexec/jamid`).
- Техаккаунт создан **headless через D-Bus** (`ConfigurationManager.addAccount`): AccountId `386142fdf8b64c01`, **Jami ID: `7b1cf78913278f3b854286e36abf82b723ce971b`** (alias «MSPShield always-online»).
  - Добавьте этот ID контактом в нужные группы (с телефона) — узел будет синхронизировать историю офлайн-участникам.
- Данные: `/home/jamiserver/.local/share/jami` (бэкапится через `/home`).
- Второй узел для резервирования — остаётся на этап эксплуатации.

## Обновление этапов (статус на 30.09.2026)

1. ✅ Always-online daemon — один узел работает (второй — позже).
2. ✅ Name Service (`names.`).
3. ✅ Портал приглашений (`invite.`).
4. ✅ UnifiedPush/ntfy (`push.`).
5. ⏸ TURN на отдельную ВМ — отложено по решению владельца (остаётся на текущей ВМ).
6. ✅ Бэкапы: `/opt/jams` (CA/ключи), `/etc/turnserver.conf`, база dhtnode и БД новых сервисов — в restic.

## Кастомизация клиентов: blueprint вместо дефолтов (30.09.2026)

**Почему клиент показывает `bootstrap.jami.net` / `turn.jami.net`**: это встроенные дефолты Jami. Пока аккаунту не назначена политика с нашими серверами, клиент использует публичные bootstrap/DHT Proxy (`dhtproxy.jami.net`) и TURN (`turn.jami.net`). JAMS раздаёт настройки через **blueprints** (привязываются к группам).

Сделано:
- Blueprint **`MSPShield`**: `turnEnabled=true`, `turnServer=turn.msp-claude.online` (user `jami`), `proxyEnabled=true`, `proxyServer=dht.msp-claude.online`.
- Группа **`MSPShield`** (blueprint = MSPShield); пользователи добавлены.
- При следующем синке настроек клиент переключится на наши TURN/DHT Proxy (кнопка «Обновить настройки» в клиенте ускоряет; bootstrap-список перекрывается параметром DHT Proxy).

Проверка в JAMS: разделы Blueprints → `MSPShield`, Groups → `MSPShield`.

## Админка приглашений (веб) (30.09.2026)

- <https://invite.msp-claude.online/admin?token=INVITE_ADMIN_TOKEN> — форма создания (имя, Jami ID, TTL, заметка), список со статусами, копирование ссылки, удаление; одноразовость и QR — как раньше.
- Токен — в `~/msp-deploy-secrets.txt` [JamiServices]. CLI-скрипты остаются: `bin/jami-invite-create`, `bin/jami-name-add`.

## Мониторинг Jami (30.09.2026)

- **Blackbox**: внешние проверки `m.`, `names./health`, `invite./health`, `push./v1/health`, `dht./` + алерт `JamiEndpointDown`.
- **jami-exporter** (контейнер в `jami-services`, :8892): `jami_jams_up`, `jami_jams_users_total`, `jami_jams_devices_total`, `jami_dht_up`, `jami_dht_peers_good`, `jami_service_up{name}`; scrape-джоб `jami` в Prometheus (сеть msp-monitoring).
- **Host-метрики** (cron раз в минуту → node_exporter textfile): `jami_turn_sessions`, `jami_dht_proxy_clients`, `jami_daemon_up`.
- **Grafana**: дашборд «Jami: сервисы и нагрузка» (папка MSPShield): пользователи, устройства, TURN-сессии, DHT Proxy клиенты, пиры DHT, health сервисов, внешние endpoint.
- Алерты: `monitoring/prometheus/rules/jami.yml` (JamiServiceDown, JamsDown, JamiDhtDown, JamiDaemonDown, JamiEndpointDown).

**Как считаются «онлайн-клиенты»**: прямого счётчика «онлайн» у JAMS API нет — используем три практичных показателя: активные **TURN-сессии** (медиа/звонки), установленные TCP-соединения к **DHT Proxy**, и общее число **устройств** в JAMS (`devices_total`). Вместе они дают картину нагрузки на инфраструктуру.

## Пользователи JAMS: создание, пароль, отзыв (30.09.2026)

- **Создание**: JAMS → Users → «Новый пользователь» (логин и пароль задаёт админ).
- **Пароль** нужен клиенту не только для входа: им расшифровывается архив аккаунта. При первом подключении нового устройства Jami показывает окно «миграции» с запросом пароля — это нормальный шаг онбординга (вводится один раз). Если окно повторяется при каждом запуске/настройки не открываются — пароль введён неверно или импорт прерван: удалите аккаунт в клиенте и подключитесь заново; при необходимости смените пароль в JAMS (Change password) и введите новый.
- **«Удаление» пользователя = Revoke**: JAMS отзывает сертификат (CRL) — пользователь сразу теряет доступ, но запись остаётся в списке (сделано осознанно, для аудита; жёсткого delete нет). Отозванных можно скрыть галочкой «Hide revoked users» в списке Users.
- Смена пароля: Users → пользователь → Change password.

## Приглашения v2: JAMS-данные, QR-формат, карточки контактов (30.09.2026)

- В приглашение добавлены поля: **JAMS-логин** и (опционально) **пароль нового пользователя** — показываются получателю на странице `/i/<token>` с кнопками копирования; добавлен блок-инструкция «Подключение к JAMS».
- QR-код контакта теперь кодирует **`jami:<40-hex>`** (канонический URI Jami; прежний вариант `jami://` клиенты не распознавали). QR рисуется только при указанном Jami ID приглашающего; иначе — подсказка.
- Новые публичные инструменты: `/qr/<jami-id>.png` — PNG с QR; `/c/<jami-id>` — «карточка контакта» (QR + ID + как добавить), удобно пересылать.
- CLI: `bin/jami-invite-create "Имя" <jami-id> [ttl] [note] [jams_username] [jams_password]`.
- Проверено: payload = `jami:<id>` (md5 совпал с эталонной генерацией), тесты страниц/QR/удаления пройдены.

## Как добавить контакт (коротко)

1. Пользователь сообщает свой Jami ID (в клиенте: Настройки аккаунта → «Поделиться»; ID — 40 hex) или QR.
2. Сгенерируйте карточку: `https://invite.msp-claude.online/c/<id>` — отправьте ссылку или сам QR.
3. Получатель сканирует QR в Jami («Добавить контакт» → «Сканировать») или вставляет ID вручную.
- Jami ID можно взять： (а) в клиенте (Настройки аккаунта → «Поделиться»); (б) автоматически — в **личном кабинете портала**: JAMS формирует ID при создании учётки, и кабинет показывает его с QR-кодом (см. «Портал v3»).

## Портал v3: самообслуживание + личный кабинет (30.09.2026)

Новый сквозной сценарий онбординга:

1. **Приглашение создаёт админ или любой пользователь.** В админке есть «Профиль приглашающего по умолчанию» (имя + Jami ID) — подставляется автоматически, вручную ID вводить не нужно. Из кабинета приглашение всегда создаётся от имени владельца (с его ID).
2. **Получатель открывает `/i/<token>`** и создаёт учётную запись прямо на странице (логин, пароль, имя). Портал сам заводит пользователя в JAMS через admin API; приглашение сразу становится использованным (одноразовое).
3. Показывается страница с **данными подключения** (сервер/логин/пароль с копированием) и ссылкой на **личный кабинет** `/u/<ctoken>`.
4. В кабинете: **Jami ID** с QR и ссылкой-карточкой, кнопка «Обновить Jami ID», создание/удаление своих приглашений.
5. Честное ограничение: **автоподключения по ссылке у Jami нет** — клиент не умеет «сам настроиться» по URL (проверено по исходникам: схема `jami:` обрабатывает только поиск контактов). Портал минимизирует ручной ввод: все поля копируются в один тап.

Техника: портал ходит в JAMS admin API (`POST /api/login` → JWT, `POST /api/admin/user`, `GET /api/admin/user?username=`, groups/members); креды — `JAMS_ADMIN_USER`/`JAMS_ADMIN_PASS` в `/opt/jami-services/.env` (root:600, из секретов [JAMS]). При регистрации портал автоматически добавляет пользователя в группу MSPShield — blueprint с нашими TURN/DHT применяется сам.

Ограничение JAMS: **логины не переиспользуются** — после revoke запись остаётся, повторно занять то же имя нельзя. Удаления пользователей нет (только отзыв сертификата). Практика: выдавать новые логины (`ilya2`, `ilya.mspshield` и т.п.).
