# Path A: единая VM (Caddy + Docker) — deep-dive

> **Где это в общей картине.** Это **полный raw-флоу Path A** —
> production-стек на одной статической IP-VM в Yandex Cloud, с автоматизацией
> через PowerShell-скрипт `deploy.ps1`.
>
> **Обзор обоих путей (Path A vs Path B)** — в [`../../docs/deployment/README.md`](../../docs/deployment/README.md).
> **Path B (две VM, Terraform + Ansible)** — в [`../../docs/deployment/landing_production.md`](../../docs/deployment/landing_production.md).
>
> Этот документ нужен, если ты уже выбрал Path A и хочешь пошаговый
> командный флоу с Win10.

Автоматическое развёртывание production-стека:

- **Лендинг** (React static) + **Backend** (FastAPI + MongoDB)
- **Caddy** — авто-HTTPS через Let's Encrypt, TCP/443
- **AmneziaWG** на UDP/443 (bastion-функция совмещена с landing VM; см. [`../../technical/0_Common/amneziawg/`](../../technical/0_Common/amneziawg/))
- **Stalwart Mail Server** — admin@, sales@, alert@ ящики (submit-only 465/587, outbound через Yandex Cloud Postbox; см. [STALWART_RELAY_MODE.md](STALWART_RELAY_MODE.md))

Запускается одной командой PowerShell на Windows 10.

---

## 0. TL;DR — за 5 минут

```powershell
# 1. Клонируйте репозиторий
cd C:\Projects
git clone https://github.com/i1yxaluk-del/Newbie.git
cd Newbie

# 2. Запустите деплой
.\deploy\yandex\deploy.ps1

# 3. Получите public IP в выводе и пропишите в DNS:
#     A    msp-claude.online      → <IP>
#     A    www.msp-claude.online  → <IP>
#     A    mail.msp-claude.online → <IP>

# 4. Через 10-30 минут (после DNS propagation) откройте:
#     https://msp-claude.online
```

---

## 1. Что разворачивается

```
                              Internet
                                 │
            ┌────────────────────┼───────────────────────┐
            │                    │                       │
        :443 HTTPS         :465/587/993/...          :22 SSH
            │                    │                       │
       ┌────▼────┐         ┌─────▼─────┐                 │
       │  Caddy  │         │  Stalwart │                 │
       │ (host)  │         │  (Docker) │                 │
       └────┬────┘         └─────┬─────┘                 │
            │                    │                       │
   ┌────────┴────────┐           │                       │
   │                 │           │                       │
   ▼ /api/*          ▼ /         ▼ mail-storage          ▼
┌────────┐    ┌──────────┐    ┌─────────┐         ┌──────────┐
│Backend │    │  Static  │    │ stalwart│         │ ubuntu@VM│
│FastAPI │    │  React   │    │  -data  │         │ (Docker) │
│ :8001  │    │  /var/www│    │  volume │         └──────────┘
└───┬────┘    │ /landing │    └─────────┘
    │         └──────────┘
    ▼
┌──────┐
│Mongo │
│ :27017│
│(внутр)│
└──────┘
```

**Ресурсы Yandex Cloud:**
- 1 × VM (`msp-cloud-vm`, по умолчанию 2 vCPU / 4 GB RAM / 50 GB SSD, прерываемая)
- 1 × Static IP (reserved, обязателен для preemptible — см. стоимость ниже)
- 1 × VPC сеть (`msp-net`)
- 1 × Subnet (`msp-subnet`, 10.10.0.0/24)
- 1 × Security Group (`msp-sg`) — открыты 22/80/443 + 465/587/143/993/4190 (Stalwart submit-only). **TCP/25 НЕ открыт** — Yandex Cloud блокирует на уровне платформы.

**Стоимость (реальные данные из деплоя, май 2026):**

| Компонент | Спеки | ₽/мес |
|---|---|---:|
| Preemptible VM | 2 vCPU 50%, 4 GB, 50 GB SSD | ~1 486 |
| Static IP (reserved) | обязателен для preemptible (иначе IP меняется при рестарте) | ~190 |
| **Итого** | | **~1 676** |

> ⚠️ Preemptible VM может быть остановлена YC в любой момент. При рестарте
> IP сохраняется только если зарезервирован static IP (+190₽/мес). Без static IP
> DNS A-записи устаревают после каждого рестарта.

**Альтернатива:** гарантированная (regular) VM с теми же спеками — ~1 300₽/мес + static IP = ~1 490₽/мес (дороже preemptible, но без риска остановки).

**Для сравнения (из тарифов):**
- Bronze отпускная цена: от 25 000 ₽/мес
- Инфра-расход: ~1 700₽ → маржа ≈ 93% (без учёта труда)

---

## 2. Требования

