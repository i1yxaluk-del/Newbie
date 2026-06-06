# Kaiten под МСП Облако — полная настройка

> Цель: довести Kaiten от «пустой регистрации» до состояния, когда форма лида
> на лендинге → бэкенд → карточка в Kaiten едет автоматически, а команда
> (вы + супруга-маркетолог по [`roadmap/wife_role.md`](roadmap/wife_role.md))
> работает по единому процессу.
>
> Документ предполагает **актуальный код проекта** (`backend/integrations/kaiten.py`,
> `scripts/kaiten_bootstrap.py`, форма `frontend/src/components/sections/CTAForm.jsx`).
> На 2026-05-18 это и есть «правда».
>
> Альтернативные CRM (Pipedrive, HubSpot, Bitrix24) умышленно не рассматриваются —
> в [`roadmap/budget_constraints.md`](roadmap/budget_constraints.md) Kaiten зафиксирован
> как бесплатный baseline до 10 пользователей.

---

## 0. TL;DR (минимальный путь)

Если уже всё понятно и нужно просто получить рабочий канал «лид → карточка»:

```bash
# 1. Регистрируешь Kaiten (5 мин)
#    https://kaiten.ru → Sign up → выбираешь поддомен,
#    например msp-oblako.kaiten.ru → Free tier

# 2. Создаёшь API-токен:
#    https://msp-oblako.kaiten.ru/profile/api-token

# 3. Скрипт сам создаст Space, Board и колонки:
KAITEN_DOMAIN=msp-oblako.kaiten.ru \
KAITEN_API_TOKEN=xxxxxxxxxxxxxxxxxxxx \
python scripts/kaiten_bootstrap.py

# 4. Копируешь из вывода скрипта KAITEN_DOMAIN / KAITEN_BOARD_ID / KAITEN_COLUMN_ID
#    в backend/.env, перезапускаешь backend.

# 5. Отправляешь тестовую заявку с лендинга → карточка должна появиться
#    в колонке «Новая» доски «Lead Pipeline».
```

Если хочется понимать, что и зачем — читай дальше.

---

## 1. Зачем Kaiten в этом проекте

| Задача | Где это в проекте | Почему Kaiten, а не Mongo напрямую |
|---|---|---|
| Воронка продаж (6 стадий) | [`sales/funnel_6_stages.md`](sales/funnel_6_stages.md) | визуальная Kanban-доска, drag-n-drop стадий |
| BANT-Q квалификация лидов | [`sales/bant_q_script.md`](sales/bant_q_script.md) | чек-листы и кастомные поля прямо в карточке |
| Account-management активных клиентов | [`deployment/tenant_onboarding.md`](deployment/tenant_onboarding.md) | отдельная доска с клиентами на удержании |
| Управление инцидентами (P1/P2/P3) | SLA-таблицы в [`contracts/v2/build/03_prilozhenie_2_sla.docx`](../contracts/v2/build/03_prilozhenie_2_sla.docx) | приоритеты и SLA-таймеры |
| Личное обучение (week_01..week_12) | [`training/week_*.md`](training/) | бэклог обучающих карточек, ретро |
| Спринты (раз в 2 недели) | [`roadmap/etape_4_sprints.md`](roadmap/etape_4_sprints.md) | стандартный sprint board |

**Где Kaiten НЕ источник истины:**

- **Лиды как сырые данные** — храним в MongoDB (`backend/server.py`, коллекция `leads`).
  Kaiten — это **рабочая поверхность** для лидов, но не БД. Если Kaiten умрёт —
  список лидов восстанавливается из Mongo.
- **Договоры и акты** — Word/ЭДО (см. `contracts/v2/`).
- **Тех. документация** — Markdown в Git (`docs/`), не Kaiten.
- **Секреты и доступы клиентов** — Vaultwarden (см. [`deployment/secrets_management.md`](deployment/secrets_management.md)).
  Никогда не клади пароли в карточки Kaiten.

---

## 2. Регистрация и тариф

### 2.1. Регистрация

1. Идёшь на https://kaiten.ru → **Создать пространство** → email + пароль (или
   через Яндекс ID).
2. Выбираешь поддомен. Рекомендация: **`msp-oblako.kaiten.ru`** (соответствует
   текущему ребрендингу `МСП Облако`).
3. Подтверждаешь email — workspace создан.

### 2.2. Тариф

На M0–M3 однозначно: **Free**.

