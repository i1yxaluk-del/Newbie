# MSPShield · Гид администратора (Junior-friendly)

> **Кому:** инженеру/админу, который впервые видит этот сайт. Цель —
> поднять MSPShield локально и в проде, починить типовые проблемы и
> уметь смотреть тестовые заявки в CRM.
>
> **Версия:** v4.5 (минималистичный лендинг + JWT-логин админки + Kaiten CRM).

---

## 1. Что это (за 60 секунд)

MSPShield — это маркетинговый лендинг + форма заявки + админка.

```
[Браузер пользователя]
        │ HTTPS
        ▼
[ nginx ]  ─── /        → React SPA (build/)
   │       ─── /api/    → FastAPI (127.0.0.1:8001)
   │       ─── /metrics → Prometheus (внутренняя сеть)
   ▼
[ FastAPI · backend/server.py ]
   │
   ├── MongoDB                 ─── основное хранилище заявок
   ├── Telegram Bot (опц.)     ─── мгновенный пинг в чат менеджеру
   ├── Kaiten REST API (опц.)  ─── создаёт карточку в воронке Sales
   └── CRM_WEBHOOK_URL (опц.)  ─── n8n / Make / Zapier / Bitrix24
```

Лид сначала пишется в Mongo (источник истины), затем в фоне рассылается
во все включённые каналы. Если CRM упал — лид всё равно сохранён, его
видно в админке.

---

## 2. Локальный запуск (5 минут)

Требования: `docker` + `docker compose` + `python 3.12` + `node 20+` + `yarn 1.22`.

```bash
git clone https://github.com/i1yxaluk-del/Newbie.git
cd Newbie

# 2.1 — секреты
cp backend/.env.example backend/.env
# В backend/.env минимум проверь:
#   ADMIN_TOKEN — это пароль для входа в /admin (можно оставить дефолт в dev)
#   MONGO_URL   — mongodb://localhost:27017 если поднимешь докером ниже

# 2.2 — поднимаем MongoDB
docker run -d --name mspshield-mongo --rm -p 27017:27017 mongo:7

# 2.3 — backend
cd backend
pip install -r requirements.txt
uvicorn server:app --reload --host 127.0.0.1 --port 8001
# → http://127.0.0.1:8001/api/health должен отдать {"status":"ok"}

# 2.4 — frontend (новое окно)
cd ../frontend
echo 'REACT_APP_BACKEND_URL=http://127.0.0.1:8001' > .env
yarn install
yarn start
# → http://localhost:3000  лендинг
# → http://localhost:3000/admin  админка (введи ADMIN_TOKEN)
```

Чек-лист «всё работает локально»:

- [ ] `curl localhost:8001/api/health` → `200 ok`
- [ ] Открыл `localhost:3000`, лендинг загрузился без ошибок в консоли
- [ ] Заполнил форму, дождался зелёной плашки «Заявка принята»
- [ ] В `localhost:3000/admin` вошёл по `ADMIN_TOKEN` → твоя заявка в списке
- [ ] Сменил статус через выпадашку → перезагрузил → статус сохранился

### 2.1. Типовые ошибки локального запуска

**«Не удалось отправить. Попробуйте ещё раз.» + в логах backend `Connection refused`**

В логах увидишь:
```
mspshield - WARNING - failed to ensure indexes: localhost:27017 [Errno 111] Connection refused
```
Это значит, что backend стартовал, но Mongo не запущена.
Причина: ты не поднял Mongo, или контейнер остановился после ребута.
Решение:
```bash
# одной командой:
docker run -d --name mspshield-mongo --restart=always -p 27017:27017 mongo:7
# или, если контейнер уже создан:
docker start mspshield-mongo
```

**В консоли браузера: `POST http://localhost:3000/api/leads 404` или `GET http://192.168.x.x:3000/api/health 404`**

Frontend стучится сам в себя (на `:3000`), а не в backend (на `:8001`).
Причина: пустой/отсутствующий `frontend/.env` с переменной `REACT_APP_BACKEND_URL`.
Решение:
```bash
cd frontend
echo "REACT_APP_BACKEND_URL=http://localhost:8001" > .env  # или http://192.168.x.x:8001 если открываешь не с localhost
# CRA читает .env только при старте — обязательно перезапусти:
yarn start
```
Ещё нюанс: если открываешь сайт с другой машины в локалке (`http://192.168.x.x:3000`), backend подними на `0.0.0.0` и в `backend/.env` пропиши:
```
CORS_ORIGINS=*  # только для dev! в проде — конкретный домен
```
И запусти backend как `uvicorn server:app --host 0.0.0.0 --port 8001 --reload`.