| Компонент | Версия / источник |
|-----------|---------------------|
| Windows  | 10 build 1803+ или 11 |
| PowerShell | 5.1+ (встроен в Windows) |
| OpenSSH client | Встроен в Win10 1803+ (`Settings → Apps → Optional features`) |
| tar | Встроен в Win10 17063+ |
| Интернет | для скачивания yc CLI + OAuth + образов Docker |
| Yandex Cloud аккаунт | с привязанной картой (https://console.cloud.yandex.ru) |
| Домен | зарегистрированный, с доступом к DNS-зоне |

**`yc` CLI скрипт ставит автоматически** при первом запуске (через
официальный installer-скрипт от Яндекса).

---

## 3. Запуск

### 3.1. Дефолтные параметры

```powershell
cd C:\путь\к\репозиторию\Newbie
.\deploy\yandex\deploy.ps1
```

Развернёт:
- Домен: `msp-claude.online`
- Зона: `ru-central1-a`
- ВМ: 2 vCPU (50% guarantee) / 4 GB / 50 GB SSD, прерываемая
- Mail: Stalwart с 3 ящиками (admin@, sales@, alert@)

### 3.2. С параметрами

```powershell
.\deploy\yandex\deploy.ps1 `
    -Domain "msp-claude.online" `
    -Zone "ru-central1-b" `
    -VmCores 4 `
    -VmMemoryGb 8 `
    -VmDiskGb 100 `
    -Preemptible:$false
```

### 3.3. Только web, без почты

```powershell
.\deploy\yandex\deploy.ps1 -SkipMail
```

### 3.4. Пересоздать с нуля (УНИЧТОЖИТ MongoDB!)

```powershell
.\deploy\yandex\deploy.ps1 -Recreate
```

---

## 4. Что делает скрипт (8 этапов)

```
[1/8] Проверка yc CLI и SSH      — ставит yc если нет
[2/8] OAuth Yandex Cloud         — открывает браузер, токен сохраняется локально
[3/8] SSH key + VPC + Subnet     — генерит ed25519 ключ, создаёт сеть
[4/8] Создание ВМ                — Ubuntu 22.04, cloud-init = базовый bootstrap
[5/8] Ожидание RUNNING + sshd    — до 5 минут на boot + cloud-init
[6/8] Загрузка кода (scp)        — tarball ~10 MB → /opt/msp/Newbie
[7/8] setup-on-vm.sh             — yarn build, .env, docker compose up
[8/8] Healthcheck + DNS-инструкции
```

Логи всех этапов: `%TEMP%\msp-deploy-YYYYMMDD-HHMMSS.log`.

---

## 5. После деплоя

### 5.1. Пропишите DNS-записи

| Тип | Имя | Значение |
|-----|-----|----------|
| `A` | `msp-claude.online` | `<public IP из вывода скрипта>` |
| `A` | `www.msp-claude.online` | `<public IP>` |
| `A` | `mail.msp-claude.online` | `<public IP>` |
| `A` | `vault.msp-claude.online` | `<public IP>` |
| `A` | `bastion.msp-claude.online` | `<public IP>` |
| `MX` | `msp-claude.online` | `10 mail.msp-claude.online` |
| `TXT` | `msp-claude.online` | `v=spf1 a mx ip4:<public IP> -all` |
| `TXT` | `_dmarc.msp-claude.online` | `v=DMARC1; p=quarantine; rua=mailto:admin@msp-claude.online` |
| `TXT` | `default._domainkey.msp-claude.online` | *(см. 5.2)* |

### 5.2. Получите DKIM-ключ из Stalwart

После того как DNS пропагнулся (хотя бы A-записи на лендинг + mail):

```powershell
# Запустите SSH-туннель к Stalwart admin (порт 8080)
$IP = "<ваш IP>"
$SshKey = "$env:USERPROFILE\.ssh\id_ed25519_yc_new"
ssh -L 8080:localhost:8080 -i $SshKey ubuntu@$IP
```

Затем откройте в браузере http://localhost:8080/admin

- Логин: `admin`
- Пароль: из файла на ВМ (`cat ~/msp-deploy-secrets.txt`)

В Settings → Domains → msp-claude.online → **Generate DKIM**.
Stalwart выдаст TXT-запись вида:
```
default._domainkey.msp-claude.online   TXT   "v=DKIM1; k=rsa; p=MIGfMA0GCSq..."
```
Скопируйте её к регистратору домена.

### 5.3. Создайте mailbox-аккаунты в Stalwart

В том же admin WebUI:

1. **Settings → Accounts → Add User**
   - `admin@msp-claude.online` — пароль из `msp-deploy-secrets.txt`
   - `sales@msp-claude.online`
   - `alert@msp-claude.online`

2. **Settings → Domains → msp-claude.online**
   - Убедитесь что **status = active**
   - **MX records → Verify** должен показать ✓

3. **Settings → TLS → Certificates → Add Manual Certificate**
   - Путь к cert: `/etc/stalwart-certs/certificates/acme-v02.api.letsencrypt.org-directory/mail.msp-claude.online/mail.msp-claude.online.crt`
   - Путь к key: `/etc/stalwart-certs/certificates/acme-v02.api.letsencrypt.org-directory/mail.msp-claude.online/mail.msp-claude.online.key`

   (Каталог появится после того как Caddy получит сертификат — это происходит автоматически в первые 1-2 минуты после propagation A-записи `mail.<domain>`.)

### 5.4. Получите пароли с ВМ

```powershell
$IP = "<ваш IP>"
$SshKey = "$env:USERPROFILE\.ssh\id_ed25519_yc_new"
ssh -i $SshKey ubuntu@$IP "cat ~/msp-deploy-secrets.txt"
```

Скопируйте этот файл в надёжное место (1Password / Vaultwarden / KeePass)
и **удалите с ВМ**:

```powershell
ssh -i $SshKey ubuntu@$IP "shred -u ~/msp-deploy-secrets.txt"
```

### 5.5. Тестовая отправка письма (через локальный submit)

```bash
# На VM — отправка через Stalwart SMTPS (stalwart-cli НЕТ в Docker v0.16)
python3 -c "
import smtplib, ssl
from email.mime.text import MIMEText
msg = MIMEText('Test from Stalwart')
msg['Subject'] = 'Test'
msg['From'] = 'alert@msp-claude.online'
msg['To'] = 'admin@msp-claude.online'
ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE
s = smtplib.SMTP_SSL('127.0.0.1', 465, timeout=15, context=ctx)
s.login('alert@msp-claude.online', '<alert-password>')
s.send_message(msg)
s.quit()
print('SENT OK')
"
```

```bash
# Или просто с Outlook/Thunderbird: SMTP mail.msp-claude.online:465, implicit TLS
```

### 5.6. Чтение почты в Thunderbird/Outlook

- **Сервер:** `mail.msp-claude.online`
- **IMAP:** порт 993 / SSL/TLS
- **SMTP submission:** порт 465 (implicit TLS) или 587 (STARTTLS)
- **Логин:** `sales@msp-claude.online`
- **Пароль:** из `msp-deploy-secrets.txt`

Входящие письма из интернета **прилетают через внешний MX-провайдер**
(Yandex 360 / Mailgun routes / Cloudflare Email Routing) → forwards на наш :587 → Stalwart кладёт
в локальные ящики. Конфигурация — в [STALWART_RELAY_MODE.md](STALWART_RELAY_MODE.md).

---

## 6. ⚠️ Yandex Cloud блокирует TCP/25 на публичных IP VPC

**Цитата из ответа Yandex Cloud support:**

> Yandex Cloud автоматически блокирует трафик, который отправляется с
> публичных IP-адресов Virtual Private Cloud на TCP-порт 25 любых
> серверов в интернете и в Yandex Compute Cloud. Выдать адрес с
> открытым портом 25 сейчас не получится по техническим причинам.
> Для альтернативного решения предлагаем перенастроить почтовый сервер
> на открытые почтовые порты — 465 и 587.

### Что это значит для нас

| Сценарий | Работает? |
|----------|-----------|
| MX-приём почты на наш публичный IP (`:25`) | ❌ нет |
| Прямой outbound с нашей VM на чужой `:25` (Gmail/Outlook/Mail.ru) | ❌ нет |
| Submission auth на наш Stalwart `:465` / `:587` | ✅ да |
| Локальная доставка между ящиками `*@msp-claude.online` | ✅ да |
| Grafana/Wazuh/Alertmanager → Stalwart `:587` (внутри VM) | ✅ да |
| Outbound через smarthost Yandex Cloud Postbox `postbox.cloud.yandex.net:465` implicit TLS | ✅ да |
| Чтение ящиков через IMAPS `:993` | ✅ да |

### Архитектурное решение — submit-only Stalwart + внешний MX

Stalwart **не работает как MX**. Inbound почта приходит через внешнего
провайдера (Yandex 360 / Mailgun routes / Cloudflare Email Routing),
который принимает её на свой `:25` и пересылает к нам на `:587`.

Outbound — через smarthost Yandex Cloud Postbox на `:465` implicit TLS
(auth = API key ID + secret service account `postbox-sender`). Postbox
MX-записи НЕ выдаёт — он только отправляет.

Полный пошаговый план настройки (DNS, smarthost, DKIM, проверка):
[STALWART_RELAY_MODE.md](STALWART_RELAY_MODE.md).

### Если YC всё же разблокирует `:25`

Иногда YC support одобряет разблокировку по обоснованному тикету
(B2B-юрлицо, SPF/DKIM/DMARC настроены, anti-spam меры в Stalwart). По
состоянию на 2025-11 это **редкость**, а ответ «выдать IP с открытым :25
не получится по техническим причинам» — стандартный.

Если разблокировка произошла — секция «Откат» в
[STALWART_RELAY_MODE.md](STALWART_RELAY_MODE.md)
описывает, как вернуть классическую MX-схему.

---

## 7. Репутация нового IP

Новый IP в Яндекс/Selectel/Hetzner — это **mail reputation = 0**.
Первые 2-4 недели крупные провайдеры (Gmail, Mail.ru, Outlook) будут
часть писем класть в спам или вообще rejecting'ить.

**Как ускорить разогрев:**

1. **Не шлите 1000 писем сразу.** Начните с 10-20 в день, через неделю — 50, через 2 — 100.
2. **Попросите получателей** вытащить из спама + добавить в адресную книгу.
3. **Постучитесь в Postmaster Tools:**
   - Google: https://postmaster.google.com — добавьте `msp-claude.online`
   - Microsoft SNDS: https://sendersupport.olc.protection.outlook.com/snds/
   - Mail.ru Postmaster: https://postmaster.mail.ru/
4. **Регулярно проверяйте blacklist'ы**: https://mxtoolbox.com/blacklists.aspx

---

## 8. Подключение к интеграциям

### 8.1. Grafana → SMTP-алерты через Postbox

Grafana отправляет email **напрямую через Postbox** (не через внутренний Stalwart),
т.к. мониторинг-стек работает в отдельной Docker-сети `msp-monitoring`.
Настройка через env vars в `deploy/yandex/monitoring/.env`:
```
GF_SMTP_ENABLED=true
GF_SMTP_HOST=postbox.cloud.yandex.net:465
GF_SMTP_USER=<postbox-api-key-id>
GF_SMTP_PASSWORD=<postbox-api-key-secret>
GF_SMTP_FROM_ADDRESS=alert@msp-claude.online
```

### 8.2. Wazuh → SMTP

В `/var/ossec/etc/ossec.conf` (Wazuh на той же VM — через внутренний Stalwart):
```xml
<global>
  <email_notification>yes</email_notification>
  <smtp_server>stalwart</smtp_server>
  <email_from>alert@msp-claude.online</email_from>
  <email_to>admin@msp-claude.online</email_to>
</global>
```

### 8.3. Alertmanager → Stalwart :25 (email для всех алёртов)

Alertmanager отправляет email **через внутренний Stalwart** (`stalwart:25`),
т.к. AM v0.27 не поддерживает implicit TLS (Postbox :465 требует implicit TLS).
AM подключён к обеим сетям (`msp-monitoring` + `msp_default`).
Конфиг в `deploy/yandex/monitoring/alertmanager/alertmanager.yml`:
```yaml
global:
  smtp_smarthost: "stalwart:25"
  smtp_from: "alert@msp-claude.online"
  smtp_hello: "msp-claude.online"
  smtp_auth_username: "alert@msp-claude.online"
  smtp_auth_password: "<alert-password>"
  smtp_require_tls: false
```

---

## 9. Управление развёрнутой системой

### 9.1. SSH на ВМ

```powershell
ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=NUL -i "$env:USERPROFILE\.ssh\id_ed25519_yc_new" ubuntu@<public-ip>
```

> ⚠️ `UserKnownHostsFile=NUL` обязателен для preemptible VM — host keys
> меняются при каждом рестарте.

### 9.2. Логи контейнеров

```bash
cd /opt/msp/Newbie/deploy/yandex
docker compose logs backend  -f
docker compose logs mongo    -f
docker compose logs stalwart -f
docker compose logs          -f --tail=100   # все сразу
```

### 9.3. Логи Caddy (хост, не Docker)

```bash
journalctl -u caddy -f
tail -f /var/log/caddy/access.log
```

### 9.4. Обновление кода

```powershell
# Перезалить код и пересобрать (без удаления MongoDB)
.\deploy\yandex\deploy.ps1
```

или вручную:

```bash
# На ВМ
cd /opt/msp/Newbie
git pull
cd frontend && yarn build && sudo cp -r build/* /var/www/landing/
cd ../deploy/yandex && docker compose build && docker compose up -d
```

### 9.5. Удалить ВМ (полная очистка)

```powershell
yc compute instance delete --name msp-cloud-vm --folder-id <id>
```

или через UI: https://console.cloud.yandex.ru/

---

## 10. Уроки реального деплоя (май 2026)

> Эти проблемы возникли при реальном деплое и заняли часы на диагностику.
> Добавлены в конфиги как русские комментарии, но дублируем здесь для видимости.

### 10.0.1. Docker 29 + overlayfs driver = cAdvisor не видит контейнеры

**Симптом:** cAdvisor healthy, но `container_last_seen` показывает только `/` (корень).
Grafana dashboard "Docker containers" — пустой.

**Причина:** Docker 29.5 на Ubuntu 22.04 по умолчанию использует `overlayfs`
storage driver (containerd snapshotter). Он НЕ создаёт
`/var/lib/docker/image/overlayfs/layerdb/mounts/` — cAdvisor ищет этот
каталог и не находит → "Failed to create existing container... no such file".

**Фикс:**
1. `/etc/docker/daemon.json` → `{"storage-driver": "overlay2"}`
2. `sudo systemctl restart docker` (образы re-pull, volumes не теряются)
3. cAdvisor обновить до v0.51+ и добавить `docker.sock` mount

**Профилактика:** `cloud-init.yaml` включает `daemon.json` с `overlay2`.

### 10.0.2. Опечатка домена mcp→msp = staging-сертификаты LE

**Симптом:** браузер показывает "CERT_AUTHORITY_INVALID", Caddy получил
сертификат от `STAGING...` вместо настоящего Let's Encrypt.

**Причина:** домен в Caddyfile был `mcp-claude.online` вместо `msp-claude.online`.
DNS A-запись указывала на правильный домен → LE verification NXDOMAIN →
Caddy молча fallback'нулся на staging CA.

**Фикс:** замена домена во всех файлах + очистка ACME кэша:
```bash
sudo rm -rf /var/lib/caddy/.local/share/caddy/acme
sudo systemctl restart caddy
```

**Профилактика:** Caddyfile содержит `acme_ca` global block — явное указание
production LE endpoint предотвращает silent fallback на staging.

### 10.0.3. Preemptible VM = меняется IP и host keys

**Симптом:** SSH "REMOTE HOST IDENTIFICATION HAS CHANGED" после рестарта VM.

**Причина:** preemptible VM при рестарте получает новый ephemeral IP и
новые SSH host keys.

**Фикс:**
- Зарезервировать static IP (+190₽/мес) → IP не меняется
- SSH опции: `-o StrictHostKeyChecking=no -o UserKnownHostsFile=NUL`

### 10.0.4. PowerShell 5.1 + yc stderr = ErrorRecord

**Симптом:** `yc compute instance create ...` сыплет ErrorRecord в PS5.1,
хотя команда успешна.

**Фикс:** все yc-команды через `cmd /c "yc ... 2>&1"` — stderr сливается
в stdout, PS видит чистый текст.

### 10.0.5. SCP через WireGuard = таймауты

**Симптом:** `scp file ubuntu@<IP>:/tmp/` висит или теряет соединение.

**Обходные пути:**
- `Start-Process scp` вместо прямого вызова (PS5.1 stderr конфликт)
- Для маленьких файлов: `echo BASE64 | ssh ... "base64 -d > file"`
- Отключить WireGuard перед SCP, если возможно

### 10.0.6. Postbox :587 STARTTLS не работает — используйте :465 implicit TLS

**Симптом:** Stalwart не может отправить письмо через `postbox.cloud.yandex.net:587 STARTTLS`. Соединение устанавливается, но Postbox отбрасывает его.

**Причина:** Yandex Cloud Postbox на порту 587 с STARTTLS **не принимает релей**.
Единственный рабочий вариант — порт 465 с implicit TLS.

**Фикс:**
1. В Stalwart route: Port=465, Implicit TLS=ВКЛ
2. В docker-compose.yml bootstrap: `STALWART_ROUTES_POSTBOX_OUTBOUND_PORT: "465"`, `STALWART_ROUTES_POSTBOX_OUTBOUND_TLS_IMPLICIT: "true"`
3. В Grafana/Alertmanager/Vaultwarden: `postbox.cloud.yandex.net:465`

**Профилактика:** docker-compose.yml теперь использует :465 по умолчанию.

### 10.0.7. Stalwart v0.16 — нет CLI в Docker-образе

**Симптом:** `docker exec msp-stalwart-1 stalwart-cli ...` → `stalwart-cli: not found`

**Причина:** Docker-образ `stalwartlabs/stalwart:v0.16` не включает CLI.
Все управление — через JMAP API или Admin WebUI.

**Обходные пути:**
- Admin WebUI: http://localhost:8080/admin (SSH tunnel)
- JMAP API: `POST http://127.0.0.1:8080/jmap/` с Basic auth
- Custom methods через `x:` prefix: `x:MtaRoute/get`, `x:MtaRoute/set`

### 10.0.8. Stalwart v0.16 — Principal/set JMAP баг

**Симптом:** JMAP `Principal/set` всегда возвращает `{"type":"notRequest"}`.

**Причина:** Баг в Stalwart v0.16. Создание/изменение аккаунтов (пароли)
через JMAP не работает.

**Обход:** создавать аккаунты и менять пароли только через Admin WebUI.

### 10.0.9. Necoray TUN-режим ломает AmneziaWG

**Симптом:** AmneziaWG handshake не проходит — VPN-туннель не поднимается,
ping к 10.9.0.1 не идёт.

**Причина:** Necoray в TUN-режиме создаёт адаптер `neko-tun`, который
перехватывает UDP-пакеты AWG handshake (UDP/443). AWG не получает ответ
от сервера.

**Фикс:** переключить Necoray в **proxy-режим** (не TUN). В proxy-режиме
Necoray не создаёт TUN-адаптер, AWG работает через свой Wintun-адаптер
`awg0-msp` без конфликтов.

**Профилактика:** не использовать TUN-клиенты на Windows-станции совместно
с AmneziaWG на том же endpoint.

### 10.0.10. Monitoring-стек в отдельной сети — Alertmanager через Stalwart :25

**Симптом:** Grafana не может отправить email через `stalwart:587`, Alertmanager не может через `postbox:465`.

**Причина:** мониторинг-стек развёрнут из отдельного compose-файла
(`/opt/msp/Newbie/deploy/yandex/monitoring/docker-compose.yml`) в сети `msp-monitoring`
(172.20.0.0/24). Stalwart работает в сети `msp_default` — сети не связаны.

**Фикс:**
- Grafana отправляет email **напрямую через Postbox** (`postbox.cloud.yandex.net:465`).
- Alertmanager подключён к **обеим сетям** (`msp-monitoring` + `msp_default`) и отправляет email через **Stalwart :25** (`stalwart:25`, `smtp_require_tls: false`), т.к. AM v0.27 не поддерживает implicit TLS.

### 10.0.11. UFW зависает при множественных вызовах из SSH

**Симптом:** `sudo ufw status` или `sudo ufw delete N` висит по SSH.

**Причина:** предыдущий вызов ufw не завершился (Python3 процесс),
последующие вызовы блокируются на lock-файле. Накопление процессов
усугубляет проблему.

**Фикс:**
1. Убить зависшие процессы: `pkill -9 -f '/usr/sbin/ufw'`
2. Удалять правила напрямую через iptables: `sudo iptables -D ufw-user-input -p tcp --dport N -j ACCEPT`
3. Не использовать `ufw delete` в неинтерактивных SSH-скриптах

### 10.0.12. Alertmanager v0.27 не поддерживает implicit TLS на SMTP

**Симптом:** Alertmanager не может отправить email через `postbox:465` с `smtp_require_tls: true`.

**Причина:** Alertmanager v0.27内置 SMTP client не поддерживает implicit TLS (STARTTLS только). Порт 465 требует implicit TLS → handshake fails.

**Фикс:** Подключить Alertmanager к обеим сетям (`msp-monitoring` + `msp_default`) и отправлять email через Stalwart `:25` без TLS:
```yaml
smtp_smarthost: "stalwart:25"
smtp_require_tls: false
smtp_hello: "msp-claude.online"
```
`smtp_hello` обязателен — Stalwart отклоняет container hostname как EHLO domain.

### 10.0.13. Alertmanager email в spam — нет text/plain части

**Симптом:** Alertmanager email приходит, но Gmail/Outlook кладёт в spam.

**Причина:** Alertmanager по умолчанию отправляет только HTML (`html:` template). Большинство spam-фильтров penalize HTML-only email без text/plain альтернативы.

**Фикс:** Добавить `text:` template в email_configs и anti-spam заголовки:
```yaml
email_configs:
  - html: '{{ template "mspshield.alert.html" . }}'
    text: '{{ template "mspshield.alert.text" . }}'
    headers:
      List-ID: "MSPShield Alerts <alerts.msp-claude.online>"
      X-Mailer: "MSPShield Alertmanager"
      X-Priority: '{{ if eq .Status "firing" }}1{{ else }}3{{ end }}'
```

### 10.0.14. Prometheus status-history панель: "Data does not have a time field"

**Симптом:** Grafana `status-history` панель показывает ошибку "Data does not have a time field".

**Причина:** `status-history` ожидает range data с time-полем. Gauge-метрики с подзапросами типа `max_over_time(...)[1d:1h]` возвращают instant vector без time series.

**Фикс:** Использовать `state-timeline` тип панели вместо `status-history`. `state-timeline` работает с gauge-метриками напрямую: `restic_backup_success{repo="mspshield-prod"}` с `range: true` и `spanNulls: true`.

### 10.0.15. node-exporter textfile collector — метрики restic не видны Prometheus

**Симптом:** `restic_backup_*` метрики не появляются в Prometheus, хотя `.prom` файл существует на хосте.

**Причина:** node-exporter запущен без флага `--collector.textfile.directory` и без volume mount для директории с `.prom` файлами.

**Фикс:**
1. Добавить volume: `/var/lib/node_exporter/textfile_collector:/var/lib/node_exporter/textfile_collector:ro`
2. Добавить command flag: `--collector.textfile.directory=/var/lib/node_exporter/textfile_collector`
3. Обновить backup-скрипт чтобы писал в эту директорию

### 10.0.16. Restic stale lock блокирует следующий бэкап

**Симптом:** `restic forget --prune` или следующий `restic backup` падает с "repository is already locked by PID ... lock was created at ... ago".

**Причина:** Предыдущий запуск restic был прерван (OOM, timeout, manual kill) и не снял lock.

**Фикс:** `sudo bash -c 'source /etc/restic/env.sh && restic unlock'`
**Профилактика:** Добавить `restic unlock` в начало backup-скрипта или использовать `--cleanup-cache`.

---

## 10.M. Мониторинг — что мониторится и как

### Архитектура

```
┌─────────────────────────────────────────────────────────────────┐
│ VM node-01 (158.160.47.130 / 10.9.0.1 via AWG)                  │
│                                                                  │
│  ┌─── msp_default сеть ──────────────────────────────────────┐  │
│  │  mongo:7.0  backend(FastAPI)  stalwart:0.16  vaultwarden  │  │
│  │  caddy(host)  blackbox-exporter                            │  │
│  └────────────────────────────────────────────────────────────┘  │
│                                                                  │
│  ┌─── msp-monitoring сеть (172.20.0.0/24) ───────────────────┐  │
│  │  prometheus:2.51 (172.20.0.10)                             │  │
│  │  alertmanager:0.27 (172.20.0.11 + msp_default)            │  │
│  │  grafana:10.4 (172.20.0.12)                               │  │
│  │  node-exporter:1.7 (172.20.0.13)                           │  │
│  │  cadvisor:0.51 (172.20.0.14)                               │  │
│  │  blackbox-exporter:0.24 (172.20.0.15 + msp_default)        │  │
│  └────────────────────────────────────────────────────────────┘  │
│                                                                  │
│  restic-backup (systemd timer, 02:00 daily)                      │
│  → S3: mspshield-backups-new                                    │
│  → metrics via node-exporter textfile                            │
└─────────────────────────────────────────────────────────────────┘
```

**Alert flow:**
```
Prometheus → Alertmanager → email (Stalwart :25 → Postbox → inbox)
                          → webhook (backend /api/alerts/alertmanager → MAX/Telegram)
```

### Что мониторится

| Категория | Метрики | Алёрты |
|-----------|---------|--------|
| **VM (host)** | CPU, RAM, disk, network via node-exporter | NodeDown P1, HighCPU P2, LowDisk P2, HighMemory P2 |
| **Docker** | container CPU/RAM/restarts via cAdvisor | ContainerDown P1, ContainerRestartLoop P2, ContainerHighMemory P2 |
| **Сайт** | HTTP probes (blackbox) | SiteDown P1, BackendHealthFail P1, SiteSlowResponse P3 |
| **Почта** | IMAP :993, SMTP :465 probes | StalwartImapDown P1, StalwartSmtpDown P1 |
| **Сервисы** | HTTP health probes (internal) | VaultwardenDown P1, GrafanaDown P2, ServiceSlowResponse P3 |
| **SSL** | cert expiry from blackbox | SSLExpiringSoon P2, SSLExpired P1 |
| **Бэкапы** | restic_backup_success/timestamp/size via textfile | BackupFailed P1, BackupMissed24h P1, BackupSizeDropped P2, BackupInProgress P3 |
| **Backend** | up, leads_rejected_total | HighErrorRate5xx P3 |

### Grafana дашборды

| UID | Название | Содержание |
|-----|-----------|-----------|
| `mspshield-overview` | MSPShield Overview | Статусы, counters, dropdown к поддашбордам |
| `msp-vm` | MSPShield VM | CPU, RAM, disk, network (node-exporter) |
| `msp-containers` | MSPShield Containers | CPU/RAM/restarts по контейнерам (cAdvisor) |
| `msp-services` | MSPShield Services | HTTP/SMTP probes, SSL expiry (blackbox) |
| `mspshield-backups` | MSPShield Backups | Статус, размер, возраст, retention, 7-дневная история (restic textfile) |

### Alert routing

| Severity | group_wait | repeat_interval | Каналы |
|----------|------------|-----------------|--------|
| P1 | 10s | 1h | email + webhook |
| P2 | 1m | 4h | email + webhook |
| P3 | 1m | 4h | email + webhook |

P1 ингибирует P2/P3 с тем же alertname+instance.

### Restic бэкап

**Пути:** `/etc`, `/home`, `/root`, `/opt`, `/var/www`, `/var/lib/docker/volumes`, `/var/lib/caddy`

**Retention:** daily 7, weekly 4, monthly 6, yearly 1

**Verify:** каждую неделю (воскресенье, в backup-скрипте)

**Метрики:** `restic_backup_success{host="node-01",repo="mspshield-prod"}`, `restic_backup_timestamp_seconds`, `restic_backup_size_bytes`

**Runbooks:** `deploy/yandex/monitoring/runbooks/R-*.md` — 22 файла, ссылки из алёртов ведут на GitHub

### Ключевые файлы мониторинга

```
deploy/yandex/monitoring/
├── docker-compose.yml          # Все сервисы мониторинга
├── .env                        # GF_ADMIN_PASSWORD, GF_SMTP_*
├── prometheus/
│   ├── prometheus.yml          # Scrape configs
│   └── rules/
│       ├── common.yml          # VM: NodeDown, HighCPU, LowDisk, HighMemory
│       ├── containers.yml      # Docker: ContainerDown, RestartLoop, HighMem
│       ├── site.yml            # HTTP: SiteDown, BackendDown, Slow, 5xx
│       ├── services.yml        # Internal: Vaultwarden, Grafana, IMAP, SMTP, Slow
│       ├── ssl.yml             # SSL: ExpiringSoon, Expired
│       └── backups.yml         # Restic: Failed, Missed24h, SizeDropped, InProgress
├── alertmanager/
│   ├── alertmanager.yml        # Routing P1/P2/P3, SMTP via Stalwart :25
│   └── templates/
│       └── mspshield.tmpl       # HTML + text email template
├── grafana/
│   ├── dashboards/             # 5 JSON dashboards
│   ├── provisioning/           # Datasource + dashboard auto-load
│   ├── grafana.ini             # Custom settings
│   └── theme/                  # MSPShield CSS override
├── runbooks/                   # 22 runbook markdown files
└── restic-exporter/
    ├── run-backup.sh           # Cron wrapper with metrics
    ├── restic-metrics.sh       # Textfile exporter
    └── README.md               # Backup metrics documentation
```

## 10.1. Caddy не получает сертификат

```bash
journalctl -u caddy -f
# Ищите строки про "obtain"
```

**Возможные причины:**
- DNS A-запись не пропагнулась (проверь `dig msp-claude.online`)
- Yandex Cloud не пускает :80/:443 (проверь security-group)
- Превышен лимит Let's Encrypt (5 в неделю на домен) → ждать или https://crt.sh для проверки

### 10.2. Backend не отвечает / 502

```bash
docker compose logs backend | tail -50
curl -v http://localhost:8001/api/health
```

**Возможные причины:**
- MongoDB не поднялся (`docker compose logs mongo`)
- Ошибка в `.env` (например, синтаксис)
- Контейнер OOM-нулся (увеличь RAM ВМ)

### 10.3. Stalwart не принимает почту

```bash
docker compose logs stalwart | tail -100

# С другого сервера (только submission, не MX):
swaks --to sales@msp-claude.online --from postmaster@example.com \
      --server mail.msp-claude.online -p 587 --tls --auth \
      --auth-user sales@msp-claude.online --auth-password '...'
```

**Возможные причины:**
- DNS A-запись `mail.<domain>` не пропагнулась
- Caddy не успел выпустить сертификат (`journalctl -u caddy -f`)
- Stalwart wizard не пройден (зайдите через SSH tunnel в admin UI и завершите setup)
- Внешний MX-провайдер ещё не forwards-ит почту нам (проверьте логи в его UI)
- **НЕ пытайтесь** проверять через `:25` извне — YC блокирует, это ожидаемо

### 10.4. SSH "Permission denied"

Проверь что ключ из аргумента совпадает с `~/.ssh/id_ed25519_yc_new`:
```powershell
ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=NUL -i "$env:USERPROFILE\.ssh\id_ed25519_yc_new" -v ubuntu@<ip>
```

### 10.5. Скрипт упал на этапе `[7/8] setup-on-vm.sh`

Зайдите на ВМ и посмотрите лог:
```bash
ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=NUL -i ~/.ssh/id_ed25519_yc_new ubuntu@<ip>
tail -200 /var/log/msp-deploy.log
```

Запустите setup-on-vm.sh вручную:
```bash
export MSP_DOMAIN=msp-claude.online
bash /opt/msp/Newbie/deploy/yandex/setup-on-vm.sh
```

### 10.6. PowerShell: «Непредвиденная лексема» / «Отсутствует закрывающий знак "}"»

Симптом — при запуске `.\deploy\yandex\deploy.ps1` сыпятся ошибки парсера
вида:

```
deploy.ps1:96  знак:21
+ function Write-Ok   { param([string]$Text) Write-Host "  вњ“ $Text" ...
                       ~
Отсутствует закрывающий знак "}" в блоке операторов или определении типа.
```

`вњ“` / `РџРѕСЃР»Рµ` / `в”Њв”Ђ` в выводе ошибок — это мусор от того, что
PowerShell 5.1 на русской Windows 10 прочитал UTF-8 файл как Windows-1251.

**Причина.** `deploy.ps1` в репозитории сохранён в UTF-8 **с BOM** (`EF BB BF`)
именно для совместимости с PowerShell 5.1. Если файл был обработан
посредником (некоторые сторонние Git-клиенты, текст-эдиторы, антивирусы,
zip-распаковщики), BOM мог быть удалён — и тогда парсер ломается на
первом же Unicode-символе (✓, ─, ┌, кириллица).

**Решение.**

1. Свежий клон через стандартный `git` сохранит BOM:
   ```powershell
   git clone https://github.com/i1yxaluk-del/Newbie C:\msp\Newbie
   ```

2. Проверить BOM:
   ```powershell
   $bytes = [System.IO.File]::ReadAllBytes("deploy\yandex\deploy.ps1")
   "{0:X2} {1:X2} {2:X2}" -f $bytes[0], $bytes[1], $bytes[2]
   # должно быть: EF BB BF
   ```

3. Если BOM пропал — восстановите его:
   ```powershell
   $text = [System.IO.File]::ReadAllText("deploy\yandex\deploy.ps1",
            [System.Text.UTF8Encoding]::new($false))
   [System.IO.File]::WriteAllText("deploy\yandex\deploy.ps1", $text,
            [System.Text.UTF8Encoding]::new($true))   # $true = with BOM
   ```

4. Альтернатива (если ставить BOM нечем) — запускайте под **PowerShell 7+**
   (`pwsh.exe`), он по умолчанию читает скрипты как UTF-8 без BOM:
   ```powershell
   winget install --id Microsoft.PowerShell -e
   pwsh -File .\deploy\yandex\deploy.ps1
   ```

### 10.7. PowerShell: `ArgumentOutOfRangeException` / «Имя параметра: times»

Симптом — парсер прошёл (BOM на месте), но скрипт всё равно падает:

```
.\deploy\yandex\deploy.ps1 : Заданный аргумент находится вне диапазона
допустимых значений.
Имя параметра: times
строка:1 знак:1
+ .\deploy\yandex\deploy.ps1
    + CategoryInfo          : OperationStopped: (:) [deploy.ps1], ArgumentOutOfRangeException
    + FullyQualifiedErrorId : System.ArgumentOutOfRangeException,deploy.ps1
```

**Причина (исправлена в PR #38).** Заголовок скрипта печатает
рамку фиксированной ширины 52 символа через паттерн
`" " * (52 - $Value.Length)`. В PowerShell оператор `*` для строк
выкидывает `ArgumentOutOfRangeException` с именем параметра ровно
`times`, если множитель отрицательный — а это происходит, когда
`$Value` длиннее ширины поля. На типичной Windows-машине `$LogFile =
$env:TEMP\msp-deploy-YYYYMMDD-HHmmss.log` ≈ 60-70 символов (особенно
при длинном имени пользователя), что и триггерит ошибку.

**Что сделано в скрипте.** Введён хелпер `Format-BoxField`, который
безопасно паддит ИЛИ усекает строку до нужной ширины (длинные значения
получают префикс `...` и сохранённый «хвост» — для путей это
сохраняет timestamp в имени файла). Все 6 паттернов в заголовке
заменены на вызов хелпера.

**Если ловите эту ошибку на старой версии `deploy.ps1`:** обновитесь
до PR #38 (`git pull`). Никаких других обходов не нужно — фикс
полностью на стороне скрипта.

**Дополнительные альтернативы запуска (на всякий случай):**

```powershell
# 1. Без интерактивного профиля:
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\deploy\yandex\deploy.ps1

# 2. Под PowerShell 7+:
pwsh -File .\deploy\yandex\deploy.ps1

# 3. Из cmd.exe:
cmd /c "powershell.exe -ExecutionPolicy Bypass -File .\deploy\yandex\deploy.ps1"
```

---

## 11. Установка PTR-записи (обратная DNS)

Без PTR `mail.msp-claude.online ↔ <IP>` Gmail и Outlook будут отмечать
вашу почту как spam с высокой вероятностью.

```powershell
# Узнайте network interface id
yc compute instance get --name msp-cloud-vm --format json | `
  jq -r '.network_interfaces[0].index'

# Установите PTR
yc compute instance update-network-interface `
  --instance-name msp-cloud-vm `
  --network-interface-index 0 `
  --new-public-ip-ptr "mail.msp-claude.online"
```

Проверка:
```bash
dig +short -x <public-ip>
# Должен вернуть: mail.msp-claude.online.
```

---

## 12. Безопасность

### Что закрыто

- MongoDB — только в Docker-сети, наружу не светит
- Backend — `127.0.0.1:8001`, доступ только через Caddy
- Stalwart admin — `127.0.0.1:8080`, доступ только через SSH tunnel
- SSH ключ ed25519, без пароля → НЕ КОММИТИТЬ
- UFW + Yandex Cloud Security Group двойной layer

### Что НЕ закоммичено

См. <ref_file file="/home/ubuntu/repos/Newbie/deploy/yandex/.gitignore" />

- `.deploy-state.json` — содержит folder-id, VM-id, IP
- `.env` (в этом каталоге)
- Файлы паролей на ВМ
- SSH-ключи

### Регулярные задачи

- Раз в месяц — `apt update && apt upgrade -y` на ВМ
- Раз в 3 месяца — `docker compose pull && docker compose up -d` для обновления mongo/stalwart
- Раз в неделю — `tail -100 /var/log/caddy/access.log` на странные запросы
- DKIM ротация — через WebUI Stalwart, раз в 6 месяцев
- Postbox API key (smarthost auth: `POSTBOX_API_KEY_ID` + `POSTBOX_API_KEY_SECRET`) — ротация раз в 6 месяцев или при компрометации
- См. секцию 13 «Почта — чеклист доделать» для пошагового плана

---

## 13. Почта — чеклист доделать после деплоя

Ниже — конкретные шаги, которые нужно выполнить в Stalwart Admin UI
для завершения настройки почты. API-ключ Postbox уже создан и лежит
в `.env`, но Stalwart v0.16 не имеет CLI в Docker-образе — всё через WebUI
или JMAP API.

> **Важно**: env-переменные Postbox в docker-compose.yml подхватываются
> **ТОЛЬКО при первом запуске** Stalwart (пустой volume stalwart-etc).
> После первого запуска конфиг живёт в RocksDB volume — изменения через
> Admin UI или JMAP API (`POST http://127.0.0.1:8080/jmap/`).

### Подключение к Admin UI

```powershell
# SSH-туннель (через VPN или внешний IP)
ssh -L 8080:localhost:8080 -i "$env:USERPROFILE\.ssh\id_ed25519_yc_new" ubuntu@10.9.0.1
# → http://localhost:8080/admin
# Логин: admin / Пароль: из ~/msp-deploy-secrets.txt на ВМ (shred после копирования!)
```

### Шаги

| # | Шаг | Где в Admin UI | Статус |
|---|-----|----------------|--------|
| 1 | **Указать auth в маршруте `postbox-outbound`** — Port=465, Implicit TLS=ВКЛ, Auth user=API key ID, Auth password=API key secret | Settings → SMTP → Routes → postbox-outbound → Edit | ✅ Сделано (JMAP) |
| 2 | **Убедиться что outbound strategy = postbox-outbound** | MTA → Outbound → Strategy → default route | ✅ Сделано |
| 3 | **Добавить TLS-сертификат для mail.** | Settings → TLS → Certificates → Add Manual → cert/key пути к Caddy-сертификатам | ✅ Сделано (auto) |
| 4 | **Создать аккаунты** admin@, sales@, alert@ | Settings → Accounts → Add User → тип Individual | ✅ Сделано |
| 5 | **Сгенерировать DKIM-ключ** | Settings → Domains → msp-claude.online → Generate DKIM | ✅ Сделано |
| 6 | **Прописать DNS TXT-записи** (SPF + DKIM + DMARC) у регистратора | Вне VM — Namecheap/Cloudflare DNS | ✅ Сделано |
| 7 | **Настроить Grafana SMTP** — Postbox direct, :465 implicit TLS | `deploy/yandex/monitoring/.env` → `GF_SMTP_*` | ✅ Сделано |
| 8 | **Настроить Alertmanager SMTP** — Stalwart :25 (AM v0.27 не поддерживает implicit TLS) | `deploy/yandex/monitoring/alertmanager/alertmanager.yml` | ✅ Сделано |
| 9 | **Настроить Vaultwarden SMTP** — Postbox direct, :465 force_tls | `deploy/yandex/.env` → `SMTP_*` | ✅ Сделано |

### DNS TXT-записи (после DKIM из шага 5)

```
TXT  msp-claude.online                     v=spf1 a ip4:158.160.47.130 include:_spf.yandex.net -all
TXT  default._domainkey.msp-claude.online   v=DKIM1; k=rsa; p=<из Stalwart Admin шаг 5>
TXT  _dmarc.msp-claude.online              v=DMARC1; p=quarantine; rua=mailto:admin@msp-claude.online
```

`include:_spf.yandex.net` обязателен — Postbox отправляет от нашего имени.

### Postbox — привязка домена

В YC Console → **Postbox → Домены** → добавить `msp-claude.online` →
подтвердить TXT-записью. После подтверждения Postbox начнёт принимать
входящие на `mx.yandex.net` и форвардить на наш `:587`.

### Интеграции (все настроены через Postbox direct)

| Сервис | SMTP сервер | Порт | TLS | Логин |
|--------|-------------|------|-----|-------|
| Grafana | postbox.cloud.yandex.net | 465 | implicit | API key ID |
| Alertmanager | stalwart (внутр.) | 25 | нет | alert@... |
| Vaultwarden | postbox.cloud.yandex.net | 465 | force_tls | API key ID |
| Backend (FastAPI) | stalwart (внутр.) | 25 | нет | alert@... |

### Тест отправки

```bash
# На VM — через Stalwart SMTPS (нет stalwart-cli в Docker v0.16)
python3 -c "
import smtplib, ssl
from email.mime.text import MIMEText
msg = MIMEText('Test from Stalwart via Postbox')
msg['Subject'] = 'Stalwart Postbox test'
msg['From'] = 'alert@msp-claude.online'
msg['To'] = 'admin@msp-claude.online'
ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE
s = smtplib.SMTP_SSL('127.0.0.1', 465, timeout=15, context=ctx)
s.login('alert@msp-claude.online', '<alert-password>')
s.send_message(msg)
s.quit()
print('SENT OK')
"
```

---

## 14. Дополнительно

- **Stalwart docs:** https://stalw.art/docs/
- **Caddy docs:** https://caddyserver.com/docs/
- **Yandex Cloud CLI:** https://yandex.cloud/ru/docs/cli/
- **Let's Encrypt rate limits:** https://letsencrypt.org/docs/rate-limits/

---

## 15. Бэкапы — что бэкапится

| Путь | Что внутри | Критичность |
|------|-----------|-------------|
| `/etc` | Конфиги ОС, systemd units, UFW rules, restic env | Высокая |
| `/home` | Домашние директории пользователей | Средняя |
| `/root` | Root home | Средняя |
| `/opt` | `/opt/msp/Newbie/deploy/yandex/monitoring/`, `/opt/msp/Newbie/deploy/`, `/opt/restic-scripts/` | Высокая |
| `/var/www` | Лендинг `landing/` (React build) | Средняя |
| `/var/lib/docker/volumes` | Все Docker volumes: mongo-data, stalwart-etc, stalwart-data, vaultwarden-data, grafana-data, prometheus-data, alertmanager-data | Критическая |
| `/var/lib/caddy` | SSL-сертификаты Let's Encrypt (152K) — без них Caddy не стартанёт | Критическая |

**Restic конфиг:** `/etc/restic/env.sh`, скрипт: `/opt/restic-scripts/backup.sh`

**Запуск:** systemd timer `restic-backup.timer`, ежедневно 02:00 + random 5min

**Retention:** daily 7, weekly 4, monthly 6, yearly 1

**S3 bucket:** `mspshield-backups-new` (Yandex Object Storage)

**Verify:** каждую неделю (воскресенье, встроено в backup-скрипт)

**Метрики:** `restic_backup_success/timestamp_seconds/size_bytes` через node-exporter textfile collector → Prometheus → Grafana dashboard `mspshield-backups`

---

> Поддержка: `admin@msp-claude.online` (после деплоя) ·
> репозиторий: https://github.com/i1yxaluk-del/Newbie
