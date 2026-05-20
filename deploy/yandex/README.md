# Деплой МСП Облако в Yandex Cloud

Автоматическое развёртывание production-стека:

- **Лендинг** (React static) + **Backend** (FastAPI + MongoDB)
- **Caddy** — авто-HTTPS через Let's Encrypt
- **Stalwart Mail Server** — admin@, sales@, alert@ ящики

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
#     A    mcp-claude.online      → <IP>
#     A    www.mcp-claude.online  → <IP>
#     A    mail.mcp-claude.online → <IP>

# 4. Через 10-30 минут (после DNS propagation) откройте:
#     https://mcp-claude.online
```

---

## 1. Что разворачивается

```
                              Internet
                                 │
            ┌────────────────────┼───────────────────────┐
            │                    │                       │
        :443 HTTPS         :25,587,465,...           :22 SSH
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
- 1 × VPC сеть (`msp-net`)
- 1 × Subnet (`msp-subnet`, 10.10.0.0/24)
- 1 × Security Group (`msp-sg`) — открыты 22/80/443 + почтовые
- Public IP (один на ВМ)

**Стоимость:**
- Прерываемая (preemptible): **~400-500 ₽/мес**
- Гарантированная: **~1100-1300 ₽/мес**
- Public IP: ~125 ₽/мес (отдельно)

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
- Домен: `mcp-claude.online`
- Зона: `ru-central1-a`
- ВМ: 2 vCPU (50% guarantee) / 4 GB / 50 GB SSD, прерываемая
- Mail: Stalwart с 3 ящиками (admin@, sales@, alert@)

### 3.2. С параметрами

```powershell
.\deploy\yandex\deploy.ps1 `
    -Domain "mcp-claude.online" `
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
| `A` | `mcp-claude.online` | `<public IP из вывода скрипта>` |
| `A` | `www.mcp-claude.online` | `<public IP>` |
| `A` | `mail.mcp-claude.online` | `<public IP>` |
| `MX` | `mcp-claude.online` | `10 mail.mcp-claude.online` |
| `TXT` | `mcp-claude.online` | `v=spf1 a mx ip4:<public IP> -all` |
| `TXT` | `_dmarc.mcp-claude.online` | `v=DMARC1; p=quarantine; rua=mailto:admin@mcp-claude.online` |
| `TXT` | `default._domainkey.mcp-claude.online` | *(см. 5.2)* |

### 5.2. Получите DKIM-ключ из Stalwart

После того как DNS пропагнулся (хотя бы A-записи на лендинг + mail):

```powershell
# Запустите SSH-туннель к Stalwart admin (порт 8080)
$IP = "<ваш IP>"
$SshKey = "$env:USERPROFILE\.ssh\id_ed25519_yc"
ssh -L 8080:localhost:8080 -i $SshKey ubuntu@$IP
```

Затем откройте в браузере http://localhost:8080/admin

- Логин: `admin`
- Пароль: из файла на ВМ (`cat ~/msp-deploy-secrets.txt`)

В Settings → Domains → mcp-claude.online → **Generate DKIM**.
Stalwart выдаст TXT-запись вида:
```
default._domainkey.mcp-claude.online   TXT   "v=DKIM1; k=rsa; p=MIGfMA0GCSq..."
```
Скопируйте её к регистратору домена.

### 5.3. Создайте mailbox-аккаунты в Stalwart

В том же admin WebUI:

1. **Settings → Accounts → Add User**
   - `admin@mcp-claude.online` — пароль из `msp-deploy-secrets.txt`
   - `sales@mcp-claude.online`
   - `alert@mcp-claude.online`

2. **Settings → Domains → mcp-claude.online**
   - Убедитесь что **status = active**
   - **MX records → Verify** должен показать ✓

3. **Settings → TLS → Certificates → Add Manual Certificate**
   - Путь к cert: `/etc/stalwart-certs/certificates/acme-v02.api.letsencrypt.org-directory/mail.mcp-claude.online/mail.mcp-claude.online.crt`
   - Путь к key: `/etc/stalwart-certs/certificates/acme-v02.api.letsencrypt.org-directory/mail.mcp-claude.online/mail.mcp-claude.online.key`

   (Каталог появится после того как Caddy получит сертификат — это происходит автоматически в первые 1-2 минуты после propagation A-записи `mail.<domain>`.)

### 5.4. Получите пароли с ВМ

```powershell
$IP = "<ваш IP>"
$SshKey = "$env:USERPROFILE\.ssh\id_ed25519_yc"
ssh -i $SshKey ubuntu@$IP "cat ~/msp-deploy-secrets.txt"
```

Скопируйте этот файл в надёжное место (1Password / Vaultwarden / KeePass)
и **удалите с ВМ**:

```powershell
ssh -i $SshKey ubuntu@$IP "shred -u ~/msp-deploy-secrets.txt"
```

### 5.5. Тестовый письма (через MX, локально)

```bash
# На ВМ
echo "Test from local" | mail -s "Hello sales" sales@mcp-claude.online
docker compose -f /opt/msp/Newbie/deploy/yandex/docker-compose.yml \
  logs stalwart | tail -20
