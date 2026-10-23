# Почта: Postbox, Stalwart, SMTP и DNS

SMTP передаёт письмо. Postbox выполняет внешнюю отправку. Stalwart нужен в mail-профиле как локальный почтовый сервис и хранит конфигурацию и данные в отдельных томах. Пустой `stalwart-data` после переноса запускает режим первичной настройки и не означает успешное восстановление.

SPF перечисляет разрешённые источники отправки. DKIM подписывает письмо; для Postbox публикуется CNAME из консоли. DMARC задаёт политику для получателя. Эти записи повышают доверие, но не обещают попадание во «Входящие».

Ошибка 535 относится к авторизации SMTP. `identity not verified` относится к отправителю или DNS. Исправление начинается с полного ответа сервера и состояния очереди, а не со случайной смены пароля.

## Как работать с материалом

Сначала прочитайте объяснение главы. Затем откройте перечисленные файлы в рабочем репозитории и сопоставьте текст с текущим кодом. Команды изменения выполняйте на учебной среде. Разделы ниже включены полностью, поэтому глава одновременно служит учебником и справочником.

## Материал проекта: `deploy/yandex/STALWART_RELAY_MODE.md`

<!-- SOURCE deploy/yandex/STALWART_RELAY_MODE.md 8f47fc92ca979e29 -->

> **Статус: условный production-компонент.** Backend, Alertmanager, Grafana и
> Vaultwarden отправляют напрямую через Postbox `:465` implicit TLS. Stalwart
> запускается только профилем `mail`, если нужны локальные ящики/IMAP. После
> restore его route credentials остаются в RocksDB: `.env` их не обновляет.

---

## Stalwart Mail Server — Yandex Cloud Postbox relay/submit-only режим

### TL;DR

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

### Архитектура почтового потока

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

### Шаг 1 · Yandex Cloud Postbox — создание API-ключа

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

### Шаг 2 · Outbound smarthost через Yandex Cloud Postbox

Поскольку Yandex Cloud режет `OUTBOUND :25`, Stalwart **не должен**
напрямую коннектиться к MX-серверам Gmail / Outlook / Mail.ru. Весь
исходящий трафик заворачиваем на `postbox.cloud.yandex.net:465` (implicit TLS).

> **Критический урок из деплоя**: порт **465 + implicit TLS** — единственный
> рабочий вариант. Postbox на порту 587 STARTTLS **отбрасывает соединения**.
> Мы потратили часы на диагностику почему Stalwart не может отправить почту
> через `:587 STARTTLS` — переключение на `:465 implicit TLS` решило проблему
> мгновенно.

#### Вариант A · Настройка через Stalwart admin UI

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

#### Вариант B · Настройка через JMAP API

> Stalwart v0.16 **не имеет CLI** в Docker-образе (`stalwart-cli` отсутствует).
> Все управление — через JMAP API или Admin WebUI.

```bash
## Получить текущие маршруты
curl -s -u admin:<password> http://127.0.0.1:8080/jmap/ \
-H 'Content-Type: application/json' \
-d '{"using":["urn:ietf:params:jmap:core","urn:stalwart:jmap"],"methodCalls":[["x:MtaRoute/get",{},"0"]]}'

## Обновить маршрут (id = isa3jzsgaaqa — подставить реальный из /get)
curl -s -u admin:<password> http://127.0.0.1:8080/jmap/ \
-H 'Content-Type: application/json' \
-d '{"using":["urn:ietf:params:jmap:core","urn:stalwart:jmap"],"methodCalls":[["x:MtaRoute/set",{"update":{"isa3jzsgaaqa":{"address":"postbox.cloud.yandex.net","port":465,"implicitTls":true,"authUsername":"<API_KEY_ID>","authSecret":{"@type":"Value","secret":"<API_KEY_SECRET>"}}}},"0"]]}'
```

> **Проверено 28.09.2026** (перенос в новый YC-аккаунт): управляющая учётка — `admin` (без домена; пароль — `STALWART_ADMIN_PASSWORD` в `deploy/yandex/.env`); логин `admin@<домен>` на `x:*-методах` получает `forbidden`. После `x:MtaRoute/set` **обязателен `docker restart msp-stalwart-1`** — маршрут применяется только после рестарта. Застрявшие письма и их ошибки видны в `x:QueuedMessage/get` (напр. `535 Authentication failed`).

