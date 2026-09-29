# Резервные копии, восстановление и перенос VM

Backup — сохранённый набор данных. Restore — получение работающего состояния из копии. RPO показывает допустимую потерю последних данных, RTO — допустимое время восстановления. Эти значения измеряются упражнением, а не назначаются по желанию.

Набор MSPShield включает логический dump MongoDB, Vaultwarden, оба тома Stalwart и MAX session. Старые `.env` не переносятся как облачные учётные данные: на новой VM создаются новые секреты и ключи.

Перенос проходит стадии inventory, backup, новая VM, restore, внутренние проверки, P1, clean-room restore, внешний scan и DNS switch. Старую VM сохраняют выключенной до окончания наблюдения.

## Как работать с материалом

Сначала прочитайте объяснение главы. Затем откройте перечисленные файлы в рабочем репозитории и сопоставьте текст с текущим кодом. Команды изменения выполняйте на учебной среде. Разделы ниже включены полностью, поэтому глава одновременно служит учебником и справочником.

## Материал проекта: `migration/README.md`

<!-- SOURCE migration/README.md 71362e7347f4f7a2 -->

## Миграция MSPShield на новую VM

### Принципы

- переносим данные и отдельно проверенные session artifacts, а не старые `.env`;
- SSH host key сверяем через console/provider metadata; `StrictHostKeyChecking=no` запрещён;
- DNS переключаем только после health, alert и restore gates;
- snapshot не заменяет clean-room restore.

### Артефакты

| Файл | Источник | Восстановление |
|---|---|---|
| `mongodump.archive.gz` | логический dump Mongo | `mongorestore --drop` |
| `vaultwarden-data.tar.gz` | остановленный writer volume | Docker volume |
| `stalwart-etc.tar.gz` | mail config/domain/DKIM | Docker volume |
| `stalwart-data.tar.gz` | mail data | Docker volume |
| `max-session.tar.gz` | остановленный max-alerter | bind directory |

Архивы создаёт `migration/restic-backup.sh`. Raw live-copy `/var/lib/docker/volumes` не используется.

### Новая VM

1. Deploy кода.
2. Создать новые `backend/.env`, `deploy/yandex/.env`, `monitoring/.env`.
3. `bash scripts/deployment/preflight.sh --fix`.
4. Загрузить только перечисленные артефакты в `/tmp/migration`.
5. Запустить:

```bash
sudo /tmp/migration/restore-on-vm.sh
```

### Gate DNS switch

- [ ] backend, Prometheus, Alertmanager и MAX health зелёные;
- [ ] Mongo count и выборочные записи проверены;
- [ ] Vaultwarden login проверен;
- [ ] Stalwart домен/ящик/DKIM проверены, если mail profile включён;
- [ ] `max_alerter.auth` возвращает 0 без `--authorize`;
- [ ] P1 доставлен в MAX и Postbox email;
- [ ] новый restic snapshot создан;
- [ ] файл восстановлен в clean target, RTO/RPO записаны;
- [ ] внешний scan не показывает internal ports.

Если MAX session не принимается, только оператор выполняет:

```bash
sudo docker exec -it msp-max-alerter python -m max_alerter.auth --authorize
```

Старую VM держать выключенной до завершения периода наблюдения; удалять после подтверждённого backup новой среды.


### Журнал выполнения (28.09.2026)

- Перенесено успешно: Mongo (`mongorestore --drop`), `vaultwarden-data`, `stalwart-etc` + `stalwart-data`, `max-session`.
- Подтверждено на практике: `restore-on-vm.sh` требует **плоскую раскладку** файлов в `MIGRATION_DIR`:

  ```text
  /tmp/migration/mongodump.archive.gz
  /tmp/migration/vaultwarden-data.tar.gz
  /tmp/migration/stalwart-etc.tar.gz
  /tmp/migration/stalwart-data.tar.gz
  /tmp/migration/max-session.tar.gz
  ```

  В полном ките бэкапа файлы лежат в `opt/msp-backups/current/` и `.../volumes/` — перед запуском скопировать плоско (из root-only каталогов — только `sudo sh -c 'cp ...'`: glob в пользовательском шелле не раскроется).