| Тариф | Цена | Когда переходить |
|---|---|---|
| **Free** | 0 ₽ | M0–M3: 1–2 пользователя, до 10 досок, базовая автоматизация |
| **Standard** | от 420 ₽/мес/user | M4+: появилась супруга в качестве 2-го пользователя, нужны множественные автоматизации, расширенные права |
| **Pro** | от 720 ₽/мес/user | M12+: появился Junior, время-трекинг, диаграммы Ганта, кастомные роли |

В [`roadmap/budget_constraints.md`](roadmap/budget_constraints.md) Kaiten зафиксирован
бесплатным до 10 user-ов. Это близко к правде: Free Kaiten не имеет жёсткого лимита
пользователей, но ограничивает количество досок и продвинутые автоматизации.
Если упрёшься — переходи на Standard.

### 2.3. Юридическая сторона (152-ФЗ)

Kaiten — российский сервис, серверы в РФ. Достаточно для требований
**ч. 5 ст. 18 152-ФЗ** (локализация ПДн граждан РФ).

В [`COMPLIANCE.md`](../docs/COMPLIANCE.md) Kaiten уже зафиксирован как один из
обработчиков ПДн **по поручению МСП Облака**. Соответственно:

- В политике конфиденциальности на лендинге (`frontend/public/docs/privacy.html`)
  Kaiten должен быть упомянут как место обработки заявок. Проверь, что он там
  есть в разделе «Кому передаются данные».
- Между нами и Kaiten — пользовательское соглашение Kaiten (публичное на
  kaiten.ru), которое и есть «договор-поручение». Дополнительный договор-поручение
  на обработку ПДн с Kaiten **не нужен** — он покрыт публичной офертой.

---

## 3. Структура пространств и досок

Под МСП Облако делаем **3 Space-а** (минимум). Это разделение позволяет позднее
дать доступ супруге только к нужному, не открывая всё.

```
МСП Облако
├── Sales · Воронка лидов               (Space 1)
│     └── Lead Pipeline                 (Board)
│
├── Operations · Активные клиенты       (Space 2)
│     ├── Active Clients                (Board: 1 карточка = 1 клиент)
│     └── Incidents · P1/P2/P3          (Board: тикеты по SLA)
│
└── Internal · Личное                   (Space 3)
      ├── Sprints                       (Board: 2-недельные спринты)
      ├── Training                      (Board: weekly self-learning)
      └── Backlog · Idea pool           (Board: список идей)
```

### 3.1. Space 1 — Sales · Воронка лидов

**Создаётся автоматически** скриптом `scripts/kaiten_bootstrap.py`.

Title: `MSPShield · Sales` (название в коде; можно переименовать в UI на
`МСП Облако · Воронка` — `external_id` лидов не зависит от названия).

#### Board: Lead Pipeline

6 колонок по [`sales/funnel_6_stages.md`](sales/funnel_6_stages.md):

```
[Новая] → [Первичный контакт] → [Аудит] → [КП] → [Переговоры] → [Закрыта]
```

В коде скрипта это:

```python
COLUMNS = [
    "Новая",
    "Первичный контакт",
    "Аудит",
    "КП",
    "Переговоры",
    "Закрыта · Win/Lost",
]
```

Связь со стадиями в `funnel_6_stages.md`:

| Колонка Kaiten | Стадия в funnel | SLA нахождения |
|---|---|---|
| Новая | 1. New Lead | 24 ч |
| Первичный контакт | 2. Qualified | 3 дня |
| Аудит | 3. Discovery | 7 дней |
| КП | 4. Proposal | 10 дней |
| Переговоры | 5. Negotiation | 14 дней |
| Закрыта | 6. Onboarded / Lost | — |

#### Дорожки (Lanes) — опционально

Если поток лидов растёт (> 30/мес), добавь **горизонтальные дорожки** по
источникам, чтобы видеть, какой канал даёт лиды:

```
─── Лендинг ────────────────────────────────
     [Новая] [Перв.контакт] [Аудит] [КП] ...
─── Партнёры / ref ─────────────────────────
     [Новая] [Перв.контакт] [Аудит] [КП] ...
─── Холодные продажи ───────────────────────
     [Новая] [Перв.контакт] [Аудит] [КП] ...
```

При наличии дорожки укажи `KAITEN_LANE_ID` в `backend/.env` — карточки с лендинга
будут падать в первую дорожку.

### 3.2. Space 2 — Operations · Активные клиенты

**Создаётся вручную** в UI Kaiten (для бутстраппинга достаточно Sales).

#### Board: Active Clients

1 карточка = 1 клиент, проведённый через воронку. Колонки:

```
[Onboarding 1-7d] [Onboarding 8-30d] [Active] [Renewal soon] [Paused] [Churned]
```

