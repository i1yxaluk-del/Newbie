# Анализ проекта MSPShield — 2026-06-07

> Технический и продуктовый разбор репозитория `i1yxaluk-del/Newbie`.
> **Из анализа исключена папка `Domik/`** — это отдельный проект (сайт гостевого
> дома «Алина» на FastAPI+SQLite/React+Vite, не связан с MSPShield).
>
> Документ описательный: кода он не меняет, нужен как «снимок состояния» для
> преемственности между сессиями и для будущих junior-инженеров.

---

## 1. Резюме (TL;DR)

**Что это.** MSPShield — управляемые ИБ/ИТ-услуги (Managed Service Provider) для
малого и среднего бизнеса в РФ. Продуктовая воронка: лендинг → форма заявки →
бэкенд принимает лид → доставка во все включённые каналы (Kaiten CRM, Telegram,
email, MAX, webhook) → продажа подписки по тарифам Bronze / Silver / Gold.

**Зрелость.** Это **не прототип, а зрелый MVP**, развёрнутый на проде
(`msp-claude.online`, Yandex Cloud). Репозиторий совмещает три пласта:
1. **Работающий продукт** — React-лендинг + админка, FastAPI-бэкенд, MongoDB.
2. **Инфраструктуру как код** — Terraform (Yandex Cloud), Ansible-роли, Caddy/Nginx,
   мониторинг (Prometheus/Grafana/Alertmanager/Loki/Wazuh), VPN (AmneziaWG), бэкапы (restic).
3. **Бизнес-операционку** — финмодель, юнит-экономика, договоры (.docx),
   SOP-процессы по тарифам, обучающая программа junior'а, runbooks на инциденты.

**Общая оценка: 8/10.** Сильная архитектура, аккуратный код с RU-комментариями,
богатая документация, тесты на интеграции зелёные. Главные минусы — один
закоммиченный секрет (см. §7), отсутствие CI и часть «бумажной» инфраструктуры,
которую трудно проверить из песочницы.

| Метрика | Значение |
|---|---|
| Коммитов в `main` | 229 |
| Файлов (без `Domik/`, `.git`, `node_modules`) | 463 |
| Python (backend) | ~2 900 строк, 14 файлов |
| React (frontend `src`) | ~10 400 строк, 79 `.jsx` + JS |
| Markdown-документации | 150 файлов |
| Ansible YAML / playbooks / roles | 75 `.yml`, ~15 ролей |
| Договоры (.docx) | 15 файлов |
| Unit-тесты (backend, проходят) | 43 ✅ |

---

## 2. Архитектура и стек

```
Браузер ──> Caddy/Nginx (TLS) ──> FastAPI (uvicorn) ──> MongoDB 7
                                       │
                                       ├─(BackgroundTasks)─> Kaiten CRM (REST)
                                       ├──────────────────-> Telegram
                                       ├──────────────────-> email (Postbox :465)
                                       ├──────────────────-> MAX (Bot API)
                                       └──────────────────-> generic webhook
            Prometheus <─ /metrics ────┘
            Grafana / Alertmanager / Loki / Wazuh (мониторинг)
            AmneziaWG VPN (обфускация против РКН-DPI), restic → Object Storage
```

| Слой | Технология | Где |
|---|---|---|
| Frontend | React 19 + Tailwind + shadcn/ui (Radix), react-router 7, recharts | `frontend/` |
| Backend | FastAPI 0.110 + Motor (async MongoDB) + Pydantic v2 | `backend/` |
| БД | MongoDB 7 (источник истины по лидам) | docker-compose |
| Reverse proxy / TLS | Caddy (Path A) или Nginx+Certbot (Path B) | `deploy/` |
| Облако | Yandex Cloud (VPC + Compute + Object Storage) | `infra/terraform/` |
| Конфиг-менеджмент | Ansible (роли: nginx, mongo, fastapi_backend, monitoring, awg_hub, restic…) | `technical/0_Common/ansible/` |
| Мониторинг | Prometheus + Grafana + Alertmanager (+ Loki Silver, Wazuh Gold) | `deploy/yandex/monitoring/` |
| Секреты | Vaultwarden (self-hosted) + Yandex Lockbox | `deploy/vaultwarden/` |
| CRM | Kaiten REST API | `backend/integrations/kaiten.py` |

