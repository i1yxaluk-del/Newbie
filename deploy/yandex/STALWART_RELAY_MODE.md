# Stalwart Mail Server — Yandex Cloud relay/submit-only режим

## TL;DR

Yandex Cloud **блокирует TCP/25** на публичных IP VPC (анти-спам, на уровне
платформы) — поэтому:

- классический MX-приём на наш IP **не работает**;
- исходящие коннекты к чужим `:25` тоже режутся;
- получить адрес с открытым `:25` сейчас **технически невозможно** (YC прямо
  отказывает);
- альтернатива, рекомендованная YC support — перевести почтовый сервер на
  **465 (SMTPS implicit TLS)** и **587 (Submission STARTTLS)**.

**Outbound идёт через Yandex Cloud Postbox** (managed SMTP-relay в YC) —
это канонический вариант для нашего деплоя. См. «Шаг 2 · Outbound
smarthost». Postbox не принимает входящую почту; для входящих (если
нужны) — внешний MX-провайдер (См. «Шаг 1»).

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
            (входящие письма от чужих серверов на :25)    │
                                                          ▼
                ┌──────────────────────────────────────────────────┐
                │  Внешний MX-провайдер (только если нужен inbound)   │
                │  (Yandex 360 │ Mail.ru для бизнеса │           │
                │   Mailgun routes │ Cloudflare Email Routing)     │
                │  Yandex Cloud Postbox = только outbound,        │
                │  MX-записи для него НЕ выдаются.            │
                └──────────────┬───────────────────────────────────┘
                               │  (forward по :587 STARTTLS или
                               │   API webhook → SMTP relay)
                               ▼
   ┌──────────────────────────────────────────────────────────────────┐
   │  Yandex Cloud VM (наш Stalwart) — submit-only режим              │
   │                                                                  │
   │   :465  ◄── Outlook/Thunderbird/скрипты шлют ИСХОДЯЩЕЕ (auth)    │
   │   :587  ◄── Grafana/Wazuh/Alertmanager шлют АЛЕРТЫ (auth)        │
   │   :993  ◄── читают ящики (IMAPS)                                 │
   │                                                                  │
   │   Stalwart кладёт принятые письма в локальные ящики /var/lib/    │
   │   stalwart, фильтрует Sieve, отдаёт IMAP.                        │
   │                                                                  │
   │   ИСХОДЯЩИЕ к интернету ── НЕ напрямую на :25 (YC блокирует) ──► │
   │   Stalwart → smarthost на :465 или :587 ──► внешний relay        │
   │                                                                  │
   └────────────────────────────┬─────────────────────────────────────┘
                                │
                                ▼
                ┌──────────────────────────────────────────────┐
                │  Smarthost (outbound relay)                  │
                │  → Yandex Cloud Postbox  (основной, managed)  │
                │    postbox.cloud.yandex.net:587 STARTTLS     │
                │    auth: API key (ID + secret)               │
                │  → или Mailgun / Brevo как fallback           │
                │    (при outbound из других регионов)            │
                └──────────────────────────────────────────────┘
```

---

## Шаг 1 · Inbound: внешний MX-провайдер (приём почты)

> **Важно:** Yandex Cloud Postbox — это **только outbound**. Он не принимает
> входящую почту и не выдаёт MX-записи для вашего домена. Если вам
> нужны «normal» ящики `*@msp-claude.online` для приёма писем от клиентов —
> выберите один из вариантов ниже. Если вам нужен **только** отправлять из `alert@`
> и `admin@` (transactional, alerts, DMARC reports) — инбаунд можно не настраивать,
> хватит Postbox из «Шага 2». Биллинг Postbox — только за исходящий трафик,
> фиксированной платы нет.
>
> **Отдельно про DNS:** в нашем случае NS домена живёт на Namecheap
> (не переводили на Yandex Cloud DNS). Означает что никакие inbound-варианты
> из этого раздела не подключены автоматически; MX/SPF/DKIM записи нужно
> прописывать в панели Namecheap (Domain List → Advanced DNS).

### Вариант A · Yandex 360 для бизнеса (полные ящики в РФ)

> **Не путать с Yandex Cloud Postbox** — это разные сервисы. Yandex 360 —
> ящики/диски/календарь для бизнеса (платный по пользователям).
> Postbox — бэкенд для transactional outbound (oplata за трафик).

1. Регистрация: <https://360.yandex.ru/business>.
2. Подтвердить владение доменом (TXT-запись).
3. В Namecheap (или текущего регистратора) создать:
   ```
   MX  @  10 mx.yandex.net.
   TXT @  v=spf1 redirect=_spf.yandex.net
   ```
4. Создать ящики (`admin@`, `sales@`, etc.). Ящик `alert@` в Yandex 360 не нужен —
   transactional отправка идёт через Postbox (Шаг 2).
5. **Рабочий outbound всё равно через Postbox** — Yandex 360 здесь нужен
   **только для приёма**. Пароль приложений в 360 создавать не надо.

### Вариант B · Mailgun (международный, $0 до 5000 писем/мес)

1. Регистрация: <https://www.mailgun.com/>.
2. Add Domain → `<your-domain>` → выдаст MX/TXT записи.
3. В Mailgun → **Receiving → Routes** → создать route:
   - Filter: `match_recipient(".*@<your-domain>")`
   - Action: `forward("smtp://<your-public-ip>:587")` + auth-header
4. Для исходящих создать SMTP-credential → пойдут в Stalwart smarthost.

### Вариант C · Cloudflare Email Routing (бесплатно, требует DNS на CF)

1. Перенести NS домена в Cloudflare (если ещё нет).
2. Cloudflare Dashboard → Email → **Email Routing** → Enable.
3. CF добавит MX/TXT-записи автоматически.
4. Добавить правила forward → внешний адрес ИЛИ через Workers → POST на
   наш `https://<domain>/api/mail/inbound` (вам нужно реализовать в backend).