---

## 3. Production-развёртывание (Yandex Cloud, базовая конфигурация)

### 3.1. Инфраструктура

```
mspshield-landing  ── nginx + frontend build + FastAPI + Mongo (1 VM)
mspshield-bastion  ── WireGuard + центр управления (опц., см. docs/deployment/)
mspshield-monitor  ── Prometheus + Grafana (опц.)
```

Минимум — одна VM. Бэкап Mongo — на S3 (Object Storage).

### 3.2. Переменные

```bash
# на VM:
sudo -u mspshield bash -c '
  cd /home/mspshield/app/backend
  cp .env.example .env
  sed -i "s/ADMIN_TOKEN=.*/ADMIN_TOKEN=$(openssl rand -hex 32)/" .env
  sed -i "s|MONGO_URL=.*|MONGO_URL=mongodb://localhost:27017|" .env
  sed -i "s|DB_NAME=.*|DB_NAME=mspshield|" .env
  sed -i "s|CORS_ORIGINS=.*|CORS_ORIGINS=https://mspshield.ru|" .env
'
```

Опциональные интеграции (заполняются ПОСЛЕ создания учёток в Telegram/Kaiten — см. разделы 5–6):

```
TG_BOT_TOKEN=…
TG_CHAT_ID=…
KAITEN_DOMAIN=acme.kaiten.ru
KAITEN_API_TOKEN=…
KAITEN_BOARD_ID=…
KAITEN_COLUMN_ID=…
CRM_WEBHOOK_URL=…    # опционально вместо/вместе с Kaiten
```

### 3.3. Сервисы (systemd)

```ini
# /etc/systemd/system/mspshield-backend.service
[Unit]
Description=MSPShield FastAPI backend
After=network.target mongod.service
Requires=mongod.service

[Service]
Type=simple
User=mspshield
WorkingDirectory=/home/mspshield/app/backend
Environment=PYTHONUNBUFFERED=1
ExecStart=/home/mspshield/.local/bin/uvicorn server:app --host 127.0.0.1 --port 8001 --workers 2
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now mspshield-backend
sudo systemctl status mspshield-backend
```

### 3.4. Frontend build + nginx

```bash
cd /home/mspshield/app/frontend
yarn install --frozen-lockfile
yarn build
sudo rsync -a --delete build/ /var/www/mspshield/

# nginx конфиг (готовый):
sudo cp /home/mspshield/app/deploy/nginx/mspshield.conf /etc/nginx/sites-available/
sudo ln -sf /etc/nginx/sites-available/mspshield.conf /etc/nginx/sites-enabled/
sudo nginx -t && sudo systemctl reload nginx

# TLS:
sudo certbot --nginx -d mspshield.ru -d www.mspshield.ru
```

### 3.5. Бэкап Mongo (cron + S3)

```bash
# /etc/cron.d/mspshield-backup
0 3 * * * mspshield /home/mspshield/app/scripts/backup_mongo.sh >> /var/log/mspshield-backup.log 2>&1
```

Подробнее — [`docs/deployment/landing_production.md`](deployment/landing_production.md).

---

## 4. Админка — как пользоваться

### 4.1. Вход

1. Открой `https://mspshield.ru/admin`.
2. Введи **значение `ADMIN_TOKEN`** из `backend/.env` (это пароль).
3. Получишь JWT-сессию на 24 часа — повторно вводить не нужно.

### 4.2. Что внутри

- Таблица заявок (новые сверху).
- Фильтры: по статусу (новая / связались / квалифицирован / Win / Lost) и тарифу.
- Кнопка «Экспорт CSV» — выгружает все заявки.
- Колонка **Kaiten** — кликабельная ссылка прямо на карточку лида в CRM
  (если интеграция включена).
- Меняй статус через select — изменения сохраняются мгновенно.

### 4.3. Что делать, если не работает

