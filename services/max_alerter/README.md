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

## Авторизация (сессия слетает при пересоздании контейнера)

**Запускать только с `-it`** — pymax отправляет SMS и ждёт ввод кода в терминале:

```bash
# На VM через SSH:
docker exec -it msp-max-alerter python -m max_alerter.auth

# → MAX отправляет SMS на +79990703823
# → Вводишь 6-значный код → сессия сохранена
```

Сессия: `/session/max.db` (volume: `/opt/msp-monitoring/max-session/`).

---

## Диагностика

```bash
# Логи контейнера (имя: msp-max-alerter, НЕ max-alerter!)
docker logs msp-max-alerter --tail 50

# Здоровье webhook
curl http://localhost:9095/health

# Проверить, жива ли MAX-сессия
docker exec msp-max-alerter python -c "
import asyncio
from pymax import Client
async def check():
    c = Client(phone='+79990703823', work_dir='/session', session_name='max.db')
    try:
        await asyncio.wait_for(c.start(), timeout=10)
        print('MAX session OK')
    except Exception as e:
        print('MAX session FAILED:', e)
asyncio.run(check())
"

# Лог недоставленных алертов
cat /opt/msp-monitoring/max-alerter-data/failed_alerts.log
```

---

## Безопасность

- Сессия хранится в SQLite, монтируется как volume — не внутри контейнера.
- Авторизация выполняется на хосте, не в Docker.
- Bearer-токен для webhook — рекомендуется.
- Telegram fallback — рекомендуется для критичных алертов.