# Продакшен-развёртывание лендинга `mspshield.ru`

Цель: поднять публичный сайт на Yandex Cloud, чтобы `https://mspshield.ru` отдавал лендинг с валидным SSL, форма заявки писала в MongoDB, Telegram-бот получал уведомления.

**Время:** 4–6 часов (первый раз).
**Стоимость:** ~2 500–4 000 ₽/мес (2 VM + Object Storage + domain).
**Предпосылка:** локально всё работает ([`local_dev.md`](local_dev.md)).
**Когда делать:** спринт 2 Этапа 4 (см. [`../roadmap/etape_4_sprints.md`](../roadmap/etape_4_sprints.md)).

---

## Обзор этапов

1. [Подготовка домена](#1-домен).
2. [Установка CLI-инструментов](#2-инструменты).
3. [Terraform apply — поднятие VM, сети, Object Storage](#3-terraform).
4. [WireGuard bootstrap на bastion](#4-wireguard).
5. [Ansible site.yml — настройка landing-VM](#5-ansible).
6. [DNS-переключение + SSL от Let's Encrypt](#6-dns--ssl).
7. [Telegram-уведомления](#7-telegram).
8. [Мониторинг: Prometheus + Alertmanager](#8-monitoring).
9. [Smoke-test + чек-лист готовности](#9-smoke-test).

---

<a id="1-домен"></a>
## 1. Домен

### Покупка

- Купить `mspshield.ru` на [reg.ru](https://reg.ru) или [beget.com](https://beget.com). Цена: ~600–900 ₽/год.
- Настроить DNS-сервер: сначала **оставить по умолчанию** (NS от регистратора), чтобы потом безболезненно переключить на Yandex Cloud DNS.

### Почему сейчас, а не позже

Домен нужен, чтобы Let's Encrypt выпустил SSL-сертификат. Пока не куплен — `certbot` не сработает.

---

<a id="2-инструменты"></a>
## 2. Установка CLI

| Инструмент | Версия | Установка |
|------------|--------|-----------|
| `yc` | последняя | `curl -sSL https://storage.yandexcloud.net/yandexcloud-yc/install.sh \| bash` |
| `terraform` | ≥ 1.5 | [releases](https://developer.hashicorp.com/terraform/downloads) |
| `ansible` | ≥ 2.15 | `pip install ansible` или `apt install ansible` |
| `certbot` | последняя | на landing-VM, ставится через Ansible |
| `wireguard-tools` | любая | на bastion, ставится через Ansible |

### Инициализация yc

```bash
yc init
# Выбрать аккаунт → folder → default-zone ru-central1-a.
```

Получить `folder_id`:

```bash
yc config get folder-id
# b1g...
```

Получить `ubuntu_image_id`:

```bash
yc compute image list --folder-id standard-images --format json \
  | jq '.[] | select(.family=="ubuntu-2204-lts") | {id, status, family}' \
  | head -10
# Взять последний с status=ACTIVE.
```

---

<a id="3-terraform"></a>
## 3. Terraform — базовая инфраструктура

Конфигурация лежит в [`infra/terraform/main.tf`](../../infra/terraform/main.tf). Разворачивает landing-VM, bastion-VM, сеть, Object Storage bucket.

### 3.1. Создать state-bucket в Yandex Object Storage (один раз)

```bash
yc storage bucket create --name mspshield-tfstate
# И создать сервис-аккаунт с правами storage.editor на этот бакет,
# получить static-key: yc iam access-key create --service-account-id ...
# Экспортировать:
export AWS_ACCESS_KEY_ID=<key_id>
export AWS_SECRET_ACCESS_KEY=<secret>
```

### 3.2. Подготовить terraform.tfvars (локально, не коммитить)

Создать `infra/terraform/terraform.tfvars`:

```hcl
folder_id         = "b1g..."
ubuntu_image_id   = "fd8..."
ssh_public_key    = "ssh-ed25519 AAAA... user@host"
admin_ssh_sources = ["1.2.3.4/32"]  # твой домашний IP /32
env               = "prod"
```

Убедиться, что этот файл в `.gitignore`:

```bash
echo "infra/terraform/terraform.tfvars" >> .gitignore
echo "infra/terraform/.terraform/" >> .gitignore
echo "infra/terraform/*.tfstate*" >> .gitignore
```

### 3.3. Apply

```bash
cd infra/terraform
terraform init
terraform plan   # внимательно прочитать — что будет создано
terraform apply  # yes
```

Время: ~3–5 минут.

### 3.4. Получить публичные IP

```bash
terraform output -raw bastion_public_ip
# 51.xxx.xxx.xxx

terraform output -raw landing_public_ip
# 51.yyy.yyy.yyy
```

Сохранить оба IP — нужны на следующих шагах.

---

<a id="4-wireguard"></a>
## 4. WireGuard bootstrap на bastion

### 4.1. Зайти на bastion

```bash
ssh ubuntu@<bastion_public_ip>
```

### 4.2. Запустить wg_bootstrap.sh

```bash
# На bastion:
sudo apt update && sudo apt install -y wireguard-tools
# Склонировать репо (read-only key хватит):
git clone https://github.com/i1yxaluk-del/Newbie.git
cd Newbie
sudo bash technical/0_Common/wireguard/wg_bootstrap.sh
```

Скрипт:

- Сгенерирует server_private.key / server_public.key в `/etc/wireguard/`.
- Создаст `/etc/wireguard/wg0.conf` с Address = 10.10.0.1/16, ListenPort = 51820.
- Включит `wg-quick@wg0.service`.

Проверка:

```bash
sudo wg show
# interface: wg0
#   public key: ...
#   private key: (hidden)
#   listening port: 51820
```

### 4.3. Добавить peer для landing-VM

```bash
sudo bash technical/0_Common/wireguard/tenant_add.sh landing 10.10.0.11/32
# Вывод: peer-config для landing, сохранить временно.
```

Скопировать на landing-VM и включить WireGuard там (Ansible сделает это автоматически на следующем шаге).

---

<a id="5-ansible"></a>
## 5. Ansible — настройка landing-VM

### 5.1. Подготовка control-машины

На своей машине (не на VM):

```bash
cd technical/0_Common/ansible
export BASTION_PUBLIC_IP=<из terraform output>
# Проверить, что инвентарь доступен:
ansible all -m ping
# Должно быть: mspshield-landing | SUCCESS
```

Если ping не проходит — проблема с ProxyJump через bastion. Проверить `~/.ssh/config`:

```
Host mspshield-bastion
    HostName <bastion_public_ip>
    User ubuntu

Host 10.10.0.*
    ProxyJump mspshield-bastion
    User ubuntu
```

### 5.2. Запуск site.yml

```bash
ansible-playbook playbooks/site.yml --limit landing
```

Playbook поставит:

- baseline hardening (SSH config, auditd, unattended-upgrades, fail2ban);
- nginx с конфигом из `deploy/nginx/mspshield.conf`;
- FastAPI как systemd-сервис;
- MongoDB локально;
- WireGuard-peer к bastion (подключение к оверлею 10.10.0.0/16);
- Prometheus node_exporter на 9100.

Время: ~10–15 минут.

### 5.3. Верификация

```bash
ssh ubuntu@mspshield-landing  # через bastion ProxyJump
sudo systemctl status nginx mongodb mspshield-backend
# Все три — active (running).
```

---

<a id="6-dns--ssl"></a>
## 6. DNS + SSL от Let's Encrypt

### 6.1. DNS

В панели регистратора (reg.ru / beget):

- A-запись `mspshield.ru` → `<landing_public_ip>`.
- A-запись `www.mspshield.ru` → `<landing_public_ip>`.
- TTL 300.

Дождаться распространения:

```bash
dig +short mspshield.ru
# должен быть <landing_public_ip>
```

Обычно 5–30 минут.

### 6.2. Выпустить SSL-сертификат

На landing-VM:

```bash
ssh ubuntu@mspshield-landing
sudo apt install -y certbot python3-certbot-nginx
sudo certbot --nginx -d mspshield.ru -d www.mspshield.ru \
  --non-interactive --agree-tos --email owner@mspshield.ru --redirect
```

Сертификат будет обновляться автоматически (systemd-timer `certbot.timer`). Проверка:

```bash
sudo certbot renew --dry-run
```

### 6.3. Проверка HTTPS

```bash
curl -I https://mspshield.ru
# HTTP/2 200
# server: nginx
```

Открыть в браузере — должен быть зелёный замок.

---

<a id="7-telegram"></a>
## 7. Telegram-уведомления

### 7.1. Создать бота

1. В Telegram: чат с `@BotFather` → `/newbot` → имя `MSPShield Leads Bot` → username `mspshield_leads_bot` → получить `BOT_TOKEN` (например, `7123456789:AAH...`).
2. Создать канал или группу для уведомлений, добавить бота как админа.
3. Получить `CHAT_ID`: прислать в группу любое сообщение, затем:

```bash
curl "https://api.telegram.org/bot<BOT_TOKEN>/getUpdates" | jq '.result[].message.chat.id'
# например, -1001234567890
```

### 7.2. Прописать на landing-VM

```bash
ssh ubuntu@mspshield-landing
sudo nano /etc/mspshield/backend.env
# TG_BOT_TOKEN=7123456789:AAH...
# TG_CHAT_ID=-1001234567890

sudo systemctl restart mspshield-backend
```

### 7.3. Тест

Отправить заявку с `https://mspshield.ru` → проверить, что сообщение прилетело в канал.

---

<a id="8-monitoring"></a>
## 8. Мониторинг

Prometheus и Alertmanager ставятся Ansible-playbook'ом `monitoring_install.yml` (см. `technical/0_Common/ansible/playbooks/`). Конфиги — [`technical/0_Common/monitoring/prometheus.yml`](../../technical/0_Common/monitoring/prometheus.yml) и [`alertmanager.yml`](../../technical/0_Common/monitoring/alertmanager.yml).

### Быстрая проверка

```bash
ssh ubuntu@mspshield-landing
curl -s http://localhost:9090/-/healthy
# Prometheus is Healthy.
curl -s http://localhost:9093/-/healthy
# OK
```

### Алёрты в Telegram

В [`alertmanager.yml`](../../technical/0_Common/monitoring/alertmanager.yml) уже есть `telegram` и `telegram_p1` receivers. Надо:

1. Положить `/etc/alertmanager/tg_bot_token` (тот же бот или отдельный «alerts»-бот).
2. Заменить `chat_id: 0` на реальный chat_id (можно другой чат для P1/P2).
3. `sudo systemctl restart alertmanager`.

---

<a id="9-smoke-test"></a>
## 9. Smoke-test + готовность

### Чек-лист production-готовности

- [ ] `curl -I https://mspshield.ru` → 200 + TLS-валидный.
- [ ] `curl https://mspshield.ru/api/health` → `{"status":"ok"}`.
- [ ] Форма заявки отправляется → запись появилась в MongoDB (`mongo --eval 'db.leads.countDocuments()'`).
- [ ] Telegram-бот получил уведомление о заявке.
- [ ] `curl https://mspshield.ru/api/leads -H "X-Admin-Token: ..."` → список заявок.
- [ ] В Prometheus (`http://localhost:9090/targets` через SSH-туннель) — все таргеты `UP`.
- [ ] `curl https://mspshield.ru/metrics` **заблокирован** извне (должно быть 403/404 от nginx).
- [ ] `certbot renew --dry-run` — успех.
- [ ] На bastion `wg show` — peer landing подключен.
- [ ] `backup_install.yml` прогнан на landing (есть бэкапы в Object Storage).
- [ ] Мониторинг: создан тестовый алёрт (остановить nginx на 60 сек) → Telegram получил, восстановление (resolved) тоже пришло.

### Smoke-test формы заявки

```bash
curl -X POST https://mspshield.ru/api/leads \
  -H "Content-Type: application/json" \
  -d '{
    "name":"Тест Тестов",
    "phone":"+79991112233",
    "email":"test@example.com",
    "company":"Тест-ООО",
    "tier":"bronze",
    "consent":true,
    "website":""
  }'
# {"id":"...","status":"новая",...}
```

Если всё зелёное — лендинг в продакшене, можно двигаться к спринту 3 Этапа 4 (HH-hunter kick-off).

---

## Что дальше

- Клиент подписал контракт → [`tenant_onboarding.md`](tenant_onboarding.md).
- Сбой в проде → [`disaster_recovery.md`](disaster_recovery.md), [`../runbooks/`](../runbooks/).
- Проблема с развёртыванием → [`troubleshooting.md`](troubleshooting.md).
