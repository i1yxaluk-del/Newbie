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
                │  Внешний MX-провайдер                            │
                │  (Yandex 360 для бизнеса │ Mail.ru для бизнеса │ │
                │   Mailgun routes │ Cloudflare Email Routing)      │
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
                │  Yandex 360 для бизнеса │ Mailgun │ Brevo    │
                │  Подключение на их :465 (SMTPS) или :587     │
                │  с auth от лица alert@<domain>.              │
                └──────────────────────────────────────────────┘
```

---

## Шаг 1 · Внешний MX-провайдер (приём почты)

### Вариант A · Yandex 360 для бизнеса (рекомендуется в РФ)

1. Регистрация: <https://360.yandex.ru/business>.
2. Подтвердить владение доменом (TXT-запись).
3. У регистратора домена создать:
   ```
   MX  @  10 mx.yandex.net.
   TXT @  v=spf1 redirect=_spf.yandex.net
   ```
4. Создать первый ящик: `alert@<your-domain>` (для исходящих алертов).
5. В Yandex 360 → ящик → **«Пароли приложений»** → создать пароль для
   `smtp.yandex.ru:465`. Этот пароль пойдёт в Stalwart smarthost.

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

### Настройка через Stalwart admin UI

1. SSH-tunnel в админку:
   ```powershell
   ssh -L 8080:localhost:8080 -i "$HOME\.ssh\id_ed25519_yc" ubuntu@<vm-ip>
   ```
   Открыть в браузере: <http://localhost:8080/admin>

2. Логин: `admin` / пароль из `~/msp-deploy-secrets.txt`.

3. **Settings → SMTP → Outbound**:
   ```
   Default route               relay
   ```

4. **Settings → SMTP → Routes → Add route**:
   ```
   Name:                       relay
   Mode:                       Relay
   Address:                    smtp.yandex.ru   (или smtp.eu.mailgun.org)
   Port:                       465              (или 587 для STARTTLS)
   TLS:                        Implicit         (или STARTTLS — для :587)
   Auth user:                  alert@<your-domain>
   Auth password:              <Yandex 360 app-password или Mailgun key>
   ```

5. Тест отправки:
   ```bash
   # На самой VM
   docker compose exec stalwart stalwart-cli queue message send \
       --from alert@<domain> --to <ваш-личный-email> \
       --subject "Stalwart smarthost test" --body "ok"
   ```

### Smarthost через переменные окружения

Альтернативно (если не любите WebUI), задайте при первом старте
контейнера:

```yaml
# deploy/yandex/docker-compose.yml — services.stalwart.environment:
environment:
  STALWART_RECOVERY_ADMIN: "admin:${STALWART_ADMIN_PASSWORD:-changeme}"
  # Smarthost для всех исходящих
  STALWART_QUEUE_DEFAULT_ROUTE: relay
  STALWART_ROUTES_RELAY_TYPE: relay
  STALWART_ROUTES_RELAY_ADDRESS: smtp.yandex.ru
  STALWART_ROUTES_RELAY_PORT: "465"
  STALWART_ROUTES_RELAY_TLS_IMPLICIT: "true"
  STALWART_ROUTES_RELAY_AUTH_USERNAME: alert@${MSP_DOMAIN}
  STALWART_ROUTES_RELAY_AUTH_SECRET: ${YANDEX360_APP_PASSWORD}
```

Эти значения подхватятся при первом запуске; в дальнейшем правьте через
WebUI (Stalwart хранит конфиг в `/etc/stalwart`, который маунтится в
volume `stalwart-etc`).

---

## Шаг 3 · DNS-записи для submit-only домена

```
A     mail.<domain>       <yc-vm-public-ip>
TXT   <domain>            v=spf1 a ip4:<yc-vm-public-ip> include:_spf.yandex.net -all
TXT   default._domainkey  v=DKIM1; k=rsa; p=<сгенерированный Stalwart открытый ключ>
TXT   _dmarc.<domain>     v=DMARC1; p=quarantine; rua=mailto:admin@<domain>
```

`MX` зависит от выбранного варианта (см. шаг 1):

- Вариант A (Yandex 360):  `MX @ 10 mx.yandex.net.`
- Вариант B (Mailgun):     `MX @ 10 mxa.mailgun.org.` + `MX @ 10 mxb.mailgun.org.`
- Вариант C (Cloudflare):  CF добавляет автоматически.

DKIM-ключ генерируется в Stalwart admin UI:
`Settings → Domains → <domain> → Generate DKIM key`.
Скопируйте TXT и положите в DNS у регистратора.

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
ssh -i "$HOME\.ssh\id_ed25519_yc" ubuntu@<vm-ip> `
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