```

### 5.6. Тест извне

С любого Gmail-ящика отправьте письмо на `sales@mcp-claude.online`.
Письмо должно появиться в IMAP-папке INBOX. Откройте Thunderbird:

- **Сервер:** `mail.mcp-claude.online`
- **Тип:** IMAP, порт 993, SSL/TLS
- **Логин:** `sales@mcp-claude.online`
- **Пароль:** из `msp-deploy-secrets.txt`

---

## 6. ⚠️ Yandex Cloud блокирует исходящий :25

По умолчанию **новые аккаунты YC не могут отправлять SMTP на :25 в интернет.**
Это анти-спам. Последствия:

| Что | Работает? |
|-----|-----------|
| Приём почты (входящий :25) | ✅ да |
| Локальная доставка между ящиками `*@mcp-claude.online` | ✅ да |
| Письма Grafana/Wazuh → `alert@mcp-claude.online` | ✅ да (через :587 локально) |
| Отправка `sales@mcp-claude.online` → `client@gmail.com` | ❌ нет (пока :25 заблокирован) |

### Решение А: попросить YC разблокировать (рекомендованный путь)

1. Зайти в [https://console.cloud.yandex.ru/](https://console.cloud.yandex.ru/)
2. Поддержка → Создать тикет
3. Тема: «Разблокировать исходящий SMTP (порт 25) для VM».
4. Текст:
   ```
   Прошу разблокировать исходящий :25 на ВМ msp-cloud-vm в каталоге msp-cloud
   для отправки транзакционных писем нашим клиентам с домена
   mcp-claude.online (B2B IT-услуги, юр. лицо ИП [имя]).

   SPF / DKIM / DMARC настроены. Antifrood-меры: rate limiting в Stalwart
   на 100 писем/час/account, лог всех отправлений.

   Согласен с правилами анти-спама YC.
   ```
5. Обычно одобряют за 1-3 дня.

### Решение Б: использовать smarthost-релей

Если YC не разблокировал или нужно срочно — настройте Stalwart на отправку через внешний SMTP:

**Mailgun** (5000 писем/мес бесплатно):
```
Stalwart admin UI → Settings → SMTP → Outbound → Smarthost:
  Host:     smtp.eu.mailgun.org
  Port:     587
  Username: postmaster@<your-mailgun-domain>
  Password: <api-key>
```

**Brevo** (300 писем/день бесплатно):
```
  Host:     smtp-relay.brevo.com
  Port:     587
  Username: <ваш-логин-brevo>
  Password: <smtp-key-brevo>
```

---

## 7. Репутация нового IP

Новый IP в Яндекс/Selectel/Hetzner — это **mail reputation = 0**.
Первые 2-4 недели крупные провайдеры (Gmail, Mail.ru, Outlook) будут
часть писем класть в спам или вообще rejecting'ить.

**Как ускорить разогрев:**

1. **Не шлите 1000 писем сразу.** Начните с 10-20 в день, через неделю — 50, через 2 — 100.
2. **Попросите получателей** вытащить из спама + добавить в адресную книгу.
3. **Постучитесь в Postmaster Tools:**
   - Google: https://postmaster.google.com — добавьте `mcp-claude.online`
   - Microsoft SNDS: https://sendersupport.olc.protection.outlook.com/snds/
   - Mail.ru Postmaster: https://postmaster.mail.ru/
4. **Регулярно проверяйте blacklist'ы**: https://mxtoolbox.com/blacklists.aspx

---

## 8. Подключение к интеграциям

### 8.1. Grafana → SMTP-алерты на alert@

В `/etc/grafana/grafana.ini`:
```ini
[smtp]
enabled = true
host = mail.mcp-claude.online:587
user = alert@mcp-claude.online
password = <из msp-deploy-secrets.txt>
from_address = alert@mcp-claude.online
from_name = MSP Grafana
startTLS_policy = MandatoryStartTLS
```

### 8.2. Wazuh → SMTP

В `/var/ossec/etc/ossec.conf`:
```xml
<global>
  <email_notification>yes</email_notification>
  <smtp_server>mail.mcp-claude.online</smtp_server>
  <email_from>alert@mcp-claude.online</email_from>
  <email_to>admin@mcp-claude.online</email_to>