> **Баг Stalwart v0.16**: `Principal/set` JMAP всегда возвращает `notRequest`.
> Создание/изменение аккаунтов (пароли) — только через Admin WebUI.

#### Вариант C · Настройка через docker-compose env (только bootstrap)

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

### Шаг 3 · DNS-записи

```
A     mail.<domain>       <yc-vm-public-ip>
TXT   <domain>            v=spf1 a ip4:<yc-vm-public-ip> include:_spf.yandex.net -all
CNAME <selector>._domainkey → <selector>.dkim.pstbx.ru   (в проде DKIM-подпись делает Postbox; собственный ключ Stalwart не используется)
TXT   _dmarc.<domain>     v=DMARC1; p=quarantine; rua=mailto:admin@<domain>
```

MX-запись управляется Yandex Cloud Postbox (подтверждение домена через
TXT в шаге 1). После подтверждения Postbox автоматически направляет MX
на свои серверы.

В production DKIM подписывает **Postbox**. Публикуйте CNAME из его консоли:
`<selector>._domainkey → <selector>.dkim.pstbx.ru`. Собственный DKIM TXT
Stalwart для этого контура не создаётся.

> SPF **обязан** включать `include:_spf.yandex.net` — Postbox отправляет
> от нашего имени через свои IP. Без этого SPF-провал у получателей.

---

### Шаг 4 · Проверка

```powershell
## С Windows-станции:

## 1. Порт 465 принимает TLS
openssl s_client -connect mail.<domain>:465 -servername mail.<domain> -brief

## 2. Порт 587 поднимает STARTTLS
openssl s_client -connect mail.<domain>:587 -starttls smtp -servername mail.<domain> -brief

## 3. IMAPS работает
openssl s_client -connect mail.<domain>:993 -servername mail.<domain> -brief
```

Логи Stalwart:
```bash
docker compose -f /opt/msp/Newbie/deploy/yandex/docker-compose.yml logs -f stalwart
```

---

### Шаг 5 · Интеграция с MSP-сервисами

#### Grafana / Alertmanager — SMTP напрямую через Postbox

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

#### Vaultwarden — SMTP через Postbox

Vaultwarden тоже подключается напрямую к Postbox:
```yaml
SMTP_HOST: postbox.cloud.yandex.net
SMTP_PORT: 465
SMTP_SECURITY: force_tls
SMTP_FROM: alert@<domain>
SMTP_USERNAME: <postbox-api-key-id>
SMTP_PASSWORD: <postbox-api-key-secret>
```

#### Backend (FastAPI) — SMTP через внутренний Stalwart

Backend работает в сети `msp_default` и может отправлять через Stalwart:
```ini
SMTP_HOST=stalwart
SMTP_PORT=587
SMTP_USER=alert@<domain>
SMTP_PASSWORD=<alert-password>
SMTP_FROM=alert@<domain>
```

---

### Чем НЕЛЬЗЯ заменить смарт-хост

- ~~Прямой `OUTBOUND :25` к Gmail/Outlook~~ — Yandex Cloud режет на уровне VPC.
- ~~Stalwart как самодостаточный MX через `:25`~~ — публичный `:25` нам не выдадут.
- ~~Postbox `:587 STARTTLS`~~ — **не работает**, соединения отбрасываются. Используйте `:465 implicit TLS`.

Если бизнес-сценарий требует **именно** автономный MX на собственном IP без
внешнего провайдера — нужна другая площадка (Hetzner, OVH, собственная
железка), где `:25` не блокируется.


## Материал проекта: `technical/0_Common/SERVICES/mail_dns.md`

<!-- SOURCE technical/0_Common/SERVICES/mail_dns.md b945245797638b4a -->

## Сервис: Почта + DNS

> **Сложность:** ⭐⭐⭐☆☆. Junior — после L1.
> **Тарифы:** мониторинг на Bronze, доставляемость и DKIM/SPF — Silver+.
> **Критичность:** **ВЫСОКАЯ** — неработающая почта = нет контрактов, счетов, заявок.

### Типичный стек почты клиента

| Вариант | Доля | Наша зона |
|---|---|---|
| Яндекс 360 / Mail.ru для бизнеса | 55% | DNS-записи, аудит, мониторинг доступности |
| Самохостинг Postfix + Dovecot | 20% | Полный мониторинг + антиспам + бэкапы |
| Exchange 2019 / 2022 on-premise | 15% | Мониторинг + DAG + бэкапы |
| Stalwart / Mailcow / iRedMail | 10% (рост) | Полный мониторинг |

