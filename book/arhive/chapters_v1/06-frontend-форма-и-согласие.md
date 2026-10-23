# Frontend, форма, согласие и SmartCaptcha

Браузер нельзя считать доверенной стороной. Проверка поля в интерфейсе помогает пользователю, но запрос можно отправить напрямую. Поэтому backend повторно проверяет обязательные поля, формат и явное согласие.

Сборка frontend превращает исходники в статические файлы. Переменные, попавшие в браузерный bundle, видны пользователю и не могут быть секретами. Решение SmartCaptcha при отказе должно быть явным: fail-open пропускает запрос без проверки, fail-closed останавливает его. Для production выбран безопасный режим, но нужно следить, чтобы недоступность CAPTCHA не стала незаметной потерей лидов.

Тест формы включает успешную отправку, отсутствие согласия, повреждённый JSON, отказ CAPTCHA, повтор и недоступную интеграцию.

## Как работать с материалом

Сначала прочитайте объяснение главы. Затем откройте перечисленные файлы в рабочем репозитории и сопоставьте текст с текущим кодом. Команды изменения выполняйте на учебной среде. Разделы ниже включены полностью, поэтому глава одновременно служит учебником и справочником.

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

## Материал проекта: `docs/PROJECT_8_OF_10.md`

<!-- SOURCE docs/PROJECT_8_OF_10.md ebb173906bf99184 -->

## План качества проекта: критерии 8/10

Документ переводит оценку проекта из субъективной в проверяемую. Оценка 8/10 относится только к ограниченному Bronze-пилоту, а не к критичной инфраструктуре и не к круглосуточному Gold.

### Матрица готовности

| Область | Критерий | Состояние |
|---|---|---|
| Сеть | backend/Mongo/Vaultwarden не доступны извне; HTTPS работает | проверяется CI external-perimeter |
| Секреты | нет unsafe defaults, MFA и персональные учётные записи | обязательный onboarding checklist |
| CRM | заявка переживает рестарт и повторяется через outbox | реализовано, семантика at-least-once |
| Форма | явное согласие обязательно; CAPTCHA fail-closed | реализовано |
| Backup | full restore в чистую среду с измеренными RTO/RPO | обязательный gate перед критичным клиентом |
| Договоры | MSA + тариф + SLA + периметр + DPA/NDA | канонический комплект в `contracts/canonical/` |
| Экономика | труд, налог, банк и incident reserve включены | `PRICING_SOURCE_OF_TRUTH.md` |
| Обучение | Junior имеет уровни допуска и практический экзамен | `docs/training/README.md` |
| Обещания | лендинг, КП, бот и договор используют одни цены/SLA | проверяется `validate_business_consistency.py` |

### Gate перед первым критичным клиентом

Все пункты должны иметь ссылку на evidence:

- [ ] внешний скан выполнен после последнего изменения firewall;
- [ ] full restore выполнен в чистом окружении;
- [ ] фактические RTO/RPO не хуже подписываемых;
- [ ] российский юрист проверил договорный комплект и схему ПДн;
- [ ] назначен резервный инженер и проведена передача смены;
- [ ] проведена tabletop-тренировка P1;
- [ ] клиент подписал перечень критичных систем и исключений;
- [ ] известны владельцы DNS, облака, backup и аварийных контактов.

### Что не даёт оценка 8/10

- сертификат соответствия 152-ФЗ или требованиям ФСТЭК;
- гарантию отсутствия инцидентов;
- право обещать 24/7 без дежурной команды;
- доказанную масштабируемость нескольких backend/outbox workers.


## Практический результат

Перескажите цепочку своими словами, выполните безопасную лабораторную работу и сохраните команды без секретов, фактический результат и способ отката. Если результат отличается от текста, остановитесь: сначала исправляется расхождение, а не подгоняется отчёт.
