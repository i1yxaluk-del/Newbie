# MSPShield v3.1 · PRD

## Original Problem Statement
Проанализировать GitHub-репозиторий `joejonsonw-hue/Workingplan` (MSPShield v3.0 — B2B managed IT services для РФ). Поправить под реалии рынка 2026. Переписать лендинг так, чтобы он работал на текущем B2B-рынке РФ и приносил прибыль. Проверить структуру, MD-файлы и конфигурации на читаемость и реалистичность. Пользовательские параметры: B2B-сегмент, стиль «минимализм, премиум, бизнес».

## Architecture
- **Frontend:** React 19 + React Router + Tailwind + shadcn/ui + lucide-react + sonner
- **Backend:** FastAPI + MongoDB (motor) + httpx (опц. Telegram)
- **Design:** Editorial premium — Cormorant Garamond (display) + DM Sans (body) + DM Mono (data). Палитра cream `#F7F4EE` + forest `#1B4D3E` + ink `#1A1815`.

## User Personas
1. **Владелец SMB (15–80 чел.)** — юрист/бухгалтер/консалтинг. Бюджет 25–50k ₽/мес. Bronze/Silver.
2. **Ген.дир / главбух медклиники** — compliance-чувствительный. 85–150k ₽/мес. Gold.
3. **IT-директор (80–300 чел.)** — хочет снять рутину с команды. 50–100k ₽/мес. Silver.

## Core Requirements (статичные)
- Лендинг с ROI-калькулятором и работающей формой заявок
- Админ-панель заявок с токеном
- Опциональные Telegram-уведомления о заявках
- Актуализированный анализ рынка 2026
- Читаемая структура документации (README, docs/, contracts/, analysis/)
- Акцент на 152-ФЗ, импортозамещение, отечественные ОС

## Implementation History

### 2026-04-20 · v3.1 MVP

- **Backend:** `/api/health`, `/api/leads` (POST public + GET admin + PATCH status), `/api/stats`. Pydantic-валидация (servers enum, email regex). Опциональный Telegram-webhook через env. Admin-auth через `X-Admin-Token`.
- **Frontend (React SPA):**
  - Nav (sticky glass), Hero (с live-card мониторинга), Pain + ROI-калькулятор
  - HowItWorks, **ForWhom** (новое — 3 сегмента B2B), **Compliance** (новое — 152-ФЗ/импортозамещение)
  - Compare (3 колонки — штатный / фрилансер / MSPShield), Pricing без эмодзи
  - **Process** (новое — день 0 → регулярный сервис), Tools (lucide-иконки), **Cases** (новое — обезличенные)
  - FAQ (shadcn Accordion), CTAForm с валидацией и POST
  - Admin `/admin/leads` с таблицей, фильтром статусов, обновлением через PATCH
- **Docs:** Переписан `README.md`, создан `analysis/market_analysis.md` (редакция 2026), `docs/DEPLOYMENT.md`, `docs/OPERATIONS.md`, `docs/COMPLIANCE.md`, `contracts/README.md`.
- **Testing:**
  - Backend: 15/15 pytest-кейсов пройдено (health, lead-validation, admin-auth, stats, status-transitions)
  - Frontend: 100% в iteration_2 после фиксов (Pricing→tariff state sync, mobile overflow)

## Known Limitations (carried over, non-blocking)
- Нет rate-limiting на `POST /api/leads` (рекомендовано slowapi/nginx перед продом)
- `CORS_ORIGINS='*'` с `allow_credentials=True` — сузить до конкретных доменов перед деплоем
- Пустая форма пропускается через HTML5 `required` (нативное окно браузера), toast.error не триггерится — оставлено как есть

## Prioritized Backlog

### P0 (блокирующие продакшен)
- [ ] Заменить плейсхолдеры реквизитов в `contract_*.html` на реальные ИП-данные
- [ ] Сгенерировать сильный `ADMIN_TOKEN` (32+ hex-символов) и положить в prod-.env
- [ ] Сузить `CORS_ORIGINS` до продового домена

### P1 (пост-запуск)
- [ ] Rate-limiting на публичные эндпоинты (slowapi / nginx limit_req)
- [ ] Статические страницы `/docs/privacy.html`, `/docs/offer.html`, `/docs/sla.html`
- [ ] amoCRM / Битрикс24 интеграция вместо/дополнительно к Telegram
- [ ] ЮKassa для онлайн-оплаты первого месяца

### P2 (развитие)
- [ ] Блог/журнал (`/blog`) для SEO на Habr-материалах
- [ ] English-версия лендинга
- [ ] Дашборд клиента (public Grafana snapshot → React-обёртка)

## Test Credentials
См. `/app/memory/test_credentials.md`. Текущий `ADMIN_TOKEN = change-me-to-strong-random-string` — заменить перед деплоем.