---

### 1. ПРИЁМ

```markdown
#### Опросник: Почта

1. Провайдер: [Яндекс 360 / Mail.ru / свой Postfix / Exchange / Mailcow / ...]
2. Домен почты: _____________@_____________.ru
3. DNS-провайдер: [клиент сам / reg.ru / Yandex 360 DNS / ...]
4. MX-запись: _______________________ (priority + hostname)
5. SPF: _______________________ (v=spf1 include:... all)
6. DKIM: _______________________ (selector._domainkey)
7. DMARC: _______________________ (v=DMARC1; p=quarantine; rua=mailto:...)
8. Если самохостинг:
   - IP почтового сервера: __________________
   - PTR-запись (reverse DNS): есть / нет
   - BlackList-статус (spamhaus, barracuda): чист / проблемы
9. Бэкап почты: да / нет
10. Архивирование входящих/исходящих (требование ФЗ): настроено / нет
```

**Красные флаги:**
- Нет SPF / DKIM / DMARC — письма падают в спам
- PTR-запись не указывает на mail.example.ru — тоже в спам
- IP в blacklist → нужно срочно чистить
- Exchange 2013 / 2016 — EOL, компрометировано через ProxyShell-уязвимости

---

### 2. ПОДКЛЮЧЕНИЕ

#### 2.1. Внешний мониторинг (blackbox)

Добавить к blackbox jobs:

```yaml
- job_name: blackbox_smtp
  metrics_path: /probe
  params: { module: [smtp_banner] }
  static_configs:
    - targets: [mail.example.ru:25, mail.example.ru:587]

- job_name: blackbox_imap_tls
  metrics_path: /probe
  params: { module: [tcp_connect] }
  static_configs:
    - targets: [mail.example.ru:993]
```

#### 2.2. DNS-мониторинг

Skрипт `dns_check.sh` раз в 15 мин через systemd timer, записывает в textfile:

```bash
#!/usr/bin/env bash
TEXTFILE=/var/lib/node_exporter/textfile_collector/dns.prom
DOMAIN=example.ru
TMP=$(mktemp)

## MX
MX=$(dig +short MX $DOMAIN | head -1)
[[ -n "$MX" ]] && echo "dns_mx_present 1" || echo "dns_mx_present 0" >> $TMP

## SPF
SPF=$(dig +short TXT $DOMAIN | grep -c "v=spf1")
echo "dns_spf_records $SPF" >> $TMP

## DKIM: TXT для обычных MTA или CNAME для Postbox. Селекторы Postbox
## передаются из консоли, а не угадываются.
for SEL in default mail selector1 s1 "${POSTBOX_DKIM_SELECTOR_1:-}" "${POSTBOX_DKIM_SELECTOR_2:-}"; do
  [[ -z "$SEL" ]] && continue
  TXT_N=$(dig +short TXT "${SEL}._domainkey.${DOMAIN}" | grep -ci "v=DKIM1" || true)
  CNAME_N=$(dig +short CNAME "${SEL}._domainkey.${DOMAIN}" | grep -ci "\.dkim\.pstbx\.ru\.?$" || true)
  (( TXT_N > 0 || CNAME_N > 0 )) && DKIM=1 || DKIM=0
  echo "dns_dkim_present{selector=\"$SEL\"} $DKIM" >> "$TMP"
done

## DMARC
DMARC=$(dig +short TXT _dmarc.$DOMAIN | grep -c "v=DMARC1")
echo "dns_dmarc_present $DMARC" >> $TMP

## PTR (если mail.example.ru резолвится)
MAIL_IP=$(dig +short mail.$DOMAIN A)
if [[ -n "$MAIL_IP" ]]; then
  PTR=$(dig +short -x $MAIL_IP | grep -c "$DOMAIN")
  echo "dns_ptr_matches_fwd $PTR" >> $TMP
fi

mv $TMP $TEXTFILE
```

#### 2.3. Самохостинг Postfix

```bash
## postfix_exporter — свежая метрика + лог-парсинг
docker run -d --name postfix-exporter \
  -v /var/log:/var/log:ro \
  -v /var/spool/postfix:/var/spool/postfix:ro \
  --restart unless-stopped \
  -p 9154:9154 \
  kumina/postfix_exporter \
  --postfix.showq_path=/var/spool/postfix/public/showq \
  --postfix.logfile_path=/var/log/mail.log
```

