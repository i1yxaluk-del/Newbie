# Миграция MSP Cloud — полный цикл

> Перенос `msp-claude.online` со старого аккаунта YC (грант кончился) на новый (с грантом).
> Дата миграции: 29–30 июля 2026.

## Финальный статус (30.07.2026)

| Компонент | Статус | Примечание |
|-----------|--------|------------|
| HTTPS + SSL (Caddy) | ✅ | Let's Encrypt, автопродление |
| API + форма заявки | ✅ | 201 Created, валидация |
| Email (Postbox SMTP) | ✅ | `yc.postbox.send` scope обязателен |
| Kaiten (карточки) | ✅ | card создаётся автоматически |
| MongoDB (leads) | ✅ | 10 leads перенесено |
| Stalwart (почта) | ✅ | re-bootstrap с новым паролем |
| Vaultwarden | ✅ | данные перенесены |
| Monitoring (12 конт.) | ✅ | Prometheus+Grafana+Alertmanager |
| AmneziaWG VPN | ✅ | SSH только через 10.9.0.1 |
| Restic бэкапы | ✅ | новый бакет `mspshield-backups-new` |
| Telegram-уведомления | ⚠️ | токен протух — пересоздать в @BotFather |
| MAX (webhook) | ⚠️ | нужна интерактивная авторизация (SMS-код) |

## Итог миграции

| Параметр | Старое | Новое |
|----------|--------|-------|
| Cloud | cloud-maksivanovza (`b1gu6po1t5di6it51evm`) | cloud-maksivanovzas (`b1g8s8tejacfu2l10f3b`) |
| Organization | bpfek9ipbftoamr39i3i | bpfrqtijkphjvdaa29hq |
| Folder | msp-cloude-20260520-220407 (`b1gd6dph0a4cnds0heel`) | default (`b1g9vtje8gar4is5qnsm`) |
| VM ID | fhmab2qg10esn09j0na2 | fhmedri2e4gitkd90l1i |
| IP | 93.77.184.219 (static) | **158.160.47.130** (static) |
| Статус | STOPPED (грант кончился) | RUNNING |

---

## Фаза 1: Извлечение данных со старой ВМ

### 1.1. Запуск старой ВМ

```powershell
yc config profile activate msp-cloudeeeeeee
yc compute instance start fhmab2qg10esn09j0na2 --folder-id b1gd6dph0a4cnds0heel
```

### 1.2. Подключение и инвентаризация

```powershell
ssh -i ~/.ssh/id_ed25519_yc -o StrictHostKeyChecking=no ubuntu@93.77.184.219
```

На ВМ обнаружено:
- Caddy (systemd) — reverse proxy, HTTPS
- Docker Compose "msp": mongo, backend, stalwart, vaultwarden
- Docker Compose "monitoring": prometheus, alertmanager, grafana, node-exporter, cadvisor, blackbox, telegram-webhook, max-alerter
- Restic backup (systemd timer, 02:00 daily → S3)
- UFW: 22 правила

### 1.3. Дамп данных

```bash
mkdir -p /tmp/migration

# MongoDB
docker exec msp-mongo-1 mongodump --archive --gzip > /tmp/migration/mongodump.archive.gz

# Stalwart (почта)
sudo tar czf /tmp/migration/stalwart-etc.tar.gz -C /var/lib/docker/volumes/msp_stalwart-etc/_data .
sudo tar czf /tmp/migration/stalwart-data.tar.gz -C /var/lib/docker/volumes/msp_stalwart-data/_data .

# Vaultwarden (пароли)
sudo tar czf /tmp/migration/vaultwarden-data.tar.gz -C /var/lib/docker/volumes/msp_vaultwarden-data/_data .

# Caddy (SSL-сертификаты)
sudo tar czf /tmp/migration/caddy-data.tar.gz -C /var/lib/caddy .

# Secrets
sudo cp /opt/msp/Newbie/backend/.env /tmp/migration/backend.env.bak
sudo cp /opt/msp/Newbie/deploy/yandex/.env /tmp/migration/deploy.env.bak

# Restic
sudo cp /etc/restic/env.sh /tmp/migration/restic-env.sh
sudo cp /opt/restic-scripts/backup.sh /tmp/migration/restic-backup.sh
sudo cp /opt/restic-scripts/excludes.txt /tmp/migration/restic-excludes.txt
```