| Симптом                        | Причина                                                          | Что сделать                                                                                                                |
| ------------------------------ | ---------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------- |
| Красная плашка «Backend недоступен» | Backend упал или nginx не проксирует `/api/`                      | `sudo systemctl status mspshield-backend` → `journalctl -u mspshield-backend -n 100`. `curl https://mspshield.ru/api/health` |
| 401: пароль не совпадает       | Введён не тот `ADMIN_TOKEN` или JWT истёк                         | Возьми текущий из `backend/.env`. Если ротировал — все JWT инвалидируются (фича).                                          |
| 503: `Admin access not configured` | На сервере пустой `ADMIN_TOKEN`                                  | `grep ADMIN_TOKEN backend/.env` → должен быть непустым. Перезапустить backend.                                             |
| `/admin` показывает 404        | nginx не настроен на SPA fallback                                  | В `nginx.conf`: `try_files $uri /index.html;` для `location /`.                                                            |
| Заявок нет, форма работает     | Форма пишет в Mongo, но админка читает другую базу                 | `grep DB_NAME backend/.env` совпадает с тем, куда форма пишет?                                                             |

---

## 5. Kaiten CRM — настройка с нуля и просмотр заявок

> **Зачем Kaiten:** отдел продаж (даже если он = ты + второй человек)
> работает удобнее в карточках/колонках, чем в табличке админки. Бесплатный
> тариф Kaiten покрывает до 10 пользователей и поддерживает API.

### 5.1. Регистрация (5 минут)

1. Открой <https://kaiten.ru>, зарегистрируйся бесплатно.
2. Получишь домен вида `https://acme.kaiten.ru` — это `KAITEN_DOMAIN`
   (без `https://`).
3. Зайди в **профиль → API → Создать токен** → скопируй. Это `KAITEN_API_TOKEN`.

### 5.2. Создание базы (одной командой)

```bash
cd /home/mspshield/app
KAITEN_DOMAIN=acme.kaiten.ru \
KAITEN_API_TOKEN=ваш_токен \
python scripts/kaiten_bootstrap.py
```

Скрипт сам создаст:

- **Space** «MSPShield · Sales»
- **Board** «Lead Pipeline»
- **6 колонок**:
  `Новая` → `Первичный контакт` → `Аудит` → `КП` → `Переговоры` → `Закрыта · Win/Lost`

Скрипт **идемпотентен** — можно запускать многократно, дубли не создаются.

В конце выводит:

```
KAITEN_DOMAIN=acme.kaiten.ru
KAITEN_BOARD_ID=12345
KAITEN_COLUMN_ID=67890
Открой доску в браузере: https://acme.kaiten.ru/space/.../boards/12345
```

Скопируй `KAITEN_BOARD_ID` и `KAITEN_COLUMN_ID` в `backend/.env`, перезапусти backend.

### 5.3. Тестовые заявки

Чтобы убедиться, что цепочка форма → backend → Mongo → Kaiten работает:

```bash
BACKEND_URL=https://mspshield.ru python scripts/seed_test_lead.py
```

Скрипт отправит 3 тестовые заявки с префиксом `[test]` в названии и
`source=test` в полях. Через 1–2 секунды:

- В **админке** (`/admin`) появятся 3 строки с `source=test`.
- В **Kaiten** в колонке «Новая» доски «Lead Pipeline» — 3 карточки
  `[bronze|silver|gold] TEST · ООО ...`.
- В **Telegram** (если настроен) — 3 уведомления.

### 5.4. Удалить тестовые заявки

В админке: фильтр по `source=test` — выбираешь и удаляешь через Mongo
(`db.leads.deleteMany({source:"test"})`) или просто игнорируешь.

В Kaiten: открой доску → найди карточки `[test ...]` → выдели → удали.

### 5.5. Что делать, если Kaiten не отвечает

Лиды всё равно сохраняются в Mongo, ты ничего не теряешь. Проверь:

```bash
# свежие логи backend'а: ищи "kaiten ..."
sudo journalctl -u mspshield-backend -n 200 | grep -i kaiten

# проверка токена руками:
curl -H "Authorization: Bearer $KAITEN_API_TOKEN" \
     https://$KAITEN_DOMAIN/api/latest/users/current
```

Если `401` — токен протух или скопирован неверно, перевыпусти.

---

