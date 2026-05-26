# Stalwart Mail Server — Yandex Cloud Postbox relay/submit-only режим

## TL;DR

Yandex Cloud **блокирует TCP/25** на публичных IP VPC (анти-спам, на уровне
платформы) — поэтому:

- классический MX-приём на наш IP **не работает**;
- исходящие коннекты к чужим `:25` тоже режутся;
- получить адрес с открытым `:25` сейчас **технически невозможно** (YC прямо
  отказывает);
- решение: исходящие через **Yandex Cloud Postbox** (`postbox.cloud.yandex.net:587`
  STARTTLS, авторизация по API-ключу YC), входящие — forward к нам на :587.

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
   │   :587  ◄── Grafana/Alertmanager шлют АЛЕРТЫ (auth)              │
   │   :993  ◄── читают ящики (IMAPS)                                 │
   │                                                                  │
   │   Stalwart кладёт принятые письма в локальные ящики,              │
   │   фильтрует Sieve, отдаёт IMAP.                                  │
   │                                                                  │
   │   ИСХОДЯЩИЕ ── НЕ напрямую на :25 (YC блокирует) ──────────────► │
   │   Stalwart → postbox.cloud.yandex.net:587 ──► Yandex Postbox      │
   │                                                                  │
   └──────────────────────────────────────────────────────────────────┘
```

---

## Шаг 1 · Yandex Cloud Postbox — создание API-ключа

1. В Yandex Cloud Console → **IAM → Сервисные аккаунты** → создать аккаунт
   `postbox-sender` с ролью `postbox.sender`.
2. Создать **API-ключ** (IAM → API-ключи → Создать).
3. Записать:
   - **ID ключа** (строка вида `aje...`) → `authUsername` в Stalwart;
   - **Секретный ключ** (длинная строка) → `authSecret` в Stalwart.
4. Привязать домен в Postbox: YC Console → **Postbox → Домены** → добавить
   домен → подтвердить TXT-записью у регистратора.

---

## Шаг 2 · Outbound smarthost через Yandex Cloud Postbox

Поскольку Yandex Cloud режет `OUTBOUND :25`, Stalwart **не должен**
напрямую коннектиться к MX-серверам Gmail / Outlook / Mail.ru. Весь
исходящий трафик заворачиваем на `postbox.cloud.yandex.net:587` (STARTTLS).

### Вариант A · Настройка через Stalwart admin UI

1. SSH-tunnel в админку:
   ```powershell
   ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=NUL -L 8080:localhost:8080 -i "$HOME\.ssh\id_ed25519_yc" ubuntu@<vm-ip>
   ```
   Открыть в браузере: <http://localhost:8080/admin>

2. Логин: `admin` / пароль из `~/msp-deploy-secrets.txt`.

3. **Settings → SMTP → Routes → Add route**:
   ```
   Name:                       postbox-outbound
   Mode:                       Relay
   Address:                    postbox.cloud.yandex.net
   Port:                       587
   TLS:                        Implicit TLS = ВЫКЛ (587 — STARTTLS, не implicit)
   Allow Invalid Certs:        ВЫКЛ
   Auth user:                  <ID API-ключа (aje...)>
   Auth password:              <секретный ключ>
   ```

   > **Важно**: порт 587 использует STARTTLS, а не Implicit TLS.
   > Если включить Implicit TLS — Stalwart попытается установить шифрование
   > с первого байта, что для :587 неверно, и соединение упадёт.

4. **MTA → Outbound → Strategy** → выбрать `postbox-outbound` как маршрут
   по умолчанию.

5. Тест отправки:
   ```bash
   # На самой VM
   docker compose exec stalwart stalwart-cli queue message send \
       --from alert@<domain> --to <ваш-личный-email> \
       --subject "Stalwart Postbox test" --body "ok"
   ```

### Вариант B · Настройка через stalwart-cli (если UI скрывает поля auth)

```bash
# Создать маршрут
stalwart-cli mta route create postbox-outbound --config '{
  "@type": "Relay",
  "address": "postbox.cloud.yandex.net",
  "port": 587,
  "protocol": "smtp",
  "implicitTls": false,
  "authUsername": "ЗДЕСЬ_ID_КЛЮЧА_AJE",
  "authSecret": { "@type": "Value", "data": "ЗДЕСЬ_СЕКРЕТНЫЙ_КЛЮЧ" }
}'

# Назначить маршрутом по умолчанию
stalwart-cli mta strategy update default --config '{
  "@type": "Strategy",
  "route": "postbox-outbound"
}'
```

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

# 4. Очередь отправки на VM
ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=NUL -i "$HOME\.ssh\id_ed25519_yc" ubuntu@<vm-ip> `
  "docker compose -f /opt/msp/Newbie/deploy/yandex/docker-compose.yml exec -T stalwart stalwart-cli queue list"
```

Логи Stalwart:
```bash
docker compose -f /opt/msp/Newbie/deploy/yandex/docker-compose.yml logs -f stalwart
```

---

## Шаг 5 · Интеграция с MSP-сервисами

### Grafana / Alertmanager — шлют на ВНУТРЕННИЙ `587`

Поскольку Grafana и Alertmanager крутятся **на той же VM**, они
подключаются к Stalwart на внутреннем `:587` (имя контейнера `stalwart`,
без TLS-валидации внешнего сертификата — внутренняя сеть docker-compose):

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

Stalwart, в свою очередь, через Postbox-маршрут отправит письма наружу
через `postbox.cloud.yandex.net:587` (STARTTLS, API-ключ).

---

## Чем НЕЛЬЗЯ заменить смарт-хост

- ~~Прямой `OUTBOUND :25` к Gmail/Outlook~~ — Yandex Cloud режет на уровне VPC.
- ~~Stalwart как самодостаточный MX через `:25`~~ — публичный `:25` нам не выдадут.

Если бизнес-сценарий требует **именно** автономный MX на собственном IP без
внешнего провайдера — нужна другая площадка (Hetzner, OVH, собственная
железка), где `:25` не блокируется.
