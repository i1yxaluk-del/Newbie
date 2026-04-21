# Сервис: Почта + DNS

> **Сложность:** ⭐⭐⭐☆☆. Junior — после L1.
> **Тарифы:** мониторинг на Bronze, доставляемость и DKIM/SPF — Silver+.
> **Критичность:** **ВЫСОКАЯ** — неработающая почта = нет контрактов, счетов, заявок.

## Типичный стек почты клиента

| Вариант | Доля | Наша зона |
|---|---|---|
| Яндекс 360 / Mail.ru для бизнеса | 55% | DNS-записи, аудит, мониторинг доступности |
| Самохостинг Postfix + Dovecot | 20% | Полный мониторинг + антиспам + бэкапы |
| Exchange 2019 / 2022 on-premise | 15% | Мониторинг + DAG + бэкапы |
| Stalwart / Mailcow / iRedMail | 10% (рост) | Полный мониторинг |

---

## 1. ПРИЁМ

```markdown
### Опросник: Почта

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

## 2. ПОДКЛЮЧЕНИЕ

### 2.1. Внешний мониторинг (blackbox)

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

### 2.2. DNS-мониторинг

Skрипт `dns_check.sh` раз в 15 мин через systemd timer, записывает в textfile:

```bash
#!/usr/bin/env bash
TEXTFILE=/var/lib/node_exporter/textfile_collector/dns.prom
DOMAIN=example.ru
TMP=$(mktemp)

# MX
MX=$(dig +short MX $DOMAIN | head -1)
[[ -n "$MX" ]] && echo "dns_mx_present 1" || echo "dns_mx_present 0" >> $TMP

# SPF
SPF=$(dig +short TXT $DOMAIN | grep -c "v=spf1")
echo "dns_spf_records $SPF" >> $TMP

# DKIM (ожидаем selector 'default' или 'mail')
for SEL in default mail selector1 s1; do
  DKIM=$(dig +short TXT ${SEL}._domainkey.$DOMAIN | grep -c "v=DKIM1")
  echo "dns_dkim_present{selector=\"$SEL\"} $DKIM" >> $TMP
done

# DMARC
DMARC=$(dig +short TXT _dmarc.$DOMAIN | grep -c "v=DMARC1")
echo "dns_dmarc_present $DMARC" >> $TMP

# PTR (если mail.example.ru резолвится)
MAIL_IP=$(dig +short mail.$DOMAIN A)
if [[ -n "$MAIL_IP" ]]; then
  PTR=$(dig +short -x $MAIL_IP | grep -c "$DOMAIN")
  echo "dns_ptr_matches_fwd $PTR" >> $TMP
fi

mv $TMP $TEXTFILE
```

### 2.3. Самохостинг Postfix

```bash
# postfix_exporter — свежая метрика + лог-парсинг
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

### 2.4. Blackbox для blacklist проверки (custom module)

Напишем отдельный сервис `rbl-checker`:

```python
# /opt/mspshield/tools/rbl_check.py — запускается раз в час
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

## 3. АЛЕРТЫ

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

## 4. КОНТРОЛЬ

### Еженедельно
- DNS SPF/DKIM/DMARC — все в порядке
- Blacklist — чист на всех RBL
- Размер очередей Postfix / Exchange queue
- DMARC aggregate reports (если настроен)

### Ежемесячно
- Рост объёма почты (не забить диск)
- Ротация DKIM ключей (раз в 6 мес рекомендация)
- Проверка certs (IMAPs/SMTPs) — срок действия

---

## 5. TROUBLESHOOTING

### 5.1. «Письма уходят в спам»
```
1. Проверить SPF, DKIM, DMARC в DNS
2. Mail-tester.com — прислать тестовое письмо
3. Проверить IP в RBL (spamhaus, barracuda)
4. PTR-запись: провайдер должен указать
5. DMARC p=reject слишком строгая? → переключить на quarantine
```

### 5.2. Postfix очередь deferred растёт
```
1. postqueue -p | head -20        # посмотреть
2. mailq | awk '/^[A-F0-9]/{print $7}' | sort | uniq -c  # по получателям
3. Если все на один домен — DNS/сеть этой стороны
4. Если на всё подряд — проблема у нас:
   - TLS-клиент
   - Rate limit провайдера (mail.ru порой)
5. postsuper -d <queue_id> — удалить заклинившее
```

### 5.3. «Не приходит почта снаружи»
```
1. Проверить MX записи (dig MX example.ru)
2. Snmart helo telnet 25 снаружи (open порта)
3. postfix/main.cf — inet_interfaces = all, mydestination = ...
4. fail2ban ban на внешнем IP?
```

---

## Upsell

| Триггер | Предложение | Цена |
|---|---|---|
| Нет DKIM/SPF/DMARC | Имплементация DMARC | ADDON 8–15k₽ |
| Попадание в RBL | Clean-up + retention | ADDON 10k₽ |
| Миграция c Mail.ru на Яндекс 360 | Проект миграции | 25–45k₽ |
| Архивирование почты для 152-ФЗ | Stalwart + S3 архив | 40k₽ + хранение |
| Смена домена почты | Полная DNS + SPF + обучение юзеров | 20k₽ |

---

## Чек-лист junior

- [ ] Умею читать MX/SPF/DKIM/DMARC через dig
- [ ] Знаю, как проверять blacklist
- [ ] Настроил Postfix-exporter на учебном стенде
- [ ] Понимаю разницу размещения (Yandex 360 vs самохостинг — наша зона разная)
- [ ] Могу за 10 минут развернуть DMARC reporting