Поля карточки (custom fields):

- Тариф (Bronze / Silver / Gold);
- Дата старта;
- MRR (₽);
- Контракт № (ссылка на ЭДО);
- SLA-окно обслуживания;
- Контактные лица (имя, телефон, email);
- Согласованный канал связи (Telegram / email / ticket);
- Дата ближайшего weekly-sync;
- Ссылка на Periметр обслуживания (наш Приложение № 3 из `contracts/v2/`).

#### Board: Incidents · P1/P2/P3

Колонки по статусу инцидента:

```
[Новый] [В работе] [Ожидание ответа клиента] [Решено] [Post-mortem]
```

**Дорожки** — по приоритету:

```
─── P1 Critical ──── (SLA реакция 1 час 24/7)
─── P2 High ──────── (SLA реакция 4 часа 9-21)
─── P3 Medium ────── (SLA реакция след. раб. день)
─── P4 / Запросы ──── (не SLA, плановое)
```

Связь с SLA Приложения № 2 — см. `contracts/v2/build/03_prilozhenie_2_sla.docx`.

### 3.3. Space 3 — Internal · Личное

#### Board: Sprints

Стандартный sprint-board под [`roadmap/etape_4_sprints.md`](roadmap/etape_4_sprints.md):

```
[Backlog] [Спринт N · TODO] [In progress] [In review] [Done] [Cancelled]
```

#### Board: Training

12-недельный onboarding под `docs/training/week_*.md`. Колонки = недели:

```
[Week 01] [Week 02] ... [Week 12] [Permanent backlog]
```

#### Board: Backlog · Idea pool

Произвольные идеи, которые не дозрели до спринта.

---

## 4. Бутстрап через скрипт (Space + Board + колонки)

В репо уже лежит готовый скрипт **[`scripts/kaiten_bootstrap.py`](../scripts/kaiten_bootstrap.py)**
— **используй его, не создавай вручную**. Скрипт:

- идемпотентен (можно перезапускать без дубликатов);
- создаёт `Space "MSPShield · Sales"`, `Board "Lead Pipeline"`, 6 колонок;
- выводит готовые значения для `backend/.env`.

### 4.1. Получение API-токена

1. Зайди в Kaiten под аккаунтом-владельцем.
2. Открой https://`<твой-домен>`.kaiten.ru/profile/api-token
3. Нажми **Создать токен**, дай название «backend-mspshield».
4. **Скопируй токен один раз** — повторно его уже не покажут.

### 4.2. Запуск скрипта

```bash
cd /path/to/Newbie
pip install httpx  # если ещё нет

KAITEN_DOMAIN=msp-oblako.kaiten.ru \
KAITEN_API_TOKEN=k_xxxxxxxxxxxxxxxxxxxxxxx \
python scripts/kaiten_bootstrap.py
```

Вывод (пример):

```
→ Kaiten base: https://msp-oblako.kaiten.ru/api/latest
✓ space created: id=421337 title='MSPShield · Sales'
✓ board created: id=1234567 title='Lead Pipeline'
✓ column created: 'Новая' id=999001
✓ column created: 'Первичный контакт' id=999002
✓ column created: 'Аудит' id=999003
✓ column created: 'КП' id=999004
✓ column created: 'Переговоры' id=999005
✓ column created: 'Закрыта · Win/Lost' id=999006

────────────────────────────────────────────────────────────
Готово. Скопируй в backend/.env:

KAITEN_DOMAIN=msp-oblako.kaiten.ru
KAITEN_BOARD_ID=1234567
KAITEN_COLUMN_ID=999001
────────────────────────────────────────────────────────────
Открой доску в браузере:
  https://msp-oblako.kaiten.ru/space/421337/boards/1234567
```

### 4.3. Заполнение backend/.env

Открой `backend/.env` (если его нет — `cp backend/.env.example backend/.env`),
впиши значения:

```ini
KAITEN_DOMAIN=msp-oblako.kaiten.ru
KAITEN_API_TOKEN=k_xxxxxxxxxxxxxxxxxxxxxxx
KAITEN_BOARD_ID=1234567
KAITEN_COLUMN_ID=999001
# KAITEN_LANE_ID=...    # опционально, если в Lead Pipeline несколько дорожек
```

Перезапусти backend:

```bash
# dev
cd backend && uvicorn server:app --reload --port 8000

# либо docker-compose
docker-compose restart backend
```

### 4.4. Проверка статуса интеграции

Эндпойнт `/api/integrations/status` отдаёт булевы флаги без секретов:

