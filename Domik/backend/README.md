# Domik — Backend

FastAPI + SQLite. Заявки, авторизация админа, редактор контента лендинга, нотификации Email + Telegram.

## Запуск локально

```bash
python -m venv .venv
.venv\Scripts\activate          # Windows
pip install -r requirements.txt
copy .env.example .env          # Windows
uvicorn app.main:app --reload
```

Swagger: http://127.0.0.1:8000/docs

## Эндпоинты
- `POST /api/leads` — публичный приём заявок (триггерит email + TG)
- `POST /api/auth/login` — логин админа (`email`, `password`)
- `GET  /api/leads` — список заявок (admin)
- `PATCH /api/leads/{id}` — смена статуса (admin)
- `DELETE /api/leads/{id}` — удалить (admin)
- `GET  /api/content` — публичный контент лендинга
- `PUT  /api/content` — обновить контент (admin) — основа `landing-edit`

## Нотификации
- Email через SMTP (см. `.env`: `SMTP_*`, `NOTIFY_EMAIL_TO`)
- Telegram через бота (`TG_BOT_TOKEN`, `TG_CHAT_ID`)

Если переменные пусты — нотификация молча пропускается (заявка всё равно сохраняется).