### 1.4. Скачивание на локальную машину

```powershell
scp -i ~/.ssh/id_ed25519_yc -r ubuntu@93.77.184.219:/tmp/migration/* ./migration/
```

### 1.5. Остановка старой ВМ

```powershell
yc compute instance stop fhmab2qg10esn09j0na2 --folder-id b1gd6dph0a4cnds0heel
```

---

## Фаза 2: Авторизация в новом аккаунте

### 2.1. Проблема с OAuth (post June 2026)

```
ERROR: OAuth token for user '...', issued after '2026-06-01',
is not supported for IAM token exchange
```

Yandex Cloud с июня 2026 не поддерживает новые OAuth-токены для `yc init`.

### 2.2. Решение: сервисный аккаунт

1. Console → org `bpfrqtijkphjvdaa29hq` → IAM → Сервисные аккаунты
2. Создать SA `msp-deploy` → роль `admin` на облако
3. Создать JSON-ключ → скачать
4. Привязать:

```powershell
yc config profile create msp-new
yc config profile activate msp-new
yc config set service-account-key "C:\path\to\authorized_key.json"
```

### 2.3. Создание облака (если нет)

Облако создаётся в консоли (CLI не даёт прав на создание cloud).
Folder `default` создаётся автоматически.

---

## Фаза 3: Развёртывание в новом облаке

### 3.1. Инфраструктура

```powershell
yc config set cloud-id b1g8s8tejacfu2l10f3b
yc config set folder-id b1g9vtje8gar4is5qnsm
yc config set compute-default-zone ru-central1-a

# VPC + Subnet
yc vpc network create --name msp-net
yc vpc subnet create --name msp-subnet --network-id <net-id> --zone ru-central1-a --range 10.10.0.0/24

# Security Group (все порты)
yc vpc security-group create --name msp-sg --network-id <net-id> \
  --rule direction=ingress,port=22,protocol=tcp,v4-cidrs=[0.0.0.0/0] \
  --rule direction=ingress,port=80,protocol=tcp,v4-cidrs=[0.0.0.0/0] \
  --rule direction=ingress,port=443,protocol=tcp,v4-cidrs=[0.0.0.0/0] \
  --rule direction=ingress,port=443,protocol=udp,v4-cidrs=[0.0.0.0/0] \
  --rule direction=ingress,port=25,protocol=tcp,v4-cidrs=[0.0.0.0/0] \
  --rule direction=ingress,port=465,protocol=tcp,v4-cidrs=[0.0.0.0/0] \
  --rule direction=ingress,port=587,protocol=tcp,v4-cidrs=[0.0.0.0/0] \
  --rule direction=ingress,port=143,protocol=tcp,v4-cidrs=[0.0.0.0/0] \
  --rule direction=ingress,port=993,protocol=tcp,v4-cidrs=[0.0.0.0/0] \
  --rule direction=ingress,port=4190,protocol=tcp,v4-cidrs=[0.0.0.0/0] \
  --rule direction=egress,from-port=0,to-port=65535,protocol=any,v4-cidrs=[0.0.0.0/0]
```

### 3.2. Создание ВМ

```powershell
yc compute instance create --name msp-cloud-vm --zone ru-central1-a \
  --platform-id standard-v3 --cores 2 --core-fraction 50 --memory 4GB --preemptible \
  --create-boot-disk image-id=fd8vnd2mu7b90qob1v6p,size=50GB,type=network-ssd \
  --network-interface subnet-id=<subnet-id>,nat-ip-version=ipv4,security-group-ids=<sg-id> \
  --metadata ssh-keys="ubuntu:<pubkey>"
```