```bash
curl http://localhost:8000/api/integrations/status
# {"kaiten":true,"telegram":false,"webhook":false,"smartcaptcha":false}
```

Если `kaiten:false` — какая-то из 4 переменных `KAITEN_*` пустая.

---

## 5. Как лиды попадают из формы в Kaiten

### 5.1. Поток данных

```
┌──────────────────────────────────────────────────────────────────────┐
│  Лендинг: frontend/src/components/sections/CTAForm.jsx               │
│  Поля: name, company, contact, email, servers, tariff, message,     │
│         honeypot, smartcaptcha_token                                  │
└──────────────────────┬───────────────────────────────────────────────┘
                       │ POST /api/leads
                       ▼
┌──────────────────────────────────────────────────────────────────────┐
│  Backend: backend/server.py · create_lead()                          │
│  1. Honeypot check (молча отвергаем ботов)                           │
│  2. SmartCaptcha verify (если включено)                              │
│  3. Rate-limit по IP                                                  │
│  4. Сохранение в Mongo (коллекция `leads`)                           │
│  5. Background task: deliver_to_crm()                                │
│     - telegram.send()      (если настроено)                          │
│     - webhook.send()       (если настроено)                          │
│     - kaiten.create_card() (если настроено)                          │
└──────────────────────┬───────────────────────────────────────────────┘
                       │ POST https://<domain>/api/latest/cards
                       ▼
┌──────────────────────────────────────────────────────────────────────┐
│  Kaiten: карточка появляется в колонке «Новая» доски Lead Pipeline   │
│  Title:       [Tariff] Company · Name                                │
│  Description: имя, компания, контакт, email, серверы, тариф,          │
│               источник, downtime_loss, сообщение, lead_id            │
│  external_id: <lead_id> (UUID из Mongo — идемпотентность)            │
└──────────────────────────────────────────────────────────────────────┘
```

### 5.2. Что прилетает в карточку (точная схема)

См. `backend/integrations/kaiten.py:_format_description()`. В description идут:

```
- **Имя:** Иванов Иван
- **Компания:** ООО Ромашка
- **Контакт:** +7 999 ...
- **Email:** ivan@romashka.ru
- **Серверы:** 5-10
- **Тариф:** silver
- **Источник:** landing
- **Потери/год (калькулятор):** 1 200 000 ₽

**Сообщение клиента:**

> Привет, нам нужен мониторинг и бэкапы

_lead_id:_ `4f3b...`
```

В `title`:

```
[silver] ООО Ромашка · Иванов Иван
```

### 5.3. Идемпотентность

`backend/integrations/kaiten.py:build_card_payload()` ставит `external_id=lead_id`
(UUID лида из Mongo). Kaiten **не** проверяет `external_id` на уникальность сам,
поэтому идемпотентность обеспечивает наш код:

`create_card()` перед созданием карточки вызывает `find_card_by_external_id()`
(`GET /cards?external_id=<lead_id>`). Если карточка с таким `external_id` уже
есть — вторая **не создаётся**, возвращается существующая. Это защищает от:
- двойного клика «Отправить» на лендинге;
- повторной фоновой доставки при рестарте backend в момент обработки лида.

Если же проверка существования не сработала (сеть/таймаут до Kaiten) — мы НЕ
блокируем создание: лучше получить дубль карточки, чем потерять заявку. В этом
редком случае в Kaiten может прийти вторая карточка — удали лишнюю руками.

### 5.4. Что происходит при ошибке Kaiten

`kaiten.create_card()` ретраит **3 раза** с экспоненциальной задержкой 1 → 4 → 16 с.
Если за это время Kaiten не отвечает:

- лид всё равно сохранён в Mongo и виден в `/admin/leads`;
- ошибка пишется в лог `mspshield.kaiten` (`logger.error`);
- метрика `crm_kaiten_error_total` инкрементится;
- пользователю всё равно вернётся `{"status":"ok"}` — UX не блокируется.

Что делать, если регулярно `kaiten:error`:
- проверь `curl https://msp-oblako.kaiten.ru/api/latest/spaces -H "Authorization: Bearer $TOKEN"` — токен живой?
- проверь, что `KAITEN_BOARD_ID` и `KAITEN_COLUMN_ID` правильные (могут устареть, если доску пересоздавали);
- если 401 — токен отозван, перевыпусти и обнови `.env`.

---

## 6. Карточки клиентов и инцидентов

### 6.1. Шаблон карточки клиента (Active Clients)

Когда лид доходит до **Onboarded** (стадия 6), переноси его руками в Space 2
«Operations · Активные клиенты», заводи новую карточку по шаблону:

