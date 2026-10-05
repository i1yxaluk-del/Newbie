# Миграция MSPShield → Cloud.ru Evolution

Перенос production со single-VM Yandex Cloud на Cloud.ru Evolution.
Канонический порядок и gates — [`./README.md`](README.md) и [`../docs/deployment/MIGRATION_RUNBOOK.md`](../docs/deployment/MIGRATION_RUNBOOK.md).
Здесь — только отличия для Cloud.ru и адаптированные команды.

## Известные факты (исходные данные)

| Поле | Значение |
|---|---|
| Новая ВМ | `vm-971aab`, зона `ru.AZ-3`, статус «Запускается» |
| Публичный IP | `45.132.177.214` |
| Внутренний IP | `10.0.0.5` |
| Security group | `Default` |
| S3-ключи (restic-бэкап) | Key ID + Key Secret (из консоли Cloud.ru Object Storage) |
| DNS A-записи | уже прописаны (проверить фактические значения перед switch) |

Локальный бэкап-кит в [`migration/`](.) :
`mongodump.archive.gz`, `vaultwarden-data.tar.gz`, `stalwart-etc.tar.gz`,
`stalwart-data.tar.gz`, `caddy-data.tar.gz`, `backend.env.bak`, `deploy.env.bak`,
`awg-admin.conf`, `restic-env.sh`, `restic-excludes.txt`.

Отсутствует `max-session.tar.gz` → MAX-сессия потребует ручной авторизации
(`docker exec -it msp-max-alerter python -m max_alerter.auth --authorize`) — это штатно.

## Чем Cloud.ru отличается от Yandex Cloud