## 6. Telegram-уведомления (опционально, 3 минуты)

1. В Telegram открой [@BotFather](https://t.me/BotFather), `/newbot`,
   придумай имя — получишь токен `123456:AAB...`. Это `TG_BOT_TOKEN`.
2. Открой [@getmyid_bot](https://t.me/getmyid_bot), он пришлёт `chat_id`
   (число). Это `TG_CHAT_ID`.
3. **Важно:** напиши боту любое сообщение (можно `/start`) — иначе он не
   сможет тебе отвечать.
4. Внеси значения в `backend/.env`, перезапусти backend.
5. Отправь тестовый лид через `seed_test_lead.py` — придёт уведомление.

---

## 7. Универсальный CRM webhook (для не-Kaiten)

Если используешь n8n / Make / Zapier / Bitrix24 inbound webhook /
самодельный сервис — настрой вместо или вместе с Kaiten:

```bash
# backend/.env
CRM_WEBHOOK_URL=https://my-n8n.example.com/webhook/mspshield-leads
CRM_WEBHOOK_TOKEN=secret-bearer  # опционально, в Authorization header
```

POST приходит JSON-ом со всеми полями лида (см. модель `Lead` в `backend/server.py`).
Включить можно одновременно с Kaiten — лид уйдёт в оба канала.

---

## 8. Чек-лист «готов к запуску»

- [ ] `ADMIN_TOKEN` сгенерирован через `openssl rand -hex 32` (не дефолт!)
- [ ] `CORS_ORIGINS` указывает на боевой домен (не `*`)
- [ ] `MONGO_URL` указывает на боевую Mongo (с auth, не `localhost`)
- [ ] `mspshield-backend.service` стартует через systemd, виден в `systemctl status`
- [ ] nginx отдаёт TLS (curl `https://mspshield.ru/api/health` → `200`)
- [ ] Бэкап Mongo в cron, тест-восстановление сделан хотя бы раз
- [ ] Yandex Metrika / счётчик посещений установлен (если используется)
- [ ] Kaiten бутстрап выполнен, `seed_test_lead.py` создаёт карточки
- [ ] Telegram-бот пингует канал
- [ ] `/admin` логин по `ADMIN_TOKEN` работает, JWT в localStorage держится
- [ ] CSP не ругается в браузере (DevTools → Console)

---

## 9. Типовые проблемы и команды

```bash
# Перезапустить backend (после правок .env):
sudo systemctl restart mspshield-backend

# Проверить, что nginx отдаёт правильный конфиг:
sudo nginx -T | less

# Ошибки последнего часа:
sudo journalctl -u mspshield-backend --since "1 hour ago"

# Метрики Prometheus (внутренняя сеть):
curl http://127.0.0.1:8001/metrics | grep mspshield_

# Сколько заявок за сутки (без админки):
docker exec -it mspshield-mongo mongosh mspshield --quiet --eval \
  'db.leads.countDocuments({created_at:{$regex:"^"+new Date().toISOString().slice(0,10)}})'

# Сделать бэкап вручную прямо сейчас:
docker exec mspshield-mongo mongodump --archive --gzip > "mspshield-$(date +%F-%H%M).gz"

# Восстановить из бэкапа:
gunzip -c mspshield-2026-05-01-0300.gz | docker exec -i mspshield-mongo mongorestore --archive --gzip
```

---

## Куда смотреть дальше

- [`README.md`](../README.md) — общее описание стэка
- [`docs/deployment/landing_production.md`](deployment/landing_production.md) — продакшен в Yandex Cloud, детально
- [`docs/sales/`](sales/) — рабочая воронка продаж + скрипты
- [`docs/audit/`](audit/) — bug-fix реестр прошлых релизов
- [`backend/server.py`](../backend/server.py) — бизнес-логика API
- [`backend/integrations/kaiten.py`](../backend/integrations/kaiten.py) — что отправляется в CRM
- [`scripts/kaiten_bootstrap.py`](../scripts/kaiten_bootstrap.py) — создание базы в CRM
- [`scripts/seed_test_lead.py`](../scripts/seed_test_lead.py) — тестовые заявки

Если что-то не работает — копируй сообщение об ошибке + кусок логов и
приходи к старшему. Не пытайся «починить руками в проде» без бэкапа Mongo.