</global>
```

### 8.3. Alertmanager → Stalwart (если кому-то нравится email вместо MAX)

В уже существующем `deploy/alertmanager/alertmanager.yml` добавьте receiver:
```yaml
receivers:
  - name: 'msp-email'
    email_configs:
      - to: 'alert@mcp-claude.online'
        from: 'alert@mcp-claude.online'
        smarthost: 'mail.mcp-claude.online:587'
        auth_username: 'alert@mcp-claude.online'
        auth_password: '<password>'
        require_tls: true
```

---

## 9. Управление развёрнутой системой

### 9.1. SSH на ВМ

```powershell
ssh -i "$env:USERPROFILE\.ssh\id_ed25519_yc" ubuntu@<public-ip>
```

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

## 10. Troubleshooting

### 10.1. Caddy не получает сертификат

```bash
journalctl -u caddy -f
# Ищите строки про "obtain"
```

**Возможные причины:**
- DNS A-запись не пропагнулась (проверь `dig mcp-claude.online`)
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
# С другого сервера:
swaks --to test@mcp-claude.online --from postmaster@example.com --server mail.mcp-claude.online -p 25
```

**Возможные причины:**
- DNS MX-запись не пропагнулась
- PTR-запись не установлена (см. §11)
- Stalwart wizard не пройден (зайдите через SSH tunnel в admin UI и завершите setup)

### 10.4. SSH "Permission denied"

Проверь что ключ из аргумента совпадает с `~/.ssh/id_ed25519_yc`:
```powershell
ssh -i "$env:USERPROFILE\.ssh\id_ed25519_yc" -v ubuntu@<ip>
```

### 10.5. Скрипт упал на этапе `[7/8] setup-on-vm.sh`

Зайдите на ВМ и посмотрите лог:
```bash
ssh -i ~/.ssh/id_ed25519_yc ubuntu@<ip>
tail -200 /var/log/msp-deploy.log
```

Запустите setup-on-vm.sh вручную:
```bash
export MSP_DOMAIN=mcp-claude.online
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

**Причина.** Это известный баг **PSReadLine 2.x** на Windows 10 PS 5.1
(см. PSReadLine [#468](https://github.com/PowerShell/PSReadLine/issues/468),
[#2189](https://github.com/PowerShell/PSReadLine/issues/2189)): если скрипт
меняет `[Console]::InputEncoding` или зовёт `chcp 65001` внутри
интерактивной сессии PowerShell, PSReadLine теряет состояние буфера колонок
и при ближайшей перерисовке prompt'а бросает `ArgumentOutOfRangeException`
с параметром `times` (это `times`-параметр в `Console.Write(char, int times)`).

**Что сделано в скрипте.** Начиная с PR #37 `deploy.ps1`:
- НЕ трогает `[Console]::InputEncoding`;
- НЕ зовёт `chcp 65001`;
- сохраняет прежнее значение `[Console]::OutputEncoding` и восстанавливает
  его через `try / finally` при любом выходе из скрипта (успех, ошибка,
  Ctrl+C).

**Если ошибка уже была хоть раз — состояние PSReadLine в текущем окне уже
испорчено.** Закройте окно PowerShell и откройте новое:

```powershell
exit            # или просто закройте окно
# новое окно:
cd C:\msp\Newbie
.\deploy\yandex\deploy.ps1
```

**Альтернативы, которые гарантированно работают:**

```powershell
# 1. Без интерактивного профиля (PSReadLine не загружается):
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\deploy\yandex\deploy.ps1

# 2. Под PowerShell 7+ (PSReadLine там стабильнее):
pwsh -File .\deploy\yandex\deploy.ps1

# 3. Из cmd.exe (не PowerShell — PSReadLine не задействован):
cmd /c "powershell.exe -ExecutionPolicy Bypass -File .\deploy\yandex\deploy.ps1"
```

---

## 11. Установка PTR-записи (обратная DNS)

Без PTR `mail.mcp-claude.online ↔ <IP>` Gmail и Outlook будут отмечать
вашу почту как spam с высокой вероятностью.

```powershell
# Узнайте network interface id
yc compute instance get --name msp-cloud-vm --format json | `
  jq -r '.network_interfaces[0].index'

# Установите PTR
yc compute instance update-network-interface `
  --instance-name msp-cloud-vm `
  --network-interface-index 0 `
  --new-public-ip-ptr "mail.mcp-claude.online"
```

Проверка:
```bash
dig +short -x <public-ip>
# Должен вернуть: mail.mcp-claude.online.
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

---

## 13. Дополнительно

- **Stalwart docs:** https://stalw.art/docs/
- **Caddy docs:** https://caddyserver.com/docs/
- **Yandex Cloud CLI:** https://yandex.cloud/ru/docs/cli/
- **Let's Encrypt rate limits:** https://letsencrypt.org/docs/rate-limits/

---

> Поддержка: `admin@mcp-claude.online` (после деплоя) ·
> репозиторий: https://github.com/i1yxaluk-del/Newbie
