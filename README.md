# MSPShield v3.1

> **Managed IT Services для бизнеса в РФ.**
> Мониторинг 24/7 · Автоматические бэкапы · Реакция по SLA · 152-ФЗ.

Веб-платформа (React + FastAPI + MongoDB) с посадочной страницей, ROI-калькулятором
и админ-панелью заявок. Плюс полный технический playbook развёртывания MSP
(Bronze / Silver / Gold) и комплект документов.

---

## Содержание

- [Что внутри](#что-внутри)
- [Быстрый старт](#быстрый-старт)
- [Структура репозитория](#структура-репозитория)
- [Технический стек MSP](#технический-стек-msp)
- [Тарифы](#тарифы)
- [Документация](#документация)
- [Дорожная карта](#дорожная-карта)

---

## Что внутри

| Компонент | Назначение |
|---|---|
| `frontend/` | React-лендинг, калькулятор простоя, форма заявки, админ-панель |
| `backend/` | FastAPI + MongoDB — приём лидов, статистика, админ-API, Telegram-уведомления |
| `technical/` | Playbook развёртывания MSP: Bronze / Silver / Gold + Junior training |
| `contracts/` | Шаблоны договоров (Bronze / Silver / Gold) + приложения SLA |
| `analysis/` | Анализ рынка РФ 2026, юнит-экономика, воронка продаж |
| `docs/` | Operations, Deployment, Compliance (152-ФЗ) |

---

## Быстрый старт

### 1. Backend

```bash
cd backend
pip install -r requirements.txt
cp .env.example .env        # при необходимости
# Заполнить ADMIN_TOKEN и (опционально) TG_BOT_TOKEN / TG_CHAT_ID
uvicorn server:app --host 0.0.0.0 --port 8001 --reload
```

**Переменные окружения** (`backend/.env`):

| Переменная | Обязательно | Назначение |
|---|---|---|
| `MONGO_URL` | да | URI MongoDB |
| `DB_NAME` | да | Имя базы |
| `CORS_ORIGINS` | нет | CSV-список origin, по умолчанию `*` |
| `ADMIN_TOKEN` | для `/admin/leads` | Защита админ-эндпоинтов (заголовок `X-Admin-Token`) |
| `TG_BOT_TOKEN` | опц. | Токен Telegram-бота для оповещений о заявках |
| `TG_CHAT_ID` | опц. | ID чата/канала получателя |

### 2. Frontend

```bash
cd frontend
yarn install
# REACT_APP_BACKEND_URL в frontend/.env указывает на бекенд
yarn start
```

### 3. Проверка API

```bash
curl http://localhost:8001/api/health
# {"status":"ok","db":"connected"}

curl -X POST http://localhost:8001/api/leads \
  -H 'Content-Type: application/json' \
  -d '{"name":"Иван","company":"ООО","contact":"@ivan","servers":"4-10"}'
```

---

## Структура репозитория

```
mspshield/
├── frontend/                     React SPA
│   └── src/
│       ├── pages/                Landing, AdminLeads, NotFound
│       ├── components/sections/  Hero, Pain, HowItWorks, ForWhom, Compliance,
│       │                         Compare, Pricing, Process, Tools, Cases, FAQ, CTAForm
│       └── components/ui/        shadcn/ui (Accordion, Input, Dialog и т.д.)
│
├── backend/                      FastAPI + MongoDB
│   ├── server.py                 /api/leads · /api/stats · /api/health
│   └── requirements.txt
│
├── technical/                    MSP playbook (неизменный из v3.0)
│   ├── 0_Common/                 WireGuard · Docker · Alertmanager · скрипты
│   ├── 1_Bronze/                 Prometheus · Grafana · restic · node_exporter
│   ├── 2_Silver/                 + Loki · Puppet · Ansible · AD/GPO
│   ├── 3_Gold/                   + Wazuh SIEM · Kaspersky · osTicket
│   └── Junior/                   Программа обучения L1 / L2 / L3
│
├── contracts/                    Договоры Bronze / Silver / Gold
├── analysis/                     Рынок, юнит-экономика, воронка
├── docs/                         Operations, Deployment, Compliance
└── README.md
```

---

## Технический стек MSP

| Слой | Инструмент | Bronze | Silver | Gold |
|---|---|:-:|:-:|:-:|
| Метрики | Prometheus + Grafana | ✓ | ✓ | ✓ |
| Агенты (Linux) | node_exporter | ✓ | ✓ | ✓ |
| Агенты (Windows) | windows_exporter | ✓ | ✓ | ✓ |
| Бэкапы | restic + Yandex S3 | ✓ | ✓ | ✓ |
| VPN | WireGuard + Bastion | ✓ | ✓ | ✓ |
| Уведомления | Alertmanager → Telegram / Email | ✓ | ✓ | ✓ |
| Логи | Loki + Promtail | — | ✓ | ✓ |
| Конфиг-менеджмент | Puppet Server + Agent | — | ✓ | ✓ |
| Автоматизация | Ansible | — | ✓ | ✓ |
| AD / DNS / GPO | Native Windows + скрипты | — | ✓ | ✓ |
| SIEM | Wazuh Manager + Indexer | — | — | ✓ |
| EDR | Kaspersky Security Center | — | — | ✓ |
| Тикеты | osTicket | — | — | ✓ |
| Отечественные ОС | Astra Linux, РЕД ОС, ALT | ✓ | ✓ | ✓ |

---

## Тарифы

> Цены 2026 года. Финальная стоимость зависит от количества серверов и SLA.

| Тариф | Цена/мес | Запуск | SLA P1 | Кого обслуживает |
|---|---|---|---|---|
| **Bronze** | от 25 000 ₽ | 15–25k ₽ | ≤ 4 ч | 1–5 серверов, малый бизнес |
| **Silver** | от 50 000 ₽ | 30–50k ₽ | ≤ 2 ч | 80–300 сотр., AD/GPO, Windows+Linux |
| **Gold**   | от 85 000 ₽ | 45–80k ₽ | ≤ 1 ч 24/7 | Compliance, 152-ФЗ, медицина/финансы |

Юнит-экономика: [`analysis/market_analysis.md`](./analysis/market_analysis.md)

---

## Документация

| Документ | Назначение |
|---|---|
| [`docs/DEPLOYMENT.md`](./docs/DEPLOYMENT.md) | Деплой лендинга и API в продакшен |
| [`docs/OPERATIONS.md`](./docs/OPERATIONS.md) | Операционные регламенты (onboarding, incident, backup-verify) |
| [`docs/COMPLIANCE.md`](./docs/COMPLIANCE.md) | 152-ФЗ, импортозамещение, Реестр ПО |
| [`analysis/market_analysis.md`](./analysis/market_analysis.md) | Рынок РФ 2026, воронка, ценообразование |
| [`technical/1_Bronze/Bronze.md`](./technical/1_Bronze/Bronze.md) | Мастер-гайд Bronze |
| [`technical/2_Silver/Silver.md`](./technical/2_Silver/Silver.md) | Мастер-гайд Silver |
| [`technical/3_Gold/Gold.md`](./technical/3_Gold/Gold.md) | Мастер-гайд Gold |
| [`technical/Junior/junior_training.md`](./technical/Junior/junior_training.md) | Программа обучения |

---

## Дорожная карта

### v3.1 (текущий релиз)
- [x] React SPA-лендинг (премиум editorial design)
- [x] FastAPI + MongoDB для приёма заявок
- [x] Админ-панель `/admin/leads` с токеном
- [x] Интерактивный ROI-калькулятор
- [x] Telegram-уведомления о заявках (опционально)
- [x] Новые секции: «Для кого», «Соответствие РФ», «Кейсы», «Процесс»

### v3.2 (план)
- [ ] `/docs/privacy.html`, `/docs/offer.html`, `/docs/sla.html` (статические страницы)
- [ ] Интеграция с amoCRM / Битрикс24 для автоматизации воронки
- [ ] ЮKassa / СБП — онлайн-оплата первого месяца
- [ ] Блог на статьях (Habr-кросс-постинг) для SEO
- [ ] English-версия лендинга для экспортных контрактов

---

**Лицензия:** частный проект. Репозиторий закрыт для внешнего использования без письменного согласия автора.
