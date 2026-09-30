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

## Следующие этапы

1. **Always-online Jami daemon**: `apt install jami-daemon`; техаккаунт создаётся на Linux-ПК, затем `rsync` `~/.local/share/jami` и `~/.config/jami` на пользователя `jamiserver`, служба `launchjami` (шаблон — в плане внедрения от 30.09).
2. **Name Service** (`names.`): мини-сервис Postgres + REST `GET /name/{username}` → Jami ID; регистрация только админом JAMS, аудит, rate-limit.
3. **Портал приглашений** (`invite.`): одноразовые токены, QR, детект платформы; «Заявка использована» после подтверждения.
4. **UnifiedPush** (`push.`) для Android.
5. При росте (>30 юзеров): вынести TURN на отдельную ВМ; второй DHT/bootstrap.
6. Бэкап: включить в restic `/opt/jams` (CA/ключи!), `/etc/turnserver.conf`, базы dhtnode и будущих сервисов.