Метрики: очереди (deferred, active, hold), rate RBL-отказов, TLS-handshakes.

#### 2.4. Blackbox для blacklist проверки (custom module)

Напишем отдельный сервис `rbl-checker`:

```python
## /opt/mspshield/tools/rbl_check.py — запускается раз в час
import dns.resolver, socket, sys
IP = sys.argv[1]
RBL = ["zen.spamhaus.org", "b.barracudacentral.org",
       "bl.spamcop.net", "dnsbl.sorbs.net"]
reversed_ip = ".".join(reversed(IP.split(".")))
for rbl in RBL:
    try:
        dns.resolver.resolve(f"{reversed_ip}.{rbl}", "A")
        print(f'mail_ip_in_rbl{{rbl="{rbl}"}} 1')
    except dns.resolver.NXDOMAIN:
        print(f'mail_ip_in_rbl{{rbl="{rbl}"}} 0')
```

Вывод перенаправляется в node_exporter textfile.

---

### 3. АЛЕРТЫ

```yaml
- alert: Mail_Unreachable
  expr: probe_success{job=~"blackbox_(smtp|imap_tls)"} == 0
  for: 5m
  labels: { severity: critical, service: "mail" }

- alert: DNS_SPF_Missing
  expr: dns_spf_records == 0
  for: 30m
  labels: { severity: warning, service: "dns" }

- alert: DNS_DMARC_Missing
  expr: dns_dmarc_present == 0
  for: 30m
  labels: { severity: warning, service: "dns" }

- alert: DNS_PTR_Mismatch
  expr: dns_ptr_matches_fwd == 0
  for: 30m
  labels: { severity: warning, service: "dns" }

- alert: Mail_IP_Blacklisted
  expr: mail_ip_in_rbl == 1
  for: 15m
  labels: { severity: critical, service: "mail" }
  annotations:
    summary: "IP {{ $labels.instance }} попал в {{ $labels.rbl }}"

- alert: Postfix_DeferredQueue
  expr: postfix_showq_message_count{queue="deferred"} > 50
  for: 15m
  labels: { severity: warning, service: "mail" }
```

---

### 4. КОНТРОЛЬ

#### Еженедельно
- DNS SPF/DKIM/DMARC — все в порядке
- Blacklist — чист на всех RBL
- Размер очередей Postfix / Exchange queue
- DMARC aggregate reports (если настроен)

#### Ежемесячно
- Рост объёма почты (не забить диск)
- Ротация DKIM ключей (раз в 6 мес рекомендация)
- Проверка certs (IMAPs/SMTPs) — срок действия

---

### 5. TROUBLESHOOTING

#### 5.1. «Письма уходят в спам»
```
1. Проверить SPF, DKIM, DMARC в DNS
2. Mail-tester.com — прислать тестовое письмо
3. Проверить IP в RBL (spamhaus, barracuda)
4. PTR-запись: провайдер должен указать
5. DMARC p=reject слишком строгая? → переключить на quarantine
```

#### 5.2. Postfix очередь deferred растёт
```
1. postqueue -p | head -20        # посмотреть
2. mailq | awk '/^[A-F0-9]/{print $7}' | sort | uniq -c  # по получателям
3. Если все на один домен — DNS/сеть этой стороны
4. Если на всё подряд — проблема у нас:
   - TLS-клиент
   - Rate limit провайдера (mail.ru порой)
5. postsuper -d <queue_id> — удалить заклинившее
```

#### 5.3. «Не приходит почта снаружи»
```
1. Проверить MX записи (dig MX example.ru)
2. Snmart helo telnet 25 снаружи (open порта)
3. postfix/main.cf — inet_interfaces = all, mydestination = ...
4. fail2ban ban на внешнем IP?
```

---

### Upsell

| Триггер | Предложение | Цена |
|---|---|---|
| Нет DKIM/SPF/DMARC | Имплементация DMARC | ADDON 8–15k₽ |
| Попадание в RBL | Clean-up + retention | ADDON 10k₽ |
| Миграция c Mail.ru на Яндекс 360 | Проект миграции | 25–45k₽ |
| Архивирование почты для 152-ФЗ | Stalwart + S3 архив | 40k₽ + хранение |
| Смена домена почты | Полная DNS + SPF + обучение юзеров | 20k₽ |

---

### Чек-лист junior