- **Нет `yc`-CLI.** Управление — консоль `console.cloud.ru`; IaC — Terraform-провайдер
  [`cloud-ru/evo-terraform`](https://github.com/cloud-ru/evo-terraform). Для переноса уже
  созданной ВМ CLI не нужен — работаем по SSH напрямую.
- **Object Storage — S3-совместимый.** Для restic используется тот же `s3:`-backend,
  меняется endpoint и статические ключи (см. ниже).
- **Порт 25 открыт в обе стороны** (в отличие от Yandex Cloud, где 25/tcp заблокирован).
  Поэтому почта может работать **полностью самостоятельно, без Postbox**: Stalwart
  доставляет по MX получателя напрямую. Требуется лишь корректный PTR (в Evolution DNS
  есть PTR-зоны) и записи SPF/DKIM/DMARC/MX — Stalwart генерирует готовый zone file сам.
  Итог практики — [`../docs/deployment/POSTMORTEM_CLOUDRU_MIGRATION.md`](../docs/deployment/POSTMORTEM_CLOUDRU_MIGRATION.md).
- **Обязательно: маршрутизация при двух интерфейсах.** Если у ВМ есть и внутренний
  (`enp3s0`, 10.0.0.6), и direct-IP (`enp8s0`), DHCP выдаёт **два default-маршрута с
  одинаковой метрикой** → асимметрия, соединения рвутся (SSH/HTTP таймаутят, хотя
  сервисы слушают). Фикс — приоритетный default через direct-IP:
  ```bash
  ip route replace default via <gw> dev enp8s0 metric 50
  ```
  Проверка: `ip route get 8.8.8.8` должен показать `dev enp8s0`. Скрипт —
  [`cloudru-fix-routing.sh`](cloudru-fix-routing.sh) (ставится systemd-сервисом).

## Шаги

### 0. Пререквизиты (операторская Windows-станция)

- SSH-ключ к новой ВМ (путь; по умолчанию в скриптах — `~\.ssh\id_ed25519_yc_new`).
- TCP-доступность `45.132.177.214` на 22/80/443 **из РФ** (обязательный gate, урок 28.09):
  ```bash
  nc -vz 45.132.177.214 22
  curl -sS --connect-timeout 5 -o /dev/null -w '%{http_code}\n' http://45.132.177.214/
  ```
  Если ICMP проходит, а TCP — нет: сменить зарезервированный адрес, не переключать DNS.

### 1. Security group (Cloud.ru console)

В SG `Default` (или отдельной) разрешить ingress:
`22/tcp`, `80/tcp`, `443/tcp`, `443/udp` (AmneziaWG), `465/587/143/993/4190/tcp`,
и весь egress. Аналог правил из `deploy.ps1` (стадии 3–4) и `cloud-init.yaml` (ufw).

Дополнительно для Jami/JAMS (см. [`../docs/deployment/JAMS_SETUP.md`](../docs/deployment/JAMS_SETUP.md) «Порты»):
`3478` tcp+udp, `5349` tcp+udp, ретрансляция `49160-49250/udp` (TURN),
`4222` tcp+udp (OpenDHT). `8081` (JAMS) и `8888` (DHT Proxy) наружу НЕ открываются — только через Caddy.

### 2. Код на ВМ

```bash
ssh -i <KEY> ubuntu@45.132.177.214
sudo mkdir -p /opt/msp/Newbie && sudo chown ubuntu:ubuntu /opt/msp/Newbie
git clone https://github.com/i1yxaluk-del/Newbie.git /opt/msp/Newbie
```

> Базовый образ — Ubuntu 22.04 + Docker/Caddy/Node 20/unzip/restic. На Cloud.ru
> `cloud-init.yaml` из `deploy/yandex/` в общем применим, но `deploy.ps1` (yc) не
> используется — Cloud.ru ВМ создаётся в консоли. Минимальный набор после образа:
> `docker`, `docker compose` (plugin), `caddy`, `node 20` + `yarn` (corepack), `unzip`, `restic`, `ufw`.

### 3. Env-файлы (3 шт., создаются заново — не копировать старые cloud-креды)

`backend/.env`, `deploy/yandex/.env`, `deploy/yandex/monitoring/.env`.
Обязательные ключи — [`../docs/deployment/DEPLOY_RUNBOOK.md`](../docs/deployment/DEPLOY_RUNBOOK.md) §3
и `preflight.sh`. Из `backend.env.bak`/`deploy.env.bak` переносятся только домен,
Kaiten/Telegram/MAX-токены и (если Postbox остаётся) Postbox-ключи.

### 4. Гейт и стеки

```bash
cd /opt/msp/Newbie && sudo bash scripts/deployment/preflight.sh --fix   # PRE-FLIGHT OK
cd deploy/yandex && docker compose up -d --build                         # mongo, backend, vaultwarden
cd monitoring && docker compose up -d --build                           # prometheus, grafana, am, max-alerter
```

### 5. Восстановление данных

```powershell
# операторская Windows-станция (см. migration/migrate.ps1):
.\migration\migrate.ps1 -NewVmIp 45.132.177.214 -SshKeyPath <KEY>
```

`migrate.ps1` кладёт артефакты плоско в `/tmp/migration` и запускает `restore-on-vm.sh`
(mongo `mongorestore --drop` → тома → max-session → стеки → healthcheck).
После — проверить Stalwart не в bootstrap: `docker logs msp-stalwart-1 | grep -c 'bootstrap mode'` → `0`.

### 6. Caddy

`setup-on-vm.sh` ставит боевой `Caddyfile` с `MSP_DOMAIN`, либо вручную:
```bash
sudo install -m 0644 /opt/msp/Newbie/deploy/yandex/Caddyfile /etc/caddy/Caddyfile
sudo sed -i 's/{$MSP_DOMAIN}/<DOMAIN>/g' /etc/caddy/Caddyfile
sudo mkdir -p /etc/systemd/system/caddy.service.d
printf '[Service]\nEnvironment="MSP_DOMAIN=<DOMAIN>"\n' | sudo tee /etc/systemd/system/caddy.service.d/override.conf
sudo systemctl daemon-reload && sudo systemctl restart caddy
```
Проверка: `grep -c provisioning /etc/caddy/Caddyfile` → `0`.

### 7. restic на Cloud.ru S3

Новый репозиторий (старые YC S3-ключи не подходят к новому бакету — `SignatureDoesNotMatch`):

```bash
# /etc/restic/env.sh
export AWS_ACCESS_KEY_ID=<Cloud.ru Key ID>
export AWS_SECRET_ACCESS_KEY=<Cloud.ru Key Secret>
export RESTIC_REPOSITORY=s3:https://<S3_ENDPOINT>/<bucket>
export RESTIC_PASSWORD=<новый/перенесённый пароль>
```

> S3-эндпойнт и имя бакета взять из консоли Cloud.ru Object Storage (проверить:
> `storage.cloud.ru` для Evolution; точное значение показано при создании бакета/ключа).

```bash
restic init && sudo bash /opt/restic-scripts/backup.sh   # тестовый снапшот
systemctl enable --now restic-backup.timer
```

### 8. AmneziaWG

Серверные ключи сохранены (`migration/awg-admin.conf`) — обновить `Endpoint` на новый IP
и раздать клиентам обновлённый туннель. `net.ipv4.ip_forward=1`, MASQUERADE на eth0,
ufw `allow 443/udp` + SSH из `10.9.0.0/24`.

### 9. Gates до DNS switch (и после)

- TCP-доступность нового IP из РФ (22/80/443);
- `curl https://<domain>/api/health` → ok (локально, до DNS);
- Mongo count и выборочные записи; Vaultwarden login; Stalwart не в bootstrap;
- MAX: `docker exec msp-max-alerter python -m max_alerter.auth` → exit 0;
- тестовый P1 → MAX + email; письмо внутрь/наружу;
- новый restic snapshot; `du -sh` томов ≈ бэкап; внешний скан не показывает internal ports.

Старая ВМ — выключена до acceptance, удаляется после подтверждённого бэкапа новой среды.

### 10. Jami / JAMS-инфраструктура (пилот, 30.09.2026)

Развёрнута на той же ВМ после миграции 28.09; её данные **не входят в локальный кит
`migration/`** (там только pre-Jami артефакты). Источник данных — restic-снапшоты старого
YC-бакета (`/opt`, `/etc`, `/home`) либо пересборка по [`../docs/deployment/JAMS_SETUP.md`](../docs/deployment/JAMS_SETUP.md).

Компоненты и их данные:

| Компонент | Размещение/данные | Источник при переносе |
|---|---|---|
| JAMS (8081, `m.`) | `/opt/jams/{CA.pem,keystore.jks,config.json,oauth.key,jams.crl}` + `jams.service` | restic `/opt/jams`, иначе пересборка (JDK 26 + Maven + `git.jami.net/jami-jams`) |
| coturn (`turn.`, 3478/5349) | `/etc/turnserver.conf`, user `jami` | restic `/etc` + `turnadmin -a` |
| OpenDHT dhtnode (4222, `dht.`) | `dhtnode.service`, БД dhtnode | пересборка: `apt install dhtnode` + unit (`tail -f /dev/null | dhtnode -v -p 4222 -b bootstrap.jami.net --proxyserver 8888`) |
| jami-services (compose `deploy/jami-services/`) | `/opt/jami-services/{pgdata,invite-data,ntfy-cache}` | restic `/opt/jami-services` + `pg_dump` nameservice (в `backup.sh`) |
| always-online jamid | `/home/jamiserver/.local/share/jami`, `jamiserver.service` | restic `/home` (иначе headless D-Bus addAccount заново) |

- Доп. DNS A-записи (все → новый IP): `m.`, `dht.`, `turn.`, `names.`, `invite.`, `push.`.
- Доп. Caddy-блоки `m./dht./turn./names./invite./push.` (стиль `{$MSP_DOMAIN}`) — `setup-on-vm.sh` их не ставит, добавить в `/etc/caddy/Caddyfile` вручную.
- `jami-services` `.env`: `JAMI_PG_PASSWORD`, `JAMS_ADMIN_USER`, `JAMS_ADMIN_PASS`, `JAMS_ADMIN_PASSWORD` (значения — из секретов/`~/msp-deploy-secrets.txt`, которых нет в локальном ките).
- Пароли/CA JAMS и TURN — восстановить из restic `/opt/jams`, `/etc/turnserver.conf`, `/home`; при недоступности restic — пересборка и перевыпуск (логины JAMS не переиспользуются после revoke).

## Почта без Postbox (прямая доставка по MX)

Cloud.ru не блокирует 25/tcp, поэтому внешний релей не нужен. Порядок:

1. **Убедиться, что 25/tcp разрешён** в SG (ingress) и в ufw; проверить исходящий:
   `python3 -c "import socket;socket.create_connection(('gmail-smtp-in.l.google.com',25),8)"`.
2. **Переключить Stalwart на прямую доставку.** В его конфиге (RocksDB, том
   `stalwart-data`) маршрут `mx` уже есть; удалить релей Postbox через JMAP:
   ```bash
   PW=$(sudo grep '^STALWART_ADMIN_PASSWORD=' deploy/yandex/.env | cut -d= -f2-)
   # список: x:MtaRoute/get ; удалить релей (имя обычно BaseYandex/postbox-outbound):
   curl -s -u "admin:$PW" -H 'Content-Type: application/json' \
     -d '{"using":["urn:ietf:params:jmap:core","urn:stalwart:jmap"],"methodCalls":[["x:MtaRoute/set",{"destroy":["<route-id>"]},"0"]]}' \
     http://127.0.0.1:8080/jmap/
   ```
   > env-переменные Stalwart применяются **только при первом запуске**; после
   > восстановления конфига из бэкапа правки — только через JMAP/Admin UI.
3. **Опубликовать DNS-записи.** Stalwart генерирует полный zone file:
   `x:Domain/get` → `dnsZoneFile` (сохранён в [`../deploy/yandex/dns-zone-stalwart.txt`](../deploy/yandex/dns-zone-stalwart.txt)):
   DKIM (ed25519+rsa), `mail.` SPF (`v=spf1 a -all`), apex SPF (`v=spf1 mx -all`),
   MX → `mail.<domain>`, DMARC (`p=reject`), SRV (imaps/submissions/jmap/caldav/carddav/pop3s),
   MTA-STS + TLS-RPT, CAA, autoconfig/autodiscover.
   > **Минимизация:** для почты реально нужны лишь 5 DNS-записей + PTR;
   > полный разбор и готовый набор — [`../deploy/yandex/DNS_RECORDS.md`](../deploy/yandex/DNS_RECORDS.md)
   > и [`../deploy/yandex/NAMECHEAP_DNS_SETUP.md`](../deploy/yandex/NAMECHEAP_DNS_SETUP.md).
4. **PTR:** в консоли Cloud.ru → **Evolution DNS → Обратные зоны** создать PTR-зону для
   публичного IP → `mail.<domain>` (важно для доставляемости; текущий PTR по умолчанию
   равен имени ВМ).
5. **TLS почты:** импортировать актуальный сертификат Caddy в Stalwart и **перезапустить**
   контейнер (без рестарта listener отдаёт старый/self-signed):
   ```bash
   # x:Certificate/set с certificate/privateKey из /var/lib/caddy/.../mail.<domain>.{crt,key}
   sudo docker restart msp-stalwart-1
   echo | openssl s_client -connect 127.0.0.1:465 -servername mail.<domain> 2>/dev/null | openssl x509 -noout -dates
   ```
   Скрипт — [`cloudru-mail-cert.sh`](cloudru-mail-cert.sh).
6. **Проверка:** письмо наружу (Gmail/Яндекс) — доставлено, DKIM `pass`; письмо внутрь на
   `admin@<domain>` — появилось в ящике; `openssl s_client` отдаёт LE-сертификат.

> Порт 587/143 (STARTTLS) снаружи фильтруется облаком — клиентам указывать implicit-TLS
> (`465` submission, `993` IMAP).

## VPN (AmneziaWG) и SSH только через туннель

VPN-сервер AmneziaWG поднят **на той же ВМ**, что и прод (функция bastion).

1. **Установка** ([`cloudru-awg-install.sh`](cloudru-awg-install.sh)):
   `add-apt-repository -y ppa:amnezia/ppa && apt-get install -y amneziawg-dkms amneziawg-tools qrencode`.
   Проверка: `awg --version`, `dkms status` → `amneziawg/1.0.0 ... installed`.
2. **Bootstrap сервера** ([`../technical/0_Common/amneziawg/awg_bootstrap.sh`](../technical/0_Common/amneziawg/awg_bootstrap.sh)):
   ключи сервера, `awg0` = `10.9.0.1/24`, слушает **UDP/443** (не конфликтует с Caddy TCP/443),
   обфускация `Jc/Jmin/Jmax/S1/S2/H1..H4`. В SG уже есть ingress `udp 443` («AmneziaWG»).
3. **Пир админа** ([`cloudru-awg-add-admin-peer.sh`](cloudru-awg-add-admin-peer.sh)): добавляет нашу
   станцию `10.9.0.2` с **существующим** клиентским ключом — в клиентском конфиге меняются только
   `Endpoint` и `PublicKey` сервера.
4. **Клиент** ([`awg-admin.conf.example`](awg-admin.conf.example) — шаблон; рабочий файл
   `migration/awg-admin.conf` в `.gitignore`, т.к. содержит приватный ключ): `Endpoint = 45.132.176.143:443`,
   `PublicKey = ZWvrjrDSsMQShEKXjZoD/TiTa1dQ07AIGLugWerXRyU=`. Импорт в AmneziaWG for Windows:
   ```powershell
   & "C:\Program Files\AmneziaWG\amneziawg.exe" /uninstalltunnelservice awg-msp
   & "C:\Program Files\AmneziaWG\amneziawg.exe" /installtunnelservice C:\path\awg-msp.conf  # .conf БЕЗ BOM!
   & "C:\Program Files\AmneziaWG\awg.exe" show   # latest handshake = туннель поднят
   ```
   Конфиг **обязательно без BOM** — Windows-клиент иначе не принимает файл.
5. **Проверка:** `ssh -i <key> ubuntu@10.9.0.1` (адрес сервера внутри туннеля).
   Если менялся хост-ключ — `ssh-keygen -R 10.9.0.1`.

**Закрытие SSH снаружи** ([`cloudru-ssh-lockdown-ufw.sh`](cloudru-ssh-lockdown-ufw.sh)):
- ufw: удалить `allow 22/tcp`, оставить `allow from 10.9.0.0/24 to any port 22 proto tcp`.
- Security Group: удалить ingress-правило `tcp 22:22 from 0.0.0.0/0` — API
  `GET/DELETE /api/v1/security-groups/{sg}/rules[/{rule}]` (**без** `project_id` в query,
  иначе `extra_forbidden`).
- Итог: `45.132.176.143:22` → timeout; SSH через `10.9.0.1` → работает; 80/443/465/993/25 снаружи живы.

> **Порядок критичен:** сначала поднять туннель и убедиться, что SSH через `10.9.0.1` работает,
> и только потом закрывать 22. Все изменения применять **через туннель**, не через публичный IP.
> Аварийный доступ — веб-консоль Cloud.ru (`is_serial_ready: true`).

## Статус и что осталось

Выполнено:
- [x] pwsh на станции — восстановлен перезапуском Harness (работаем в PowerShell 5.1).
- [x] SSH — `ubuntu@45.132.176.143`, ключ `~/.ssh/id_ed25519_yc_new`.
- [x] ВМ/диск/интерфейсы/IP и порты созданы через API Cloud.ru Evolution.
- [x] Код, env, `preflight` → OK; данные восстановлены; стек healthy.
- [x] DNS A-записи → `45.132.176.143`; TLS выпущен для всех доменов.
- [x] Асимметричная маршрутизация исправлена и закреплена systemd-сервисом.
- [x] Почта переведена на прямую доставку без Postbox; TLS почты валиден.
- [x] Ящик `postmaster@` создан ([`cloudru-create-postmaster.sh`](cloudru-create-postmaster.sh)).
- [x] Логи Stalwart починены (`/var/lib/stalwart/logs/` — раньше писались в несуществующий каталог).
- [x] AmneziaWG на новой ВМ + туннель `awg-msp` (`latest handshake` OK).
- [x] SSH снаружи закрыт (ufw + SG), доступ только через туннель `10.9.0.1`.
- [x] VM watcher переведён на Cloud.ru API ([`../services/vm_watcher/`](../services/vm_watcher/)).

Осталось:
- [x] **DKIM RSA в DNS** исправлен и проверен на обоих NS (420 симв., пробелов в base64 — 0).
- [x] **Jami/JAMS пересобраны** на новой ВМ: JAMS (свой CA), coturn, OpenDHT, `jami-services`,
      blueprint+группа `MSPShield`, always-online демон — см. [`../docs/deployment/JAMI_MIGRATION_CLOUDRU.md`](../docs/deployment/JAMI_MIGRATION_CLOUDRU.md).
- [x] **Docker DNS** на ВМ: `8.8.8.8` из cloud.ru недоступен → в `daemon.json` прописаны `1.1.1.1`/`8.8.4.4`.
- [x] **Экспорт секретов** в Vaultwarden: 16 элементов (13 инфра + 3 Jami).

Осталось:
- [ ] **PTR** → `mail.msp-claude.online` (Evolution DNS → Обратные зоны, консоль; API недоступен).
- [ ] **Дубль `_dmarc`**: удалить запись `_dmarc.msp-claude.online` (создаёт `_dmarc.msp-claude.online.msp-claude.online`).
- [ ] **Vaultwarden SMTP** всё ещё смотрит на `postbox.cloud.yandex.net` — перевести на локальный Stalwart.
- [ ] **Jami ID** для always-online узла (демон работает, техаккаунт через D-Bus не создан).
- [ ] **S3-статические ключи** Object Storage + имя бакета → restic (`/etc/restic/env.sh`, `restic init`).
- [ ] MAX re-auth.
- [ ] Удалить старую ВМ после периода наблюдения.
