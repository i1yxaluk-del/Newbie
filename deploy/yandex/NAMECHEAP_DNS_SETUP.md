# Почта: что вписать в Namecheap (Advanced DNS)

Домен `msp-claude.online` · IP `45.132.176.143` · прямая доставка Stalwart (без Postbox).

## ⚠️ Три особенности Namecheap — прочитать до правок

1. **Mail Settings.** Домен должен стоять на **Custom MX** (Domain List → Manage → вкладка
   *Advanced DNS* → блок *Mail Settings* → `Custom MX`). Если выбран *Email Forwarding*,
   Namecheap **подменяет ваши MX-записи** своими и почта на `mail.msp-claude.online` не пойдёт.
2. **Host — относительный.** Домен подставляется автоматически: пишем `mail`, `_dmarc`,
   `v1-rsa-20260521._domainkey` — **без** `.msp-claude.online` в конце.
   (В вашем списке есть ошибочная запись `_dmarc.msp-claude.online` — см. «Удалить».)
3. **TXT ≤ 255 символов.** Длинный DKIM-RSA (420 символов) в одно поле **не влезет** —
   вписывайте **двумя кавычечными строками в одном значении** (ниже готово). ed25519 (76)
   влезает целиком.

## Оставить как есть

- **12 A-записей** (`@`, `bastion`, `dht`, `invite`, `m`, `mail`, `mon`, `names`, `push`,
  `turn`, `vault`, `www`) → `45.132.176.143` ✓
- **TXT `@` = `v=spf1 mx -all`** — уже правильно ✓ (жёсткий `-all`, Postbox убран)
- **MX** (в вашем списке не видно — **проверьте, что запись есть**):

  | Type | Host | Value | Priority | TTL |
  |---|---|---|---|---|
  | `MX Record` | `@` | `mail.msp-claude.online.` | `10` | Automatic |

## Добавить: 2 записи DKIM

Сначала в панели: **Add New Record** → Type `TXT Record`.

**1) RSA (основной, поддерживают все).** Host: `v1-rsa-20260521._domainkey`

Значение вставляйте **одной строкой, БЕЗ кавычек и БЕЗ пробелов**. Панель сама разобьёт
его на две строки по 255 символов:

```
v=DKIM1; k=rsa; h=sha256; p=MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEAxTIIvVK0CaefVJQKaNeFYd5qH6eV1iMVxuiLfpnXzawdiqM0s4Kjgc55FFdgk3kkyukgHka8y/+blPlzbifU6Ax41BB6lQzQtnoS9GX8bR2iI+GFIml3+zQl6yKVrfwm45Xx7KGKc3WfDDiNp2UQbdsQOjvV2H33xX42bET1pg/t23Zdynnw4350ygW7uDJdrMEme15jqlzi6FGg00gj0rOFL+I1iaTw5OZkB3qGIdawkePE5xioLEjRQf/lbkhe//ItZJfkdR+dMnsdh1pGG74DN8CjmQBi4x5X+AR3TnMhAzSvRI0qSR77PLkpCU0lq8EirgJRPUZ3XjXA3w1MKQIDAQAB
```

⚠️ **Главная ошибка (проверено на живом NS):** если вписать значение в виде
`"фрагмент1" "фрагмент2"` (с кавычками), Namecheap сохраняет кавычки и пробел
между ними **как часть значения** — пробел попадает внутрь base64-ключа, и запись
ломается. В итоге DNS отдаёт 421 символ вместо 420, а вторая строка начинается с пробела:

```
"…Zdynnw435"        ← 255 символов, последние 3: w435
" 0ygW7uDJ…"        ← 166 символов, ПЕРВЫЙ символ — пробел  ❌
```

Правильно — 420 символов, вторая строка начинается сразу с `0`:

```
"…Zdynnw435"        ← 255 символов
"0ygW7uDJ…MKQIDAQAB" ← 165 символов, начинается с цифры 0   ✅
```

