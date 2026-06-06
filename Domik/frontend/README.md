# Domik — Frontend (React + Vite)

Минималистичный «летний» лендинг гостевого дома «Алина» у Азовского моря, плюс админка и landing-edit.

## Запуск
```bash
cd Domik/frontend
npm install
npm run dev
```
Откройте http://localhost:5173

Бэкенд должен быть запущен на http://127.0.0.1:8000 (см. `Domik/backend/README.md`).
В dev-режиме Vite сам проксирует `/api` на бэкенд.

## Сборка
```bash
npm run build
```
Результат в `dist/` — статика, готовая для деплоя на Netlify/Vercel/Cloudflare Pages.

Для прод-деплоя задайте `VITE_API_URL=https://your-backend.example` перед `npm run build`.

## Маршруты
- `/` — лендинг
- `/admin/login` — вход в админку
- `/admin/leads` — заявки
- `/admin/landing-edit` — редактор контента лендинга
