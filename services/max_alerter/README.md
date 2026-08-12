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

## Авторизация и постоянная сессия

**Запускать только с `-it`** — pymax отправляет SMS и ждёт ввод кода в терминале:

```bash
# На VM через SSH:
docker exec -it msp-max-alerter python -m max_alerter.auth --authorize

# → MAX отправляет SMS на +79990703823
# → Вводишь 6-значный код → сессия сохранена
```

Сессия: `/session/max.db`, bind mount
`/opt/msp/Newbie/deploy/yandex/monitoring/max-session:/session`.
Это host path, поэтому `docker compose down/up`, restart Docker и recreate
контейнера не удаляют его. Не удаляйте данный каталог.

Безопасная проверка после reboot (не запускает pymax и не отправляет SMS):

```bash
docker exec msp-max-alerter python -m max_alerter.auth
docker inspect msp-max-alerter --format '{{range .Mounts}}{{println .Source "->" .Destination}}{{end}}'
```

Команда проверки возвращает `0`, если файл есть, и `2`, если отсутствует.
При отсутствии или ошибке сессии сервис не инициирует авторизацию: он делает
одну неуспешную попытку доставки, затем подавляет MAX-повторы на cooldown.
Реавторизация всегда выполняется оператором с `--authorize`.

---

## Диагностика

```bash
# Логи контейнера (имя: msp-max-alerter, НЕ max-alerter!)
docker logs msp-max-alerter --tail 50

# Здоровье webhook
curl http://localhost:9095/health

# Проверить наличие сессии безопасно (без pymax/SMS)
docker exec msp-max-alerter python -m max_alerter.auth

# Лог недоставленных алертов
cat /opt/msp/Newbie/deploy/yandex/monitoring/max-alerter-data/failed_alerts.log
```

---

## Безопасность

- Сессия хранится в SQLite, монтируется как volume — не внутри контейнера.
- Авторизация выполняется на хосте, не в Docker.
- Bearer-токен для webhook — рекомендуется.
- Telegram и email независимы. При ошибке MAX или Telegram уведомление о
  неисправном канале уходит на email, не блокируя остальные каналы.
- Токены и SMTP-пароли задаются только в ignored `.env` на VM.
