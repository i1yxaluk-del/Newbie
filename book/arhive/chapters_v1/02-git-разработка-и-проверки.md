# Разработка: Git, backend, frontend, тесты и Pull Request

Git хранит историю решений. Коммит должен отвечать на вопрос «что изменилось и зачем», а Pull Request — показывать риск, проверку и возврат. `git status` и `git diff` ничего не меняют; они дают исходные данные перед действием. Секреты, клиентские данные и локальные `.env` в историю не попадают.

Backend — серверная часть на Python. Frontend — код, который собирается и выполняется в браузере. Изменение формы считается законченным только после проверки браузера, API, базы и интеграций. Тест функции не доказывает работу production, а успешная сборка интерфейса не доказывает отправку заявки.

Маршрут разработчика: найти источник истины, создать ветку, изменить один связный участок, прогнать профильные тесты, посмотреть итоговую конфигурацию, открыть PR и выполнить проверку после развёртывания.

## Как работать с материалом

Сначала прочитайте объяснение главы. Затем откройте перечисленные файлы в рабочем репозитории и сопоставьте текст с текущим кодом. Команды изменения выполняйте на учебной среде. Разделы ниже включены полностью, поэтому глава одновременно служит учебником и справочником.

## Материал проекта: `docs/NAVIGATION.md`

<!-- SOURCE docs/NAVIGATION.md bdb0cd778d9a953a -->

## Карта репозитория

