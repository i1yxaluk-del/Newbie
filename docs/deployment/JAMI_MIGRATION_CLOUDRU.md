# Jami / JAMS: пересборка на Cloud.ru Evolution

Дополняет [`JAMS_SETUP.md`](JAMS_SETUP.md) (исходное развёртывание на Yandex Cloud) и
[`POSTMORTEM_CLOUDRU_MIGRATION.md`](POSTMORTEM_CLOUDRU_MIGRATION.md).

## Контекст: восстановить было нечего

Данные Jami жили только в restic-бакете старого Yandex Cloud (`mspshield-backups-new`),
доступа к нему нет. Значит — **пересборка с нуля**, а это смена идентичностей:

- новый CA → всем клиентам Jami переподключаться;
- JAMS-логины не переиспользуются (ограничение JAMS) → выдавать новые;
- у always-online узла **новый Jami ID** → контактам добавить его заново.

Инфраструктура уже была готова: A-записи `m./dht./turn./names./invite./push.` → `45.132.176.143`,
порты в SG (`3478`, `5349`, `4222`, `49160-49250`) открыты.

## Порядок развёртывания (проверено)

| Шаг | Скрипт | Что делает |
|---|---|---|
| 1 | [`cloudru-caddy-jami2.sh`](../../migration/cloudru-caddy-jami2.sh) | Caddy-блоки Jami-хостов → выпуск 6 сертификатов |
| 2 | [`cloudru-coturn-dht.sh`](../../migration/cloudru-coturn-dht.sh) + `-fix.sh` | coturn (TURN 3478/5349) + dhtnode (OpenDHT 4222 + DHT Proxy 8888) |
| 3 | [`cloudru-docker-dns-fix.sh`](../../migration/cloudru-docker-dns-fix.sh) | **сначала!** рабочий DNS для Docker (иначе сборка сервисов не пройдёт) |
| 4 | [`cloudru-jams-prep.sh`](../../migration/cloudru-jams-prep.sh) | JDK 26, Maven 3.9, клон исходников JAMS |
| 5 | [`cloudru-jams-build.sh`](../../migration/cloudru-jams-build.sh) | сборка React-клиента + `mvn package` |
| 6 | [`cloudru-jams-portfix.sh`](../../migration/cloudru-jams-portfix.sh) | правка порта 8080→8081 в лаунчере + пересборка |
| 7 | [`cloudru-jams-deploy.sh`](../../migration/cloudru-jams-deploy.sh) | дистрибутив → `/opt/jams`, служба `jams.service` |
| 8 | [`cloudru-jams-install4.sh`](../../migration/cloudru-jams-install4.sh) | свой CA + мастер установки через API |
| 9 | [`cloudru-jami-services2.sh`](../../migration/cloudru-jami-services2.sh) | стек `jami-services` (docker compose) |
| 10 | [`cloudru-jami-blueprint.sh`](../../migration/cloudru-jami-blueprint.sh) | blueprint `MSPShield` + одноимённая группа |
| 11 | [`cloudru-jamiserver-fix.sh`](../../migration/cloudru-jamiserver-fix.sh) | always-online демон `jamiserver.service` |

## Свежие решения (грабли, найденные при пересборке)

### 1. JDK 26 обязателен и в `JAVA_HOME`, и в `PATH`
Лаунчер JAMS запускает **дочернюю** JVM командой `java -jar jams-server.jar <port>` —
то есть берёт `java` из `PATH`. Если там системная Java 11:
`UnsupportedClassVersionError: class file version 70.0 ... up to 55.0`.
В unit нужны обе строки: `Environment=JAVA_HOME=/opt/jdk26` **и** `Environment=PATH=/opt/jdk26/bin:...`.

### 2. Порт 8080 захардкожен в лаунчере
`jams-launcher/src/main/java/launcher/AppStarter.java:193`:
`new ProcessBuilder("java", "-jar", "jams-server.jar", "8080")`.
8080 занимает админка Stalwart (docker-proxy) → Tomcat падает с `BindException`, при этом
сервер пишет «Server is now running!» (вводит в заблуждение). Лечится правкой на `8081` **и пересборкой**
(`mvn package`), затем подменой `/opt/jams/jams-launcher.jar`. **При обновлении JAMS правку повторить.**