### 3.3. Static IP

```powershell
yc vpc address create --name msp-static-ip --external-ipv4 zone=ru-central1-a
# → 158.160.47.130

yc compute instance remove-one-to-one-nat msp-cloud-vm --network-interface-index 0
yc compute instance add-one-to-one-nat msp-cloud-vm --nat-address 158.160.47.130 --network-interface-index 0
```

### 3.4. Базовая подготовка (вместо cloud-init)

Через SSH: установка Docker CE, Caddy, Node.js 20, Yarn, UFW, AmneziaWG.
Полный скрипт: `deploy/yandex/cloud-init.yaml` (runcmd секция).

### 3.5. Загрузка кода

```powershell
# Zip (только backend + frontend + deploy, без node_modules)
# SCP на ВМ → unzip в /opt/msp/Newbie
```

### 3.6. Сборка и запуск

```bash
cd /opt/msp/Newbie/frontend && yarn install && yarn build
sudo cp -r build /var/www/landing
# Caddyfile: sed '{$MSP_DOMAIN}' → 'msp-claude.online'
sudo systemctl restart caddy
cd /opt/msp/Newbie/deploy/yandex && sudo docker compose build && sudo docker compose up -d
cd monitoring && sudo docker compose up -d --build
```

### Уроки этой миграции

- `craco.config.js` не попал в zip → билд упал. **Всегда включать все конфиги фронта.**
- `sudo` создает файлы root'ом → `yarn build` падает с EACCES. **Фикс: `sudo chown -R ubuntu:ubuntu /opt/msp`**
- Caddyfile: `{$MSP_DOMAIN}` не заменяется через PowerShell→SSH→sed (экранирование). **Фикс: base64-encode команды.**
- `yc vpc address create` требует `--external-ipv4 zone=...` (не просто `--zone`).
- Monitoring: `services/max_alerter` нужен для билда. **Включать в zip.**
- Alertmanager entrypoint.sh: нет +x после unzip. **Фикс: `chmod +x`.**
- `/var/log/caddy/access.log` — Caddy не стартует без прав. **Фикс: `mkdir + chown caddy:caddy`.**
- OAuth-токены после 01.06.2026 не работают с yc CLI. **Фикс: SA JSON-ключ.**
- Postbox SMTP: API key без scope `yc.postbox.send` → 535. **Scope обязателен.**
- `docker compose restart` НЕ перечитывает env_file. **Нужен `up -d --force-recreate`.**
- AmneziaWG скрипты с CRLF (из Windows) → `set: pipefail\r: invalid`. **Фикс: `sed -i 's/\r$//'`.**
- UFW `delete` спрашивает подтверждение → таймаут. **Фикс: `yes | sudo ufw delete N`.**
- Stalwart bootstrap: env vars читаются ТОЛЬКО при пустом volume. После restore — старый конфиг. **Фикс: удалить volume + re-bootstrap.**

---

## Фаза 4: Восстановление данных

### 4.1. Загрузка migration-данных

```powershell
scp -i ~/.ssh/id_ed25519_yc_new -r ./migration/* ubuntu@158.160.47.130:/tmp/migration/
```

### 4.2. restore-on-vm.sh

```bash
sudo bash /tmp/migration/restore-on-vm.sh
```

Скрипт:
1. Останавливает контейнеры
2. Восстанавливает MongoDB (mongorestore --archive --gzip --drop)
3. Восстанавливает Stalwart volumes (tar → docker volume)
4. Восстанавливает Vaultwarden volume
5. Восстанавливает Caddy data (SSL certs)
6. Перезаписывает .env (реальные секреты вместо сгенерированных)
7. Устанавливает restic backup (systemd timer)
8. Запускает все контейнеры
9. Перезапускает Caddy