[← Главная](https://github.com/i1yxaluk-del/Newbie/blob/main/README.md) · [Оглавление документации](https://github.com/i1yxaluk-del/Newbie/blob/main/docs/README.md)

Эта карта разделяет **документы**, **исполняемый код** и **историю**. В каждой работе сначала открывается index, затем конкретная инструкция.

### Продажи

```text
commercial/README.md
  → PRICING.md
  → SALES_FUNNEL.md
  → SALES_PLAYBOOK.md
  → PROPOSAL.md
  → contracts/README.md
  → MSP_SERVICE_AGREEMENT.md
```

- [Коммерческое оглавление](https://github.com/i1yxaluk-del/Newbie/blob/main/commercial/README.md)
- [Единый договор](https://github.com/i1yxaluk-del/Newbie/blob/main/contracts/README.md)
- После оплаты: [клиентский lifecycle](https://github.com/i1yxaluk-del/Newbie/blob/main/docs/operations/CLIENT_LIFECYCLE.md)

### Развёртывание

```text
docs/deployment/README.md
  → DEPLOY_RUNBOOK.md
  → scripts/deployment/preflight.sh
  → deploy/yandex/README.md
  → health/test alert/restore evidence
```

- [Оглавление deployment](https://github.com/i1yxaluk-del/Newbie/blob/main/docs/deployment/README.md)
- [Что является кодом deployment](https://github.com/i1yxaluk-del/Newbie/blob/main/deploy/README.md)
- [Уроки deployment](https://github.com/i1yxaluk-del/Newbie/blob/main/docs/deployment/DEPLOYMENT_LESSONS.md)
- [Ревизия свежести всего репозитория](https://github.com/i1yxaluk-del/Newbie/blob/main/docs/audit/repository_deployment_freshness_2026-09.md)

### Миграция и восстановление

```text
migration/README.md
  → restic-backup.sh
  → restore-on-vm.sh
  → health/alert/restore gates
  → DNS switch
```

- [Миграция VM](https://github.com/i1yxaluk-del/Newbie/blob/main/migration/README.md)
- [Пошаговый migration runbook](https://github.com/i1yxaluk-del/Newbie/blob/main/docs/deployment/MIGRATION_RUNBOOK.md)
- [Disaster recovery](https://github.com/i1yxaluk-del/Newbie/blob/main/docs/deployment/disaster_recovery.md)

### Эксплуатация клиента

```text
Won
  → operations/CLIENT_LIFECYCLE.md
  → onboarding/README.md
  → runbooks/README.md
  → checklists/README.md
  → report / renewal / offboarding
```

- [Оглавление operations](https://github.com/i1yxaluk-del/Newbie/blob/main/docs/operations/README.md)
- [Onboarding](https://github.com/i1yxaluk-del/Newbie/blob/main/docs/onboarding/README.md)
- [Runbooks](https://github.com/i1yxaluk-del/Newbie/blob/main/docs/runbooks/README.md)
- [Регулярные проверки](https://github.com/i1yxaluk-del/Newbie/blob/main/docs/checklists/README.md)

### Monitoring и MAX

```text
Prometheus → Alertmanager → msp-max-alerter:9095/alert
→ pymax userbot → /session/max.db → MAX
```

- [MAX setup](https://github.com/i1yxaluk-del/Newbie/blob/main/docs/MAX_SETUP.md)
- [Сервисы](https://github.com/i1yxaluk-del/Newbie/blob/main/services/README.md)
- [MAX alerter](https://github.com/i1yxaluk-del/Newbie/blob/main/services/max_alerter/README.md)
- [Monitoring runbooks](https://github.com/i1yxaluk-del/Newbie/blob/main/docs/runbooks/README.md)

### Обучение и допуск

- [Программа Junior](https://github.com/i1yxaluk-del/Newbie/blob/main/docs/training/README.md)
- [Как работать с production](https://github.com/i1yxaluk-del/Newbie/blob/main/docs/training/JUNIOR_OPERATIONS_GUIDE.md)
- [Deployment/migration labs](https://github.com/i1yxaluk-del/Newbie/blob/main/docs/training/DEPLOYMENT_MIGRATION_LABS.md)
- [Runbooks](https://github.com/i1yxaluk-del/Newbie/blob/main/docs/runbooks/README.md)

### Разработка

| Зона | Путь | Перед PR |
|---|---|---|
| Backend/API/integrations | [`../backend/`](https://github.com/i1yxaluk-del/Newbie/blob/main/backend) | unit tests, compileall, env example |
| Landing/admin | [`../frontend/`](https://github.com/i1yxaluk-del/Newbie/blob/main/frontend) | yarn build, контент и consent |
| MAX/VM services | [`../services/`](https://github.com/i1yxaluk-del/Newbie/blob/main/services) | service tests и README |
| Compose/Nginx | [`../deploy/`](https://github.com/i1yxaluk-del/Newbie/blob/main/deploy) | preflight и production-config |
| CI/validators | [`../scripts/`](https://github.com/i1yxaluk-del/Newbie/blob/main/scripts) | локальный запуск validator |

### Что не является источником истины

`analysis/`, старые `marketing/`, `docs/sales/`, audit reports и postmortem объясняют историю, но не определяют текущие цену, SLA или deployment-команды. Их ссылки должны вести обратно в канонический index.

### Если ссылка сломана

1. Не угадывать соседний файл.
2. Вернуться в этот index.
3. Запустить `python scripts/validate_markdown_links.py`.
4. Исправить ссылку и ближайший index в одном PR.


## Материал проекта: `docs/training/JUNIOR_OPERATIONS_GUIDE.md`

<!-- SOURCE docs/training/JUNIOR_OPERATIONS_GUIDE.md 3ffffe67a676a074 -->

## Памятка Junior: как читать скрипты и runbook

### Перед запуском shell/Python/PowerShell

- Прочитай комментарий в начале файла: назначение, входы, побочные эффекты, rollback.
- Найди команды удаления, перезапуска, firewall и изменения прав.
- Убедись, что переменные не пустые и относятся к нужному tenant.
- Запусти режим проверки (`--dry-run`, `--check`, `set -n`) если он доступен.
- Не вставляй токены в командную строку: они попадут в history/process list.

### Обязательные русские комментарии для нового скрипта

```text
Назначение: какую проблему решает скрипт.
Где запускать: workstation / bastion / monitoring / client host.
Входные параметры: что обязательно и пример безопасного значения.
Побочные эффекты: какие файлы, сервисы или правила меняются.
Проверка успеха: команда и ожидаемый результат.
Откат: как вернуть состояние.
```

Комментарии должны объяснять «почему», а не повторять синтаксис команды. Секреты и реальные клиентские значения в примеры не добавляются.

### Стоп-условия

Остановись и эскалируй, если не совпадает hostname, нет backup/rollback, команда затрагивает несколько tenants, получен неожиданный вывод, операция касается ПДн вне подписанного периметра или требуется действие вне твоего допуска.


## Материал проекта: `backend/.env.example`

<!-- SOURCE backend/.env.example e9d53d757950e645 -->

```text
# ═══════════════════════════════════════════════════════════════════
# MSPShield backend · .env.example
# ═══════════════════════════════════════════════════════════════════
# Скопируй в backend/.env и заполни значения под свою среду.
# Локально:  cp backend/.env.example backend/.env
# В проде:   секреты берутся из Vaultwarden / секрет-хранилища,
#            НЕ коммитить реальный .env в git (он в .gitignore).
# ═══════════════════════════════════════════════════════════════════

# ── MongoDB ────────────────────────────────────────────────────────
# Локально через docker-compose: mongodb://mongo:27017
# Локально dev (без compose):   mongodb://localhost:27017
# Прод:                          mongodb://user:pass@host:27017/?authSource=admin
MONGO_URL=mongodb://localhost:27017

# Имя БД. dev: mspshield_dev. prod: mspshield.
DB_NAME=mspshield_dev

# ── Admin auth ─────────────────────────────────────────────────────
# Этот же ADMIN_TOKEN — пароль для входа в /admin (/api/admin/login).
# В dev можно оставить дефолт. На проде ОБЯЗАТЕЛЬНО:
#     ADMIN_TOKEN=$(openssl rand -hex 32)
# и ничего больше — JWT-сессия выпускается автоматически после ввода
# этого токена в форме логина.
ADMIN_TOKEN=dev-admin-token-local-testing-only

# JWT-секрет (по умолчанию = ADMIN_TOKEN, можно отдельный).
# JWT_SECRET=
# JWT_TTL_SECONDS=86400  # 24 часа по умолчанию

# ── Telegram-нотификации (опционально) ─────────────────────────────
# В dev оставить пустыми — уведомления не отправляются.
# В проде: создать бота через @BotFather, узнать chat_id через @getmyid_bot.
TG_BOT_TOKEN=
TG_CHAT_ID=
# Отдельный чат для Alertmanager-алертов (по умолчанию = TG_CHAT_ID).
# Удобно, если хочется разделить «новые лиды» и «инциденты».
# TG_ALERT_CHAT_ID=

# ── MAX мессенджер · Bot API (опционально) ────────────────────────
# https://dev.max.ru/docs-api — официальный, бесплатный (как Telegram).
#
# Шаги:
#   1. В мессенджере MAX откройте чат с @MasterBot → /create → имя →
#      получите токен.
#   2. MAX_BOT_TOKEN     — этот токен (не публикуйте его в git).
#   3. MAX_ALERT_CHAT_ID — chat_id, куда уходят уведомления о новых
#      лидах с лендинга. Можно поставить ваш user_id (узнайте в
#      @MasterBot → бот → «Получить мой ID»). Оставьте пустым,
#      если бот нужен только для входящих заявок.
#   4. MAX_WEBHOOK_SECRET — придумайте случайную строку 32+ символов:
#         openssl rand -hex 32
#      Тот же секрет указывается при подписке на webhook (см. ниже).
#   5. MAX_BOT_USERNAME  — username бота без `@` (для кнопки
#      «Написать в MAX» на лендинге, deep-link https://max.ru/<username>).
#
# Регистрация вебхука (после деплоя backend на HTTPS-домен):
#   python scripts/max_setup_webhook.py
# либо вручную:
#   curl -X POST "https://platform-api.max.ru/subscriptions" \
#     -H "Authorization: $MAX_BOT_TOKEN" \
#     -H "Content-Type: application/json" \
#     -d '{"url":"https://msp-claude.online/api/max/webhook","secret":"'"$MAX_WEBHOOK_SECRET"'"}'
#
# ВНИМАНИЕ: MAX требует HTTPS на порту 443 с валидным TLS-сертификатом
# (не self-signed). Встроенного long-polling режима нет: локально нужен mock
# или временный HTTPS-туннель. Alertmanager использует отдельный pymax userbot.
MAX_BOT_TOKEN=
MAX_ALERT_CHAT_ID=
MAX_WEBHOOK_SECRET=
MAX_BOT_USERNAME=
# MAX_API_BASE=https://platform-api.max.ru
# LANDING_URL=https://msp-claude.online

# ── Alertmanager → MAX/Telegram (опционально) ─────────────────────
# Prometheus Alertmanager шлёт webhook на /api/alerts/alertmanager,
# мы fan-out отправляем алерты в настроенные каналы (MAX + Telegram).
#
# ALERTMANAGER_WEBHOOK_TOKEN — Bearer-токен. Сгенерируй:
#   openssl rand -hex 32
# Тот же токен Alertmanager шлёт в заголовке `Authorization: Bearer ...`
# (см. deploy/alertmanager/alertmanager.yml). Если пуст — приёмник
# открыт (НЕ для прода).
#
# ALERT_CHANNELS — список каналов через запятую: max,telegram.
# По умолчанию — оба, если настроены. Можно оставить пустым (= оба).
#
# ALERT_RESOLVED_NOTIFY — отправлять ли resolved-уведомления.
# По умолчанию true.
ALERTMANAGER_WEBHOOK_TOKEN=
# ALERT_CHANNELS=max,telegram
# ALERT_RESOLVED_NOTIFY=true

# ── Email-уведомления о лидах (опционально) ─────────────────────────
# Отправляет письмо на каждый новый лид. Включается через SMTP_HOST + LEAD_EMAIL_TO.
#
# Рекомендация для прода: Postbox (Yandex Cloud :465) — даёт DKIM-подпись,
# письмо не попадает в спам. Stalwart :25 тоже работает, но без DKIM
# и часто триггерит спам-фильтры.
#
# LEAD_EMAIL_TO — список через запятую (sales@, admin@).
# SMTP_FROM_NAME — отображаемое имя отправителя (не «Alert» — триггерит спам).
SMTP_HOST=postbox.cloud.yandex.net
SMTP_PORT=465
SMTP_USER=
SMTP_PASSWORD=
SMTP_FROM=sales@msp-claude.online
SMTP_FROM_NAME=MSPShield
LEAD_EMAIL_TO=

# ── Yandex Cloud Postbox · outbound SMTP relay ────────────────────
# Smarthost для исходящих писем (transactional alerts от Alertmanager,
# DMARC RUA-репорты, welcome-письма клиентам). Stalwart форвардит сюда
# весь outbound — см. deploy/yandex/STALWART_RELAY_MODE.md §2 · Вариант A.
#
# Получение ключей (однократно):
#   1. Консоль Yandex Cloud → Postbox → создать конфигурацию домена
#      для msp-claude.online: ownership — по подсказке консоли, DKIM — только
#      CNAME `<selector>._domainkey → <selector>.dkim.pstbx.ru`.
#   2. Создать service account "postbox-sender" с ролью postbox.sender.
#   3. Создать API key для этого SA (scope = yc.postbox.send).
#   4. Сохранить id (aje...) и secret в Vaultwarden, потом в этот .env.
#
# Эти переменные читаются Stalwart-контейнером при первом bootstrap
# (см. deploy/yandex/docker-compose.yml STALWART_ROUTES_POSTBOX_*).
POSTBOX_API_KEY_ID=
POSTBOX_API_KEY_SECRET=

# ── Kaiten CRM (опционально) ───────────────────────────────────────
# Бесплатный тариф Kaiten поддерживает API. Получи токен:
#   https://<твой-домен>.kaiten.ru/profile/api-token
# Затем запусти:
#   python scripts/kaiten_bootstrap.py
# Скрипт создаст пространство и доску, выведет board_id и column_id —
# скопируй их в KAITEN_BOARD_ID / KAITEN_COLUMN_ID.
KAITEN_DOMAIN=
KAITEN_API_TOKEN=
KAITEN_SPACE_ID=
KAITEN_BOARD_ID=
KAITEN_COLUMN_ID=
# Опционально: дорожка (lane), если в доске их несколько.
KAITEN_LANE_ID=

# ── Универсальный webhook (опционально) ────────────────────────────
# Альтернатива/дополнение Kaiten — POST лида в произвольный URL
# (n8n, Make, Zapier, Bitrix24 inbound, Notion-bridge, …).
# Включается параллельно с Kaiten — лид уйдёт во все настроенные
# каналы.
CRM_WEBHOOK_URL=
CRM_WEBHOOK_TOKEN=

# ── CORS ───────────────────────────────────────────────────────────
# Три режима (приоритет сверху вниз):
#
# (a) CORS_ALLOW_ORIGIN_REGEX — задан → используем regex.
#     Это самый удобный режим для dev в локальной сети, когда сайт
#     открывается с разных машин (192.168.x.x, 10.x.x.x, 172.16-31.x.x).
#     Раскомментируй СНИЗУ, если открываешь :3000 не с localhost:
#
# CORS_ALLOW_ORIGIN_REGEX=^http://(localhost|127\.0\.0\.1|192\.168\.\d+\.\d+|10\.\d+\.\d+\.\d+|172\.(1[6-9]|2\d|3[01])\.\d+\.\d+):3000$
#
# (b) CORS_ORIGINS=* — wildcard. Включает all-origins, но БЕЗ credentials
#     (по CORS-спецификации). Никогда не используй в prod.
#
# (c) CORS_ORIGINS=список через запятую — точный allow-list + credentials.
#     Это рабочий вариант для прода. По умолчанию в dev — localhost+127.0.0.1
#     (этот же fallback применяется, если переменная пустая).
CORS_ORIGINS=http://localhost:3000,http://127.0.0.1:3000
# CORS_ALLOW_ORIGIN_REGEX=
# Прод (пример): CORS_ORIGINS=https://msp-claude.online

# ── Rate limit ─────────────────────────────────────────────────────
# Сколько заявок с одного IP допускается в окне.
RATE_LIMIT_PER_MIN=10
RATE_LIMIT_WINDOW_SEC=60

# ── Yandex SmartCaptcha (опционально) ──────────────────────────────
# Оставь пустым в dev — сервер пропустит форму без проверки капчи.
# В проде: https://cloud.yandex.ru/services/smartcaptcha
SMARTCAPTCHA_SERVER_KEY=
SMARTCAPTCHA_VERIFY_URL=https://smartcaptcha.yandexcloud.net/validate

```

## Материал проекта: `frontend/package.json`

<!-- SOURCE frontend/package.json 108b713d512cbb21 -->

```json
{
  "name": "frontend",
  "version": "0.1.0",
  "private": true,
  "dependencies": {
    "@hookform/resolvers": "^5.0.1",
    "@radix-ui/react-accordion": "^1.2.8",
    "@radix-ui/react-alert-dialog": "^1.1.11",
    "@radix-ui/react-aspect-ratio": "^1.1.4",
    "@radix-ui/react-avatar": "^1.1.7",
    "@radix-ui/react-checkbox": "^1.2.3",
    "@radix-ui/react-collapsible": "^1.1.8",
    "@radix-ui/react-context-menu": "^2.2.12",
    "@radix-ui/react-dialog": "^1.1.11",
    "@radix-ui/react-dropdown-menu": "^2.1.12",
    "@radix-ui/react-hover-card": "^1.1.11",
    "@radix-ui/react-label": "^2.1.4",
    "@radix-ui/react-menubar": "^1.1.12",
    "@radix-ui/react-navigation-menu": "^1.2.10",
    "@radix-ui/react-popover": "^1.1.11",
    "@radix-ui/react-progress": "^1.1.4",
    "@radix-ui/react-radio-group": "^1.3.4",
    "@radix-ui/react-scroll-area": "^1.2.6",
    "@radix-ui/react-select": "^2.2.2",
    "@radix-ui/react-separator": "^1.1.4",
    "@radix-ui/react-slider": "^1.3.2",
    "@radix-ui/react-slot": "^1.2.0",
    "@radix-ui/react-switch": "^1.2.2",
    "@radix-ui/react-tabs": "^1.1.9",
    "@radix-ui/react-toast": "^1.2.11",
    "@radix-ui/react-toggle": "^1.1.6",
    "@radix-ui/react-toggle-group": "^1.1.7",
    "@radix-ui/react-tooltip": "^1.2.4",
    "axios": "^1.8.4",
    "class-variance-authority": "^0.7.1",
    "clsx": "^2.1.1",
    "cmdk": "^1.1.1",
    "cra-template": "1.2.0",
    "date-fns": "^4.1.0",
    "embla-carousel-react": "^8.6.0",
    "input-otp": "^1.4.2",
    "lucide-react": "^0.507.0",
    "next-themes": "^0.4.6",
    "react": "^19.0.0",
    "react-day-picker": "8.10.1",
    "react-dom": "^19.0.0",
    "react-hook-form": "^7.56.2",
    "react-resizable-panels": "^3.0.1",
    "react-router-dom": "^7.5.1",
    "react-scripts": "5.0.1",
    "recharts": "^3.6.0",
    "sonner": "^2.0.3",
    "tailwind-merge": "^3.2.0",
    "tailwindcss-animate": "^1.0.7",
    "vaul": "^1.1.2",
    "zod": "^3.24.4"
  },
  "scripts": {
    "start": "craco start",
    "build": "craco build",
    "test": "craco test"
  },
  "browserslist": {
    "production": [
      ">0.2%",
      "not dead",
      "not op_mini all"
    ],
    "development": [
      "last 1 chrome version",
      "last 1 firefox version",
      "last 1 safari version"
    ]
  },
  "devDependencies": {
    "@babel/plugin-proposal-private-property-in-object": "^7.21.11",
    "@craco/craco": "^7.1.0",
    "@eslint/js": "9.23.0",
    "autoprefixer": "^10.4.20",
    "eslint": "9.23.0",
    "eslint-plugin-import": "2.31.0",
    "eslint-plugin-jsx-a11y": "6.10.2",
    "eslint-plugin-react": "7.37.4",
    "eslint-plugin-react-hooks": "5.2.0",
    "globals": "15.15.0",
    "postcss": "^8.4.49",
    "tailwindcss": "^3.4.17"
  },
  "packageManager": "yarn@1.22.22+sha512.a6b2f7906b721bba3d67d4aff083df04dad64c399707841b7acf00f6b133b7ac24255f2652fa22ae3534329dc6180534e98d17432037ff6fd140556e2bb3137e"
}

```

## Материал проекта: `frontend/.env.example`

<!-- SOURCE frontend/.env.example add41d40701b96d2 -->

```text
# ═══════════════════════════════════════════════════════════════════
# MSPShield frontend · .env.example
# ═══════════════════════════════════════════════════════════════════
# Скопируй в frontend/.env и заполни под свою среду:
#     cp frontend/.env.example frontend/.env
#
# CRA читает .env ТОЛЬКО при старте `yarn start` / `yarn build`.
# После любых правок этого файла — перезапусти сборку, иначе изменения
# не подхватятся.
# ───────────────────────────────────────────────────────────────────

# Базовый URL backend'а. Должен ВКЛЮЧАТЬ протокол.
# - Локально:                 http://localhost:8001
# - С другой машины в локалке: http://192.168.x.x:8001  (тогда backend
#                              стартуй с --host 0.0.0.0)
# - Прод (одна VM, nginx):     оставь пустым → axios шлёт same-origin,
#                              nginx проксирует /api/ на 127.0.0.1:8001
REACT_APP_BACKEND_URL=http://localhost:8001

# Опционально. Public client-side ключ Yandex SmartCaptcha. Если не задан
# (как в dev), форма отправляется без капчи — backend делает fail-open.
# Получить: https://smartcaptcha.yandexcloud.net (нужен YC-аккаунт).
REACT_APP_SMARTCAPTCHA_SITE_KEY=

# Yandex.Metrika counter ID. Used by utils/metrika.js for reachGoal events.
# Defaults to 109692310 if not set.
REACT_APP_YM_COUNTER_ID=109692310

# ───────────────────────────────────────────────────────────────────
# Дальше — НЕ трогай без необходимости. CRA-флаги по умолчанию.
# ───────────────────────────────────────────────────────────────────

# WDS (webpack-dev-server) HMR через WebSocket. По умолчанию CRA сам
# определяет порт; на прод-домене с другим хостом полезно явно указать.
# WDS_SOCKET_HOST=
# WDS_SOCKET_PORT=

# Принудительно отключить browserify-fallback warnings.
DISABLE_ESLINT_PLUGIN=false

```

## Практический результат

Перескажите цепочку своими словами, выполните безопасную лабораторную работу и сохраните команды без секретов, фактический результат и способ отката. Если результат отличается от текста, остановитесь: сначала исправляется расхождение, а не подгоняется отчёт.
