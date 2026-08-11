> ⚠️ **УСТАРЕЛО (deprecated since v4.3).** Этот документ описывает Stalwart
> Mail в submit-only режиме как relay через smarthost. **В проде Stalwart
> больше не используется** — outbound mail идёт напрямую через **Yandex
> Cloud Postbox (MSA :465, implicit TLS)**, см. CHANGELOG v4.3 и v5.4.
> Файл сохранён для истории и на случай отката. Актуальный мейл-стек:
> [`deploy/yandex/README.md`](README.md) → раздел "Postbox".

---

# Stalwart Mail Server — Yandex Cloud Postbox relay/submit-only режим

## TL;DR

Yandex Cloud **блокирует TCP/25** на публичных IP VPC (анти-спам, на уровне
платформы) — поэтому:

- классический MX-приём на наш IP **не работает**;
- исходящие коннекты к чужим `:25` тоже режутся;
- получить адрес с открытым `:25` сейчас **технически невозможно** (YC прямо
отказывает);
- решение: исходящие через **Yandex Cloud Postbox** (`postbox.cloud.yandex.net:465`
implicit TLS, авторизация по API-ключу YC), входящие — forward к нам на :587.

Stalwart в `deploy/yandex/docker-compose.yml` настроен под эту реальность:

| Порт  | Назначение                                       | Открыт наружу |
|-------|--------------------------------------------------|---------------|
| ~~25~~  | MX inbound (классическое получение почты)      | **НЕТ** (YC блокирует) |
| 465   | SMTPS submission, implicit TLS                   | да            |
| 587   | SMTP submission, STARTTLS                        | да            |
| 143   | IMAP STARTTLS (legacy клиенты)                   | да            |
| 993   | IMAPS (TLS) — основное чтение                    | да            |
| 4190  | ManageSieve (фильтры на сервере)                 | да            |
| 8080  | Admin WebUI                                      | только 127.0.0.1 (SSH tunnel) |

---

## Архитектура почтового потока

```
                                                     Internet
                                                        │
           (входящие письма от чужих серверов на :25)     │
                                                        ▼
              ┌──────────────────────────────────────────────────┐
              │  Yandex Cloud Postbox                             │
              │  MX = mx.yandex.net, принимает почту для домена  │
              │  Forward → наш Stalwart по :587 STARTTLS         │
              └──────────────┬───────────────────────────────────┘
                             │
                             ▼
 ┌──────────────────────────────────────────────────────────────────┐
 │  Yandex Cloud VM (наш Stalwart) — submit-only режим              │
 │                                                                  │
 │   :465  ◄── Outlook/Thunderbird/скрипты шлют ИСХОДЯЩЕЕ (auth)    │
 │   :587  ◄── Legacy клиенты / inbound forwarding                  │
 │   :993  ◄── читают ящики (IMAPS)                                 │
 │                                                                  │
 │   Stalwart кладёт принятые письма в локальные ящики,              │
 │   фильтрует Sieve, отдаёт IMAP.                                  │
 │                                                                  │
 │   ИСХОДЯЩИЕ ── НЕ напрямую на :25 (YC блокирует) ──────────────► │
 │   Stalwart → postbox.cloud.yandex.net:465 ──► Yandex Postbox      │
 │                                                                  │
 └──────────────────────────────────────────────────────────────────┘
```

---

## Шаг 1 · Yandex Cloud Postbox — создание API-ключа

1. В Yandex Cloud Console → **IAM → Сервисные аккаунты** → создать аккаунт
 `postbox-sender` с ролью `postbox.sender`.
2. Создать **API-ключ** (IAM → API-ключи → Создать) со scope `yc.postbox.send`.
3. Записать:
 - **ID ключа** (строка вида `aje...`) → `authUsername` в Stalwart;
 - **Секретный ключ** (длинная строка) → `authSecret` в Stalwart.
4. Привязать домен в Postbox: YC Console → **Postbox → Домены** → добавить
 домен → подтвердить TXT-записью у регистратора.

> **Важно**: API-ключ ОБЯЗАТЕЛЬНО должен иметь scope `yc.postbox.send`. Ключи
> без этого scope проходят AUTH, но не могут отправлять — ошибка проявляется
> только при фактической отправке письма.

---

## Шаг 2 · Outbound smarthost через Yandex Cloud Postbox

