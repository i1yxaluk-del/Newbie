# MSPShield v4.5

> **Managed IT Services для СМБ в РФ · 2026.**
> Мониторинг 24/7 · Автоматические бэкапы · Реакция по SLA · 152-ФЗ · Импортозамещение.

> 📘 **Новый? Начни с [`docs/JUNIOR_GUIDE.md`](docs/JUNIOR_GUIDE.md)** — инструкция
> для junior-инженера: локальный запуск, прод, админка, CRM Kaiten, тестовые
> заявки, типовые проблемы.
>
> 🗂 **Настройка Kaiten под проект:** [`docs/KAITEN_SETUP.md`](docs/KAITEN_SETUP.md)
> — пространства, доски, воронка, custom fields, ролевая модель, бэкапы,
> чек-лист первого запуска.
>
> ✏️ **Изменить тексты, тарифы, иконки на лендинге:** UI-конфигуратор
> [`/admin/landing-edit`](#управление-контентом-лендинга) + полное
> руководство [`docs/EDITING.md`](docs/EDITING.md). Весь редактируемый
> контент — один файл [`frontend/src/content/landing.ru.json`](frontend/src/content/landing.ru.json),
> React-код трогать не нужно.

**Что нового в v4.5:**
- Минималистичный лендинг — 6 секций вместо 9 (`Hero · Pain · Pricing · Process · FAQ · CTAForm`).
- **UI-конфигуратор лендинга `/admin/landing-edit`** — все тексты, тарифы, FAQ и иконки редактируются в браузере с live-preview (override в `localStorage`), потом «Скачать JSON» → коммит в репо. Полная инструкция: [`docs/EDITING.md`](docs/EDITING.md).
- Админка переписана: вход по паролю → JWT (24 ч) в localStorage. `X-Admin-Token` сохранён для CLI/curl. Фильтры по статусу/тарифу + экспорт CSV.
- Связь формы с CRM **Kaiten** через REST API (карточка создаётся в фоне, идемпотентно по `lead_id`).
- Универсальный `CRM_WEBHOOK_URL` (n8n / Make / Zapier / Bitrix24 inbound).
- Скрипт `scripts/kaiten_bootstrap.py` — создаёт Space + Board + 6 колонок воронки одной командой.
- Скрипт `scripts/seed_test_lead.py` — три тестовые заявки для проверки сквозной интеграции.
- Lazy-load админки: главный bundle лендинга — **126 KB gzip**.
- Mongo-индексы (`status`, `tariff`, `created_at`) создаются на старте.
- nginx: gzip + immutable cache для `/static/`, no-store для `index.html`.

Полный пакет для запуска MSP-бизнеса с нуля до первых клиентов:
**продукт** (React 19 + FastAPI + MongoDB), **playbook развёртывания**
(Bronze / Silver / Gold), **договоры**, **операционные регламенты**,
**инфраструктура-как-код** (Terraform + Ansible) и **стратегия
go-to-market**.

**Что нового в v4.1 (vs v4.0):**
- Материализованы **все 53 артефакта Марафона 3.1–3.5** как реальные файлы репо:
  - `analysis/` — юнит-экономика, CAC/LTV, финмодель M1–M24, ICP, ADDON-каталог, политика скидок.
  - `frontend/` — форма заявки с consent + honeypot + Yandex SmartCaptcha; страницы `privacy`, `offer`, `sla`; SEO/A-B/blog-план.
  - `backend/` — rate-limit, honeypot-проверка, consent (152-ФЗ), server-side SmartCaptcha, `/metrics` Prometheus.
  - `docs/sales/` — 6-стадийная воронка, BANT-Q скрипт, 7 email-шаблонов.
  - `docs/onboarding/` — pre-onboarding checklist, Day 1–7 runbook, welcome-пакет клиенту.
  - `docs/runbooks/` — R-01…R-11 (ransomware, access-loss, backup, 1С, AD, disk, SSL, VPN, password, patch, DR).
  - `docs/checklists/` — weekly/monthly/quarterly ритмы.
  - `docs/hiring/` + `docs/training/` — JD + screening + тест-задание + интервью + 12-недельная программа.
  - `deploy/` — nginx reverse-proxy, docker-compose, Vaultwarden.
  - `infra/terraform/` — Yandex Cloud baseline (VPC, landing, bastion, S3 бэкапов).
  - `technical/0_Common/` — Ansible playbooks (baseline/backup/patch), Prometheus+Alertmanager конфиги, WireGuard tenant-add и bootstrap скрипты, `dr_drill.sh`, `monthly_report.py`, `rotate_junior_access.sh`.
- `README.md` переписан под реальную структуру, каждый артефакт имеет ссылку.

---

## Содержание

- [С чего начать — 3 сценария (5 / 30 / 120 мин)](#с-чего-начать)
- [Быстрый старт (dev-окружение)](#быстрый-старт-dev-окружение)
- [Управление контентом лендинга](#управление-контентом-лендинга)
- [Структура репозитория](#структура-репозитория)
- [53 артефакта Марафона 3.1–3.5](#53-артефакта-марафона-3135)
- [Карта документов по ролям](#карта-документов-по-ролям)
- [Технический стек MSP](#технический-стек-msp)
- [Тарифы и юнит-экономика](#тарифы-и-юнит-экономика)
- [Roadmap (Этап 4 · 12 спринтов)](#roadmap-этап-4--12-спринтов)
- [Дорожная карта](#дорожная-карта-v40--v50)
- [Контроль качества (DoD)](#контроль-качества-dod)

---

## С чего начать

### Сценарий «5 минут» — понять, что это такое
1. Прочитать блок «Что нового в v4.1» (выше).
2. Посмотреть [Тарифы](#тарифы-и-юнит-экономика) и [Технический стек](#технический-стек-msp).
3. Открыть лендинг локально: см. [Быстрый старт](#быстрый-старт-dev-окружение).

### Сценарий «30 минут» — решить, готов ли я запускать
1. [`analysis/unit_economics.md`](analysis/unit_economics.md) — юниты по тарифам, маржа, LTV/CAC.
2. [`analysis/finmodel_m1_m24.md`](analysis/finmodel_m1_m24.md) — помесячная модель до break-even.
3. [`analysis/icp_profiles.md`](analysis/icp_profiles.md) — 3 ICP и анти-ICP.
4. [`docs/burnout_guard.md`](docs/burnout_guard.md) — до-старта: хард-лимиты собственника.

### Сценарий «120 минут» — погрузиться в продукт и план
1. Всё из «30 минут».
2. [`technical/README.md`](technical/README.md) → структура playbook.
3. [`technical/1_Bronze/Bronze.md`](technical/1_Bronze/Bronze.md) → мастер-гайд минимального тарифа.
4. [`docs/onboarding/day_1_7_runbook.md`](docs/onboarding/day_1_7_runbook.md) → как выглядит первая неделя с клиентом.
5. [`docs/runbooks/README.md`](docs/runbooks/README.md) → 11 инцидентных runbook'ов.
6. [`contracts/contract_bronze.html`](contracts/contract_bronze.html) → договор с клиентом.
7. Раздел [53 артефакта Марафона](#53-артефакта-марафона-3135) — полный список с ссылками.

### «Я хочу запустить продажи в течение 4 недель»

Критический путь:
1. **Security P0:** прошить `backend/.env` на основе [`backend/.env.example`](backend/.env.example); код v4.1 уже содержит rate-limit, consent, honeypot и опциональный SmartCaptcha.
2. **Инфра:** `terraform apply` в [`infra/terraform/`](infra/terraform/) → bastion + landing в Yandex Cloud. Потом `ansible-playbook` из [`technical/0_Common/ansible/`](technical/0_Common/ansible/).
3. **Лендинг:** опубликовать с рабочей формой. Юридика — [`frontend/public/docs/privacy.html`](frontend/public/docs/privacy.html), [`offer.html`](frontend/public/docs/offer.html), [`sla.html`](frontend/public/docs/sla.html).
4. **Первые продажи:** открыть [`docs/sales/funnel_6_stages.md`](docs/sales/funnel_6_stages.md) и [`bant_q_script.md`](docs/sales/bant_q_script.md). Использовать [`email_templates.md`](docs/sales/email_templates.md) для HH-перехвата и 1С-партнёров.
5. **Weekly discipline:** [`docs/checklists/weekly.md`](docs/checklists/weekly.md) — каждую пятницу.

---

## Быстрый старт (dev-окружение)

### 0. MongoDB (контейнером)

```bash
# Один раз создаём контейнер (переживёт ребут благодаря --restart=always):
docker run -d --name mspshield-mongo --restart=always -p 27017:27017 mongo:7
# Если уже создавали — просто:
docker start mspshield-mongo
```
Без этого backend стартует, но падает с `Connection refused: localhost:27017`,
а форма на лендинге отдаёт «Не удалось отправить».

### 1. Backend (FastAPI + MongoDB)

```bash
cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # ВАЖНО: заполни ADMIN_TOKEN через openssl rand -hex 32
# Запусти локальный MongoDB (docker run -d -p 27017:27017 mongo:7)
uvicorn server:app --host 0.0.0.0 --port 8001 --reload
```

**Переменные окружения** описаны полностью в [`backend/.env.example`](backend/.env.example):

| Переменная | Обязательно | Назначение |
|---|---|---|
| `MONGO_URL` | да | URI MongoDB (`mongodb://localhost:27017`) |
| `DB_NAME` | да | Имя базы (`mspshield`) |
| `ADMIN_TOKEN` | для `/leads`, `/stats` | `openssl rand -hex 32` |
| `CORS_ORIGINS` | prod | CSV явных origins; **нельзя `*` в prod** |
| `TG_BOT_TOKEN` / `TG_CHAT_ID` | опц. | Telegram-бот для уведомлений о лидах |
| `MAX_BOT_TOKEN` / `MAX_ALERT_CHAT_ID` / `MAX_WEBHOOK_SECRET` / `MAX_BOT_USERNAME` | опц. | MAX-бот ([@MasterBot](https://max.ru), бесплатный официальный Bot API). См. [`docs/MAX_SETUP.md`](docs/MAX_SETUP.md) |
| `ALERT_CHANNELS` | опц. | Каналы fan-out для алёртов: `max,telegram` (по умолчанию — оба, если оба настроены) |
| `ALERTMANAGER_WEBHOOK_TOKEN` | опц. | Bearer-токен для `POST /api/alerts/alertmanager` (см. [`deploy/alertmanager/alertmanager.yml`](deploy/alertmanager/alertmanager.yml)) |
| `RATE_LIMIT_PER_MIN` | опц. | Per-IP лимит POST /api/leads (default 10) |
| `RATE_LIMIT_WINDOW_SEC` | опц. | Окно rate-limit (default 60s) |
| `SMARTCAPTCHA_SERVER_KEY` | prod рекомендуется | Yandex SmartCaptcha server-side verify |
| `SMARTCAPTCHA_VERIFY_URL` | опц. | Override верификационного endpoint'а |

> v4.1 уже содержит security-патчи, P0-блокеры закрыты.

### 2. Frontend (React + Tailwind)

```bash
cd frontend
cp .env.example .env  # содержит REACT_APP_BACKEND_URL=http://localhost:8001
yarn install
yarn start            # http://localhost:3000
```

**Важно:** `frontend/.env` читается CRA **только при старте**. После любых
правок переменных — перезапускай `yarn start`, иначе они не подхватятся.
Если открываешь сайт с другой машины (`http://192.168.x.x:3000`) —
поправь `REACT_APP_BACKEND_URL=http://192.168.x.x:8001` и подними
backend как `--host 0.0.0.0`.

### 3. Проверка API

```bash
curl http://localhost:8001/api/health
# {"status":"ok","db":"connected"}

curl -X POST http://localhost:8001/api/leads \
  -H 'Content-Type: application/json' \
  -d '{"name":"Иван","company":"ООО","contact":"@ivan","servers":"4-10","consent":true}'
```

### 4. Админ-панель

```
http://localhost:3000/admin/leads         — таблица заявок (CSV, фильтры, Kaiten)
http://localhost:3000/admin/landing-edit  — UI-конфигуратор лендинга (тексты, тарифы, иконки)
Header: X-Admin-Token: <ADMIN_TOKEN>       — для curl/CLI; в браузере вход по паролю → JWT 24ч
```

Конфигуратор и порядок применения правок описаны в разделе
[«Управление контентом лендинга»](#управление-контентом-лендинга) ниже
и в [`docs/EDITING.md`](docs/EDITING.md).

### 5. Prometheus /metrics

```
curl http://localhost:8001/metrics
# mspshield_leads_total{tariff="silver",source="landing"} 3
# mspshield_leads_rejected_total{reason="honeypot"} 1
```

### 6. Тесты

```bash
cd backend
pytest tests/ -v           # backend-уровневые (интеграционные, требуют поднятого API)
```

---

## Управление контентом лендинга

Весь редактируемый контент лендинга (заголовки, тарифы, FAQ, иконки,
ссылки в шапке/футере) лежит в **одном JSON-файле** —
[`frontend/src/content/landing.ru.json`](frontend/src/content/landing.ru.json).
React-компоненты читают его через хук
[`useContent.js`](frontend/src/content/useContent.js); хардкода текстов
в JSX нет. **Чтобы поменять копию — меняйте JSON, не код.**

### Два способа редактирования

| Способ | Кому удобно | Как сохранить на прод |
|---|---|---|
| **UI-конфигуратор** `/admin/landing-edit` (страница [`AdminLandingEdit.jsx`](frontend/src/pages/AdminLandingEdit.jsx)) | Маркетинг / собственник без знания React | Внутри UI кнопка **«Скачать landing.ru.json»** → положить файл в `frontend/src/content/landing.ru.json` → коммит + push |
| **Прямая правка JSON** в редакторе/IDE | Разработчик, массовые правки, рефакторинг иконок/тарифов | `git commit` + `git push` |

**Live-preview:** правки в UI пишутся в `localStorage["msp_landing_override"]`
и мгновенно отображаются в iframe-превью справа. Это видно **только в
вашем браузере**. Чтобы изменения увидели посетители — нужно зафиксировать
JSON в репозитории (см. ниже).

### Где конфиги на сервере (production)

Зависит от выбранного пути деплоя:

| Путь деплоя | Корень приложения на VM | Файл контента | Применение изменений |
|---|---|---|---|
| **Path A** — `deploy/yandex/` (Caddy + Docker, single-VM, см. [`deploy/yandex/README.md`](deploy/yandex/README.md)) | `/opt/msp/Newbie/` | `/opt/msp/Newbie/frontend/src/content/landing.ru.json` | `cd /opt/msp/Newbie && git pull && cd frontend && yarn build && docker compose -f deploy/yandex/docker-compose.yml up -d --build frontend` |
| **Path B** — Terraform + Ansible + nginx (см. [`docs/deployment/landing_production.md`](docs/deployment/landing_production.md), [`docs/JUNIOR_GUIDE.md §3.4`](docs/JUNIOR_GUIDE.md)) | `/home/mspshield/app/` | `/home/mspshield/app/frontend/src/content/landing.ru.json` | `cd /home/mspshield/app && git pull && cd frontend && yarn build && sudo rsync -a --delete build/ /var/www/mspshield/` |

В обоих случаях источник истины — Git. **На сервер не редактируем JSON
руками** — иначе следующий `git pull` затрёт правки. Любая правка идёт
через репозиторий → пересборка фронта → деплой.

### Что НЕ редактируется через JSON

- Цвета и шрифты → `frontend/src/index.css` (CSS custom properties, см. [`docs/EDITING.md §6`](docs/EDITING.md)).
- Каталог иконок → `frontend/src/components/icons/` (см. [`docs/EDITING.md §5`](docs/EDITING.md)).
- Favicon / og:image → `frontend/public/`.
- Формула калькулятора простоя → `frontend/src/components/sections/Pain.jsx`.
- Логика формы / backend / email-уведомления → `backend/.env` и `backend/server.py`.

### Полное руководство

[`docs/EDITING.md`](docs/EDITING.md) — 487 строк: архитектура, пошаговая
работа через UI, схема JSON по секциям, как добавить тариф, как заменить
иконку, цвета, деплой, FAQ редактора и чек-лист «сделал — не сломал».

---

## Структура репозитория

```
Newbie/ (MSPShield v4.1)
│
├── README.md                       ← вы здесь
├── CHANGELOG.md                    история версий
│
├── frontend/                       React 19 SPA-лендинг + админ-панель
│   ├── public/
│   │   ├── index.html              meta + OG + JSON-LD (LocalBusiness, FAQPage)
│   │   └── docs/
│   │       ├── privacy.html        152-ФЗ Политика обработки ПДн
│   │       ├── offer.html          Публичная оферта
│   │       └── sla.html            SLA
│   ├── src/
│   │   ├── content/
│   │   │   ├── landing.ru.json     ← весь редактируемый контент (см. docs/EDITING.md)
│   │   │   ├── landing.schema.json JSON Schema для валидации
│   │   │   └── useContent.js       хук + deep-merge с localStorage override
│   │   ├── pages/                  Landing, AdminLeads, AdminLandingEdit, NotFound
│   │   └── components/sections/
│   │       ├── Hero, Pain, HowItWorks, ForWhom, Compliance,
│   │       ├── Compare, Pricing, Process, Tools, Cases, FAQ
│   │       └── CTAForm.jsx         форма + consent + honeypot + SmartCaptcha
│   └── package.json
│
├── backend/                        FastAPI 0.110 + Motor/MongoDB
│   ├── server.py                   /api/{health,leads,stats,...} + /metrics
│   ├── requirements.txt
│   ├── .env.example                шаблон переменных
│   └── tests/test_mspshield_api.py
│
├── analysis/                       рынок + юнит-экономика
│   ├── unit_economics.md           юниты Bronze/Silver/Gold
│   ├── cac_model.md                CAC 3 каналов (HH, 1C, контент)
│   ├── ltv_model.md                LTV 36mo, churn, NRR
│   ├── finmodel_m1_m24.md          финмодель M1–M24 + break-even
│   ├── icp_profiles.md             3 ICP + анти-ICP + скоринг
│   ├── addon_catalog.md            каталог разовых работ (общие + tier-specific)
│   ├── discount_policy.md          политика скидок (max 10%)
│   └── market_analysis.md          анализ рынка MSP в РФ (редакция 2026)
│
├── docs/
│   ├── burnout_guard.md            лимиты собственника
│   ├── post_mortem_template.md     blameless post-mortem
│   ├── landing/
│   │   ├── seo_strategy.md         4 кластера + 12 статей
│   │   ├── ab_testing.md           8 гипотез + процесс
│   │   ├── blog_plan.md            12 конкретных статей M1–M6
│   │   └── yandex_metrika_goals.md 6 целей воронки
│   ├── sales/
│   │   ├── funnel_6_stages.md      воронка 6 стадий
│   │   ├── bant_q_script.md        скрипт квалификации + scoring
│   │   └── email_templates.md      7 email-шаблонов
│   ├── onboarding/
│   │   ├── pre_onboarding_checklist.md
│   │   ├── day_1_7_runbook.md
│   │   └── welcome_package.md
│   ├── runbooks/
│   │   ├── README.md               индекс + шаблон
│   │   ├── R-01.md Ransomware
│   │   ├── R-02.md Потеря доступа к серверу
│   │   ├── R-03.md Backup failed/corrupt
│   │   ├── R-04.md 1С не запускается/тормозит
│   │   ├── R-05.md AD replication failure
│   │   ├── R-06.md Disk space critical
│   │   ├── R-07.md SSL expired
│   │   ├── R-08.md VPN/WireGuard down
│   │   ├── R-09.md User password reset
│   │   ├── R-10.md Monthly patch window
│   │   └── R-11.md DR drill (quarterly)
│   ├── checklists/
│   │   ├── weekly.md
│   │   ├── monthly.md
│   │   └── quarterly.md
│   ├── hiring/
│   │   ├── junior_jd.md
│   │   ├── screening_call.md
│   │   ├── test_task.md
│   │   ├── technical_interview.md
│   │   └── offer_and_ndca.md
│   ├── training/
│   │   ├── README.md               12-недельная программа
│   │   └── week_01.md … week_12.md
│   └── COMPLIANCE.md               152-ФЗ, импортозамещение, статус оператора ПДн
│
├── contracts/                      договоры клиент/MSP
│   ├── contract_bronze.html
│   ├── contract_silver.html
│   └── contract_gold.html
│
├── deploy/
│   ├── docker-compose.yml          dev/staging стенд
│   ├── Dockerfile.backend
│   ├── Dockerfile.frontend
│   ├── nginx/mspshield.conf        prod reverse-proxy (SSL, CSP, rate-limit)
│   └── vaultwarden/                secret store (compose + README)
│
├── infra/terraform/                Yandex Cloud baseline
│   ├── main.tf                     VPC, landing, bastion, S3 backups
│   ├── variables.tf
│   ├── cloud-init/                 bootstrap скрипты VM
│   └── README.md
│
├── technical/
│   ├── README.md
│   ├── BUSINESS_MODEL.md
│   ├── ADDONS.md
│   ├── SCALING.md
│   ├── 0_Common/                   общее для всех тарифов
│   │   ├── ansible/                inventory + playbooks (site/backup/patch)
│   │   ├── monitoring/             prometheus + rules + alertmanager
│   │   ├── wireguard/              bootstrap + tenant_add
│   │   ├── scripts/                dr_drill.sh, monthly_report.py,
│   │   │                           rotate_junior_access.sh, verify_all.sh
│   │   └── docker/…
│   ├── 1_Bronze/                   (1–5 серверов)
│   ├── 2_Silver/                   AD/GPO + Loki + Puppet (80–300 сотр.)
│   └── 3_Gold/                     Wazuh + KSC + compliance
│
└── infra/terraform/                Yandex Cloud baseline (landing + bastion)
```

---

## 53 артефакта Марафона 3.1–3.5

### 3.1 · Бизнес-модель (7)

| # | Артефакт | Файл |
|---|---|---|
| 1 | Юнит-экономика по тарифам | [`analysis/unit_economics.md`](analysis/unit_economics.md) |
| 2 | CAC по 3 каналам | [`analysis/cac_model.md`](analysis/cac_model.md) |
| 3 | LTV 36-мес + churn + NRR | [`analysis/ltv_model.md`](analysis/ltv_model.md) |
| 4 | Финмодель M1–M24 | [`analysis/finmodel_m1_m24.md`](analysis/finmodel_m1_m24.md) |
| 5 | 3 ICP-профиля + анти-ICP | [`analysis/icp_profiles.md`](analysis/icp_profiles.md) |
| 6 | Каталог ADDON-работ | [`analysis/addon_catalog.md`](analysis/addon_catalog.md) |
| 7 | Политика скидок | [`analysis/discount_policy.md`](analysis/discount_policy.md) |

### 3.2 · Лендинг и воронка (9)

| # | Артефакт | Файл |
|---|---|---|
| 8 | Форма заявки: consent + honeypot + SmartCaptcha | [`frontend/src/components/sections/CTAForm.jsx`](frontend/src/components/sections/CTAForm.jsx) |
| 9 | Meta + JSON-LD (LocalBusiness, FAQPage) | [`frontend/public/index.html`](frontend/public/index.html) |
| 10 | Политика обработки ПДн (152-ФЗ) | [`frontend/public/docs/privacy.html`](frontend/public/docs/privacy.html) |
| 11 | Публичная оферта | [`frontend/public/docs/offer.html`](frontend/public/docs/offer.html) |
| 12 | SLA | [`frontend/public/docs/sla.html`](frontend/public/docs/sla.html) |
| 13 | SEO-стратегия (4 кластера) | [`docs/landing/seo_strategy.md`](docs/landing/seo_strategy.md) |
| 14 | A/B-тестирование (8 гипотез) | [`docs/landing/ab_testing.md`](docs/landing/ab_testing.md) |
| 15 | Blog-план M1–M6 (12 статей) | [`docs/landing/blog_plan.md`](docs/landing/blog_plan.md) |
| 16 | Цели Яндекс.Метрики | [`docs/landing/yandex_metrika_goals.md`](docs/landing/yandex_metrika_goals.md) |

### 3.3 · Операции (22)

| # | Артефакт | Файл |
|---|---|---|
| 17 | Воронка 6 стадий | [`docs/sales/funnel_6_stages.md`](docs/sales/funnel_6_stages.md) |
| 18 | BANT-Q скрипт | [`docs/sales/bant_q_script.md`](docs/sales/bant_q_script.md) |
| 19 | Email-шаблоны (7 штук) | [`docs/sales/email_templates.md`](docs/sales/email_templates.md) |
| 20 | Pre-onboarding checklist | [`docs/onboarding/pre_onboarding_checklist.md`](docs/onboarding/pre_onboarding_checklist.md) |
| 21 | Day 1–7 onboarding runbook | [`docs/onboarding/day_1_7_runbook.md`](docs/onboarding/day_1_7_runbook.md) |
| 22 | Welcome-пакет клиенту | [`docs/onboarding/welcome_package.md`](docs/onboarding/welcome_package.md) |
| 23 | Индекс runbook'ов | [`docs/runbooks/README.md`](docs/runbooks/README.md) |
| 24 | R-01 Ransomware | [`docs/runbooks/R-01.md`](docs/runbooks/R-01.md) |
| 25 | R-02 Потеря доступа | [`docs/runbooks/R-02.md`](docs/runbooks/R-02.md) |
| 26 | R-03 Backup failed | [`docs/runbooks/R-03.md`](docs/runbooks/R-03.md) |
| 27 | R-04 1С проблемы | [`docs/runbooks/R-04.md`](docs/runbooks/R-04.md) |
| 28 | R-05 AD replication | [`docs/runbooks/R-05.md`](docs/runbooks/R-05.md) |
| 29 | R-06 Disk critical | [`docs/runbooks/R-06.md`](docs/runbooks/R-06.md) |
| 30 | R-07 SSL expired | [`docs/runbooks/R-07.md`](docs/runbooks/R-07.md) |
| 31 | R-08 VPN down | [`docs/runbooks/R-08.md`](docs/runbooks/R-08.md) |
| 32 | R-09 Password reset | [`docs/runbooks/R-09.md`](docs/runbooks/R-09.md) |
| 33 | R-10 Monthly patch | [`docs/runbooks/R-10.md`](docs/runbooks/R-10.md) |
| 34 | Weekly checklist | [`docs/checklists/weekly.md`](docs/checklists/weekly.md) |
| 35 | Monthly checklist | [`docs/checklists/monthly.md`](docs/checklists/monthly.md) |
| 36 | Quarterly checklist | [`docs/checklists/quarterly.md`](docs/checklists/quarterly.md) |
| 37 | Post-mortem шаблон | [`docs/post_mortem_template.md`](docs/post_mortem_template.md) |
| 38 | Burnout guard (лимиты) | [`docs/burnout_guard.md`](docs/burnout_guard.md) |

### 3.4 · Инфраструктура (9)

| # | Артефакт | Файл |
|---|---|---|
| 39 | Backend security (rate-limit, consent, honeypot, CAPTCHA, /metrics) | [`backend/server.py`](backend/server.py) |
| 40 | .env.example (все переменные) | [`backend/.env.example`](backend/.env.example) |
| 41 | Nginx prod-конфиг | [`deploy/nginx/mspshield.conf`](deploy/nginx/mspshield.conf) |
| 42 | Terraform Yandex Cloud baseline | [`infra/terraform/main.tf`](infra/terraform/main.tf) |
| 43 | Ansible playbook site.yml | [`technical/0_Common/ansible/playbooks/site.yml`](technical/0_Common/ansible/playbooks/site.yml) |
| 44 | WireGuard tenant_add.sh | [`technical/0_Common/wireguard/tenant_add.sh`](technical/0_Common/wireguard/tenant_add.sh) |
| 45 | Vaultwarden (deploy + README) | [`deploy/vaultwarden/docker-compose.yml`](deploy/vaultwarden/docker-compose.yml) |
| 46 | DR drill script | [`technical/0_Common/scripts/dr_drill.sh`](technical/0_Common/scripts/dr_drill.sh) |
| 47 | R-11 DR drill runbook | [`docs/runbooks/R-11.md`](docs/runbooks/R-11.md) |

### 3.5 · Найм и обучение (6 + 12 недель)

| # | Артефакт | Файл |
|---|---|---|
| 48 | Junior JD | [`docs/hiring/junior_jd.md`](docs/hiring/junior_jd.md) |
| 49 | Screening call | [`docs/hiring/screening_call.md`](docs/hiring/screening_call.md) |
| 50 | Test task | [`docs/hiring/test_task.md`](docs/hiring/test_task.md) |
| 51 | Technical interview | [`docs/hiring/technical_interview.md`](docs/hiring/technical_interview.md) |
| 52 | Offer + NDA + non-compete | [`docs/hiring/offer_and_ndca.md`](docs/hiring/offer_and_ndca.md) |
| 53 | 12-недельная программа обучения | [`docs/training/README.md`](docs/training/README.md) + `week_01.md`–`week_12.md` |
| 53b | Rotate junior access (promote/revoke/rotate) | [`technical/0_Common/scripts/rotate_junior_access.sh`](technical/0_Common/scripts/rotate_junior_access.sh) |

---

## Карта документов по ролям

| Я… | Начну с… | Затем… | Для глубины… |
|---|---|---|---|
| **собственник** (принимаю решения) | [README](README.md) → [unit_economics](analysis/unit_economics.md) | [finmodel](analysis/finmodel_m1_m24.md), [burnout_guard](docs/burnout_guard.md) | [BUSINESS_MODEL](technical/BUSINESS_MODEL.md), [SCALING](technical/SCALING.md) |
| **будущий клиент** (оцениваю услугу) | [privacy.html](frontend/public/docs/privacy.html), [offer.html](frontend/public/docs/offer.html), [sla.html](frontend/public/docs/sla.html) | [contract_bronze.html](contracts/contract_bronze.html), [welcome_package](docs/onboarding/welcome_package.md) | [COMPLIANCE](docs/COMPLIANCE.md) |
| **junior engineer** (нанят или обучается) | [training/README](docs/training/README.md), [week_01](docs/training/week_01.md) | [runbooks/README](docs/runbooks/README.md), [checklists/weekly](docs/checklists/weekly.md) | [deployment/troubleshooting](docs/deployment/troubleshooting.md) |
| **senior/owner on duty** | [runbooks/README](docs/runbooks/README.md), [post_mortem_template](docs/post_mortem_template.md) | Targeted R-01…R-11 | [monthly_report.py](technical/0_Common/scripts/monthly_report.py), [dr_drill.sh](technical/0_Common/scripts/dr_drill.sh) |
| **dev / DevOps** | [deploy/docker-compose](deploy/docker-compose.yml), [infra/terraform/README](infra/terraform/README.md) | [ansible/playbooks](technical/0_Common/ansible/playbooks/), [monitoring/prometheus.yml](technical/0_Common/monitoring/prometheus.yml) | [nginx/mspshield.conf](deploy/nginx/mspshield.conf) |
| **юрист / compliance** | [privacy](frontend/public/docs/privacy.html), [offer](frontend/public/docs/offer.html) | [contracts/](contracts/), [COMPLIANCE](docs/COMPLIANCE.md) | [offer_and_ndca](docs/hiring/offer_and_ndca.md) |
| **marketer / sales** | [funnel_6_stages](docs/sales/funnel_6_stages.md) | [bant_q_script](docs/sales/bant_q_script.md), [email_templates](docs/sales/email_templates.md) | [seo_strategy](docs/landing/seo_strategy.md), [ab_testing](docs/landing/ab_testing.md) |

---

## Технический стек MSP

| Слой | Технологии | Ответственный артефакт |
|---|---|---|
| **Frontend** | React 19, React Router, Tailwind, shadcn/ui | [frontend/](frontend/) |
| **Backend** | FastAPI 0.110, Motor (async MongoDB), Pydantic v2 | [backend/server.py](backend/server.py) |
| **База данных** | MongoDB 7 | [deploy/docker-compose.yml](deploy/docker-compose.yml) |
| **Реверс-прокси** | Nginx + Let's Encrypt | [deploy/nginx/mspshield.conf](deploy/nginx/mspshield.conf) |
| **Облако** | Yandex Cloud (VPC + Compute + Object Storage) | [infra/terraform/main.tf](infra/terraform/main.tf) |
| **VPN** | WireGuard (per-tenant overlay) | [technical/0_Common/wireguard/](technical/0_Common/wireguard/) |
| **Monitoring** | Prometheus + Grafana + Alertmanager + Loki (Silver+) + Wazuh (Gold) | [technical/0_Common/monitoring/](technical/0_Common/monitoring/) |
| **Backup** | restic → Yandex Object Storage (S3) | [technical/0_Common/ansible/playbooks/backup_install.yml](technical/0_Common/ansible/playbooks/backup_install.yml) |
| **Automation** | Ansible (primary), Terraform (infra) | [technical/0_Common/ansible/](technical/0_Common/ansible/) |
| **Secrets** | Vaultwarden (self-hosted) | [deploy/vaultwarden/](deploy/vaultwarden/) |
| **Tickets/CRM** | Kaiten | — |
| **Captcha** | Yandex SmartCaptcha | [backend/server.py](backend/server.py) |

---

## Тарифы и юнит-экономика

| Тариф | Цена (₽/мес) | Серверов | SLA (P1) | Gross margin | LTV (36mo) |
|---|---:|---|---|---:|---:|
| **Bronze** | 25 000 | 1–5 | ≤ 4 ч | 89% | 750 000 |
| **Silver** | 50 000 | 6–15 | ≤ 2 ч | 87% | 1 500 000 |
| **Gold** | 85 000 | 16–30 | ≤ 1 ч, 24/7 | 74% | 2 250 000 |

Детали: [`analysis/unit_economics.md`](analysis/unit_economics.md), [`analysis/ltv_model.md`](analysis/ltv_model.md).

---

## Roadmap (Этап 4 · 12 спринтов)

После получения стратегических ответов (Q1–Q5 Этапа 5) добавлен раздел [`docs/roadmap/`](docs/roadmap/) с операционным планом запуска:

| Файл | Назначение |
|---|---|
| [`docs/roadmap/README.md`](docs/roadmap/README.md) | Индекс roadmap-документов + go/no-go триггеры |
| [`docs/roadmap/strategic_decisions.md`](docs/roadmap/strategic_decisions.md) | Ответы Q1–Q5 → binding-решения на 6 мес |
| [`docs/roadmap/etape_4_sprints.md`](docs/roadmap/etape_4_sprints.md) | 12 спринтов × 2 недели = 24 недели |
| [`docs/roadmap/wife_role.md`](docs/roadmap/wife_role.md) | Роль супруги (маркетинг + account mgmt), границы, оплата |
| [`docs/roadmap/budget_constraints.md`](docs/roadmap/budget_constraints.md) | OPEX ≤ 2 000 ₽/мес до первого клиента |
| [`contracts/wife_nda.md`](contracts/wife_nda.md) | Внутрисемейный NDA |

---

## Развёртывание (инструкции на русском)

Для запуска стека от локальной разработки до первого клиента в продакшене — см. [`docs/deployment/`](docs/deployment/):

| Файл | Назначение |
|---|---|
| [`docs/deployment/README.md`](docs/deployment/README.md) | Оглавление + архитектура в одной картинке + порядок этапов A/B/C |
| [`docs/deployment/local_dev.md`](docs/deployment/local_dev.md) | Этап A: локальный запуск через `docker compose up` (20 мин, 0 ₽) |
| [`docs/deployment/landing_production.md`](docs/deployment/landing_production.md) | Этап B: Terraform → WireGuard → Ansible → SSL → мониторинг (4–6 ч) |
| [`docs/deployment/tenant_onboarding.md`](docs/deployment/tenant_onboarding.md) | Этап C: онбординг нового клиента (Bronze/Silver/Gold) |
| [`docs/deployment/secrets_management.md`](docs/deployment/secrets_management.md) | Vaultwarden + правила работы с ключами/токенами |
| [`docs/deployment/disaster_recovery.md`](docs/deployment/disaster_recovery.md) | DR-сценарии: лендинг/bastion/MongoDB/полная потеря |
| [`docs/deployment/troubleshooting.md`](docs/deployment/troubleshooting.md) | Типовые ошибки (docker, terraform, ansible, wireguard, certbot) |

---

## Дорожная карта v4.0 → v5.0

- **v4.0** (merged) — README-only: стратегический план и навигация.
- **v4.1** (this release) — материализация всех 53 артефактов, security-патчи backend, инфра-шаблоны, полный playbook-pack.
- **v4.2** (план) — Этап 4: разложение 53 артефактов на 12 спринтов по 2 недели, календарь, backlog в Kaiten.
- **v4.3** (план) — Этап 5: стратегические ответы собственника (форма, P1, stop-loss, первый канал, партнёр) → уточнённые SOPs под реальный выбор.
- **v5.0** (план) — первый клиент онбординг-production, Junior нанят, первый квартальный monthly-report отправлен.

---

## Контроль качества (DoD)

- [x] Все 53 артефакта существуют в репозитории как реальные файлы.
- [x] README ссылается на каждый артефакт кликабельной ссылкой.
- [x] Backend содержит security-патчи: rate-limit, consent, honeypot, опциональный CAPTCHA.
- [x] `.env.example` покрывает все переменные.
- [x] Terraform + Ansible в состоянии «готов к `apply` после заполнения tfvars».
- [x] Runbooks R-01…R-11 имеют единую структуру (trigger → diagnosis → action → verification → post-actions).
- [x] 12-недельная программа обучения разложена по неделям с DoD на каждой.
- [ ] pytest зелёный — интеграционные тесты требуют поднятого API + MongoDB (`cd backend && pytest tests/ -v`). В рамках PR v4.1 не запускались (изолированного runner'а нет).
- [ ] Нагрузочные проверки — на v4.2.

---

*MSPShield — v4.1 · 2026-04*