> Cloudflare Email Routing **не отдаёт SMTP** обратно, только webhook —
> то есть Stalwart не получит входящие в виде SMTP-сессии. Подходит, если
> локальные IMAP-ящики не нужны и хватит redirect на личный email.

---

## Шаг 2 · Outbound smarthost (отправка наружу)

Поскольку Yandex Cloud режет `OUTBOUND :25`, Stalwart **не должен**
напрямую коннектиться к MX-серверам Gmail / Outlook / Mail.ru. Вместо этого
весь исходящий трафик заворачиваем на smarthost через `:465` или `:587`.

### Вариант A · Yandex Cloud Postbox — **канонический выбор для нашего деплоя**

[Postbox](https://yandex.cloud/services/postbox) — managed SMTP-relay в
том же облаке, где и наша VM. Платим только за исходящий трафик,
ящики создавать не нужно, anti-spam репутация IP — общая с другими
YC-клиентами и сопровождается Yandex.

**SMTP-параметры Postbox:**

| Параметр | Значение |
|---|---|
| Address | `postbox.cloud.yandex.net` |
| Port | `587` (STARTTLS) — рекомендуется для нашего сценария |
| Port (alt) | `465` (Implicit TLS / SMTPS) |
| Protocol | SMTP |
| Implicit TLS | **`false`** (для `:587`). Для `:465` — `true`. |
| Allow Invalid Certs | `false` (сертификат Yandex Cloud валидный) |
| Auth Username | **API key ID** (строка вида `aje...`) |
| Auth Secret | **API key secret** (длинная строка) |

> **Главное грабли**: для `:587` `Implicit TLS = false`. Если включить
> implicit TLS на 587, Stalwart пытается шифровать с первого байта —
> Postbox ждёт plain-SMTP greeting и STARTTLS-переход, хэндшейк
> сломается.

**Подготовка в консоли Yandex Cloud (однократно):**

1. Консоль YC → **Postbox** → «Создать конфигурацию отправки» для домена `msp-claude.online`.
2. Подтвердить владение доменом (TXT-запись) — добавить в Namecheap Advanced DNS.
3. Нажать «Получить DKIM» → скопировать TXT и повесить в DNS (`<selector>._domainkey`).
4. **Создать service account** «postbox-sender» с ролью `postbox.sender`.
5. **API key** для этого SA: «Создать» → Scope = `yc.postbox.send` → сохранить
   `id (aje...)` и `secret` в Vaultwarden (коллекция `internal/infra`).
6. Секрет в backend/.env / Ansible vault: `POSTBOX_API_KEY_ID`, `POSTBOX_API_KEY_SECRET`.

**Настройка Stalwart через stalwart-cli (канонический способ):**

```bash
# 1. SSH на нашу VM
ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=NUL \
    -i "$HOME\.ssh\id_ed25519_yc" ubuntu@<vm-ip>

cd /opt/msp/Newbie/deploy/yandex

# 2. Загружаем секреты в текущую сессию (не в bash history!)
#    Способ A — из backend/.env:
set -a; source /opt/msp/Newbie/backend/.env; set +a
#    Способ B — копи-пейст из Vaultwarden с leading-space, чтобы не попало в history:
#     export POSTBOX_API_KEY_ID=aje...
#     export POSTBOX_API_KEY_SECRET=...

# 3. Создаём MTA-route в Stalwart
docker compose exec stalwart stalwart-cli mta route create postbox-outbound --config '{
  "@type": "Relay",
  "address": "postbox.cloud.yandex.net",
  "port": 587,
  "protocol": "smtp",
  "implicitTls": false,
  "authUsername": "'"$POSTBOX_API_KEY_ID"'",
  "authSecret": { "@type": "Value", "data": "'"$POSTBOX_API_KEY_SECRET"'" }
}'

# 4. Назначаем route стратегией по умолчанию
docker compose exec stalwart stalwart-cli mta strategy update default --config '{
  "@type": "Strategy",
  "route": "postbox-outbound"
}'

# 5. Проверяем, что route применён
docker compose exec stalwart stalwart-cli mta strategy list
```

**Альтернативно — настройка через Stalwart admin WebUI:**

1. SSH-tunnel:
   ```powershell
   ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=NUL -L 8080:localhost:8080 -i "$HOME\.ssh\id_ed25519_yc" ubuntu@<vm-ip>
   ```
   Открыть <http://localhost:8080/admin>. Логин: `admin` / пароль из `~/msp-deploy-secrets.txt`.

2. **Settings → MTA → Routes → Add route**:
   ```
   Name:                postbox-outbound
   Mode:                Relay
   Address:             postbox.cloud.yandex.net
   Port:                587
   Implicit TLS:        OFF        ← критично для :587
   Allow Invalid Certs: OFF
   Auth user:           <API key ID, aje...>
   Auth password:       <API key secret>
   ```

3. **Settings → MTA → Outbound → Strategy** → «default» → Route = `postbox-outbound`.

> Подвох: иногда WebUI скрывает поля auth, пока не сохранить route без них
> и не открыть редактирование. Проще использовать CLI выше.

**Тест отправки:**

```bash
docker compose exec stalwart stalwart-cli queue message send \
    --from alert@msp-claude.online --to <ваш-личный-email> \
    --subject "Postbox smoke test" --body "ok"

# Смотреть queue:
docker compose exec stalwart stalwart-cli queue list
# (должно быть пусто в течение 5-10 сек)
```

### Вариант B · Mailgun (фолбэк, если Postbox недоступен в вашем регионе)

- Address: `smtp.eu.mailgun.org` или `smtp.mailgun.org`
- Port: `465` (implicit TLS) или `587` (STARTTLS)
- Auth user: `postmaster@mg.<your-domain>` (или sub-domain Mailgun)
- Auth pass: SMTP credential из Mailgun панели

### Вариант C · Yandex 360 как smarthost (не рекомендуется)

Можно, но осмысленно только если Postbox не подходит и вы уже вложились в ящики
Yandex 360. Проблема: 360 рассчитан на интерактивную почту, не на transactional
bulk, и пароль приложений жёстко рате-лимитируется на ящик (~150 писем/день на ящик).

- Address: `smtp.yandex.ru`
- Port: `465` (всегда implicit TLS у Яндекса)
- Auth user: полный адрес ящика (напр. `alert@msp-claude.online`, если будет создан)
- Auth pass: **пароль приложения** из Yandex 360 (не основной пароль ящика!)

### Smarthost через переменные окружения (bootstrap, для Postbox)

Альтернативно (если не любите отдельный stalwart-cli вызов), можно задать при
первом старте контейнера:

```yaml
# deploy/yandex/docker-compose.yml — services.stalwart.environment:
environment:
  STALWART_RECOVERY_ADMIN: "admin:${STALWART_ADMIN_PASSWORD:-changeme}"
  # Smarthost → Yandex Cloud Postbox
  STALWART_QUEUE_DEFAULT_ROUTE: postbox-outbound
  STALWART_ROUTES_POSTBOX_OUTBOUND_TYPE: relay
  STALWART_ROUTES_POSTBOX_OUTBOUND_ADDRESS: postbox.cloud.yandex.net
  STALWART_ROUTES_POSTBOX_OUTBOUND_PORT: "587"
  STALWART_ROUTES_POSTBOX_OUTBOUND_TLS_IMPLICIT: "false"    # STARTTLS для :587
  STALWART_ROUTES_POSTBOX_OUTBOUND_AUTH_USERNAME: ${POSTBOX_API_KEY_ID}
  STALWART_ROUTES_POSTBOX_OUTBOUND_AUTH_SECRET: ${POSTBOX_API_KEY_SECRET}
```

Эти значения подхватятся только при **первом запуске** Stalwart (bootstrap
config). Далее правьте через `stalwart-cli` или WebUI — конфиг живёт в
volume `stalwart-etc` (`/etc/stalwart`).

---

## Шаг 3 · DNS-записи

> **Текущее состояние:** NS домена `msp-claude.online` остаётся на Namecheap.
> Все DNS-записи ниже прописываются в Namecheap дашборде: Domain List →
> Manage → Advanced DNS. **Не переводите NS на Yandex Cloud DNS** — Postbox
> не требует этого, а риск downtime лендинга от смены NS высокий.

### Обязательные записи (для Postbox outbound)

```
A     mail.msp-claude.online      <yc-vm-public-ip>     ; для IMAPS/Stalwart WebUI
TXT   msp-claude.online           v=spf1 include:_spf.yandexcloud.net ~all
TXT   <selector>._domainkey       v=DKIM1; k=rsa; p=<из Postbox консоли>
TXT   _dmarc.msp-claude.online    v=DMARC1; p=quarantine; rua=mailto:admin@msp-claude.online
```

> Селектор DKIM выдаёт консоль Postbox при создании конфигурации домена.
> **Проверьте** фактический SPF include в доках YC — указано `_spf.yandexcloud.net`,
> но Postbox может выдавать свой персональный include при верификации домена.

### Опциональные записи (если нужен и inbound — см. Шаг 1)

`MX` зависит от выбранного inbound-варианта (Postbox MX не выдаёт):

- Вариант A (Yandex 360):  `MX @ 10 mx.yandex.net.`
- Вариант B (Mailgun):     `MX @ 10 mxa.mailgun.org.` + `MX @ 10 mxb.mailgun.org.`
- Вариант C (Cloudflare):  CF добавляет автоматически.

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

# 4. Отправка изнутри VM
ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=NUL -i "$HOME\.ssh\id_ed25519_yc" ubuntu@<vm-ip> `
  "docker compose -f /opt/msp/Newbie/deploy/yandex/docker-compose.yml exec -T stalwart stalwart-cli queue list"
```

Логи Stalwart:
```bash
docker compose -f /opt/msp/Newbie/deploy/yandex/docker-compose.yml logs -f stalwart
```

---

## Шаг 5 · Интеграция с MSP-сервисами

### Grafana / Alertmanager / Wazuh — все шлют на ВНУТРЕННИЙ `587`

Поскольку Grafana, Alertmanager, Wazuh, backend крутятся **на той же
VM**, они подключаются к Stalwart на внутреннем `:587` (имя контейнера
`stalwart`, без TLS-валидации внешнего сертификата — внутренняя сеть
docker-compose):

`deploy/grafana/grafana.ini` (или env-блок Grafana):
```ini
[smtp]
enabled       = true
host          = stalwart:587
user          = alert@<domain>
password      = <из msp-deploy-secrets.txt>
from_address  = alert@<domain>
from_name     = MSP Grafana
startTLS_policy = MandatoryStartTLS
```

`deploy/alertmanager/alertmanager.yml`:
```yaml
receivers:
  - name: msp-email
    email_configs:
      - to: alert@<domain>
        from: alert@<domain>
        smarthost: stalwart:587
        auth_username: alert@<domain>
        auth_password: '<из msp-deploy-secrets.txt>'
        require_tls: true
```

Wazuh (`/var/ossec/etc/ossec.conf`):
```xml
<global>
  <email_notification>yes</email_notification>
  <smtp_server>stalwart</smtp_server>
  <email_from>alert@<domain></email_from>
  <email_to>admin@<domain></email_to>
</global>
```

Stalwart, в свою очередь, через smarthost-routes отправит письма наружу.

---

## Чем НЕЛЬЗЯ заменить смарт-хост

- ~~Прямой `OUTBOUND :25` к Gmail/Outlook~~ — Yandex Cloud режет на уровне VPC.
- ~~Stalwart как самодостаточный MX через `:25`~~ — публичный `:25` нам не выдадут.
- ~~`POP3 fetchmail` с чужого Gmail в нашу VM по `:110/:995`~~ — это легально,
  но не решает задачу публичного домена `<your-domain>`.

Если бизнес-сценарий требует **именно** автономный MX на собственном IP без
внешнего провайдера — нужна другая площадка (Hetzner, OVH, собственная
железка), где `:25` не блокируется.

---

## Откат / hotfix

Если в будущем YC одобрит разблокировку `:25` (тикет в support):

1. Вернуть `"25:25"` в `deploy/yandex/docker-compose.yml` (раздел `ports`).
2. Вернуть `ufw allow 25/tcp` в `deploy/yandex/cloud-init.yaml`.
3. Добавить SG-правило `port=25,protocol=tcp` в `deploy/yandex/deploy.ps1`.
4. В Stalwart admin → Settings → SMTP → Outbound → удалить relay-route
   (или выставить `Default route = direct`).
5. Поднять MX-запись домена обратно на `mail.<domain>` (см. историю
   `git log -- deploy/yandex/README.md`).

Все три файла под git — изменения видно в одном PR.