> В значении допустимы ровно **3 пробела** — все в служебной части `v=DKIM1; k=rsa; h=sha256; p=`.
> Внутри base64-ключа пробелов быть не должно **ни одного**.
> Проверка после сохранения: `nslookup -type=TXT v1-rsa-20260521._domainkey.msp-claude.online`
> — во второй строке не должно быть ведущего пробела.


**2) ed25519 (современный, короче).** Host: `v1-ed25519-20260521._domainkey`
Значение:

```
v=DKIM1; k=ed25519; h=sha256; p=kHbV3jCrleZN/kV6adnqctG9yZ0ucRQxSHCjhSxLlKo=
```

## Изменить: DMARC

Откройте существующую запись **TXT `_dmarc`** и замените значение
(было `p=none` — это «наблюдение», домен можно подделывать):

```
v=DMARC1; p=quarantine; rua=mailto:alert@msp-claude.online; adkim=r; aspf=r; fo=1
```

> `p=quarantine` — на 1–2 недели обкатки, затем поменять на `p=reject`.
> `rua=` указывает на **существующий** ящик `alert@` (ящика `postmaster@` на сервере нет).

## Удалить (остатки Postbox и ошибки)

| Type | Host | Почему |
|---|---|---|
| `CNAME Record` | `egtn6ichfrjtq1kcmeki-1._domainkey` | Postbox, к тому же **пустое значение** (сломано) |
| `CNAME Record` | `egtn6ichfrjtq1kcmeki-2._domainkey` | Postbox больше не используется |
| `TXT Record` | `_dmarc.msp-claude.online` | дубль; при относительных хостах превращается в `_dmarc.msp-claude.online.msp-claude.online` |
| `A Record` | `bastion` | не нужен (bastion остался на старом облаке) — если не используете |

Оставить **одну** запись DMARC — `_dmarc`.

## Опционально: CAA (запрет выпуска сертификата чужим CA)

| Type | Host | Value | TTL |
|---|---|---|---|
| `CAA Record` | `@` | `0 issue "letsencrypt.org"` | Automatic |

> Без `accounturi=…`: с ним запись ломает выпуск сертификатов при смене аккаунта Let's Encrypt.

## Чего НЕ создавать

Stalwart сгенерировал ещё ~10 записей (6× SRV `_imaps/_submissions/_jmap/_caldavs/_carddavs/_pop3s`,
`mta-sts` + `_mta-sts`, `_smtp._tls`, `autoconfig`, `autodiscover`, `ua-auto-config` +
`_ua-auto-config`, `_validation-persist`, CAA `iodef`). Для работы почты **не нужны**:
SRV/autoconfig — только автонастройка клиентов; MTA-STS требует файла политики на сайте
(его нет — запись бесполезна); остальное — служебное. Разбор каждой — в
[`DNS_RECORDS.md`](DNS_RECORDS.md).

## Проверка после сохранения

```bash
nslookup -type=MX msp-claude.online          # -> mail.msp-claude.online (pref 10)
nslookup -type=TXT msp-claude.online         # -> v=spf1 mx -all
nslookup -type=TXT _dmarc.msp-claude.online  # -> v=DMARC1; p=quarantine; ...
nslookup -type=TXT v1-rsa-20260521._domainkey.msp-claude.online
nslookup -type=TXT v1-ed25519-20260521._domainkey.msp-claude.online
nslookup 45.132.176.143                      # PTR -> mail.msp-claude.online (задать в консоли Cloud.ru)
```

Проверка DKIM/SPF/DMARC целиком — отправить письмо на `check-auth@verifier.port25.com`
или посмотреть заголовки у Gmail (`Show original` → `spf=pass`, `dkim=pass`, `dmarc=pass`).

## Итог: 5 DNS-записей + PTR

Почта требует ровно: **MX**, **A(mail)**, **SPF**, **DKIM(RSA)**, **DMARC** — и обратную
запись (PTR) в консоли Cloud.ru. Итого у вас из новых — **2 DKIM** и правка **DMARC**;
остальное уже есть, лишнее (4 записи) удалить.
