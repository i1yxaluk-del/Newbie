# max_alerter — доставка алертов Alertmanager в MAX

Python-сервис, который принимает вебхуки от Alertmanager и доставляет
алерты в мессенджер MAX через неофициальный userbot (pymax).

> ⚠️ Использует внутренний API MAX. Работает на ваш страх и риск.
> Рекомендуется резервный канал (Telegram fallback) на случай блокировки.

---

## Архитектура

```
┌─────────────┐     POST /alert      ┌──────────────┐
│ Alertmanager│ ───────────────────► │ max_alerter  │
│  (webhook)  │   Bearer token       │  (FastAPI)   │
└─────────────┘                      └──────┬───────┘
                                          │
                     ┌────────────────────┘
                     │ TCP + SQLite session
                     ▼
            ┌─────────────────┐
            │   MAX (pymax)   │
            │  userbot client  │
            └─────────────────┘
                     │
       ┌─────────────┴─────────────┐
       │                           │
       ▼                           ▼
 ┌──────────┐              ┌──────────────┐
 │  MAX chat │  (fallback)  │  Telegram   │
 │  (client) │◄────────────│  (httpx)    │
 └──────────┘   (if MAX    └──────────────┘
                  fails)
```

---

## Быстрый старт

### 1. Авторизация (один раз, на хосте)

```bash
pip install maxapi-python
python auth.py --phone +79991234567 --session ./session/max.db
```

Введите SMS-код. Сессия сохранится в SQLite-файл.

### 2. Запуск в Docker

```bash
docker build -t max-alerter .
docker run -d \
-p 9095:9095 \
-v $(pwd)/session:/session \
-v $(pwd)/data:/data \
-e MAX_PHONE=+79991234567 \
-e MAX_CHAT_ID=1234567890 \
-e WEBHOOK_TOKEN=changeme \
-e TG_BOT_TOKEN=... \
-e TG_CHAT_ID=... \
max-alerter
```

### 3. Настройка Alertmanager

```yaml
receivers:
- name: max_alerts
  webhook_configs:
    - url: "http://max-alerter:9095/alert"
      send_resolved: true
      http_config:
        bearer_token: changeme
```

---

## Переменные окружения

| Переменная       | Описание                              | Обязательная |
|------------------|---------------------------------------|--------------|
| `MAX_PHONE`      | Номер телефона аккаунта MAX           | да           |
| `MAX_CHAT_ID`    | chat_id клиента в MAX (куда слать)    | да           |
| `WEBHOOK_TOKEN`  | Bearer-токен для входящих вебхуков    | нет          |
| `TG_BOT_TOKEN`   | Telegram-бот для fallback             | нет          |
| `TG_CHAT_ID`     | Telegram chat_id для fallback         | нет          |
| `MAX_SESSION_DIR`| Директория с SQLite-сессией           | `/session`   |
| `MAX_SESSION_NAME`| Имя файла сессии                      | `max.db`     |
| `FAILED_LOG`     | Лог недоставленных алертов            | `/data/failed_alerts.log` |

---

## Структура

```
services/max_alerter/
├── auth.py           # Интерактивная авторизация (CLI)
├── sender.py         # Отправка в MAX + Telegram fallback
├── webhook.py        # FastAPI сервер (Alertmanager webhook)
├── Dockerfile        # Контейнер
├── requirements.txt  # Зависимости
└── README.md         # Этот файл
```

---

## Диагностика

```bash
# Проверка здоровья
curl http://localhost:9095/health

# Просмотр лога недоставленных
cat data/failed_alerts.log
```

---

## Безопасность

- Сессия хранится в SQLite, монтируется как volume — не внутри контейнера.
- Авторизация выполняется на хосте, не в Docker.
- Bearer-токен для webhook — рекомендуется.
- Telegram fallback — рекомендуется для критичных алертов.