**Сильная сторона архитектуры:** MongoDB — единый источник истины, а доставка в CRM
вынесена в `BackgroundTasks`. Пользователь получает `201` мгновенно, не дожидаясь
сетевых вызовов к Kaiten/Telegram/etc. Падение любого внешнего канала не ломает
приём заявки — каждый канал обёрнут в свой `try/except` и считается в Prometheus.

---

## 3. Бэкенд (детально)

**Точка входа** `backend/server.py` (853 строки). Чисто структурирован:
Config → Pydantic-модели → Prometheus-метрики → rate-limit → helpers → endpoints.

**Эндпоинты (`/api`):**
- `POST /leads` — приём заявки. Защита: rate-limit (sliding window по IP,
  дефолт 10/60с), honeypot-поле `website`, согласие на обработку ПДн (152-ФЗ,
  поле `consent`), опциональная проверка Yandex SmartCaptcha.
- `POST /admin/login` — обмен `ADMIN_TOKEN` на JWT (24 ч, HS256).
- `GET /leads`, `PATCH /leads/{id}/status`, `GET /stats`, `GET /leads.csv` — админка.
- `GET /health` — liveness + проба БД. `GET /metrics` — Prometheus.
- `POST /max/webhook` — входящие сообщения MAX-бота (state-machine: лид прямо из мессенджера).
- `POST /alerts/alertmanager` — приём алертов мониторинга → пересылка в MAX/Telegram.
- `GET /integrations/status` — какие каналы включены (читает фронт).

**Аутентификация (`auth.py`).** Два равноправных способа: long-lived
`X-Admin-Token` (удобно для curl/cron) и JWT-сессия (UX логина в `/admin`).
Аккуратная деталь — `ADMIN_TOKEN` читается **динамически** (ленивый `_LazyToken`),
т.к. на момент import'а `.env` ещё не загружен. Если `ADMIN_TOKEN` не задан —
админка отдаёт `503` (а не открыта без пароля). Хорошо.

**Интеграции (`backend/integrations/`):** `kaiten`, `telegram`, `email`, `max`,
`webhook`, `alertmanager`. Каждая — самодостаточный модуль с `is_enabled()` и
единым контрактом. Kaiten доведён до **реальной идемпотентности** по `external_id`
(повторная доставка того же лида не создаёт дубль карточки) + `verify()`.

**Замечания по бэкенду:**
- ➕ Подробные русские докстринги и комментарии «что от чего зависит» — точно под
  запрос владельца про найм junior'ов.
- ➕ Pydantic-валидация строгая (whitelist для `servers`/`tariff`/`status`, regex email).
- ⚠️ Rate-limit **in-memory** (per-process `dict`). При нескольких воркерах uvicorn
  или горизонтальном масштабировании лимит на инстанс, а не глобальный. Для текущего
  трафика лендинга — ок, но стоит знать (решение — Redis-бэкенд при росте).
- ⚠️ `verify_smartcaptcha` **fail-open** при ошибке вышестоящего сервиса (return `True`).
  Сознательный компромисс (не терять лиды), но при атаке капча эффективно отключается.
- ⚠️ `@app.on_event("startup"/"shutdown")` — устаревший API FastAPI; в новых версиях
  рекомендован `lifespan`. Не срочно, но при апгрейде FastAPI всплывёт.

---

## 4. Фронтенд

`frontend/src` — React 19 SPA. ~10 400 строк. Структура зрелая:
- `pages/` — `Landing`, `AdminLeads`, `AdminLandingEdit`, `NotFound`.
- `components/sections/` — 15 секций лендинга (Hero, Pain, Pricing, FAQ, CTAForm…).
- `components/ui/` — полный набор shadcn/ui (Radix) — 50+ компонентов.
- `components/dashboards/` — «живые» демо-дашборды (GoldenSignals, SlaTimeline,
  BackupHealth, WazuhAlerts) — показывают клиенту, как выглядит мониторинг.
