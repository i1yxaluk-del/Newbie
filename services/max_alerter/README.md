# max_alerter — production webhook для MAX

Канонический путь: Alertmanager отправляет webhook на `msp-max-alerter:9095/alert`, сервис доставляет сообщение через вручную авторизованную пользовательскую сессию MAX.

## Запуск

```bash
cd /opt/msp/Newbie/deploy/yandex/monitoring
sudo docker compose up -d --build max-alerter alertmanager
sudo docker exec -it msp-max-alerter python -m max_alerter.auth --authorize
```

Сессия: `/session/max.db`, на хосте — `deploy/yandex/monitoring/max-session/max.db`. Авторизация всегда ручная; сервис не должен сам инициировать SMS.

## Проверка

```bash
sudo docker exec msp-max-alerter python -m max_alerter.auth
curl -fsS http://127.0.0.1:9095/health
sudo docker logs msp-max-alerter --tail 100
```

Полная инструкция и перенос: [`../../docs/MAX_SETUP.md`](../../docs/MAX_SETUP.md).

## Границы

- Это не официальный Bot API и не Telegram MTProto.
- `backend/integrations/max.py` — отдельный бот лидов.
- Номер, chat ID, webhook token и session database не хранятся в Git.
- Telegram используется только как необязательный fallback при отказе MAX.