```
Title:    [Tariff] Company

─── Описание ────────────────────────────────
Контракт:        №12-2026 от 2026-04-01 (ссылка на ЭДО)
Тариф:           Silver
MRR:             45 000 ₽
SLA-окно:        ПН-ПТ 09:00-21:00 МСК
Согл. канал:     Telegram + email (резерв)
Onboarded:       2026-04-15

Контактные лица:
- Технический:  Иванов И.И., +7 999 ..., ivan@...
- Платёжный:    Петрова А.С., +7 999 ..., buh@...

Периметр:        contracts/v2/build/04_prilozhenie_3_perimetr.docx
                 (заполненный шаблон в Vaultwarden / семейный шкаф)

Особенности:
- Active Directory 2 контроллера
- 1С (40 пользователей)
- PostgreSQL 14 (бэкапы критичны)
```

Чек-листы внутри карточки:

- Pre-onboarding (по [`onboarding/welcome_package.md`](onboarding/welcome_package.md))
- Day 1 (доступы, knowledge transfer)
- Day 7 (первый отчёт)
- Day 30 (первый weekly-sync)

### 6.2. Шаблон карточки инцидента

Доска «Incidents». Создаётся вручную при поступлении тикета.

```
Title:    [P1] ACME · PostgreSQL недоступен

─── Описание ────────────────────────────────
Клиент:          ACME (ссылка на карточку клиента)
Приоритет:       P1 Critical
Получено:        2026-05-18 14:23
SLA реакция до:  2026-05-18 15:23  (1 час по контракту Silver)
SLA разрешение:  2026-05-18 22:23  (8 часов)

Симптом:
PostgreSQL на db-01 не принимает подключения.

Воздействие:
1С недоступна, ~40 пользователей не работают.

────────── Timeline ──────────
14:23   получено уведомление в Telegram
14:31   подтверждено клиенту, начало работы
14:48   обнаружено: место на диске закончилось
15:02   очищены логи, сервис поднят
15:14   подтверждение клиента
────────── Resolved 14:48-15:14 (51 мин) ─────
```

Чек-лист:
- [ ] Уведомить клиента в согл. канале о начале работы (15 мин)
- [ ] Зафиксировать корневую причину
- [ ] Provide workaround
- [ ] Подтвердить решение клиентом
- [ ] Внести в post-mortem (если P1)

После решения — переход в колонку «Post-mortem» (только для P1) для разбора.

---

## 7. Кастомные поля (Custom Fields)

Чтобы карточки в воронке были измеримы (как требует `funnel_6_stages.md`),
заведи в Kaiten кастомные поля на уровне Space «Sales»:

| Поле | Тип | Где использовать |
|---|---|---|
| `stage_in` | дата | автомат: дата перехода в текущую колонку |
| `icp_score` | число 0-100 | заполняется на стадии 1 |
| `bant` | enum: hot/warm/cold | заполняется на стадии 2 |
| `tariff_likely` | enum: bronze/silver/gold/undecided | заполняется на стадии 2 |
| `est_mrr` | число (₽) | заполняется на стадии 3-4 |
| `source` | enum: landing/ref/cold/event | автомат из бэкенда |
| `utm_source` | строка | из Yandex Metrika |
| `utm_campaign` | строка | из Yandex Metrika |
| `lost_reason` | enum (8 значений) | заполняется при переходе в Lost |
| `next_action_due` | дата | дедлайн следующего касания |

**Где это в Kaiten:** Настройки Space → Custom Fields → Создать.

**Что заполняет бэкенд автоматически (на момент 2026-05-18):**

Бэкенд кладёт всё в `description` карточки текстом. **В custom fields ничего
автоматически не пишет**, потому что для этого нужно знать `field_id` каждого
поля, что усложнило бы интеграцию. Заполнение custom-полей — ручная работа
на этапе квалификации.

Если в будущем захотите автозаливку — расширьте `build_card_payload()` в
`backend/integrations/kaiten.py`, добавив `properties`:

```python
payload["properties"] = [
    {"id": <field_id_tariff_likely>, "value_id": <enum_value_id>},
    {"id": <field_id_source>,         "value_id": <enum_value_id>},
    {"id": <field_id_est_mrr>,        "value": int(lead.get("downtime_loss", 0) * 0.1)},
]
```

`field_id` и `value_id` получаются через `GET /api/latest/spaces/<id>/properties`.

---

## 8. Автоматизации (Kaiten Rules)

Free-tier Kaiten поддерживает несколько правил автоматизации на уровень Space.
Они работают, не блокируя бэкенд.

### 8.1. Минимальный набор для Sales

