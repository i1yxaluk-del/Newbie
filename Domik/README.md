# Domik · Гостевой дом «Алина» у Азовского моря

Минималистичный «летний» сайт гостевого дома с админкой и редактором лендинга.
Отправка заявок → уведомления на **email** + **Telegram**.

```
Domik/
├── backend/        FastAPI + SQLite (заявки, авторизация, контент)
├── frontend/       React + Vite (лендинг, /admin, /admin/landing-edit)
├── deploy/         Готовые конфиги Render + Netlify
├── docs/           BRAND.md, DEPLOY.md, CONTENT_FROM_VK.md
└── docker-compose.yml
```

## Стек
- **Backend**: Python 3.11, FastAPI, SQLAlchemy, SQLite, aiosmtplib (email), httpx (Telegram), JWT
- **Frontend**: React 18, Vite, React Router
- **Дизайн**: тёплая палитра моря и солнца (см. `docs/BRAND.md`), Inter + Marck Script

## Возможности
- Лендинг: hero, о доме, номера, удобства, галерея, расположение, контакты, форма брони
- Форма заявки → запись в БД → уведомление на личный email + в Telegram-бота
- Админка `/admin/leads`: список заявок, смена статуса, удаление
- Редактор `/admin/landing-edit`: правка любого текстового блока без деплоя
- Хранение секретов в `.env`, безопасный JWT, CORS, hash паролей (bcrypt)

## Быстрый старт (локально)

### Backend
```bash
cd Domik/backend
python -m venv .venv
.venv\Scripts\activate            # Windows
# source .venv/bin/activate       # Linux/Mac
pip install -r requirements.txt
copy .env.example .env            # Windows
# cp .env.example .env            # Linux/Mac
uvicorn app.main:app --reload
```
- API: http://127.0.0.1:8000
- Swagger: http://127.0.0.1:8000/docs

### Frontend
```bash
cd Domik/frontend
npm install
npm run dev
```
- Лендинг: http://localhost:5173
- Админка: http://localhost:5173/admin/login

Учётка по умолчанию (из `.env`): `admin@domik.local` / `ChangeMe2026!` — поменяйте.

### Docker (только backend)
```bash
cd Domik
docker compose up --build
```

## Уведомления о заявках

### Email (SMTP)
Заполните в `backend/.env`:
```
SMTP_HOST=smtp.yandex.ru
SMTP_PORT=465
SMTP_USE_TLS=true
SMTP_USER=ваш_ящик@yandex.ru
SMTP_PASSWORD=пароль_приложения
SMTP_FROM=ваш_ящик@yandex.ru
NOTIFY_EMAIL_TO=куда_слать_заявки@yandex.ru
```

### Telegram
1. У [@BotFather](https://t.me/BotFather): `/newbot` → получите `TG_BOT_TOKEN`
2. У [@userinfobot](https://t.me/userinfobot): узнайте `TG_CHAT_ID`
3. Напишите боту любое сообщение (иначе он не сможет писать вам)
4. Заполните `TG_BOT_TOKEN` и `TG_CHAT_ID` в `.env`

Если переменные пусты — заявка просто сохранится в БД, без падений.

## Деплой на бесплатный хостинг
Полная инструкция: `docs/DEPLOY.md`
Кратко:
- Backend → Render (free, Docker) — конфиг `deploy/render.yaml`
- Frontend → Netlify (free, статика) — конфиг `deploy/netlify.toml`
- Домен → `*.netlify.app` (бесплатный поддомен 2 уровня)

## Данные гостевого дома (предустановлены)
- Группа VK: https://vk.ru/gostevoy_domalina
- Руководитель: **Лукьянченко Александр Викторович**
- Телефон: **+7 918 212-96-01**
- VK руководителя: https://vk.ru/id135593764
- Фото руководителя: https://vk.ru/photo135593764_457241091

Подробности по контенту из VK: `docs/CONTENT_FROM_VK.md`.

## Маршруты API
| Метод | Путь | Доступ | Назначение |
| --- | --- | --- | --- |
| GET  | `/api/health` | public | проверка |
| POST | `/api/leads` | public | приём заявки + email + Telegram |
| POST | `/api/auth/login` | public | вход админа |
| GET  | `/api/leads` | admin | список заявок |
| PATCH| `/api/leads/{id}` | admin | смена статуса |
| DELETE | `/api/leads/{id}` | admin | удаление |
| GET  | `/api/content` | public | контент лендинга |
| PUT  | `/api/content` | admin | обновление контента |

## Roadmap (по запросу)
- Загрузка фото в галерею через админку
- Импорт фото из публичной VK-группы
- Календарь занятости / онлайн-бронирование
- Смена пароля админа из UI
- Мультиязычность (RU/EN)
