# MAX Alerter — каноническая настройка

## 1. Какая архитектура используется

В production алерты доставляются через отдельный webhook-сервис `msp-max-alerter` и пользовательскую сессию MAX:

```text
Prometheus → Alertmanager → POST http://msp-max-alerter:9095/alert
                              ↓
                        pymax userbot
                              ↓
                           MAX chat
```

Авторизация выполняется вручную внутри контейнера:

```bash
sudo docker exec -it msp-max-alerter python -m max_alerter.auth --authorize
```

Это **не Telegram MTProto**, не `my.telegram.org`, не `@BotFather` и не официальный MAX Bot API. Старые инструкции с `API_ID`, `API_HASH`, `session.session` и портом `8080` удалены как ошибочные.

## 2. Компоненты

| Компонент | Назначение |
|---|---|
| `services/max_alerter/webhook.py` | принимает Alertmanager webhook `/alert` |
| `services/max_alerter/sender.py` | отправляет в MAX и уведомляет о сбое через резервные каналы |
| `services/max_alerter/auth.py` | вручную создаёт `/session/max.db` |
| `deploy/yandex/monitoring/alertmanager/alertmanager.yml.tmpl` | направляет P1 в `msp-max-alerter:9095` |
| `deploy/yandex/monitoring/docker-compose.override.yml` | подставляет MAX-параметры из `.env`, не из Git |

`backend/integrations/max.py` относится к отдельному боту лидов. Он не является каналом production-алертов и не должен быть получателем Alertmanager при включённом userbot-контуре.

## 3. Обязательные переменные

Создайте `deploy/yandex/monitoring/.env` с правами `600`:

```env
MAX_PHONE=+7XXXXXXXXXX
MAX_CHAT_ID=-00000000000000
ALERTMANAGER_WEBHOOK_TOKEN=<случайная строка не короче 32 байт>
MAX_FAILURE_COOLDOWN=300

# Необязательный Telegram fallback
TELEGRAM_BOT_TOKEN=
TELEGRAM_CHAT_ID=

# Необязательное email-уведомление о поломке канала
SMTP_HOST=
SMTP_PORT=465
SMTP_USER=
SMTP_PASSWORD=
SMTP_FROM=
ALERT_EMAIL_TO=
```

Сгенерировать webhook token:

```bash
openssl rand -hex 32
```

Номер телефона, chat ID, токены и session database запрещено коммитить.

## 4. Первый запуск

```bash
cd /opt/msp/Newbie/deploy/yandex/monitoring
sudo chmod +x alertmanager/entrypoint.sh
sudo docker compose config >/dev/null
sudo docker compose up -d --build max-alerter alertmanager
```

Проверьте, что контейнер работает, но сессии ещё нет:

```bash
sudo docker ps --filter name=msp-max-alerter
sudo docker exec msp-max-alerter python -m max_alerter.auth
```

Код `2` до первой авторизации ожидаем.

## 5. Ручная web/SMS-авторизация

```bash
sudo docker exec -it msp-max-alerter python -m max_alerter.auth --authorize
```

1. Скрипт берёт номер из `MAX_PHONE`.
2. MAX отправляет код.
3. Оператор вводит код в интерактивном терминале.
4. Сессия сохраняется в `/session/max.db`.
5. Каталог на хосте: `deploy/yandex/monitoring/max-session/`.

Никогда не удаляйте рабочую сессию при обычном deploy. Повторная авторизация нужна только при утрате или отзыве сессии.

## 6. Проверка

```bash
# Сессия существует
sudo docker exec msp-max-alerter python -m max_alerter.auth

# Webhook жив
curl -fsS http://127.0.0.1:9095/health

# Alertmanager жив
curl -fsS http://127.0.0.1:9093/-/healthy

# Тестовый webhook из monitoring network
TOKEN=$(sudo awk -F= '$1=="ALERTMANAGER_WEBHOOK_TOKEN"{print $2}' .env)
sudo docker run --rm --network msp-monitoring curlimages/curl:8.10.1 \
  -fsS -X POST http://msp-max-alerter:9095/alert \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"status":"firing","alerts":[{"labels":{"alertname":"ManualTest","severity":"P1","env":"test"},"annotations":{"summary":"Тест MAX","description":"Удалить после проверки"}}]}'
```

Не публикуйте порт `9095` наружу. Он доступен только на `127.0.0.1` и в Docker network.

## 7. Проверка после reboot/deploy

```bash
cd /opt/msp/Newbie/deploy/yandex/monitoring
sudo docker compose up -d
sudo docker exec msp-max-alerter python -m max_alerter.auth
curl -fsS http://127.0.0.1:9095/health
sudo docker logs msp-max-alerter --tail 100
```

`docker compose restart` не перечитывает `.env`. После изменения переменных используйте:

```bash
sudo docker compose up -d --force-recreate max-alerter alertmanager
```

## 8. Перенос на новую VM

Переносить нужно каталог сессии отдельно от Git:

```bash
sudo tar czf /root/max-session-backup.tar.gz \
  -C /opt/msp/Newbie/deploy/yandex/monitoring max-session
```

На новой VM восстановить с правами только для root, затем выполнить проверку сессии. Если библиотека отвергает перенесённую сессию — удалить только нерабочий `max.db` и выполнить ручную авторизацию.

## 9. Диагностика

| Симптом | Проверка |
|---|---|
| `manual authorization required` | выполнить команду из раздела 5 |
| HTTP 401 | токены Alertmanager и max-alerter различаются |
| health OK, сообщений нет | проверить `MAX_CHAT_ID` и логи контейнера |
| MAX недоступен | проверить `failed_alerts.log`, Telegram/email fallback |
| после deploy старая конфигурация | `up -d --force-recreate`, не `restart` |
| контейнер не собирается | убедиться, что `services/max_alerter` включён в пакет переноса |

## 10. Безопасность

- `MAX_PHONE` и `MAX_CHAT_ID` только в ignored `.env`;
- `/session/max.db` считать эквивалентом учётных данных;
- webhook token обязателен в production;
- порт 9095 не публиковать в интернет;
- session backup хранить зашифрованно;
- при подозрении на компрометацию отозвать сессию и авторизоваться заново.

## 11. Что является legacy

Следующие элементы не относятся к production MAX alerter:

- `MAX_BOT_TOKEN` и `/api/max/webhook` — бот лидов;
- `platform-api.max.ru` — бот лидов;
- `API_ID`, `API_HASH`, Telethon, `my.telegram.org` — ошибочный Telegram-контент;
- `session.session`, порт `8080`, контейнер `max-alerter` — устаревшие значения.

## 12. Локальная разработка

Без реальной MAX-сессии запускайте unit-тесты форматирования и webhook. Для end-to-end требуется тестовый MAX-аккаунт и ручная авторизация. Long polling в проекте не реализован.