Поскольку Yandex Cloud режет `OUTBOUND :25`, Stalwart **не должен**
напрямую коннектиться к MX-серверам Gmail / Outlook / Mail.ru. Весь
исходящий трафик заворачиваем на `postbox.cloud.yandex.net:465` (implicit TLS).

> **Критический урок из деплоя**: порт **465 + implicit TLS** — единственный
> рабочий вариант. Postbox на порту 587 STARTTLS **отбрасывает соединения**.
> Мы потратили часы на диагностику почему Stalwart не может отправить почту
> через `:587 STARTTLS` — переключение на `:465 implicit TLS` решило проблему
> мгновенно.

### Вариант A · Настройка через Stalwart admin UI

1. SSH-tunnel в админку:
 ```powershell
 ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=NUL -L 8080:localhost:8080 -i "$HOME\.ssh\id_ed25519_yc_new" ubuntu@<vm-ip>
 ```
 Открыть в браузере: <http://localhost:8080/admin>

2. Логин: `admin` / пароль из `~/msp-deploy-secrets.txt`.

3. **Settings → SMTP → Routes → Add route**:
 ```
 Name:                       postbox-outbound
 Mode:                       Relay
 Address:                    postbox.cloud.yandex.net
 Port:                       465
 TLS:                        Implicit TLS = ВКЛ (465 — implicit TLS, не STARTTLS)
 Allow Invalid Certs:        ВЫКЛ
 Auth user:                  <ID API-ключа (aje...)>
 Auth password:              <секретный ключ>
 ```

 > **Важно**: порт 465 использует **implicit TLS** (шифрование с первого байта).
 > Порт 587 использует STARTTLS (plain → upgrade), но Postbox на :587
 > **не работает** для нашего сценария.

4. **MTA → Outbound → Strategy** → выбрать `postbox-outbound` как маршрут
 по умолчанию.

5. Тест отправки:
 ```bash
 # На самой VM — через Python (stalwart-cli НЕТ в Docker-образе v0.16)
 python3 -c "
 import smtplib
 from email.mime.text import MIMEText
 msg = MIMEText('Test from Stalwart via Postbox')
 msg['Subject'] = 'Stalwart Postbox test'
 msg['From'] = 'alert@<domain>'
 msg['To'] = 'admin@<domain>'
 import ssl
 ctx = ssl.create_default_context()
 ctx.check_hostname = False
 ctx.verify_mode = ssl.CERT_NONE
 s = smtplib.SMTP_SSL('127.0.0.1', 465, timeout=15, context=ctx)
 s.login('alert@<domain>', '<alert-password>')
 s.send_message(msg)
 s.quit()
 print('SENT OK')
 "
 ```

### Вариант B · Настройка через JMAP API

> Stalwart v0.16 **не имеет CLI** в Docker-образе (`stalwart-cli` отсутствует).
> Все управление — через JMAP API или Admin WebUI.

```bash
# Получить текущие маршруты
curl -s -u admin:<password> http://127.0.0.1:8080/jmap/ \
-H 'Content-Type: application/json' \
-d '{"using":["urn:ietf:params:jmap:core","urn:stalwart:jmap"],"methodCalls":[["x:MtaRoute/get",{},"0"]]}'

# Обновить маршрут (id = isa3jzsgaaqa — подставить реальный из /get)
curl -s -u admin:<password> http://127.0.0.1:8080/jmap/ \
-H 'Content-Type: application/json' \
-d '{"using":["urn:ietf:params:jmap:core","urn:stalwart:jmap"],"methodCalls":[["x:MtaRoute/set",{"update":{"isa3jzsgaaqa":{"address":"postbox.cloud.yandex.net","port":465,"implicitTls":true,"authUsername":"<API_KEY_ID>","authSecret":{"@type":"Value","secret":"<API_KEY_SECRET>"}}}},"0"]]}'
```

> **Баг Stalwart v0.16**: `Principal/set` JMAP всегда возвращает `notRequest`.
> Создание/изменение аккаунтов (пароли) — только через Admin WebUI.

### Вариант C · Настройка через docker-compose env (только bootstrap)

Env-переменные в `docker-compose.yml` подхватываются **только при первом
запуске** с пустым volume `stalwart-etc`. После первого запуска конфиг
хранится в RocksDB внутри volume, и env-переменные игнорируются.

Для fresh-деплоя (правильные значения):
```yaml
STALWART_ROUTES_POSTBOX_OUTBOUND_PORT: "465"
STALWART_ROUTES_POSTBOX_OUTBOUND_TLS_IMPLICIT: "true"
```