- `content/landing.ru.json` + `useContent.js` — **контент лендинга вынесен в JSON**,
  редактируется через `/admin/landing-edit` без правки кода. Сильное решение для
  команды «основатель + жена-маркетолог».

**Замечания:**
- ➕ Конфиг-driven лендинг (JSON) — маркетолог меняет тексты/тарифы сам.
- ⚠️ Папка `ui/` тянет полный shadcn-набор, хотя реально используется меньшая часть —
  лишний вес бандла. Можно подчистить неиспользуемые компоненты (не критично).

---

## 5. Инфраструктура и DevOps

Самый объёмный пласт. **Заметно сильнее, чем у типичного проекта на этой стадии.**
- **Terraform** (`infra/terraform/`) — baseline Yandex Cloud (VPC + landing + bastion + S3).
- **Ansible** (`technical/0_Common/ansible/`) — ~15 ролей: `base_hardening`, `nginx`,
  `mongo`, `fastapi_backend`, `monitoring_agent`, `alertmanager`, `awg_hub`,
  `restic_client`, `ad_health_check`. Разбито по тарифам (Bronze/Silver/Gold).
- **Мониторинг** (`deploy/yandex/monitoring/`) — готовые Grafana-дашборды,
  Prometheus-правила, Alertmanager-шаблоны, restic-exporter, telegram-webhook.
- **VPN** — миграция WireGuard → AmneziaWG (UDP/443, обфускация против РКН-DPI).
- **Деплой** — `deploy.ps1` (PowerShell, под Windows-рабочее место владельца),
  `cloud-init.yaml`, `setup-on-vm.sh`, два пути TLS (Caddy / Nginx+Certbot).
- **Бэкапы** — restic → Yandex Object Storage (AES-256), textfile-collector в Prometheus.

**Замечания:**
- ⚠️ `deploy/yandex/STALWART_RELAY_MODE.md` помечен deprecated (перешли на Postbox :465),
  но конфиг Alertmanager всё ещё ссылается на `smtp_smarthost: "stalwart:25"` —
  рассинхрон документации и конфига (см. также §7).
- ⚠️ Много инфраструктуры существует только как код/доки; из песочницы её
  работоспособность на VM проверить нельзя (нет `yc`/SSH). Это не дефект репо,
  а ограничение проверки — но go-live зависит от ручной настройки `.env` на VM.

---

## 6. Бизнес-слой и документация

Необычно сильная для технического репо часть — фактически здесь лежит «операционка бизнеса»:
- `analysis/` — `unit_economics.md`, `cac_model.md`, `ltv_model.md`,
  `finmodel_m1_m24.md` (финмодель на 24 мес), `icp_profiles.md`, `market_analysis.md`,
  `addon_catalog.md`, `discount_policy.md`. Полноценная юнит-экономика и go-to-market.
- `contracts/` — договор + 7 приложений (тарифы, SLA, периметр, ПДн, NDA, акт,
  передача) в `.docx`, плюс копии в `frontend/public/docs/` для скачивания с сайта.
- `technical/{1_Bronze,2_Silver,3_Gold}/` — SOP-процессы обслуживания, разделены на
  `CLIENT` и `EXECUTOR`.
- `docs/` — 150 .md: deployment, training (12-недельная программа junior),
  runbooks R-01..R-11 (ransomware, backup, SSL, VPN, DR), checklists,
  onboarding, sales (BANT-Q, email-шаблоны), hiring (JD + тестовое + интервью),
  COMPLIANCE (152-ФЗ + импортозамещение), KAITEN_SETUP, MAX_SETUP, roadmap.