| # | Триггер | Условие | Действие |
|---|---|---|---|
| 1 | Карточка создана | Колонка = «Новая» | Назначить ответственного = вы; дедлайн = +24 часа |
| 2 | Время прошло | Карточка > 24 ч в «Новой» | Окрасить тегом «🔥 OVERDUE» |
| 3 | Карточка перемещена | Из «Аудит» в «КП» | Добавить чек-лист «КП-шаблон» (5 пунктов) |
| 4 | Карточка перемещена | Из любой в «Закрыта» | Запросить заполнение `lost_reason` или `won` |
| 5 | Тег «hot» добавлен | — | Назначить дедлайн +48 ч на следующий контакт |

### 8.2. Для Operations / Incidents

| # | Триггер | Условие | Действие |
|---|---|---|---|
| 6 | Тег `P1` | — | Дедлайн = +1 час с момента создания, цвет красный |
| 7 | Тег `P2` | — | Дедлайн = +4 часа, цвет жёлтый |
| 8 | Тег `P3` | — | Дедлайн = +след. рабочий день |
| 9 | Решено | Колонка = «Решено» | Скопировать карточку в архив Active Clients за месяц |

### 8.3. Уведомления

Если в Telegram уже настроен бот (см. `backend/integrations/telegram.py`), его
достаточно — он уже шлёт уведомление при появлении лида.

Внутренние уведомления Kaiten (email / push) включи минимум:
- @упоминания в комментариях;
- назначение карточки на тебя;
- просроченный дедлайн.

Не включай уведомления «обо всём» — спам быстро убьёт ценность.

---

## 9. Ритм работы команды (вы + супруга)

### 9.1. Ежедневный (15 мин)

**Кто:** супруга, в начале дня.
- Открой Space «Sales» → доска Lead Pipeline.
- Просмотри карточки в «Новая» (созданы за последние 24 ч).
- Сделай первичный контакт (см. [`sales/bant_q_script.md`](sales/bant_q_script.md)).
- Заполни `icp_score`, тег `hot/warm/cold`.
- Перенеси в «Первичный контакт» (или Lost с причиной).

### 9.2. Еженедельный (30 мин, понедельник)

**Кто:** супруга, в начале недели.
- Обзор всех карточек в стадиях 2–5 в Lead Pipeline.
- Каждая карточка: что блокирует, что следующее действие, не выпала ли из SLA.
- Карточки, висящие > SLA-окна — поднять флаг для обсуждения с мужем.

### 9.3. Еженедельный (30 мин, пятница) — ретро

**Кто:** оба, по [`roadmap/wife_role.md`](roadmap/wife_role.md).
- Что закрыли (won / lost).
- Что выпало из SLA — почему.
- Спринт board: что не успели, что переносим.

### 9.4. Ежемесячный (60 мин)

**Кто:** оба.
- Pipeline-отчёт: лидов на входе / в воронке / закрыто / win-rate / средний MRR / blended conversion.
- Доска Incidents: сколько P1/P2/P3 за месяц, нарушений SLA, тренды.
- Корректировка планов спринтов.

---

## 10. Ролевая модель и доступы

Источник: [`roadmap/wife_role.md`](roadmap/wife_role.md) + [`../contracts/wife_nda.md`](../contracts/wife_nda.md).

### 10.1. Роли

| Роль | Доступ |
|---|---|
| **Owner** (вы) | Все Space, все доски, все настройки |
| **Marketing/Sales** (супруга) | Space «Sales» — Editor; Space «Operations» — Read-only; Space «Internal» — нет доступа |
| **Read-only** (для бухгалтера / партнёра) | По необходимости, точечно |

### 10.2. Что супруга НЕ должна видеть в Kaiten

Из `wife_nda.md`:

- **Не получает** доступа к серверам и техническим креденшелам.
- В Kaiten это значит: **не приглашать в Space «Operations» как Editor**
  (там в карточках клиента могут засветиться технические детали).
- Карточки активных клиентов с техническим контентом — только для вас.

Практически: дай супруге **Editor только на Space «Sales»**. На Operations —
**View-only**, чтобы она знала статус клиента (нужно для weekly-sync с клиентом),
но не правила технические подробности.

### 10.3. Как настроить

В Kaiten:
- **Настройки Space → Участники → Добавить** для каждого Space отдельно.
- При приглашении выбираешь роль: `Editor` / `Viewer` / `Owner`.

---

## 11. Связь с другими инструментами

### 11.1. Yandex Metrika → Kaiten

