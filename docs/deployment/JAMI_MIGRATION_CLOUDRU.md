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
