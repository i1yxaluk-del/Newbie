# Локальная разработка MSPShield

Цель: запустить весь стек (frontend + backend + MongoDB) на своей машине, открыть `http://localhost:3000`, увидеть лендинг, отправить тестовую заявку.

**Время:** ~20 минут (первый раз), ~3 минуты (повторный запуск).
**Стоимость:** 0 ₽.

## Требования

| Инструмент | Минимум | Проверка |
|------------|---------|----------|
| Docker | 24.0+ | `docker --version` |
| Docker Compose | 2.20+ | `docker compose version` |
| Git | 2.40+ | `git --version` |
| Свободная память | 4 ГБ | — |
| Порты свободны | 3000, 8001, 27017 | `ss -ltn \| grep -E ":(3000\|8001\|27017)"` |

Если Docker не установлен:

- **Ubuntu/Debian:** `curl -fsSL https://get.docker.com | sudo sh`
- **macOS:** [Docker Desktop](https://www.docker.com/products/docker-desktop/)
- **Windows:** WSL2 + Docker Desktop.

## Шаг 1. Клонирование репо

```bash
git clone https://github.com/i1yxaluk-del/Newbie.git
cd Newbie
```

## Шаг 2. Подготовка backend/.env

```bash
cp backend/.env.example backend/.env
# Сгенерировать ADMIN_TOKEN для защиты /api/leads GET/PATCH:
openssl rand -hex 32
# Скопировать вывод и заменить значение ADMIN_TOKEN= в backend/.env
```

Минимально в `backend/.env`:

```env
MONGO_URL=mongodb://mongo:27017
DB_NAME=mspshield
ADMIN_TOKEN=<сгенерированная-строка-на-шаге-выше>
CORS_ORIGINS=http://localhost:3000
```

Telegram-/MAX-нотификации и SmartCaptcha для локальной разработки **не нужны** — оставить пустыми (`TG_BOT_TOKEN=`, `MAX_BOT_TOKEN=`). Если хочется проверить MAX-интеграцию локально — см. [`docs/MAX_SETUP.md` §12 «Локальный dev»](../MAX_SETUP.md).

## Шаг 3. Запуск через docker compose

```bash
cd deploy
docker compose up -d --build
```

Проверка, что все три сервиса поднялись:

```bash
docker compose ps
# NAME                STATUS
# deploy-backend-1    Up
# deploy-frontend-1   Up
# deploy-mongo-1      Up
```

## Шаг 4. Проверка работоспособности

### Backend

```bash
curl http://localhost:8001/api/health
# {"status":"ok","timestamp":"..."}

curl http://localhost:8001/metrics | head -5
# # HELP mspshield_leads_total Total leads received
# ...
```

### Frontend

Открыть `http://localhost:3000`:

1. Лендинг должен отображаться (3 карточки тарифов: Bronze 25k / Silver 50k / Gold 85k).
2. Нажать «Оставить заявку» → форма откроется.
3. Заполнить имя, телефон, email, отметить согласие → отправить.
4. Ожидаем «спасибо, свяжемся в течение 2 часов».

### Админка

```bash
curl -H "X-Admin-Token: <тот-же-ADMIN_TOKEN>" http://localhost:8001/api/leads
# [{"id":"...","name":"...","phone":"...","status":"новая","created_at":"..."}]
```

Должна быть 1 заявка из предыдущего шага.

## Повторный запуск

```bash
cd deploy
docker compose up -d
```

## Остановка / очистка

```bash
# Остановить без удаления данных:
docker compose down

# Удалить контейнеры И данные MongoDB:
docker compose down -v
```

## Разработка (hot-reload)

Если активно меняешь код backend, docker compose build-and-up долго. Удобнее:

```bash
# Терминал 1 — MongoDB в docker
docker run -d --name mspshield-mongo -p 27017:27017 mongo:6

# Терминал 2 — backend с uvicorn --reload
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn server:app --reload --port 8001

# Терминал 3 — frontend с hot-reload
cd frontend
yarn install
yarn start  # открывает http://localhost:3000
```

В `backend/.env` временно поменять `MONGO_URL=mongodb://localhost:27017`.

## Типовые проблемы

### Порт 27017 занят

У вас уже запущен MongoDB локально. Либо остановите его (`sudo systemctl stop mongod`), либо поменяйте порт в `deploy/docker-compose.yml` → `mongo.ports: "27018:27017"` и в `backend/.env` → `MONGO_URL=mongodb://mongo:27017` (оставить 27017 — это **внутренний** порт контейнера).

### Frontend ругается на CORS

Проверить `CORS_ORIGINS` в `backend/.env` — должен быть `http://localhost:3000` (без слеша в конце).

### Form submission возвращает 429

Сработал rate-limit (10 запросов в минуту на IP). Подожди минуту или в `backend/.env` временно: `RATE_LIMIT_PER_MIN=1000`.

### «Please accept consent» при отправке формы

Забыл отметить галочку «Согласен на обработку ПД (152-ФЗ)». Поле обязательное.

## Что дальше

Если локально всё работает и хочешь выкатывать в прод → [`landing_production.md`](landing_production.md).

Если только смотришь проект — продолжай изучать [`../roadmap/etape_4_sprints.md`](../roadmap/etape_4_sprints.md).