Если на лендинге есть цели Yandex.Metrika (см. `docs/landing/yandex_metrika_goals.md`),
то конверсия «отправил форму» в Metrika и появление карточки в Kaiten должны
совпадать. Регулярно сверяй:

```
Yandex.Metrika · Цель «lead_submitted» / неделя : 14
Kaiten · карточек в «Новая» / неделя             : 14
Mongo  · документов в leads / неделя              : 14
```

Если расходятся — где-то теряется лид. Чаще всего: SmartCaptcha срабатывает
жёстко, бэкенд не доходит до записи в Mongo.

### 11.2. Telegram-бот → Kaiten

В `backend/integrations/telegram.py` уже есть отправка лида в Telegram. Это
**параллельный канал**, а не альтернатива Kaiten. Включай оба:

- Telegram = моментальное уведомление в чате (читаешь с телефона);
- Kaiten = постоянная рабочая поверхность и аналитика.

### 11.3. Webhook → Kaiten

`backend/integrations/webhook.py` отправляет лид в произвольный URL (n8n, Make).
Используется, если хотите подключить дополнительные автоматизации поверх Kaiten
(например, email-drip-кампания через Sender или Unisender). Не обязателен.

### 11.4. ЭДО (Контур.Диадок / СБИС) ↔ Kaiten

Kaiten не интегрируется с ЭДО напрямую. Связь — через **поле в карточке
клиента**: «Номер договора в ЭДО» + ссылка. При смене статуса контракта (новая
редакция, доп. соглашение) — обновляешь руками.

---

## 12. Бэкап и экспорт

### 12.1. Что куда

- **Лиды (сырые данные)** — в MongoDB (`mongodump` ежедневно по cron,
  см. `docs/runbooks/backup.md`).
- **Карточки Kaiten** — экспорт через UI: Настройки Space → Экспорт → CSV/JSON.
  Делай **раз в месяц вручную**, складывай в Vaultwarden / семейный шкаф.
- **Прикреплённые файлы** в карточках Kaiten — не дублируем; критичные файлы
  всегда храним в Vaultwarden или Git, а в Kaiten только ссылки.

### 12.2. План «если Kaiten умер»

Кратковременно (1–2 дня):
- Лиды продолжают сохраняться в Mongo.
- Telegram-уведомления приходят как обычно.
- Из `/admin/leads` (наша админка на фронте) видно все лиды.
- Воронку временно ведёшь в Excel/Google Sheets по выгрузке последней копии Kaiten.

Долговременно (если Kaiten реально закрылся):
- Поднять любую другую Kanban (Trello / YouTrack / Bitrix24 / GitLab Issues).
- В `backend/integrations/` добавить новый модуль по образцу `kaiten.py`.
- Переключить `deliver_to_crm()` на новый канал.

---

## 13. Чек-лист первого запуска

Перед публикацией лендинга в продакшен:

- [ ] Kaiten аккаунт создан, выбран поддомен `msp-oblako.kaiten.ru`.
- [ ] API-токен сгенерирован, сохранён в Vaultwarden.
- [ ] `python scripts/kaiten_bootstrap.py` выполнен — Space/Board/колонки на месте.
- [ ] `KAITEN_DOMAIN` / `KAITEN_API_TOKEN` / `KAITEN_BOARD_ID` / `KAITEN_COLUMN_ID` в `backend/.env`.
- [ ] Backend перезапущен.
- [ ] `curl http://localhost:8000/api/integrations/status` → `kaiten:true`.
- [ ] Отправлена тестовая заявка с лендинга → карточка появилась в «Новая» в течение 5 сек.
- [ ] В карточке корректно отображаются все поля (имя, компания, контакт, серверы, тариф).
- [ ] Custom fields созданы в Kaiten (`icp_score`, `bant`, `tariff_likely`, `lost_reason`, …).
- [ ] Минимум 3 базовые автоматизации настроены (deadline +24 ч, тег OVERDUE, чек-лист на «КП»).
- [ ] Супруга добавлена как Editor на Space «Sales».
- [ ] Telegram-бот тоже шлёт лиды (параллельный канал).
- [ ] Записан скринкаст 5 мин: «как работать с лидом от появления до закрытия» (для самих себя на M3 — забудешь).
- [ ] В `frontend/public/docs/privacy.html` Kaiten упомянут как обработчик ПДн.

---

## 14. Типичные ошибки

### 14.1. «kaiten:error» в `/api/integrations/status` или в логах