Для изменения на уже запущенном Stalwart — используйте Вариант A или B.

---

## Шаг 3 · DNS-записи

```
A     mail.<domain>       <yc-vm-public-ip>
TXT   <domain>            v=spf1 a ip4:<yc-vm-public-ip> include:_spf.yandex.net -all
TXT   default._domainkey  v=DKIM1; k=rsa; p=<сгенерированный Stalwart открытый ключ>
TXT   _dmarc.<domain>     v=DMARC1; p=quarantine; rua=mailto:admin@<domain>
```

MX-запись управляется Yandex Cloud Postbox (подтверждение домена через
TXT в шаге 1). После подтверждения Postbox автоматически направляет MX
на свои серверы.

DKIM-ключ генерируется в Stalwart admin UI:
`Settings → Domains → <domain> → Generate DKIM key`.
Скопируйте TXT и положите в DNS у регистратора.

> SPF **обязан** включать `include:_spf.yandex.net` — Postbox отправляет
> от нашего имени через свои IP. Без этого SPF-провал у получателей.

---

## Шаг 4 · Проверка

```powershell
# С Windows-станции:

# 1. Порт 465 принимает TLS
openssl s_client -connect mail.<domain>:465 -servername mail.<domain> -brief

# 2. Порт 587 поднимает STARTTLS
openssl s_client -connect mail.<domain>:587 -starttls smtp -servername mail.<domain> -brief

# 3. IMAPS работает
openssl s_client -connect mail.<domain>:993 -servername mail.<domain> -brief
```

Логи Stalwart:
```bash
docker compose -f /opt/msp/Newbie/deploy/yandex/docker-compose.yml logs -f stalwart
```

---

## Шаг 5 · Интеграция с MSP-сервисами

### Grafana / Alertmanager — SMTP напрямую через Postbox

> **Архитектурное решение**: мониторинг-стек (`msp-monitoring` compose) работает
> в отдельной Docker-сети `msp-monitoring` (172.20.0.0/24), **не подключённой**
> к `msp_default` где крутится Stalwart. Поэтому Grafana и Alertmanager
> отправляют email **напрямую через Postbox** (`postbox.cloud.yandex.net:465`),
> а не через внутренний Stalwart.

`deploy/yandex/monitoring/.env`:
```
GF_SMTP_ENABLED=true
GF_SMTP_HOST=postbox.cloud.yandex.net:465
GF_SMTP_USER=<postbox-api-key-id>
GF_SMTP_PASSWORD=<postbox-api-key-secret>
GF_SMTP_FROM_ADDRESS=alert@<domain>
```

`deploy/yandex/monitoring/alertmanager/alertmanager.yml`:
```yaml
global:
smtp_smarthost: "postbox.cloud.yandex.net:465"
smtp_from: "alert@<domain>"
smtp_auth_username: "<postbox-api-key-id>"
smtp_auth_password: "<postbox-api-key-secret>"
smtp_require_tls: true

receivers:
- name: email-alert
  email_configs:
    - to: "alert@<domain>"
      send_resolved: true
```

### Vaultwarden — SMTP через Postbox

Vaultwarden тоже подключается напрямую к Postbox:
```yaml
SMTP_HOST: postbox.cloud.yandex.net
SMTP_PORT: 465
SMTP_SECURITY: force_tls
SMTP_FROM: alert@<domain>
SMTP_USERNAME: <postbox-api-key-id>
SMTP_PASSWORD: <postbox-api-key-secret>
```

### Backend (FastAPI) — SMTP через внутренний Stalwart

Backend работает в сети `msp_default` и может отправлять через Stalwart:
```ini
SMTP_HOST=stalwart
SMTP_PORT=587
SMTP_USER=alert@<domain>
SMTP_PASSWORD=<alert-password>
SMTP_FROM=alert@<domain>
```

---

## Чем НЕЛЬЗЯ заменить смарт-хост

- ~~Прямой `OUTBOUND :25` к Gmail/Outlook~~ — Yandex Cloud режет на уровне VPC.
- ~~Stalwart как самодостаточный MX через `:25`~~ — публичный `:25` нам не выдадут.
- ~~Postbox `:587 STARTTLS`~~ — **не работает**, соединения отбрасываются. Используйте `:465 implicit TLS`.

Если бизнес-сценарий требует **именно** автономный MX на собственном IP без
внешнего провайдера — нужна другая площадка (Hetzner, OVH, собственная
железка), где `:25` не блокируется.