### 3. `install/ca` ждёт ГОТОВЫЙ CA, а не «сгенерируй»
`CreateCAServlet` парсит `CreateCARequest { fields, certificate, privateKey }`, где
`certificate`/`privateKey` — **PEM-строки** (адаптеры Gson `X509CertificateAdapter`/`PrivateKeyAdapter`),
а `fields` — subject (`commonName`, `country`, `organization`, …). Сервер CA не создаёт.
Если послать что-то другое — вернётся 200, но `JamsCA.CA` останется `null`, и на шаге
`install/settings` будет `NullPointerException ... CA is null`, а `info` так и останется `installed:false`.
Правильно: `openssl req -x509 -addext "basicConstraints=critical,CA:TRUE"` → сгенерировать,
затем POST с PEM-ами.

### 4. Все шаги мастера, кроме первого, требуют Bearer-токен
`PUT /api/install/start {username,password}` → `access_token` (JWT, 30 мин).
`install/ca`, `install/auth`, `install/settings` **без** `Authorization: Bearer …` отвечают
`401 {"error":"You are not authenticated!"}`. Повторный `install/start` даёт 500 — мастер уже начат.

### 5. Docker раздавал контейнерам нерабочий DNS (8.8.8.8)
Провайдер отдаёт в DHCP `8.8.4.4`/`8.8.8.8`; **`8.8.8.8` из cloud.ru не отвечает**
(проверено: `nslookup pypi.org 8.8.8.8` → 0 ответов; `1.1.1.1` и `77.88.8.8` → работают).
Docker прописывал контейнерам 8.8.8.8 → `pip install` в сборке **висел** до таймаута
(`No matching distribution found for fastapi>=0.115`), сборка `jami-services` падала.
Лечение: `{"dns":["1.1.1.1","8.8.4.4"]}` в `/etc/docker/daemon.json` + рестарт Docker.
Побочный эффект: полезно и для Stalwart, который жаловался на `DNS error: Server Failure`.

> ⚠️ Рестарт Docker **останавливает и прод-стек**. После рестарта обязательно поднять его заново:
> `cd /opt/msp/Newbie/deploy/yandex && docker compose --profile mail up -d`.

### 6. GPG-ключ репозитория Jami
`https://dl.jami.net/stable/ubuntu_22.04/jami.gpg` → **404**, `gpg --keyserver` → «Server indicated a failure».
Рабочий источник — HTTPS-keyserver:
```bash
curl -s "https://keyserver.ubuntu.com/pks/lookup?op=get&search=0x64CD5FA175348F84" \
  | gpg --dearmor > /usr/share/keyrings/jami.gpg
```

### 7. `jamid` требует сессионную D-Bus
С `dbus-launch` демон стартует и сразу выходит (`Manager accessed before initialization`,
`Deactivated successfully`). Работает только через `dbus-run-session`:
```ini
ExecStart=/usr/bin/dbus-run-session -- /usr/libexec/jamid -p
```
(`-p` — оставаться живым после отключения клиента.)

### 8. Caddy: `header` нельзя в одну строку
`header { -Server }` → `Unexpected next token after '{' on same line`, и **`systemctl reload caddy`
падает**, оставляя старый конфиг. Правильно: `header -Server` **без** фигурных скобок,
либо полноценный многострочный блок.

### 9. Blueprint и группа — через API
```
POST /api/admin/policy?name=MSPShield   # тело — PolicyData JSON
POST /api/admin/group                   # {"name":"MSPShield","blueprintName":"MSPShield"}
```
`PolicyData`: `turnEnabled`, `turnServer`, `turnServerUserName`, `turnServerPassword`,
`proxyEnabled`, `proxyServer`, `videoEnabled`, `accountDiscovery`, `peerDiscovery`,
`rendezVous`, `upnpEnabled`, `publicInCalls`, `accountPublish`, `allowLookup`, `autoAnswer`.

### 10. UI падает: `theme.spacing is not a function` (главная грабля)
В браузере на странице входа:
`Uncaught TypeError: e.spacing is not a function at SignIn.tsx ... getStylesCreator.js ... makeStyles.js`.

**Причина — рассинхрон мажорных версий MUI в самом JAMS.** `SignIn.tsx` использует
`makeStyles` из `@mui/styles`, а `<ThemeProvider>` приходит из `@mui/material`. Это должны быть
пакеты одного мажора, иначе тему не видит никто:

| | до коммита `ee62171` | после `ee62171` |
|---|---|---|
| `@mui/material` | `5.13.6` | **`^9.3.0`** |
| `@mui/icons-material` | `5.11.16` | `^9.3.0` |
| `@mui/styles` | `5.13.2` | `^6.5.0` |
| react / react-dom | `^17` | `^19` |