| Симптом | Причина | Что делать |
|---|---|---|
| `kaiten:false` | хотя бы одна переменная пустая | проверь все 4 `KAITEN_*` в `.env` |
| 401 Unauthorized | токен невалидный | перевыпусти токен в `/profile/api-token` |
| 403 Forbidden | токен от пользователя, не имеющего доступ к Board | выпусти токен из аккаунта-owner-а |
| 404 Not Found | `KAITEN_BOARD_ID` / `KAITEN_COLUMN_ID` устарели | перезапусти `kaiten_bootstrap.py`, обнови `.env` |
| 422 Unprocessable | поле в payload отсутствует или пустое | смотри `r.text` в логах — Kaiten возвращает конкретное поле |
| 429 Rate Limit | слишком много заявок за минуту | автоматический ретрай через 4 / 16 с — не паникуй; если сильно — попроси Kaiten поднять лимит |
| Карточка создалась, но без `external_id` | старый Kaiten | обновись на актуальный API `/api/latest/cards` (уже так) |

### 14.2. Лиды есть в Mongo, но не в Kaiten

Скорее всего, ошибка по типу выше, **или** бэкенд был запущен без переменных
`KAITEN_*` и `kaiten.is_enabled()` вернул False. Перезапусти backend после
правки `.env`.

### 14.3. Дубликаты карточек

С версии v5.5 дубликаты предотвращаются автоматически: `create_card()` сверяет
`external_id=lead_id` через `GET /cards?external_id=...` и не создаёт вторую
карточку (двойной клик и рестарт backend больше не плодят дубли).

Остаточный редкий случай: если запрос-поиск к Kaiten упал по сети (fail-open),
карточка создастся, и теоретически может появиться дубль. Защита: в Kaiten
руками удалить второй, перезаписать `kaiten_card_id` в Mongo.

### 14.4. Капча не пропускает живых клиентов

Это не Kaiten, но проявляется как «лидов нет в Kaiten». Проверь:
- `SMARTCAPTCHA_SERVER_KEY` пустой в dev → бэкенд пропускает заявку без проверки;
- если в проде капча валит → в Yandex Cloud → SmartCaptcha → Логи → посмотри причину отказа.

### 14.5. Карточки в Kaiten есть, но в неправильной колонке

Скрипт `kaiten_bootstrap.py` создаёт колонки по порядку. Если ты руками
перетащил колонки в Kaiten — `KAITEN_COLUMN_ID` указывает на ту, что ты задал.
Это правильное поведение. Если хочешь, чтобы новые лиды падали в другую
колонку — измени `KAITEN_COLUMN_ID` в `.env` на id нужной.

---

## 15. Куда расширяться дальше

Когда базовая интеграция стабильно работает 1–2 месяца:

1. **Автозаполнение custom fields** из бэкенда (см. п. 7) — `tariff_likely`,
   `source`, `est_mrr`. Это сэкономит супруге 30 сек на лид.
2. **Webhook из Kaiten обратно в МСП Облако** — при переходе карточки в
   «Закрыта · Won» автоматически создать запись в коллекции `clients` Mongo и
   завести карточку в Operations. Free-tier Kaiten поддерживает исходящие
   webhooks.
3. **Time-tracking** (Pro-tier) — фиксировать, сколько часов потратили на
   каждого клиента, считать рентабельность.
4. **Custom roles** (Pro-tier) — точечно ограничить доступ Junior-а к
   финансовым полям карточек.
5. **OAuth-интеграция** между Kaiten и Yandex 360 — Single Sign-On для команды.

---

## 16. Источники и ссылки

- Kaiten API docs (на 2026-05-18): https://developers.kaiten.ru/
- Текущая интеграция в проекте: [`backend/integrations/kaiten.py`](../backend/integrations/kaiten.py)
- Скрипт бутстрапа: [`scripts/kaiten_bootstrap.py`](../scripts/kaiten_bootstrap.py)
- Воронка продаж (6 стадий): [`sales/funnel_6_stages.md`](sales/funnel_6_stages.md)
- BANT-Q скрипт квалификации: [`sales/bant_q_script.md`](sales/bant_q_script.md)
- Onboarding клиента: [`deployment/tenant_onboarding.md`](deployment/tenant_onboarding.md)
- Роль супруги: [`roadmap/wife_role.md`](roadmap/wife_role.md)
- Внутренний NDA: [`../contracts/wife_nda.md`](../contracts/wife_nda.md)
- Бюджет и тарифы: [`roadmap/budget_constraints.md`](roadmap/budget_constraints.md)
- Compliance / 152-ФЗ: [`COMPLIANCE.md`](COMPLIANCE.md)

---

*Последнее обновление: 2026-05-18 · v1.0 · покрывает Free / Standard тарифы Kaiten.*
