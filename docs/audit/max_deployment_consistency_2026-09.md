# Аудит MAX и опыта миграции — 2026-09

## Каноническое решение

Production alerts: Alertmanager → `msp-max-alerter:9095/alert` → pymax userbot → MAX. Сессия создаётся вручную командой `docker exec -it ... --authorize` и хранится вне Git.

## Найденные старые куски

- Telegram MTProto инструкция под именем MAX;
- официальный MAX Bot API смешан с userbot-контуром;
- Alertmanager одновременно слал P1 в userbot и backend, создавая риск дублей;
- `session.session`/8080/`max-alerter` не соответствовали `max.db`/9095/`msp-max-alerter`;
- hardcoded phone/chat ID;
- сломанный Telegram fallback URL с фигурными скобками;
- `.env.example` обещал отсутствующий long polling;
- troubleshooting использовал другой MAX API domain;
- миграционный документ содержал реальные cloud/resource IDs и static access key;
- restore использовал нестабильное имя `msp-mongo-1` и переносил старые env поверх новой среды;
- SSH отключал проверку host key.

## Принятые решения

- monitoring alerts больше не отправляются через backend official Bot API;
- P1: MAX userbot + email, P2/P3: email;
- MAX secrets только из monitoring `.env`;
- webhook token fail-closed;
- зависимости userbot закреплены;
- миграция должна переносить данные и MAX session отдельно, но не старые cloud credentials;
- после переноса обязательны health, session check и тестовый webhook.