Коммит JAMS `ee621710` «jams-react-client: update dependencies to latest» (06.08.2026) поднял
`@mui/material` до **v9**, а `@mui/styles` остался на **v6** (последняя существующая ветка —
в v7+ MUI эту устаревшую библиотеку просто нет). Пакеты начинают тянуть **разные копии**
`@mui/private-theming` (v9 и v6.4.9) → `ThemeProvider` кладёт тему в один React-контекст,
`makeStyles` читает другой → `useTheme()` возвращает пустую `defaultTheme` → `theme.spacing`
не функция.

> Этот же коммит менял и исходники (`api.tsx`, `auth.tsx`, компоненты), поэтому откатывать
> только package.json назад к v5 нельзя.

**Лечение — откатить только фронтенд на коммит до бампа.** Промежуточная попытка
«согласовать на v6» (`@mui/material@^6.5.0` + `@mui/icons-material@^6.5.0`) **проваливается**:
исходники после бампа завязаны на API v7+/v9, и `tsc --noEmit` даёт **72 ошибки** —
`TS2769: No overload matches this call` в `TextField`/`Autocomplete` и
`TS2339: Property 'slotProps' does not exist on type 'AutocompleteRenderInputParams'`.
Переписывать 43 файла с `makeStyles` на новый API тоже нереально.

Зато `ee62171` — **последний коммит в JAMS**, и он трогал **только `jams-react-client/`**
(бэкенд `jams-server` не изменялся). Поэтому достаточно откатить **один каталог** на
`ee62171~1` (коммит `48376317` «refactor: upgrade to JDK 26 and update dependencies», 31.07.2026),
где стек согласован: `@mui/material 5.13.6` + `@mui/icons-material 5.11.16` +
`@mui/styles 5.13.2` + React 17.
```bash
cd /opt/jams-src
git checkout ee62171~1 -- jams-react-client/   # ТОЛЬКО фронтенд
cd jams-react-client && rm -rf node_modules build
npm ci --legacy-peer-deps                      # по РОДНОМУ lock-файлу той версии
NODE_OPTIONS="--openssl-legacy-provider --max-old-space-size=3072" npx react-scripts build
```
Проверка успеха: в дереве **ровно одна** копия `@mui/private-theming` (5.15.9), сборка
`exit 0`, а `makeStyles` получает настоящую тему. Скрипт —
[`cloudru-jams-frontend-rollback.sh`](../../migration/cloudru-jams-frontend-rollback.sh).

⚠️ **`package-lock.json` удалять нельзя.** В нём лежит рабочая комбинация транзитивных
зависимостей. Если удалить lock и сделать `npm install`, npm подберёт `ajv-keywords@5` к
`ajv@6` и сборка упадёт с `Cannot find module 'ajv/dist/compile/codegen'`
(в lock зафиксирована совместимая пара `ajv 6.15.0` + `ajv-keywords 3.5.2`).
Правильный порядок:
```bash
git checkout -- jams-react-client/package-lock.json      # вернуть lock
python3 - <<'PY'                                          # поправить только диапазоны
import json; p="jams-react-client/package.json"; d=json.load(open(p))
d["dependencies"]["@mui/material"]="^6.5.0"
d["dependencies"]["@mui/icons-material"]="^6.5.0"
json.dump(d, open(p,"w"), indent=2)
PY
cd jams-react-client && rm -rf node_modules
npm install --legacy-peer-deps        # обновит MUI, остальное оставит по lock
# проверить: find node_modules -maxdepth 4 -type d -path '*@mui/private-theming' -> РОВНО одна
npx react-scripts build
```
Скрипт — [`cloudru-jams-mui-v6b.sh`](../../migration/cloudru-jams-mui-v6b.sh).

### 11. Прямой переход на `/signin` отдаёт 404
SPA у JAMS отдаётся Tomcat'ом без fallback: `/` работает, а `/signin`, `/signup` и прочие
пути React Router → 404 (перезагрузка страницы ломается). Лечится в Caddy: пути без
расширения переписываются на `index.html`, а `/api/*` проксируется как есть:
```caddyfile
m.msp-claude.online {
    handle /api/* { reverse_proxy 127.0.0.1:8081 }
    @spa {
        not path /api/*
        not path *.js *.css *.map *.png *.svg *.ico *.json *.txt *.woff *.woff2
    }
    handle @spa { rewrite * /index.html
                  reverse_proxy 127.0.0.1:8081 }
    handle { reverse_proxy 127.0.0.1:8081 }
}
```
Скрипт — [`cloudru-caddy-spa.sh`](../../migration/cloudru-caddy-spa.sh).

