# MAX мессенджер · настройка под МСП Облако

Полная инструкция по интеграции **MAX** (российский мессенджер от VK,
с конца 2024 года имеет официальный Bot API) в проект МСП Облако.

> **TL;DR.** Bot API у MAX **бесплатный**, как и у Telegram. Никакой
> покупки лицензии не требуется. Делаем три вещи: создаём бота через
> `@MasterBot` → подписываем его на наш webhook → лиды и алерты
> начинают летать.

---

## Оглавление

1. [Зачем MAX в проекте](#1-зачем-max-в-проекте)
2. [Что НЕ делаем (web.max.ru, scraping)](#2-что-не-делаем-webmaxru-scraping)
3. [Архитектура интеграции](#3-архитектура-интеграции)
4. [Шаг 1. Регистрация бота в MAX](#4-шаг-1-регистрация-бота-в-max)
5. [Шаг 2. Переменные окружения](#5-шаг-2-переменные-окружения)
6. [Шаг 3. Регистрация webhook](#6-шаг-3-регистрация-webhook)
7. [Шаг 4. Проверка сценариев](#7-шаг-4-проверка-сценариев)
8. [Сценарии бота](#8-сценарии-бота)
9. [Связка с Kaiten CRM](#9-связка-с-kaiten-crm)
10. [Alertmanager → MAX (и Telegram)](#10-alertmanager--max-и-telegram)
11. [Локальная разработка без HTTPS](#11-локальная-разработка-без-https)
12. [Типичные ошибки](#12-типичные-ошибки)
13. [Что не реализовано (на будущее)](#13-что-не-реализовано-на-будущее)

---

## 1. Зачем MAX в проекте

MAX закрывает три задачи параллельно с Telegram:

1. **Алерты о новых лидах с лендинга** — пуш приходит лично владельцу
   (вам и/или супруге) сразу как только сработала форма «Получить
   расчёт». Канал-дубликат к Telegram — на случай блокировок или
   проблем с одним из мессенджеров.

2. **Получение заявок прямо в боте** — пользователь нажимает на
   лендинге «Написать в MAX», запускает бота, выбирает «Рассчитать
   стоимость» / «Тарифы» / «Связаться». Бот собирает мини-анкету и
   создаёт лид в той же таблице, что и форма с сайта (`leads`
   коллекция в Mongo, тариф `source=max_bot`).

3. **Канал связи с клиентом** — после подписания договора в Kaiten на
   карточке клиента остаётся `max_chat_id`. Через
   `/admin/leads` (а в перспективе `/admin/clients`) специалист
   отправляет клиенту сообщение в MAX прямо из админки.

Всё это **бесплатно**: Bot API у MAX тарификации не имеет, лимиты
(rate limit) — стандартные для бота, для нашего объёма заявок не
проблема.

## 2. Что НЕ делаем (web.max.ru, scraping)

Изначально в задаче звучало «может быть через web.max.ru, без покупки
API». Делать через web-клиент — **категорически не годится**:

- Web-клиент авторизуется через SMS-код на ваш реальный номер.
  Это не масштабируется, и при каждом перелогине бот «отваливается».
- Эмуляция веб-клиента нарушает ToS MAX и легко детектится
  антифродом (другой User-Agent, отсутствие WS-handshake, и т. п.).
  Учётка блокируется, а с ней — весь канал.
- Web-клиент меняется без объявления — наш код будет ломаться
  каждые несколько недель.

**Bot API — официальный, бесплатный, стабильный.** Используем его.

## 3. Архитектура интеграции

```
┌──────────────┐                ┌──────────────────────┐
│ Лендинг      │ POST /leads    │ FastAPI backend      │
│ (форма)      │ ─────────────► │ /api/leads           │
└──────────────┘                │                      │
                                │ BackgroundTasks:     │
┌──────────────┐                │  - kaiten.create()   │
│ MAX-бот      │ ◄──────────────┤  - telegram.send()   │
│ (alert)      │ POST /messages │  - max.send()    ◄── │ алерт
└──────────────┘                │  - webhook.send()    │
                                └──────────────────────┘
                                            ▲
┌──────────────┐                            │
│ Пользователь │ /start                     │
│ в MAX        │ → POST /api/max/webhook    │
│              │ ────────────────────────►  │ входящий лид
└──────────────┘     update_type=*          │
                                            ▼
                                        ┌──────────┐
                                        │ Mongo    │
                                        │ leads    │
                                        │ +        │
                                        │ max_sess │
                                        └──────────┘
                                            │
                                            ▼ карточка
                                        Kaiten Sales space
```

Ключевое:

- **Источник истины — Mongo** (`leads` + `max_sessions`). Если MAX
  сломается или мы поменяем мессенджер, лиды останутся.
- **Все исходящие — async** (httpx). Время ответа на форму = время
  записи в Mongo, не зависит от MAX/Telegram/Kaiten.
- **Webhook идемпотентен**: повторная доставка одного и того же
  `mid`/`callback_id` не создаст лида дважды (фильтр по `max_user_id`
  + `step`).

## 4. Шаг 1. Регистрация бота в MAX

Делается прямо в мессенджере MAX (мобильное приложение или
[web.max.ru](https://web.max.ru/)), займёт 2 минуты.

1. Откройте поиск → введите `@MasterBot` → нажмите на профиль →
   **Запустить**.
2. В диалоге наберите `/create` или нажмите «Создать бота».
3. Введите название бота, например: `МСП Облако · поддержка`.
4. Введите username (латиница, без `@`), например: `msp_oblako_bot`.
   Запомните его — он понадобится для `MAX_BOT_USERNAME`.
5. `@MasterBot` выдаст **токен** в формате
   `mb-<набор символов>`. Скопируйте — это `MAX_BOT_TOKEN`.

Чтобы узнать свой `user_id` (нужен для `MAX_ALERT_CHAT_ID`):
в `@MasterBot` или в [настройках профиля](https://web.max.ru/) →
профиль → ID.

## 5. Шаг 2. Переменные окружения

В `backend/.env` добавьте (или раскомментируйте в `backend/.env.example`):

```bash
MAX_BOT_TOKEN=mb-aBcD...              # из @MasterBot
MAX_ALERT_CHAT_ID=123456789           # ваш user_id или id группы
MAX_WEBHOOK_SECRET=$(openssl rand -hex 32)
MAX_BOT_USERNAME=msp_oblako_bot       # без @
LANDING_URL=https://msp-claude.online     # для кнопки в боте (опционально)
```

Перезапустите backend. Эндпоинт `/api/integrations/status` теперь
должен возвращать:

```json
{
  "max": true,
  "max_alert_channel": true,
  "max_bot_username": "msp_oblako_bot",
  ...
}
```

## 6. Шаг 3. Регистрация webhook

> MAX требует **HTTPS на порту 443 с валидным TLS** (не self-signed).
> Локально это не работает — см. раздел [11](#11-локальная-разработка-без-https).

Когда backend задеплоен на ваш домен (например, `msp-claude.online` через
nginx → uvicorn — конфиг есть в `deploy/nginx/mspshield.conf`),
зарегистрируйте webhook:

**Вариант 1 — скриптом (рекомендуется):**

```bash
MAX_BOT_TOKEN=mb-aBcD... \
MAX_WEBHOOK_URL=https://msp-claude.online/api/max/webhook \
MAX_WEBHOOK_SECRET=$(grep MAX_WEBHOOK_SECRET backend/.env | cut -d= -f2) \
python scripts/max_setup_webhook.py
```

Скрипт:

- проверит токен (выведет username бота и user_id),
- покажет текущие подписки,
- удалит чужие подписки (MAX поддерживает только одну активную),
- создаст новую подписку с вашим секретом и подпиской на
  `message_created`, `message_callback`, `bot_started`.

Опции:

- `--dry-run` — показать план без изменений.
- `--token / --url / --secret` — альтернатива env-переменным.

**Вариант 2 — `curl` вручную:**

```bash
curl -X POST "https://platform-api.max.ru/subscriptions" \
  -H "Authorization: $MAX_BOT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://msp-claude.online/api/max/webhook",
    "secret": "'"$MAX_WEBHOOK_SECRET"'",
    "update_types": ["message_created", "message_callback", "bot_started"]
  }'
```

## 7. Шаг 4. Проверка сценариев

После регистрации webhook’а проверьте по чеклисту:

- [ ] Открыть бота в MAX, нажать «Запустить» → должно прилететь
      приветствие с тремя кнопками: «Рассчитать», «Тарифы»,
      «Связаться».
- [ ] Нажать «Тарифы» → пришли три кнопки Bronze / Silver / Gold.
- [ ] Нажать «Silver» → пришло описание тарифа с кнопкой
      «← К списку тарифов».
- [ ] Нажать «Рассчитать» → пришёл вопросник.
- [ ] Написать в бота произвольное сообщение → бот ответит
      благодарностью, в `/admin/leads` появилась запись с
      `source=max_bot`, в Kaiten — карточка в колонке «Новая».
- [ ] Отправить тестовую заявку через форму на лендинге → в MAX
      пришёл алерт «🛡 Новая заявка МСП Облако».

## 8. Сценарии бота

Полная mini-funnel реализована в `_handle_max_update()` в
`backend/server.py`:

| Событие | Что делает бот |
|---|---|
| `bot_started` | Шлёт `WELCOME_TEXT` + 3 кнопки + опционально ссылку на сайт. Создаёт сессию в `max_sessions` со `step=welcome`. |
| `message_callback` `show_tariffs` | Описание тарифов + 4 кнопки выбора. |
| `message_callback` `tariff_bronze\|silver\|gold` | Детали тарифа + кнопки «Рассчитать» / «Назад». Сохраняет `tariff_hint`. |
| `message_callback` `calc_start` | Просит ответить на 4 вопроса в свободной форме. Ставит `step=awaiting_calc_data`. |
| `message_created` | Создаёт лид в `leads` со `source=max_bot`, отправляет благодарность, ставит `step=lead_submitted`. |
| Любое другое | Молча игнорируется (200 OK). |

Тексты и кнопки находятся в `backend/integrations/max.py`
(`WELCOME_TEXT`, `TARIFFS_TEXT`, `TARIFF_DETAILS`, `welcome_buttons()`,
`tariffs_buttons()`). Меняйте там же.

## 9. Связка с Kaiten CRM

Лид, пришедший через бота, проходит ту же фоновую задачу
`deliver_to_crm`, что и лид с лендинга. То есть:

- Создаётся карточка в Kaiten (колонка «Новая» вашего Sales space).
- В описании карточки — все поля лида плюс `max_user_id` и
  `max_chat_id` (чтобы можно было ответить клиенту обратно в MAX).
- Карточка получает `external_id = lead.id` — идемпотентность по
  Kaiten работает (повторов не будет).

Чтобы написать клиенту в MAX из админки/Kaiten:

```python
from backend.integrations import max as max_int

await max_int.send_message(
    user_id=client.max_user_id,
    text="Здравствуйте! По вашей заявке от ... готов выслать КП.",
)
```

> На будущее: добавить кнопку «Ответить в MAX» прямо в
> `/admin/leads` (см. раздел [13](#13-что-не-реализовано-на-будущее)).

## 10. Alertmanager → MAX (и Telegram)

Prometheus Alertmanager умеет шлёт алерты через webhook. У нас есть
готовый приёмник `POST /api/alerts/alertmanager`, который fan-out
отправляет алерты в **MAX (markdown) + Telegram (HTML)** одновременно.

### 10.1. Что включить

В `backend/.env`:

```env
# Канал MAX уже настроен из шагов выше
MAX_BOT_TOKEN=...
MAX_ALERT_CHAT_ID=...

# Опционально — отдельный чат для алертов в Telegram
# (если не задан, шлётся в TG_CHAT_ID)
TG_ALERT_CHAT_ID=

# Bearer-токен для Alertmanager (генерируется один раз)
ALERTMANAGER_WEBHOOK_TOKEN=$(openssl rand -hex 32)

# Какие каналы использовать (по умолчанию оба)
# ALERT_CHANNELS=max,telegram

# Слать ли уведомления о resolved (по умолчанию true)
# ALERT_RESOLVED_NOTIFY=true
```

### 10.2. Конфиг Alertmanager

В репозитории лежит готовый пример: `deploy/alertmanager/alertmanager.yml`.
Главное — receiver с Bearer-авторизацией:

```yaml
receivers:
  - name: msp-max-tg
    webhook_configs:
      - url: 'https://msp-claude.online/api/alerts/alertmanager'
        send_resolved: true
        http_config:
          authorization:
            type: Bearer
            credentials: '<ALERTMANAGER_WEBHOOK_TOKEN из .env>'
```

Routing-tree разделяет severity на P1/P2/P3 с разной частотой
group_wait/repeat_interval — см. пример полностью.

Пример rule-файла под Prometheus (Host/Disk/HTTP-error/Backup) —
`deploy/alertmanager/rules.example.yml`.

### 10.3. Что приходит в MAX

Формат сообщения для одного алерта:

```
🔴 P1 · alert
**HostDown**

Host web-01 недоступен
Prometheus не получает метрики от web-01 более 2 минут (job node).

instance: `web-01`
job: `node`
env: `prod`
severity: `critical`
time: `2026-05-06 03:47:12 UTC`

[runbook](https://docs.msp-claude.online/runbooks/R-01-host-down) · [graph](http://prom/...)
```

Severity mapping:

| Alertmanager severity | Priority | Emoji |
|---|---|---|
| `critical`, `page`, `high`, `error` | **P1** | 🔴 |
| `warning`, `warn` | **P2** | 🟡 |
| `info`, `notice`, `none`, (пусто) | **P3** | 🔵 |
| любой `resolved` | resolved | ✅ |

### 10.4. Тест без Prometheus

```bash
curl -X POST https://msp-claude.online/api/alerts/alertmanager \
  -H "Authorization: Bearer $ALERTMANAGER_WEBHOOK_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "version":"4","status":"firing","receiver":"msp-max-tg",
    "alerts":[{
      "status":"firing",
      "labels":{"alertname":"TestAlert","severity":"critical","instance":"localhost"},
      "annotations":{"summary":"Тестовый алерт","description":"Проверка интеграции"},
      "startsAt":"2026-05-06T12:00:00Z",
      "generatorURL":"http://prom/graph?expr=up"
    }]
  }'
```

Ожидаемо: 200, в течение пары секунд приходит сообщение в MAX и Telegram.

### 10.5. Безопасность

- Bearer-токен в `Authorization` сравнивается constant-comparison
  (см. `integrations/alertmanager.py::verify_token`).
- Backend на запрос с неверным токеном вернёт **401** (не 200) —
  чтобы в логах Alertmanager видеть проблему явно.
- Webhook должен быть доступен на HTTPS с валидным TLS.
- Запросы пишутся в обычный application log
  (`mspshield.alertmanager`) с количеством алертов и receiver.

## 11. Локальная разработка без HTTPS

MAX webhook требует валидный HTTPS на :443. Локально это не работает.
Варианты:

**A. Long-polling (рекомендуется для dev).** В документации
[/updates](https://dev.max.ru/docs-api/methods/GET/updates) — простой
long-polling endpoint. Минимальный скрипт-полл (не входит в PR — можно
дописать при необходимости) опрашивает GET `/updates` и руками
вызывает тот же `_handle_max_update()` из server.py через
`httpx` на локальный `http://localhost:8001/api/max/webhook`.

**B. cloudflared / ngrok туннель.** Достаточно для одного
тестового сценария. Но MAX строго проверяет цепочку сертификатов,
поэтому **ngrok бесплатный тариф не подойдёт** (его сертификаты не
покрывают custom subdomain). Cloudflared — да, работает.

**C. Тестировать на staging.** В Yandex Cloud разверните второй
backend с поддоменом `staging.msp-claude.online` и отдельным MAX-ботом
с суффиксом `_dev`. Регистрируйте webhook на staging-домен.

## 12. Типичные ошибки

| Ошибка | Причина | Что делать |
|---|---|---|
| `401 Unauthorized` от MAX API | Токен неверный или истёк. | Перевыпустите токен в @MasterBot, обновите `MAX_BOT_TOKEN`. |
| `405 Method Not Allowed` на /subscriptions | Webhook URL отдаёт 4xx/5xx. | Проверьте, что `/api/max/webhook` отвечает 200 на пустой POST. |
| Webhook не доставляется | TLS-сертификат self-signed / SAN не совпадает. | Используйте Let’s Encrypt + правильный CN. |
| Бот не отвечает на /start | Не подписаны на `bot_started`. | Запустите `max_setup_webhook.py` ещё раз — он подписывается на нужные типы. |
| Дубль лида в Kaiten | Не передан `external_id`. | У нас передаётся, но если правили `kaiten.py` — верните `external_id = lead.id`. |
| Алерт о лиде уходит в Telegram, но не в MAX | `MAX_ALERT_CHAT_ID` пуст. | Заполните его user_id владельца. |
| Бот ведёт себя как «эхо» | `_handle_max_update` ловит свой же `bot_started` от себя. | Невозможно — MAX отдаёт `bot_started` только от пользователя. Если воспроизвели — пришлите payload в issue. |
| 429 Too Many Requests | Превышен rate limit на отправку. | В нашем объёме не должно происходить. Если случилось — `time.sleep(1)` и повтор. |

## 13. Что не реализовано (на будущее)

Сделано в этом PR — базовый каркас. Стоит к нему добавить:

1. **`/admin/leads` UI кнопка «Ответить в MAX»** — открывает модалку
   с textarea, POST на новый эндпоинт `/api/admin/max/send`.
2. **Long-polling-скрипт для dev** — `scripts/max_dev_poll.py`,
   чтобы тестировать без HTTPS-туннеля.
3. **Request_contact с проверкой `hash`** — авторизация по номеру
   через MAX (см. https://dev.max.ru/docs/chatbots/keyboards#request_contact).
4. **Мульти-операторская очередь** — когда у нас будет супруга /
   младший специалист, разделять входящие чаты между ними. Сейчас все
   идут в один общий поток.
5. **Wazuh → backend → MAX** (минуя Alertmanager) — отдельный приёмник
   `/api/alerts/wazuh` под формат Wazuh integration script. Сейчас
   можно через Alertmanager-prometheus exporter или alternative
   webhook → Alertmanager.

Файл скоро устареет — обновляйте по мере роста бота. PR-ревью на эту
доку приветствуется.