- Напоминание: пустой том `stalwart-data` = Stalwart в bootstrap-режиме (конфиг хранится внутри RocksDB); восстанавливать оба тома.
- После восстановления: `sudo docker compose --profile mail up -d stalwart` и проверка отсутствия «bootstrap mode» в логе.


## Материал проекта: `docs/deployment/MIGRATION_RUNBOOK.md`

<!-- SOURCE docs/deployment/MIGRATION_RUNBOOK.md 1064abee47f9f43a -->

## Migration Runbook — перенос MSPShield на новую VM

Короткий порядок переноса со старой VM на новую. Артефакты создаёт `migration/restic-backup.sh` (mongodump + тома с остановленными writer'ами).
Подробности и подводные камни: [`../../migration/README.md`](https://github.com/i1yxaluk-del/Newbie/blob/main/migration/README.md).

### 0. Пререквизиты

- Новая VM развёрнута по [DEPLOY_RUNBOOK.md](https://github.com/i1yxaluk-del/Newbie/blob/main/docs/deployment/DEPLOY_RUNBOOK.md) **шаги 0–6** (без DNS switch и Stalwart-wizard), `preflight` → PRE-FLIGHT OK.
- `restic` на новой VM настроен (`/etc/restic/env.sh`, тот же S3-репозиторий).

### 1. Старая VM — снять артефакты

```bash
sudo bash /opt/restic-scripts/backup.sh
## артефакты: /opt/msp-backups/current/{mongodump.archive.gz, volumes/*.tar.gz} + restic-снапшот
sudo bash -c 'source /etc/restic/env.sh && restic snapshots --latest 1'
```

Скрипт сам останавливает vaultwarden/stalwart/max-alerter на время копии томов и поднимает их обратно.

> Урок 28.09: артефакты удобно сразу складывать плоско — `restore-on-vm.sh` умеет искать и в `volumes/`, но плоская раскладка исключает сюрпризы (см. §9.4).

### 2. Доставить артефакты на новую VM

```bash
## на новой VM:
sudo bash -c 'source /etc/restic/env.sh && restic restore latest --target /tmp/restore --path /opt/msp-backups/current'
sudo mkdir -p /tmp/migration/volumes
sudo cp -r /tmp/restore/opt/msp-backups/current/* /tmp/migration/
sudo ls -la /tmp/migration /tmp/migration/volumes
```

> Копирование из root-only каталогов — только `sudo sh -c 'cp ...'` (glob раскрывается в пользовательском шелле до sudo и молча не находит файлы — урок 28.09, §9.4).

### 3. Новая VM — восстановить

```bash
cd /opt/msp/Newbie
sudo MIGRATION_DIR=/tmp/migration bash migration/restore-on-vm.sh
```

Скрипт: mongo → `mongorestore --drop` → тома (`msp_vaultwarden-data`, `msp_stalwart-etc`, `msp_stalwart-data`) → `max-session` → стек → healthcheck (backend/AM/max-alerter).

> Скрипт сам ищет артефакты во всех типовых раскладках и падает, если том пустой после восстановления; после рестарта проверяет, что Stalwart не в bootstrap (урок 28.09, §9.4). Если что-то пропущено — в логе будет `ИТОГ: пропущено …` и `WARN`/`ERROR`.
>
> Контроль самостоятельно: `docker logs msp-stalwart-1 | grep -c 'bootstrap mode'` → `0`; `du -sh /var/lib/docker/volumes/msp_*` ≈ размер бэкапа.

### 4. MAX (если сессия протухла)

```bash
sudo docker exec -it msp-max-alerter python -m max_alerter.auth --authorize
## 1) ввести SMS-код; 2) если включён 2FA — ввести пароль MAX (ввод скрыт)
## неинтерактивно: MAX_SMS_CODE / MAX_PASSWORD в monitoring/.env (после использования — удалить)
```

Проверка без SMS: `sudo docker exec msp-max-alerter python -m max_alerter.auth` (exit 0 = сессия есть).

### 5. TLS Stalwart

Импортировать сертификаты Caddy для `mail.<domain>` (bind-mount `/var/lib/caddy → /etc/stalwart-certs`), либо настроить отдельный ACME.
Авто-ACME Stalwart (TLS-ALPN-01) недоступен — 443 занят Caddy.

### 6. DNS switch

У регистратора: `A` (@/mail/mon) → новый IP. SPF/DKIM/DMARC — проверить значения (SPF с `include:postbox.cloud.yandex.net`; для Postbox — CNAME `<selector>._domainkey → <selector>.dkim.pstbx.ru` из консоли, иначе отправка получит `550 identity not verified`, §9.5).

**Сначала проверь TCP-доступность нового IP из целевой сети (из РФ)** — `nc -vz <IP> 22`; если TCP не проходит, а ICMP ок, меняй зарезервированный адрес, не переключай DNS (урок 28.09, §9.2).

### 7. Верификация

- Письмо внутрь: с Яндекса на `admin@<domain>` → появилось в ящике.
- Письмо наружу: из ящика на Gmail/Яндекс → доставлено, не в спаме.
- Тестовый P1-алерт → MAX + email (+ Telegram, если доступен с ВМ).
- `restic snapshots` на новой VM содержит новый снапшот.
- `sudo bash scripts/deployment/preflight.sh` → PRE-FLIGHT OK.

### 8. Старая VM

После подтверждения: остановить/удалить (грант/биллинг), проверить, что бэкапы ведутся с новой VM.


### 9. Журнал фактической миграции 28.09.2026 (новый YC-аккаунт)

Перенос выполнен 28.09.2026 на новую ВМ (`msp-cloud-vm`, публичный `130.193.49.21`, внутренний `10.128.0.25`). Ниже — все проблемы, с которыми столкнулись по ходу, и проверенные решения — дополнение к шагам выше для следующего переноса.

#### 9.1 Инфраструктура / аккаунт

- **`key.json` нового аккаунта был невалидным** (посторонний текст `PLEASE DO NOT REMOVE…` перед PEM) → `yc` CLI не принимал профиль. Решение: валидный JSON-ключ сервисного аккаунта; проверять формат до автоматизации.
- **cloud-init на свежей ВМ падал**: apt ходил через IPv6-зеркала (недоступны), ufw мешал ранним этапам. Решение: пересоздать ВМ с исправленным cloud-init — `Acquire::ForceIPv4`, ufw не ставится на этапе bootstrap (настраивается позже явно).
- **Битый NodeSource-репозиторий** от cloud-init (недействительный gpg-ключ) ломал `apt-get update`. Решение: удалить `sources.list.d/nodesource.list` + ключ; Node 20 — тарболом в `/usr/local`, симлинки в `/usr/local/bin`.
- **На ВМ не было `unzip`** → распаковка репозитория падала. Решение: `apt-get install -y unzip` (добавить в cloud-init).

#### 9.2 Сеть и доступ

- **Главная причина «сайт не работает»: зарезервированный IP `111.88.253.222` недостижим по TCP из РФ** (ICMP проходит, TCP — таймаут). Симптом: `ERR_CONNECTION_TIMED_OUT` у всех из России. Решение: новый зарезервированный адрес `130.193.49.21` (другой пул — доступен, проверено TCP 22/80/443), переключение NAT, DNS у Namecheap.
  - **Новый обязательный gate**: перед DNS switch — smoke-тест TCP-доступности нового публичного IP **из целевого региона** (из РФ). Если недоступен — пересоздавать адрес, не переключать DNS.
- Пока основной IP не отвечал, доступ был только через промежуточную ВМ-бастион (`msp-test`). После переключения на доступный IP бастион удалён — держать одну ВМ.
- В security group **не было UDP/443** для AmneziaWG. Решение: `msp-sg` += INGRESS UDP 443; в ufw — `allow 443/udp`; плюс ufw-правило SSH из `10.9.0.0/24`.

#### 9.3 Развёртывание

- **Caddy от cloud-init стоял с заглушкой** (`:80 → respond 503 "provisioning"`) → сайт 503. Решение: боевой `deploy/yandex/Caddyfile`.
- **Caddyfile не стартовал без `MSP_DOMAIN`** (`server block without any key`) — для systemd-юнита нет env из compose. Решение: override `Environment=MSP_DOMAIN=msp-claude.online` (`/etc/systemd/system/caddy.service.d/override.conf`).
- **Фронтенд не был собран** (пустой webroot). Решение: `yarn install --frozen-lockfile && yarn build`, выкладка в `/var/www/landing`.
- **Интеграции backend выключены, если пусты переменные**: email-уведомления лидов требуют `SMTP_*` + `LEAD_EMAIL_TO`, карточки — `KAITEN_*` (+ `KAITEN_DOMAIN/API_TOKEN/BOARD_ID/COLUMN_ID`). В ките бэкапа их не было — `is_enabled()` возвращает false, и доставка молча пропускается (лид остаётся только в Mongo). Проверка: `curl 127.0.0.1:8001/api/integrations/status` + тестовая заявка.

#### 9.4 Данные (главная ловушка)

- **`restore-on-vm.sh` ожидает артефакты плоско в `MIGRATION_DIR`**, а в полном ките они лежат в `opt/msp-backups/current/` + `.../volumes/`. Без раскладки — тома молча не восстанавливаются.
- **Ловушка `sudo cp root-only/*.tar.gz`**: glob раскрывается в шелле пользователя, root-only каталог не читается — копирование молча падает. Копировать так: `sudo sh -c 'cp .../volumes/*.tar.gz /tmp/migration/'`.
- **Пустой том `stalwart-etc` + `stalwart-data` → Stalwart стартует в bootstrap-режиме** («No configuration file found. Port 8080 open for initial setup»). Важно понимать: `config.json` — только указатель на RocksDB (`/var/lib/stalwart`), вся конфигурация (маршруты, ящики) — в `stalwart-data`. Восстанавливать **оба тома**, иначе bootstrap.
- Проверка после восстановления: размеры томов (`du -sh`) ≈ бэкап; в логе Stalwart нет «bootstrap mode»; Vaultwarden открывает сохранённые аккаунты.

#### 9.5 Почта / Postbox

- **При смене аккаунта Postbox ключи и домен не переносятся**: старый API-ключ не работает, идентичность требует повторной верификации. Заново: создать API-ключ (`yc iam api-key create … --scope yc.postbox.send`), обновить `POSTBOX_API_KEY_*` в deploy `.env` и `SMTP_AUTH_*` / `SMTP_*` / `GF_SMTP_*` в monitoring `.env`, перезапустить Stalwart / Alertmanager / Grafana.
- **DKIM у Postbox — через CNAME-делегирование, не TXT** (проверено 28.09): в консоли Postbox (страница адреса → «Email signature configuration (DKIM)») публикуются записи вида `egtn...-1._domainkey.<домен> → egtn...-1.dkim.pstbx.ru` (и `-2`). TXT `postbox._domainkey` у нового Postbox нет — не искать его (частая ошибка диагностики).
- Пока домен не verified — Postbox отклоняет отправку: `550 "identity not verified"`.
- **Маршрут Stalwart `postbox-outbound` не обновляется при смене `deploy/.env`** — после восстановления БД из бэкапа в нём остаются креды СТАРОГО аккаунта; письма молча копятся в очереди с `535 Authentication failed`. Диагностика и лечение — §9.9.
- Быстрая проверка ключей: python-smtplib login на `postbox.cloud.yandex.net:465` (без отправки письма).

#### 9.6 Бэкапы / restic

- **restic не был установлен** на свежей ВМ (`apt-get install -y restic`).
- **Креды restic привязаны к аккаунту**: старый `AWS_ACCESS_KEY_ID` даёт `SignatureDoesNotMatch` на новый бакет. Создать новый статический ключ SA `restic-backup` (`yc iam access-key create`), обновить `/etc/restic/env.sh`, `restic init` в новом бакете, проверить `restic snapshots` + тестовый снапшот, вернуть cron/timer (03:30).

#### 9.7 AmneziaWG

- **Amnezia PPA «not signed»** после переноса gpg-ключа: ключ должен лежать в `/etc/apt/trusted.gpg.d/`, и в `.list` не должно быть лишнего `signed-by`. Только после этого ставится `amneziawg` / `amneziawg-tools`.
- **Клиентские конфиги привязаны к IP сервера**: серверные ключи сохранили, поэтому достаточно заменить `Endpoint` на новый IP — клиентам обновить один туннель. Новый конфиг: `migration/awg-admin.conf`.
- После восстановления сервера: `awg-quick@awg0` enabled, `net.ipv4.ip_forward=1`, PostUp-MASQUERADE на eth0, ufw allow 443/udp + SSH из `10.9.0.0/24`.

#### 9.8 Обновление gate «до DNS switch» (по итогам)

Добавить в проверки перед переключением DNS:
- [ ] TCP-доступность нового IP из целевого региона (22/80/443);
- [ ] `du -sh` восстановленных томов ≈ размер до бэкапа; Stalwart не в bootstrap;
- [ ] `curl https://<domain>/api/health` — ok (локально, до DNS);
- [ ] `restic snapshots` в новом бакете — ok; cron/timer на месте;
- [ ] DKIM опубликован (CNAME `dkim.pstbx.ru`), домен в Postbox «verified» (иначе письма не уйдут).
- [ ] Интеграции лидов (`backend/.env`) заполнены и проверены тестовой заявкой (§9.10).

#### 9.9 Очередь Stalwart: письма копятся, наружу не уходят (535 Authentication failed)

Симптом: письма из ящиков (`admin@`/`sales@`) не доходят; `docker logs msp-stalwart-1` пуст (в этом конфиге логирование в stdout выключено). Реальная причина видна только в очереди: Postbox отвечает `535 Authentication failed` — маршрут с устаревшими кредами.

Управляющая учётка Stalwart — **`admin` (без домена!)**, пароль — `STALWART_ADMIN_PASSWORD` из `deploy/yandex/.env`. Логин `admin@<домен>` — обычный ящик; на `x:*-методах` он получает `forbidden`.

```bash
PW=$(grep '^STALWART_ADMIN_PASSWORD=' /opt/msp/Newbie/deploy/yandex/.env | cut -d= -f2-)

## 1) Очередь — по каждому получателю видна последняя ошибка:
curl -s -u "admin:$PW" -H 'Content-Type: application/json' \
  -d '{"using":["urn:ietf:params:jmap:core","urn:stalwart:jmap"],"methodCalls":[["x:QueuedMessage/get",{},"0"]]}' \
  http://127.0.0.1:8080/jmap/

## 2) Маршрут — найти id у name=postbox-outbound:
curl -s -u "admin:$PW" -H 'Content-Type: application/json' \
  -d '{"using":["urn:ietf:params:jmap:core","urn:stalwart:jmap"],"methodCalls":[["x:MtaRoute/get",{},"0"]]}' \
  http://127.0.0.1:8080/jmap/

## 3) Обновить креды маршрута на актуальный Postbox-ключ (POSTBOX_API_KEY_ID/SECRET из deploy/.env):
curl -s -u "admin:$PW" -H 'Content-Type: application/json' \
  -d '{"using":["urn:ietf:params:jmap:core","urn:stalwart:jmap"],"methodCalls":[["x:MtaRoute/set",{"update":{"<ROUTE_ID>":{"authUsername":"<KEY_ID>","authSecret":{"@type":"Value","secret":"<SECRET>"}}}},"0"]]}' \
  http://127.0.0.1:8080/jmap/

## 4) ОБЯЗАТЕЛЬНО перезапустить Stalwart — маршрут применяется только после рестарта:
sudo docker restart msp-stalwart-1
```

Проверка: письмо с `admin@` на `check-auth@verifier.port25.com`; через пару минут в ящик `admin@` вернётся автоотчёт с результатами SPF/DKIM/DMARC. Зависшие ранее письма до-отправятся на ближайших retry.

#### 9.10 Лиды после переноса: email + Kaiten

Заявка с сайта доходит до Mongo всегда; доставка в каналы зависит от переменных `backend/.env` — при пустых `SMTP_*`/`LEAD_EMAIL_TO` и `KAITEN_*` каналы молча выключены (см. §9.3). На проде 29.09 заполнено: Postbox SMTP (ключ из `deploy/.env`), `LEAD_EMAIL_TO=sales@,admin@`, Kaiten `maksivanovza.kaiten.ru` / доска `1773682` / колонка `6129074` («Новая»).

Проверка после переноса/деплоя:
- [ ] `curl 127.0.0.1:8001/api/integrations/status` → `"kaiten":true`;
- [ ] тестовая заявка → в логах `lead email sent` и `kaiten card created`; письмо пришло, карточка видна в «Новая».

Грабли: неверный/обрезанный Kaiten-токен → `401 Unauthorized` (токен показывается один раз — сразу копировать целиком или перевыпустить на `/profile/api-key`); для карточек нужны `KAITEN_BOARD_ID`+`KAITEN_COLUMN_ID` (ID забрать через API: `/api/latest/spaces/{id}/boards` и `/api/latest/boards/{id}/columns`).


## Материал проекта: `docs/deployment/disaster_recovery.md`

<!-- SOURCE docs/deployment/disaster_recovery.md 86bfc5b8784250fb -->

## Disaster Recovery

Что делать, если прод упал. Короткий практический план.

Для клиентских инцидентов — отдельные runbook'и: [`../runbooks/R-01.md`](https://github.com/i1yxaluk-del/Newbie/blob/main/docs/runbooks/R-01.md) … [`R-11.md`](https://github.com/i1yxaluk-del/Newbie/blob/main/docs/runbooks/R-11.md).
Этот документ — про **нашу** инфраструктуру (landing + bastion + мониторинг).

---

### Сценарий 1: Лендинг недоступен (https://msp-claude.online не открывается)

#### Первые 5 минут

```bash
## 1. Проверить DNS:
dig +short msp-claude.online
## Должен быть <landing_public_ip>

## 2. Проверить доступность по IP:
curl -I http://<landing_public_ip>/api/health
## Если 200 — проблема в DNS / certbot / nginx SSL.
## Если нет ответа — проблема в VM / сети.

## 3. Зайти на VM:
ssh ubuntu@mspshield-landing  # через bastion

## 4. Проверить сервисы:
sudo systemctl status nginx mspshield-backend mongodb
```

#### Типовые причины

| Симптом | Причина | Фикс |
|---------|---------|------|
| `502 Bad Gateway` | FastAPI упал | `sudo systemctl restart mspshield-backend` → смотреть `journalctl -u mspshield-backend -n 100` |
| `SSL_ERROR` в браузере | Сертификат истёк | `sudo certbot renew --force-renewal -d msp-claude.online` |
| `ERR_CONNECTION_REFUSED` | nginx упал | `sudo systemctl restart nginx` |
| `404` на корне | Пропал build | Передеплоить frontend: `ansible-playbook playbooks/site.yml --limit landing --tags frontend` |
| Timeout по IP | VM упала / Yandex Cloud-проблема | Проверить в консоли Yandex Cloud; если VM running — `ssh` с verbose; если stopped — `yc compute instance start` |
| DNS не резолвится | У регистратора проблема | Проверить `dig @ns1.reg.ru msp-claude.online`; в крайнем случае — временно на публичный IP |

#### Эскалация

Если больше 15 минут не решается, и клиенты Gold/Silver активны:

1. Написать в клиентские чаты: «Лендинг недоступен, клиентские сервисы НЕ затронуты (они на отдельных VM)».
2. Сосредоточиться на починке; НЕ параллелить с другими делами.

---

### Сценарий 2: Bastion упал (нет доступа к клиентским хостам)

#### Последствия

- **НЕ** затрагивает клиентский сервис (AmneziaWG peer-to-peer работает напрямую, если настроен `PersistentKeepalive`, но на практике AmneziaWG через hub).
- **Затрагивает** наш доступ к клиентам → мы не можем отреагировать на их инциденты.
- **Затрагивает** Prometheus scrape → ложные алёрты «Instance down».

#### План восстановления

```bash
## 1. Проверить статус VM:
yc compute instance get mspshield-bastion

## 2. Если STOPPED — запустить:
yc compute instance start mspshield-bastion

## 3. Если RUNNING но нет SSH:
## Попробовать serial console в Yandex Cloud UI.

## 4. Если VM целиком умерла — terraform apply пересоздаст её:
cd infra/terraform
terraform apply -replace=yandex_compute_instance.bastion
## ВАЖНО: публичный IP изменится! Надо:
##   - Обновить ansible.cfg (BASTION_PUBLIC_IP).
##   - Обновить Endpoint у всех клиентов в их /etc/amnezia/amneziawg/awg0.conf.
##   - AmneziaWG сервер-ключи нужно восстановить из бэкапа (см. ниже).
```

#### Восстановление AmneziaWG-ключей

Если `/etc/amnezia/amneziawg/` пропал вместе с VM:

1. Достать последний restic-снапшот bastion-ключей (`restic snapshots --host mspshield-bastion`).
2. Восстановить `/etc/amnezia/amneziawg/server_private.key`, `/etc/amnezia/amneziawg/awg0.conf`, `/etc/amnezia/amneziawg/tenants/`.
3. `sudo systemctl restart awg-quick@awg0`.

Если снапшотов нет (не должно быть, но всякое бывает):

- Пересоздать ключи (`awg_bootstrap.sh`).
- **Все клиенты пересоздаются**: `tenant_add.sh` → передать новые конфиги клиентам → они обновляют у себя.

**Время:** 30 мин с снапшотом, 2–4 часа без.

---

### Сценарий 3: Данные заявок пропали (MongoDB упала/побилась)

#### Есть ли бэкап

```bash
ssh ubuntu@mspshield-landing
sudo restic snapshots --host mspshield-landing --path /var/lib/mongodb
```

#### Восстановление

```bash
## 1. Остановить backend и mongo:
sudo systemctl stop mspshield-backend mongodb

## 2. Восстановить данные:
sudo restic restore <snapshot_id> --target /tmp/mongo-restore --include /var/lib/mongodb

## 3. Заменить:
sudo mv /var/lib/mongodb /var/lib/mongodb.broken
sudo mv /tmp/mongo-restore/var/lib/mongodb /var/lib/mongodb
sudo chown -R mongodb:mongodb /var/lib/mongodb

## 4. Запустить:
sudo systemctl start mongodb mspshield-backend

## 5. Проверить:
curl -H "X-Admin-Token: ..." https://msp-claude.online/api/leads | jq length
```

---

### Сценарий 4: Полная потеря инфры (метеорит в Yandex Cloud)

Очень маловероятно, но план нужен.

#### Что у нас есть

- Terraform state в S3-бакете `mspshield-tfstate` (другой регион? — нет, один; **слабое звено**).
- Код в GitHub.
- Restic-бэкапы данных в S3-бакете `mspshield-backups-new`.
- Vaultwarden бэкап в отдельном S3-бакете.

#### План

1. **Если tfstate-бакет жив**: `terraform apply` → AmneziaWG bootstrap → Ansible site.yml → восстановить MongoDB из restic → обновить DNS. **Время:** 4–6 часов.
2. **Если tfstate-бакет умер тоже**: `terraform init` с нуля → `terraform import` существующих ресурсов (если остались), иначе — `apply` с нуля → всё заново. **Время:** 1–2 дня.
3. **Если всё в Yandex Cloud умерло**: перенос в VK Cloud / Selectel. **Время:** 3–7 дней. Единственные данные, которые не потеряются — код в GitHub и бэкапы в S3 (при условии, что восстановим S3-ключи из Vaultwarden-бэкапа).

#### Улучшения (TODO)

- [ ] Бэкап tfstate в отдельный регион / провайдера (v4.2).
- [ ] Бэкап Vaultwarden в Box.com / Google Drive помимо Yandex S3 (v4.2).
- [ ] Документ «Runbook BCP» с контактами облачных провайдеров.

---

### Практика: квартальный DR-drill

Раз в квартал (см. [`../checklists/quarterly.md`](https://github.com/i1yxaluk-del/Newbie/blob/main/docs/checklists/quarterly.md)):

1. Для одного тенанта — `./technical/0_Common/scripts/dr_drill.sh acme` (smoke).
2. Раз в 6 мес — `dr_drill.sh acme --full`.
3. Результаты — в retrospective doc спринта.

Если drill провалился — **P0**, роадмап откладывается до фикса.

---

### Связанные документы

- [`../runbooks/`](https://github.com/i1yxaluk-del/Newbie/blob/main/docs/runbooks) — реагирование на клиентские инциденты.
- [`../post_mortem_template.md`](https://github.com/i1yxaluk-del/Newbie/blob/main/docs/post_mortem_template.md) — шаблон post-mortem после серьёзных инцидентов.
- [`troubleshooting.md`](https://github.com/i1yxaluk-del/Newbie/blob/main/docs/deployment/troubleshooting.md) — мелкие траблы.


## Практический результат

Перескажите цепочку своими словами, выполните безопасную лабораторную работу и сохраните команды без секретов, фактический результат и способ отката. Если результат отличается от текста, остановитесь: сначала исправляется расхождение, а не подгоняется отчёт.