---

## Фаза 5: DNS

### Namecheap (или reg.ru)

| Тип | Хост | Значение | TTL |
|-----|------|----------|-----|
| A | @ | 158.160.47.130 | 300 |
| A | www | 158.160.47.130 | 300 |
| A | mail | 158.160.47.130 | 300 |
| A | vault | 158.160.47.130 | 300 |
| A | mon | 158.160.47.130 | 300 |
| MX | @ | mail.msp-claude.online (10) | 300 |

Ожидание: 5-30 минут.

---

## Фаза 6: Тестирование

### 6.1. Сайт

```bash
curl -I https://msp-claude.online
# HTTP/2 200, server: Caddy

curl https://msp-claude.online/api/health
# {"status":"ok","db":"connected"}
```

### 6.2. Форма заявки

```bash
curl -X POST https://msp-claude.online/api/leads \
  -H "Content-Type: application/json" \
  -d '{"name":"Тест Миграция","phone":"+79990000001","email":"test@migr.ru","company":"Тест","tier":"bronze","consent":true,"website":""}'
# → {"id":"...","status":"новая"}
```

Проверить: Telegram-бот получил уведомление.

### 6.3. Почта

```bash
ssh -L 8080:127.0.0.1:8080 ubuntu@158.160.47.130
# → http://localhost:8080/admin (Stalwart WebUI)
```

### 6.4. Vaultwarden

```
https://vault.msp-claude.online
```

### 6.5. Grafana

```
https://mon.msp-claude.online
```

### 6.6. Мониторинг

```bash
ssh ubuntu@158.160.47.130 "curl -s http://localhost:9090/-/healthy"
# Prometheus is Healthy.

ssh ubuntu@158.160.47.130 "curl -s http://localhost:9093/-/healthy"
# OK
```

### 6.7. Бэкапы

```bash
ssh ubuntu@158.160.47.130 "systemctl status restic-backup.timer"
# active (waiting), next run 02:00
```

---

## Фаза 7: Завершение

### 7.1. Удаление старой ВМ (через 7 дней)

```powershell
yc config profile activate msp-cloudeeeeeee
yc compute instance delete fhmab2qg10esn09j0na2 --folder-id b1gd6dph0a4cnds0heel
# Опционально: удалить static IP, subnet, network, folder
```

### 7.2. Postbox (SMTP relay)

Создан в новом облаке (30.07.2026):
- SA: `postbox-sender` (`ajeq2njbvgqf0fohc2g1`), роль `postbox.sender`
- API key: `ajecoam3o060ble9c3hn` (scope: **`yc.postbox.send`** — обязательно!)
- Домен: `msp-claude.online` (DKIM verified)

**Урок**: API key БЕЗ scope `yc.postbox.send` даёт 535 Auth failed.
**Урок**: `docker compose restart` НЕ перечитывает `.env` — нужен `up -d --force-recreate`.

### 7.3. Object Storage (бэкапы)

Создан в новом облаке (30.07.2026):
- Бакет: `mspshield-backups-new`
- SA: `restic-backup` (`ajelluv4koa355uduqon`), роль `storage.editor`
- Static key: `YCAJEjHm-OMbs2zvXVNs8x5nD`
- Restic repo: `s3:storage.yandexcloud.net/mspshield-backups-new`
- Timer: ежедневно 02:00 (`restic-backup.timer`)

---

## Файлы

| Файл | Назначение |
|------|-----------|
| `migrate.ps1` | Оркестратор (SCP + restore) |
| `restore-on-vm.sh` | Восстановление на ВМ |
| `README.md` | Этот документ |
| `mongodump.archive.gz` | Дамп MongoDB (не коммитить) |
| `*.tar.gz` | Дампы volumes (не коммитить) |
| `*.env.bak` | Секреты (не коммитить!) |
| `restic-env.sh` | Ключи S3 (не коммитить!) |