- [ ] Умею читать MX/SPF/DKIM/DMARC через dig
- [ ] Знаю, как проверять blacklist
- [ ] Настроил Postfix-exporter на учебном стенде
- [ ] Понимаю разницу размещения (Yandex 360 vs самохостинг — наша зона разная)
- [ ] Могу за 10 минут развернуть DMARC reporting


## Материал проекта: `docs/deployment/DEPLOY_RUNBOOK.md`

<!-- SOURCE docs/deployment/DEPLOY_RUNBOOK.md 31ae0ee10b4d07fe -->

## Deploy Runbook — production VM с нуля

Короткий порядок развёртывания MSPShield на одной production VM (Yandex Cloud).
Полная теория и архитектура: [`deploy/yandex/README.md`](https://github.com/i1yxaluk-del/Newbie/blob/main/deploy/yandex/README.md).
Уроки, превращённые в настройки: [`DEPLOYMENT_LESSONS.md`](https://github.com/i1yxaluk-del/Newbie/blob/main/docs/deployment/DEPLOYMENT_LESSONS.md).

### 0. Пререквизиты (локально)

- `yc`-профиль с сервисным аккаунтом (пример: `msp-new`, ключ SA в `~/.config/yandex-cloud/config.yaml`).
- Домен `msp-claude.online`, SSH-ключ `~/.ssh/id_ed25519_yc_new`.
- Docker Desktop / 7-Zip не обязательны, но удобны.

### 1. ВМ в Yandex Cloud

```bash
yc compute instance create --name msp-cloud-vm \
  --zone ru-central1-a --create-boot-disk image-folder-id=standard-images,image-family=ubuntu-2204-lts \
  --preemptible --memory 4 --cores 2 \
  --network-interface subnet-name=default,nat-ip-version=ipv4 \
  --metadata-from-file user-data=deploy/yandex/cloud-init.yaml \
  --ssh-key ~/.ssh/id_ed25519_yc_new.pub
```

- `cloud-init.yaml` ставит Docker (+ `daemon.json` с `storage-driver: overlay2`), Caddy, пользователя.
- Зарезервировать **static IP** (preemptible иначе меняет IP).

### 2. Код на ВМ

```bash
ssh ubuntu@<IP>
sudo mkdir -p /opt/msp/Newbie && sudo chown ubuntu /opt/msp/Newbie
git clone https://github.com/i1yxaluk-del/Newbie.git /opt/msp/Newbie
```

> На чистой ВМ `unzip` должен быть установлен (его ставит `cloud-init.yaml`); иначе распаковка архива кода упадёт: `sudo apt-get install -y unzip`.

### 3. Env-файлы (3 шт.)

| Файл | Обязательно |
|---|---|
| `backend/.env` | `ADMIN_TOKEN` (`openssl rand -hex 32`), `MONGO_URL=mongodb://mongo:27017`, `DB_NAME=mspshield`, `TG_BOT_TOKEN`, `TG_CHAT_ID`, `TG_ALERT_CHAT_ID`; **доставка лидов**: `SMTP_HOST/PORT/USER/PASSWORD/FROM/FROM_NAME`, `LEAD_EMAIL_TO`, `KAITEN_DOMAIN/API_TOKEN/BOARD_ID/COLUMN_ID` (см. §14) |
| `deploy/yandex/.env` | `VAULTWARDEN_ADMIN_TOKEN`, `POSTBOX_API_KEY_ID`, `POSTBOX_API_KEY_SECRET`, `SMTP_USERNAME`, `SMTP_PASSWORD`, `SMTP_FROM`, `STALWART_ADMIN_PASSWORD` |
| `deploy/yandex/monitoring/.env` | `GRAFANA_ADMIN_USER/PASSWORD`, `ALERTMANAGER_WEBHOOK_TOKEN`, `SMTP_AUTH_USER`/`SMTP_AUTH_PASSWORD` (= ключ Postbox), `SMTP_HOST=postbox.cloud.yandex.net`, `SMTP_PORT=465`, `SMTP_USER/PASSWORD`, `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`, `MAX_PHONE`, `MAX_CHAT_ID`, `ALERT_EMAIL_TO`, `MAX_FAILURE_COOLDOWN` |

Формат: UTF-8 **без BOM**, LF (без CRLF).

### 4. Гейт

```bash
cd /opt/msp/Newbie && sudo bash scripts/deployment/preflight.sh --fix
## ожидаемо: PRE-FLIGHT OK
```

### 5. Стеки

```bash
cd /opt/msp/Newbie/deploy/yandex && docker compose up -d            # mongo, backend, vaultwarden (stalwart — только с --profile mail)
cd /opt/msp/Newbie/deploy/yandex/monitoring && docker compose up -d # prometheus, grafana, alertmanager, max-alerter…
```

### 6. Caddy

```bash
sudo systemctl enable --now caddy
```

Caddyfile уже в репозитории (`deploy/yandex/Caddyfile`): домены + Let's Encrypt.

**Автоматика**: `deploy/yandex/setup-on-vm.sh` сам ставит Caddyfile, подставляет `MSP_DOMAIN`
(sed + systemd override в `/etc/systemd/system/caddy.service.d/override.conf`) и прогоняет `caddy validate`.

**Внимание (урок миграции 28.09)**: сразу после cloud-init в `/etc/caddy/Caddyfile` лежит заглушка
`respond "provisioning in progress..." 503`. Пока она на месте — сайт отдаёт 503.
Проверка после деплоя: `grep -c provisioning /etc/caddy/Caddyfile` → `0`.
Если Caddy не стартует с «server block without any key» — не подставлен `MSP_DOMAIN` (см. выше).

### 7. Stalwart (если нужна почта)

1. SSH-tunnel: `ssh -L 8080:127.0.0.1:8080 ubuntu@<IP>` → `http://localhost:8080/admin`.
2. Wizard: hostname `mail.<domain>`, хранилище RocksDB, админ-аккаунт.
3. Домен + ящики `admin@`, `sales@`, `alert@` (пароли — в secrets).
4. Маршрут: `postbox-outbound` → `postbox.cloud.yandex.net:465` implicit TLS, auth = ключ Postbox.
5. **MTA → Outbound → Strategy → Routing**: `IF is_local_domain(rcpt_domain) THEN 'local' ELSE 'postbox-outbound'`.
6. **Перезапустить контейнер Stalwart** (стратегия применяется после рестарта).
7. DKIM: подпись делает Postbox — опубликовать CNAME `<selector>._domainkey → <selector>.dkim.pstbx.ru` из консоли Postbox (собственный ключ Stalwart не нужен).
8. TLS: импортировать сертификаты Caddy для `mail.<domain>` (авто-ACME Stalwart недоступен — 443 занят Caddy).

### 8. DNS (у регистратора)

```
A     msp-claude.online        <IP>
A     mail.<domain>            <IP>
A     mon.<domain>             <IP>   (Grafana)
MX    msp-claude.online        mail.<domain> (10)
TXT   msp-claude.online        v=spf1 a ip4:<IP> include:postbox.cloud.yandex.net ~all
TXT   _dmarc                   v=DMARC1; p=quarantine; rua=mailto:admin@<domain>
CNAME <selector>._domainkey    → <selector>.dkim.pstbx.ru   (Postbox; точные имена из консоли)
```

**Перед переключением DNS (урок миграции 28.09)**: проверь TCP-доступность публичного IP ВМ
**из сети целевого региона** (из РФ): `nc -vz <IP> 22 && curl -sS --connect-timeout 5 -o /dev/null -w '%{http_code}' http://<IP>/`.
Если ICMP проходит, а TCP — нет, адрес/маршрут заблокирован: пересоздай зарезервированный адрес
в другом пуле и только потом меняй DNS A-записи.

### 9. Alertmanager

Entrypoint сам подставит `SMTP_AUTH_USER/PASSWORD` и `ALERTMANAGER_WEBHOOK_TOKEN`. Проверка:

```bash
docker exec msp-alertmanager grep smtp_auth /etc/alertmanager/alertmanager.yml
```

### 10. vm_watcher (операторская Windows-станция)

```powershell
Copy-Item services\vm_watcher\* C:\Users\<user>\vm_watcher\
## конфиг: C:\Users\<user>\.config\mspshield\vm-watcher.json (по config.example.json)
powershell -File C:\Users\<user>\vm_watcher\install.ps1
```

### 11. restic + S3

`/etc/restic/env.sh` (RESTIC_REPOSITORY/PASSWORD, S3-ключи), таймер `restic-backup.timer`.
Тест: `sudo bash /opt/restic-scripts/backup.sh` → `restic_backup_success=1` в Grafana.

**При переезде ВМ в новый аккаунт (урок 28.09)**: S3-ключи старого аккаунта не подходят к новому
бакету (`SignatureDoesNotMatch`) — выпусти новый статический ключ SA (`yc iam access-key create --service-account-name restic-backup`),
обнови `/etc/restic/env.sh` и выполни `restic init` в новом бакете.

### 12. Верификация

- `https://msp-claude.online` → 200, `/api/health` → ok.
- `https://mon.<domain>` → Grafana.
- Тестовое письмо: наружу (не в спам) и внутрь (`alert@`).
- Тестовый P1-алерт → MAX/email.
- `sudo bash scripts/deployment/preflight.sh` → PRE-FLIGHT OK.
- Публичный IP доступен по TCP из целевой сети (см. §8).
- Stalwart не в bootstrap: `docker logs msp-stalwart-1 | grep -c 'bootstrap mode'` → `0` (актуально при миграции).
- При восстановлении из бэкапа `du -sh` томов ≈ размеру бэкапа (см. MIGRATION_RUNBOOK §9.4).
- Форма заявки: тест → письмо на `LEAD_EMAIL_TO` + карточка в Kaiten «Новая» (см. §14).

### 13. Харденинг SSH (после того как AWG-туннель проверен)

По умолчанию публичный SSH открыт с 0.0.0.0/0 — иначе нельзя развернуть ВМ до поднятия AWG.
После проверки туннеля закрываем публичный вход: остаётся только `10.9.0.0/24`:

```bash
## на ВМ: оставить SSH только из VPN-подсети
sudo ufw delete allow 22/tcp          # удалит и v4, и v6 «Anywhere»
sudo ufw status numbered | grep 22    # должен остаться только "22/tcp ALLOW IN 10.9.0.0/24"

## на рабочей станции (yc):
yc vpc security-group update-rules --id <sg-id> --delete-rule-id <ssh-rule-id>
```

Проверка: `nc -vz <IP> 22` снаружи → таймаут; `ssh ubuntu@10.9.0.1` через туннель → работает.

**Аварийный возврат доступа** (если туннель сломался, а зайти нужно):

```bash
yc vpc security-group update-rules --id <sg-id> \
  --add-rule "direction=ingress,protocol=tcp,port=22,v4-cidrs=0.0.0.0/0"
## на ВМ: sudo ufw allow 22/tcp  — и после ремонта снова закрыть
```

Применено на production 28.09.2026: публичный 22 закрыт на уровнях SG и ufw.

### 14. Интеграции лидов (Postbox SMTP + Kaiten)

После подъёма стека заполните в `backend/.env` доставку заявок (в проде нужны обе секции):

```env
## Почта (лиды) — прямой Postbox
SMTP_HOST=postbox.cloud.yandex.net
SMTP_PORT=465
SMTP_USER=<POSTBOX_API_KEY_ID из deploy/.env>
SMTP_PASSWORD=<POSTBOX_API_KEY_SECRET>
SMTP_FROM=sales@msp-claude.online
SMTP_FROM_NAME=MSPShield
LEAD_EMAIL_TO=sales@msp-claude.online,admin@msp-claude.online

## Kaiten CRM
KAITEN_DOMAIN=<workspace>.kaiten.ru
KAITEN_API_TOKEN=<токен с /profile/api-key>
KAITEN_BOARD_ID=<id доски>
KAITEN_COLUMN_ID=<id колонки «Новая»>
```

Пока переменных нет — каналы молча выключены (`is_enabled()=false`), заявка остаётся только в Mongo.

Перезапуск и проверка:

```bash
cd /opt/msp/Newbie/deploy/yandex && docker compose up -d --force-recreate backend
curl -s http://127.0.0.1:8001/api/integrations/status   # ожидаемо kaiten:true
## тестовая заявка на https://<domain>/api/leads → в логах "lead email sent" и "kaiten card created"
docker logs msp-backend-1 --since 3m | grep -Ei "lead|kaiten|email"
```

Текущий прод-конфиг Kaiten: `maksivanovza.kaiten.ru`, доска Lead Pipeline `1773682`, колонка «Новая» `6129074` (подробнее — `docs/KAITEN_SETUP.md`).


## Практический результат

Перескажите цепочку своими словами, выполните безопасную лабораторную работу и сохраните команды без секретов, фактический результат и способ отката. Если результат отличается от текста, остановитесь: сначала исправляется расхождение, а не подгоняется отчёт.