**Замечание:** документации очень много (150 файлов) — есть риск рассинхрона с кодом.
В репо уже есть удачная практика «один канонический README на задачу» (v4.5) и
audit-отчёты — её стоит держать, иначе доки начнут противоречить друг другу.

---

## 7. Находки и риски (по приоритету)

### 🔴 P0 — Закоммичен секрет (SMTP-пароль)
`deploy/yandex/monitoring/alertmanager/alertmanager.yml:7` содержит реальный пароль
открытым текстом:
```
smtp_auth_password: "QYIQylBaBRenxvvKuxLVx5Yq"
```
Файл **отслеживается git** (не в `.gitignore`), репозиторий **публичный** → пароль
скомпрометирован, даже если его удалить (останется в истории).
**Действия:** (1) сменить/отозвать этот пароль на стороне почты; (2) вынести его в
переменную окружения / Vaultwarden и подставлять через шаблон, как сделано для
остальных секретов; (3) при необходимости — переписать историю (git filter-repo).
Это прямо нарушает собственное правило репо «Что НЕ коммитим» из README.

### 🟠 P1 — Нет CI/CD
В репо нет `.github/workflows`. 43 unit-теста и линтеры (flake8/black/isort/mypy в
requirements) есть, но не запускаются автоматически на push/PR. Один GitHub Actions
workflow (lint + pytest + secret-scan) закрыл бы и регрессии, и проблему P0 на будущее.

### 🟡 P2 — Тесты смешивают unit и live-e2e
`tests/test_mspshield_api.py` бьётся в живой сервер по HTTP (`requests` к `BASE_URL`)
и не запускается без поднятого backend — при `pytest` всего каталога это роняет сбор
тестов (`ModuleNotFoundError: requests` + нет сервера). Стоит пометить его маркером
`@pytest.mark.e2e` и исключить из дефолтного прогона, чтобы 43 unit-теста гонялись чисто.

### 🟡 P2 — Рассинхрон Stalwart/Postbox
Документация перешла на Postbox `:465`, но Alertmanager всё ещё настроен на
`stalwart:25`. Привести конфиг в соответствие с актуальным способом доставки почты.

### 🔵 P3 — Прочее (не блокеры)
- Rate-limit in-memory (не глобальный при нескольких воркерах) — §3.
- SmartCaptcha fail-open — §3.
- Устаревший `@app.on_event` вместо `lifespan` — §3.
- Полный shadcn `ui/` тянется в бандл частично «вхолостую» — §4.
- 50 МБ `Domik/Domik.rar` в репо раздувает клон (бинарь архива в git).

---

## 8. Рекомендации (что сделать в первую очередь)

1. **Сейчас:** отозвать и заменить SMTP-пароль из §7-P0, убрать его из конфига в env/Vaultwarden.
2. **На неделе:** добавить GitHub Actions (flake8 + pytest unit + gitleaks/secret-scan на каждый PR).
3. **На неделе:** разнести unit- и e2e-тесты (`pytest.ini` + маркер `e2e`), чтобы `pytest` был зелёным «из коробки».
4. **При доводке go-live:** синхронизировать почтовый транспорт (Postbox vs Stalwart) в Alertmanager.
5. **По мере роста трафика:** перенести rate-limit в Redis; пересмотреть SmartCaptcha fail-open.
6. **Гигиена репо:** вынести `Domik.rar` из git (Git LFS или внешнее хранилище), чтобы не раздувать клон.

---

## 9. Вывод

MSPShield — серьёзный, продуманный проект уровня «работающий MVP в проде», а не
учебная заготовка. Архитектура приёма и доставки лидов корректна и отказоустойчива,
код читаемый и хорошо прокомментирован по-русски (под найм junior'ов), бизнес-слой
проработан до финмодели и договоров. Чтобы довести до «боевого» состояния без
сюрпризов, в первую очередь нужно закрыть один закоммиченный секрет и поставить CI —
остальное это улучшения, а не блокеры.

*Папка `Domik/` в анализе не участвовала — это самостоятельный проект гостевого дома.*
