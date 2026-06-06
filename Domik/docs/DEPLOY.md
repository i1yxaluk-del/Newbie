# Деплой Domik на бесплатные хостинги

Рекомендуемая бесплатная связка:
- **Backend** — Render Free (Docker, public URL)
- **Frontend** — Netlify Free (статика + бесплатный поддомен `*.netlify.app`)
- **Домен** — бесплатный поддомен Netlify (рекомендую) или Cloudflare Pages

Альтернативы: Fly.io (free), Railway (limited), Cloudflare Pages + Workers, Vercel.

---

## 1. Подготовка

1. Создайте репозиторий на GitHub и запушьте папку `Domik`.
2. Подготовьте:
   - **личный email-ящик** (Яндекс или Gmail) — для SMTP-уведомлений;
     - Яндекс: включить «Пароли приложений» → создать пароль для SMTP.
   - **Telegram-бота**:
     - в Telegram написать [@BotFather](https://t.me/BotFather) → `/newbot` → получить `TG_BOT_TOKEN`.
     - в Telegram написать [@userinfobot](https://t.me/userinfobot) → получить ваш `chat_id` → `TG_CHAT_ID`.
     - один раз отправить боту любое сообщение, чтобы он мог писать вам в ответ.

## 2. Backend на Render

1. Зарегистрируйтесь на https://render.com (free).
2. New → **Web Service** → подключите репозиторий, корень — `Domik/backend`, env: `Docker`.
3. Подставьте переменные окружения (см. `backend/.env.example`):
   - `APP_SECRET` — Render сгенерирует
   - `ADMIN_EMAIL`, `ADMIN_PASSWORD` — ваши
   - `SMTP_HOST=smtp.yandex.ru`, `SMTP_PORT=465`, `SMTP_USE_TLS=true`
   - `SMTP_USER`, `SMTP_PASSWORD`, `SMTP_FROM` — ящик и пароль приложения
   - `NOTIFY_EMAIL_TO` — куда присылать заявки (можно тот же ящик)
   - `TG_BOT_TOKEN`, `TG_CHAT_ID`
   - `CORS_ORIGINS=https://YOUR-FRONTEND.netlify.app`
4. После деплоя проверьте: `https://YOUR-BACKEND.onrender.com/api/health` → `{"ok": true}`.

> В `Domik/deploy/render.yaml` уже лежит готовый шаблон сервиса.

## 3. Frontend на Netlify

1. https://app.netlify.com → Add new site → import from Git.
2. Build settings:
   - Base directory: `Domik/frontend`
   - Build command: `npm install && npm run build`
   - Publish directory: `Domik/frontend/dist`
3. Environment:
   - `VITE_API_URL` — оставьте пустым, если используете прокси из `netlify.toml`, или укажите `https://YOUR-BACKEND.onrender.com`.
4. Откройте `Domik/deploy/netlify.toml` и замените `REPLACE-WITH-BACKEND.onrender.com` на свой backend-домен. Скопируйте файл в корень репозитория (или укажите base = `Domik/frontend` и положите `netlify.toml` рядом).
5. После деплоя сайт будет на `https://<имя>.netlify.app`. Это и есть бесплатный домен 2 уровня.

## 4. Проверка

1. Откройте `/` — лендинг.
2. Отправьте тестовую заявку — должны прилететь:
   - письмо на `NOTIFY_EMAIL_TO`
   - сообщение в Telegram-бота
3. Логин в админку: `/admin/login` (учётка из `ADMIN_EMAIL` / `ADMIN_PASSWORD`).
4. Откройте `/admin/landing-edit` и попробуйте отредактировать любой блок.

## 5. Кастомный домен (опционально, позже)

- Netlify → Domain settings → Add custom domain.
- Самый дешёвый «настоящий» домен: `.ru` ~ 200 ₽/год (reg.ru, nic.ru).
- Бесплатные альтернативы: `js.org` (нужно одобрение), `is-a.dev` (для dev-проектов), поддомены Netlify/Cloudflare.

## 6. Безопасность

- Смените `ADMIN_PASSWORD` на сложный сразу после первого входа (через прямой UPDATE в БД или повторный сидинг; добавим UI смены пароля по запросу).
- Не коммитьте `.env` (он в `.gitignore`).
- SMTP-пароль используйте только «пароль приложения», а не основной пароль почты.
