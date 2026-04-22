# MSPShield v4.0

> **Managed IT Services для СМБ в РФ · 2026.**
> Мониторинг 24/7 · Автоматические бэкапы · Реакция по SLA · 152-ФЗ · Импортозамещение.

Полный пакет для запуска MSP-бизнеса с нуля до первых клиентов:
**продукт** (React + FastAPI + MongoDB), **playbook развёртывания**
(Bronze / Silver / Gold), **договоры**, **операционные регламенты**
и **стратегия go-to-market** (Марафон 3.1–3.5).

**Что нового в v4.0 (vs v3.1):**
- Приведён в порядок и структурирован **стратегический план продаж и внедрения** (этапы 3.1–3.5).
- README переписан как **пошаговый гид**: с чего начать → куда смотреть → что делать дальше.
- Роадмап v4.0 выровнен под **реальные 53 артефакта** из марафона.
- Добавлен раздел навигации по стратегическим решениям (тарифы, CAC/LTV, инфра, найм junior).

---

## Содержание

- [С чего начать — 3 сценария (5 / 30 / 120 мин)](#с-чего-начать)
- [Быстрый старт (dev-окружение)](#быстрый-старт-dev-окружение)
- [Структура репозитория](#структура-репозитория)
- [Карта документов по ролям](#карта-документов-по-ролям)
- [Технический стек MSP](#технический-стек-msp)
- [Тарифы и юнит-экономика](#тарифы-и-юнит-экономика)
- [Стратегический план (Марафон 3.1–3.5)](#стратегический-план-марафон-3135)
- [Дорожная карта v4.0 → v5.0](#дорожная-карта-v40--v50)
- [Контроль качества (DoD)](#контроль-качества-dod)

---

## С чего начать

### Сценарий «5 минут» — понять, что это такое
1. Прочитать блок «Что нового в v4.0» (выше).
2. Посмотреть [Тарифы](#тарифы-и-юнит-экономика) и [Технический стек](#технический-стек-msp).
3. Открыть лендинг локально: см. [Быстрый старт](#быстрый-старт-dev-окружение).

### Сценарий «30 минут» — решить, готов ли я запускать
1. `analysis/market_analysis.md` — рынок РФ 2026 + воронка + юнит-экономика.
2. `technical/BUSINESS_MODEL.md` — модель оплаты и маржи по тарифам.
3. `docs/OPERATIONS.md` — как выглядит один день работы MSP.
4. `docs/COMPLIANCE.md` — 152-ФЗ и обязательные документы перед запуском.

### Сценарий «120 минут» — погрузиться в продукт и план
1. Всё из «30 минут».
2. `technical/README.md` → структура всего playbook.
3. `technical/1_Bronze/Bronze.md` → полный гайд Bronze (минимальный тариф).
4. `contracts/contract_bronze.html` → примерный договор с клиентом.
5. `technical/Junior/junior_training.md` → план обучения сотрудника L1.
6. Раздел [Стратегический план (Марафон 3.1–3.5)](#стратегический-план-марафон-3135) ниже — список 53 артефактов с приоритетами.

### «Я хочу запустить продажи в течение 4 недель»
Иди по **Критическому пути** (см. раздел [Стратегический план](#стратегический-план-марафон-3135)):
1. Исправить **P0-блокеры** (CORS, ADMIN_TOKEN, rate-limit, 152-ФЗ consent, `.env.example`).
2. Развернуть **Bastion + WireGuard** (Yandex Cloud).
3. Опубликовать **лендинг** с рабочей формой + SmartCaptcha + честной юридикой (privacy/offer/sla).
4. Запустить **1-й канал продаж** (HH-перехват + контент на Habr).

Детали и checklist — в разделе [Стратегический план](#стратегический-план-марафон-3135).

---

## Быстрый старт (dev-окружение)

### 1. Backend (FastAPI + MongoDB)

```bash
cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # ВАЖНО: заполни ADMIN_TOKEN через openssl rand -hex 32
# Запусти локальный MongoDB (docker run -d -p 27017:27017 mongo:7)
uvicorn server:app --host 0.0.0.0 --port 8001 --reload
```

**Переменные окружения (`backend/.env`):**

| Переменная | Обязательно | Назначение |
|---|---|---|
| `MONGO_URL` | да | URI MongoDB (`mongodb://localhost:27017`) |
| `DB_NAME` | да | Имя базы (`mspshield`) |
| `ADMIN_TOKEN` | для `/leads`, `/stats` | Защита админ-эндпоинтов. Genrate: `openssl rand -hex 32` |
| `CORS_ORIGINS` | prod обязательно | CSV explicit origins. В production **нельзя `*`** |
| `TG_BOT_TOKEN` | опц. | Telegram-бот для алертов о лидах |
| `TG_CHAT_ID` | опц. | ID чата получателя |
| `RATE_LIMIT_LEADS_PER_MIN` | опц. | Лимит POST /leads с одного IP (default 3) |
| `SMARTCAPTCHA_SERVER_KEY` | prod обязательно | Yandex SmartCaptcha (анти-спам) |

> **P0-блокеры security в текущем коде** (см. план Этапа 3.4 Блок А): CORS дефолт `*`,
> нет rate-limit, нет CAPTCHA, нет consent-поля. Фикс запланирован в v4.1.

### 2. Frontend (React + Tailwind)

```bash
cd frontend
yarn install
# REACT_APP_BACKEND_URL в frontend/.env указывает на backend
yarn start                       # http://localhost:3000
```

### 3. Проверка API

```bash
curl http://localhost:8001/api/health
# {"status":"ok","db":"connected"}

curl -X POST http://localhost:8001/api/leads \
  -H 'Content-Type: application/json' \
  -d '{"name":"Иван","company":"ООО","contact":"@ivan","servers":"4-10"}'
```

### 4. Админ-панель

```
http://localhost:3000/admin/leads
Header: X-Admin-Token: <ADMIN_TOKEN>
```

### 5. Тесты

```bash
cd backend
TEST_ADMIN_TOKEN=test-123 pytest tests/ -v
```

---

## Структура репозитория

```
Newbie/ (MSPShield v4.0)
│
├── README.md                      ← вы здесь (стартовая точка)
│
├── frontend/                      React SPA-лендинг + админ-панель
│   ├── public/
│   │   └── index.html             meta-tags, OG, JSON-LD (план 3.2 Блок В)
│   ├── src/
│   │   ├── pages/
│   │   │   ├── Landing.jsx        главная страница
│   │   │   ├── AdminLeads.jsx     /admin/leads (требует X-Admin-Token)
│   │   │   └── NotFound.jsx
│   │   ├── components/
│   │   │   ├── sections/          12 секций лендинга
│   │   │   │   ├── Hero.jsx
│   │   │   │   ├── Pain.jsx       ROI-калькулятор
│   │   │   │   ├── HowItWorks.jsx
│   │   │   │   ├── ForWhom.jsx
│   │   │   │   ├── Compliance.jsx
│   │   │   │   ├── Compare.jsx
│   │   │   │   ├── Pricing.jsx
│   │   │   │   ├── Process.jsx
│   │   │   │   ├── Tools.jsx
│   │   │   │   ├── Cases.jsx
│   │   │   │   ├── FAQ.jsx
│   │   │   │   └── CTAForm.jsx    форма заявки (план: +consent +honeypot +captcha)
│   │   │   └── ui/                shadcn/ui
│   │   ├── hooks/
│   │   ├── lib/
│   │   └── App.js
│   └── package.json
│
├── backend/                       FastAPI + MongoDB
│   ├── server.py                  /api/health · /api/leads · /api/stats · /metrics
│   ├── requirements.txt
│   └── tests/
│       └── test_mspshield_api.py
│
├── technical/                     Playbook развёртывания MSP
│   ├── README.md                  навигация по техническому стеку
│   ├── BUSINESS_MODEL.md          тарифная модель + маржа + ценообразование
│   ├── ADDONS.md                  каталог ADDON-проектов (разовые работы)
│   ├── SCALING.md                 сценарии масштабирования (1 → 5 → 20 клиентов)
│   │
│   ├── 0_Common/                  общее для всех тарифов
│   │   ├── docker/                docker-compose стеки (monitoring, osTicket, Wazuh)
│   │   ├── prometheus/            базовая конфигурация Prometheus
│   │   ├── grafana/               дашборды, provisioning
│   │   ├── alertmanager/          правила маршрутизации
│   │   ├── wireguard/             шаблоны tenant-per-client
│   │   ├── scripts/               verify_restic.sh, provision
│   │   └── SERVICES/              деплой-инструкции по сервисам
│   │
│   ├── 1_Bronze/                  минимальный тариф (1–5 серверов)
│   │   ├── Bronze.md              мастер-гайд
│   │   ├── CLIENT/                то, что видит клиент (SLA, welcome)
│   │   └── EXECUTOR/              playbook для executor'а
│   │       ├── SOP_executor_bronze.md
│   │       ├── prometheus/        prometheus.yml + rules
│   │       ├── grafana/
│   │       ├── alertmanager/
│   │       ├── wireguard/
│   │       └── scripts/
│   │
│   ├── 2_Silver/                  AD/GPO + Loki + Puppet (80–300 сотр.)
│   │   ├── Silver.md
│   │   ├── CLIENT/
│   │   └── EXECUTOR/              + ansible, puppet, loki, ad/gpo
│   │
│   ├── 3_Gold/                    compliance + Wazuh + KSC (регулируемые ИС)
│   │   ├── Gold.md
│   │   ├── SOP_gold_complete.md
│   │   ├── CLIENT/
│   │   └── EXECUTOR/              + wazuh, ksc, osticket
│   │
│   └── Junior/                    программа обучения (L1/L2/L3)
│       ├── junior_training.md     12-недельный план (план 3.5 Блок Б)
│       ├── ONBOARDING.md
│       ├── CHECKLISTS.md
│       ├── TROUBLESHOOTING.md
│       ├── vault_guide.md
│       ├── l1_bronze/
│       ├── l2_silver/
│       └── l3_gold/
│
├── contracts/                     договоры с клиентами
│   ├── README.md
│   ├── contract_bronze.html
│   ├── contract_silver.html
│   └── contract_gold.html
│
├── analysis/                      рынок, воронка, ценообразование
│   ├── market_analysis.md         РФ 2026 + ICP + CAC + LTV
│   └── market_analysis_original.md
│
├── docs/                          операционные и compliance-документы
│   ├── DEPLOYMENT.md              деплой лендинга и API в prod
│   ├── OPERATIONS.md              onboarding / incident / backup-verify
│   └── COMPLIANCE.md              152-ФЗ, импортозамещение, реестр ПО
│
├── memory/
│   └── PRD.md                     product requirements (предыдущая итерация)
│
├── test_reports/
│   └── pytest/                    отчёты CI
│
├── tests/
│   └── __init__.py                (placeholder под e2e-тесты v4.1)
│
├── .gitignore
├── .gitconfig
└── test_result.md                 ручной лог тестов релиза
```

---

## Карта документов по ролям

| Я… | Начну с… | Затем… | Для глубины… |
|---|---|---|---|
| **собственник** (принимаю решения) | `README.md` → [Стратегический план](#стратегический-план-марафон-3135) | `technical/BUSINESS_MODEL.md`, `analysis/market_analysis.md` | `technical/SCALING.md`, `technical/ADDONS.md` |
| **будущий клиент** (оцениваю услугу) | `README.md` → [Тарифы](#тарифы-и-юнит-экономика) | `contracts/contract_<tier>.html`, `technical/<tier>/CLIENT/` | `docs/COMPLIANCE.md` |
| **junior engineer** (нанят или обучается) | `technical/Junior/ONBOARDING.md` | `technical/Junior/junior_training.md`, `technical/Junior/CHECKLISTS.md` | `technical/Junior/TROUBLESHOOTING.md`, `technical/1_Bronze/EXECUTOR/SOP_executor_bronze.md` |
| **senior engineer** (дежурю, onboard'ю) | `docs/OPERATIONS.md` | `technical/<tier>/EXECUTOR/`, `technical/0_Common/scripts/` | `technical/0_Common/docker/`, runbooks (план 3.3 Блок В) |
| **разработчик** (трогаю код) | `backend/server.py`, `frontend/src/pages/Landing.jsx` | `backend/requirements.txt`, `frontend/package.json` | `backend/tests/`, `.env.example` |
| **юрист / безопасник** | `docs/COMPLIANCE.md` | `contracts/`, `technical/3_Gold/CLIENT/` | `technical/0_Common/wireguard/`, `technical/3_Gold/EXECUTOR/wazuh/` |
| **marketer / SEO** | [Стратегический план 3.2](#стратегический-план-марафон-3135) | `frontend/public/index.html`, `analysis/market_analysis.md` | план 3.2 Блок В (meta + JSON-LD) |

---

## Технический стек MSP

| Слой | Инструмент | Bronze | Silver | Gold |
|---|---|:-:|:-:|:-:|
| Метрики | Prometheus + Grafana | ✓ | ✓ | ✓ |
| Агенты Linux | node_exporter | ✓ | ✓ | ✓ |
| Агенты Windows | windows_exporter | ✓ | ✓ | ✓ |
| HTTP/TCP пробы | Blackbox Exporter | ✓ | ✓ | ✓ |
| Бэкапы | restic + Yandex S3 (3-2-1) | ✓ | ✓ | ✓ |
| VPN | WireGuard + Bastion (Yandex Cloud) | ✓ | ✓ | ✓ |
| Уведомления | Alertmanager → Telegram | ✓ | ✓ | ✓ |
| Логи | Loki + Promtail (multi-tenant) | — | ✓ | ✓ |
| Конфиг-менеджмент | Puppet Server + Agent | — | ✓ | ✓ |
| Автоматизация | Ansible | — | ✓ | ✓ |
| AD / DNS / GPO | Windows Native + скрипты | — | ✓ | ✓ |
| SIEM | Wazuh Manager + Indexer + Dashboard | — | — | ✓ |
| EDR | Kaspersky Security Center | — | — | ✓ |
| Service Desk | osTicket | — | — | ✓ |
| Secrets | Vaultwarden (self-hosted) | ✓ | ✓ | ✓ |
| Отечественные ОС | Astra Linux, РЕД ОС, ALT | ✓ | ✓ | ✓ |
| CRM / Wiki | Kaiten (РФ-реестр) + Яндекс 360 | ✓ | ✓ | ✓ |

> **Санкционная устойчивость:** вся инфраструктура развёрнута на РФ-резидентных
> сервисах (Yandex Cloud / Selectel / VK Cloud), с РФ-реестровым ПО как приоритетом.

---

## Тарифы и юнит-экономика

> Цены 2026 года. Финальная стоимость — функция числа серверов, SLA, compliance.

| Тариф | Цена/мес | Setup fee | SLA P1 | ICP |
|---|---|---|---|---|
| **Bronze** | от 25 000 ₽ | 15–25k ₽ | ≤ 4 ч раб. | 1–5 серверов, юристы/бухгалтеры 15–80 чел. |
| **Silver** | от 50 000 ₽ | 30–50k ₽ | ≤ 2 ч, 09–21 МСК | 80–300 сотр., AD/GPO, Win+Linux |
| **Gold** | от 85 000 ₽ | 45–80k ₽ | ≤ 1 ч, 24/7 | Compliance, 152-ФЗ, медицина/финансы |

**Ключевые показатели модели (подробности — в плане 3.1):**
- Gross margin: **Bronze 89% / Silver 87% / Gold 74%**
- Blended CAC (3 канала): **~22 000 ₽**
- LTV (cap 36 мес): **750k / 1.5M / 2.5M ₽**
- Target conversion lead→contract: **~6.7%**
- Target churn: **≤ 0.87%/мес**

Детали: [`analysis/market_analysis.md`](./analysis/market_analysis.md) · [`technical/BUSINESS_MODEL.md`](./technical/BUSINESS_MODEL.md)

---

## Стратегический план (Марафон 3.1–3.5)

**53 артефакта**, разложенных по 5 этапам. Приоритеты: 🔴 P0 (блокирует запуск) · 🟡 P1 (важно в 1-й месяц) · 🟢 P2 (по мере роста).

### Этап 3.1 · Бизнес-модель (артефакты 1–8)
- 3-tier pricing matrix · unit-economics модель · ICP для 3 сегментов ·
- CAC-модель · LTV с 36-мес cap · финмодель M1–M24 ·
- каталог 10 ADDON-проектов · политика скидок (max 10%, только годовая).

### Этап 3.2 · Лендинг (артефакты 9–20)
- H1 + stat-badges clickable · расширенная Pain с реальными числами ·
- **форма: consent checkbox + honeypot + SmartCaptcha** 🔴 ·
- meta-tags (title/description/OG/Twitter) · JSON-LD LocalBusiness ·
- `/docs/privacy.html`, `/offer.html`, `/sla.html` 🔴 ·
- Yandex.Metrika + webvisor · A/B hypothesis log · SEO-keywords · blog (10 SEO-статей).

### Этап 3.3 · Операции (артефакты 21–32)
- 6-stage sales funnel (Kaiten) · BANT-Q скрипт ·
- 4 email templates (outreach/follow-up/reject/nurture) ·
- pre-onboarding checklist · Day 1–7 runbook · welcome-package PDF ·
- `scripts/discovery.sh` · P1–P4 classifier + SLA ·
- **Top-10 runbooks** (R-01 … R-10) · post-mortem template ·
- weekly/monthly/quarterly checklists · burn-out guard.

### Этап 3.4 · Инфраструктура (артефакты 33–47)
- `backend/.env.example` 🔴 · backend security patch (CORS/rate-limit/consent/captcha/honeypot) 🔴 ·
- Nginx reverse-proxy + security headers 🔴 · backend `/metrics` ·
- Terraform Bastion (Yandex Cloud) 🔴 · WireGuard `tenant_add.sh` 🔴 ·
- Ansible inventory template + hardening role 🔴 ·
- Vaultwarden self-hosted · Prometheus `file_sd_configs` (multi-tenant) ·
- Grafana per-client folders + RBAC · Alertmanager multi-client routing ·
- DR-drill monthly script · Bastion DR runbook (R-11) ·
- Wazuh Gold stack (deferred to 1st Gold) · quarterly compliance audit.

### Этап 3.5 · Junior L1 (артефакты 48–53)
- Job description + 4-stage interview · paid test task (1 000 ₽) ·
- ГПХ договор + NDA · 12-недельный план обучения ·
- RACI-матрица · `rotate_junior_access.sh`.

### Критический путь запуска

| Период | Артефакты | Результат |
|---|---|---|
| T+0 → T+4 нед | 1–8, 15–17, 33–35, 37–38 | Бизнес-модель зафиксирована · лендинг безопасен · Bastion принимает клиентов |
| T+4 → T+8 нед | 21–28, 39, 41, 43 | Sales-процесс работает · onboarding формализован · live-monitoring |
| T+8 → T+16 нед | 29–32, 40, 42, 44–45, 48–53 | Runbooks · vault · DR · junior нанят |
| T+16+ | 46–47 | Gold-инфра по мере появления Gold-клиента |

**Полная матрица допущений и артефактов:** запрашивается по команде «Этап 4».

---

## Дорожная карта v4.0 → v5.0

### v4.0 (текущий релиз) — «стратегия закреплена»
- [x] React SPA-лендинг (12 секций)
- [x] FastAPI + MongoDB, админ-панель `/admin/leads`
- [x] ROI-калькулятор, Telegram-уведомления
- [x] Полный technical playbook (Bronze / Silver / Gold + Junior)
- [x] Договоры Bronze / Silver / Gold
- [x] **Стратегический план (марафон 3.1–3.5) закреплён в README**
- [x] Карта артефактов с приоритетами (P0/P1/P2)

### v4.1 (следующий спринт, 2 нед) — «P0-блокеры устранены»
- [ ] `backend/.env.example` + удаление `ADMIN_TOKEN` из кода тестов
- [ ] CORS без `*` + rate-limit + honeypot в `POST /leads`
- [ ] Поле `consent` (152-ФЗ) в `LeadCreate` + фиксация `consent_at`
- [ ] `/docs/privacy.html`, `/offer.html`, `/sla.html` — статические страницы
- [ ] Интеграция Yandex SmartCaptcha на фронте и валидация на бэке
- [ ] `/metrics` endpoint (prometheus_client)
- [ ] Nginx reverse-proxy с HSTS и CSP (deploy/nginx.conf)

### v4.2 (месяц 1) — «инфра готова принимать клиента»
- [ ] Terraform Bastion в Yandex Cloud
- [ ] WireGuard multi-tenant (`tenant_add.sh`)
- [ ] Ansible hardening role + inventory template
- [ ] Prometheus `file_sd_configs` + Grafana per-client folders
- [ ] Vaultwarden self-hosted

### v4.3 (месяц 2) — «первый клиент онбордится»
- [ ] Top-10 runbooks (R-01 … R-10)
- [ ] Post-mortem workflow
- [ ] Kaiten CRM + Wiki (замена Notion — в реестре ПО)
- [ ] DR-drill monthly script
- [ ] Sales templates (outreach / follow-up / reject / nurture)

### v5.0 (месяц 4–6) — «готов к масштабированию»
- [ ] Junior нанят и в onboarding-процессе
- [ ] 3+ активных клиента, ≥ 110 000 ₽ MRR
- [ ] Wazuh Gold-stack подключён (1-й Gold)
- [ ] English-версия лендинга (для экспортных контрактов)
- [ ] amoCRM / Битрикс24 sync (либо Kaiten-native)
- [ ] Онлайн-оплата (ЮKassa / СБП)

---

## Контроль качества (DoD)

Перед тегом очередного релиза проверять:

| Критерий | Команда / ссылка |
|---|---|
| Backend тесты зелёные | `cd backend && TEST_ADMIN_TOKEN=test pytest -v` |
| Frontend билдится | `cd frontend && yarn build` |
| Lint чистый (frontend) | `cd frontend && yarn lint` (если сконфигурен) |
| Нет секретов в git-history | `git log -p | grep -iE 'token|password|secret'` (ручная проверка) |
| `.env.example` актуален | сравнить с `server.py` |
| CORS не `*` в prod-деплое | проверить `backend/.env` |
| README отражает реальность | diff между секциями и кодом |
| Security-headers на prod-лендинге | https://securityheaders.com/?q=mspshield.ru (цель: A+) |
| JSON-LD валиден | https://validator.schema.org/ |

---

## Лицензия и использование

Частный проект. Репозиторий **закрыт для внешнего использования без
письменного согласия автора**. Клонирование для форка/коммерческого
использования третьими лицами не допускается.

Контакты по сотрудничеству — через `hello@mspshield.ru` (в процессе активации).

---

## Changelog

- **v4.0** (2026-04) — стратегический план 3.1–3.5 зафиксирован в репо; README переписан.
- **v3.1** (2026-04) — админ-панель, Telegram-уведомления, 5 новых секций лендинга.
- **v3.0** — полный technical playbook (Bronze/Silver/Gold) + договоры.
- **v2.x** — FastAPI backend + React SPA.
- **v1.x** — MVP-прототип.