### 12. `/api/install/start` → 404 после установки — это НОРМА
`CInstallFilter` отдаёт `404 "The server is already installed"` для всех `/api/install/*`,
как только установка завершена. Ошибка в консоли браузера ожидаема и не является проблемой.

### 13. Пользователь создан, но войти не может: `userProfile` is null
Симптом: в клиенте Jami вход падает, в логе JAMS:
```
ERROR RegisterDeviceFlow - An error occurred while enrolling the device.
NullPointerException: Cannot invoke "UserProfile.getFirstName()" because "userProfile" is null
```

Причина: JAMS создаёт пользователя и его **профиль двумя разными вызовами**. Штатный UI делает:
1. `POST /api/admin/user` `{username, password}` — учётная запись;
2. `POST /api/admin/directory/entry` `<UserProfile>` — профиль.

`UserServlet.doPost` **профиль не создаёт** (читает только username/password), поэтому портал
приглашений, вызывавший лишь первый эндпоинт, оставлял пользователей без профиля — и
`RegisterDeviceFlow` падал, не давая зарегистрировать устройство (то есть войти в клиент).

Лечение:
- **существующим пользователям** — досоздать профили ([`cloudru-jams-profile-backfill.sh`](../../migration/cloudru-jams-profile-backfill.sh)):
  `POST /api/admin/directory/entry` с телом `{"username":"…","firstName":"…","lastName":"","email":""}`;
- **на будущее** — портал теперь создаёт профиль сам: функция `_jams_create_user_profile()`
  в [`deploy/jami-services/invite/app.py`](../../deploy/jami-services/invite/app.py) вызывается
  сразу после `_jams_create_user()`.

> Проверка, что профиль на месте: `GET /api/auth/userprofile/<username>` → 200
> (раньше отдавал 500 «User profile was not found!»).

### 14. Страница `/users` пуста: NPE на пользователе без сертификата
Симптом: в админке JAMS список пользователей пустой, хотя учётки есть. В логе:
```
SEVERE: Servlet.service() for servlet [SearchDirectoryServlet] threw exception
java.lang.NullPointerException: Cannot invoke "X509Certificate.getSerialNumber()"
   because the return value of "User.getCertificate()" is null
     at SearchDirectoryServlet.doGet(SearchDirectoryServlet.java:168)
```

Причина: страницу наполняет `/api/auth/directory/search`, и он для каждого профиля берёт
сертификат пользователя. У `mspadmin` сертификата **нет** — его создал установщик JAMS **до**
фикса `signingAlgorithm` (§10), когда подпись не работала. Один такой пользователь роняет
весь список. Проверка: `queryString=ilya` → 200 с профилем, `queryString=*` → 500.

Лечение — добавить проверку в условие (`user != null && user.getCertificate() != null`):
```bash
sudo bash cloudru-jams-certfix-patch.sh    # правит исходник, собирает класс
sudo bash cloudru-jams-certfix-inject.sh   # внедряет класс в рабочий fat-jar + рестарт
```
> ⚠️ `mvn package -pl jams-server` даёт **тонкий** jar (~17 МБ) без зависимостей, а рабочий —
> **fat** (~60 МБ). Замена рабочего jar тонким ломает JAMS целиком (служба висит в `activating`).
> Поэтому патч внедряется через `jar uf <fat.jar> <class>` — правильный путь.

Заодно найден баг апстрима в `UsersServlet`: он отдаёт **только первого** пользователя —
`gson.toJson(dataStore.getUserDao().getAll().get(0))`. Список на странице формируется не им,
а поиском по каталогу, поэтому на работу не влияет, но при доработках про это надо помнить.

### 15. У always-online узла СВОЙ Jami ID — он не совпадает с записью в JAMS
При создании учётки через админ-API JAMS сам генерирует ключ и Jami ID
(`RegisterUserFlow` → `ETHAddressGenerator.generateAddress()`), а D-Bus-аккаунт демона создаёт
**свою** пару ключей. В итоге:

| Где | Jami ID |
|---|---|
| запись пользователя `always-online` в JAMS (и его встроенный nameserver) | `db70df69875caa4a42cea0c7b6c051f639ede7a1` |
| **реальный аккаунт демона** (тот, что живёт в DHT и синхронизирует историю) | **`c411a740567076504b776dc07b7b22d0d916034a`** |

Поэтому:
- **контактом добавлять надо ID демона** (`c411a740…`) — именно у него есть живое устройство;
- обратный резолв `/api/nameserver/addr/c411a740…` → `Address not found` — это **нормально**,
  имя в JAMS-nameserver привязано к другому ID; клиент покажет просто ID;
- портал приглашений умеет регистрировать имена в **своём** nameservice
  (`jami-name-add` → `POST :8889/admin/names`, токен `NAMES_ADMIN_TOKEN`), но JAMS его не
  использует — у JAMS свой nameserver.

> Проверка резолва: `curl localhost:8081/api/nameserver/addr/<jami-id>`.
> Если узел пересоздавали — ID мог поменяться, берите его из
> `getAccountDetails` (см. `cloudru-jami-alwaysonline-setup.sh`).

### 16. Сертификат пользователя — это sub-CA (так задумано), не пугайтесь
Проверяя жалобу «клиент вечно мигрирует», легко решить, что сертификаты сломаны: у
**пользователя** в цепочке `CA:TRUE, pathlen:10` и `Key Usage: Certificate Sign, CRL Sign`.
Это **корректно по замыслу JAMS** — в исходнике так и написано:

```java
// User extensions (the user is a sub-CA)
userExtensions.getExtensions().add(new Object[]{Extension.basicConstraints, true, new BasicConstraints(10)});
userExtensions.getExtensions().add(new Object[]{Extension.keyUsage, false, new KeyUsage(cRLSign | keyCertSign)});
```

Роли сертификатов:

| Сертификат | Расширения | Назначение |
|---|---|---|
| CA (`MSPShield JAMS CA`) | `CA:TRUE, pathlen:10`, `keyCertSign` | корень |
| **пользователь** | `CA:TRUE, pathlen:10`, `keyCertSign` | **sub-CA: подписывает устройства пользователя** |
| **устройство** | `CA:FALSE`, `Digital Signature, Key Agreement` | им клиент и аутентифицируется |

Аккаунт клиента ломается не из-за цепочки. Проверить, что сервер отдаёт клиенту, можно
вручную (полный успешный цикл выглядит так):
```bash
openssl req -new -newkey rsa:2048 -nodes -keyout dev.key -out dev.csr -subj "/CN=test-device"
TOKEN=$(curl -s -X POST localhost:8081/api/login -H 'Content-Type: application/json' \
  -d '{"username":"test2","password":"<пароль>"}' | python3 -c 'import json,sys;print(json.load(sys.stdin)["access_token"])')
curl -s -X POST localhost:8081/api/auth/device -H 'Content-Type: application/json' \
  -H "Authorization: Bearer $TOKEN" \
  -d "{\"csr\": $(python3 -c 'import json;print(json.dumps(open("dev.csr").read()))'), \"deviceName\":\"test-device\"}"
```
В успешном ответе: `certificateChain` (3 сертификата), `nameServer`, `deviceReceipt`,
`receiptSignature` и поля политики (`TURN.server`, `Account.proxyServer` и т.д.).
Если это приходит — сервер исправен, и причину надо искать в клиенте (версия/состояние аккаунта).

> Известные баги миграции на стороне клиента:
> [#594 «wizard cannot be skipped»](https://git.jami.net/savoirfairelinux/jami-client-gnome/-/issues/594),
> [#595 «previously used user name cannot be used»](https://git.jami.net/savoirfairelinux/jami-client-gnome/-/issues/595).

## Проверки

```bash
curl -s http://127.0.0.1:8081/api/info            # {"installed":"true"}
ss -ltnp | grep -E ':(8081|8888|8889|8890|8891|8892)'
awg show >/dev/null; systemctl is-active jams coturn dhtnode jamiserver
```
Снаружи: `m.` → 200 (JAMS UI), `dht.` → 200 (JSON), `invite.` → 200, `push.` → 200,
`turn.` → 404 (держатель сертификата для coturn).

## Что осталось

- **Jami ID для always-online узла**: демон работает, но техаккаунт (`ConfigurationManager.addAccount`
  через D-Bus) не создан — узлу ещё нет Jami ID, контактам добавлять нечего.
- Пользователи JAMS: создавать через портал `https://invite.msp-claude.online` (он сам заводит
  учётку и добавляет в группу `MSPShield`) либо вручную в JAMS.
- Ключи/токены Jami — в [`../../deploy/yandex/DNS_RECORDS.md`](../../deploy/yandex/DNS_RECORDS.md)
  и в экспорте Vaultwarden (элементы `MSPShield · JAMS`, `· coturn`, `· Jami-сервисы`).
