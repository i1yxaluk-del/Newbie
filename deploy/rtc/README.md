# RTC-стек MSPShield: LiveKit + lk-jwt + Element Call

Обслуживает **звонки MatrixRTC** (Element Call: видео/голос в Element Web, Element X, групповые звонки).
Деплой: `/opt/rtc` на VM (docker compose), домен: **dht.msp-claude.online** (свободный A-рекорд;
при желании переезжает на `call.` — правки в Caddy + matrix_rtc.transports + element_call.url).

## Состав (docker compose)

| Сервис | Образ | Порты | Роль |
|---|---|---|---|
| livekit | livekit/livekit-server | 127.0.0.1:7880; TCP 7881; UDP 49200–49250 | SFU (медиа-сервер) |
| lk-jwt | ghcr.io/element-hq/lk-jwt-service | 127.0.0.1:8088 | выдача LiveKit-токенов после проверки openid |
| element-call | ghcr.io/element-hq/element-call | 127.0.0.1:8083 | веб-приложение звонков |

Caddy (dht.msp-claude.online): `/livekit/jwt/*` → 8088 (strip prefix), `/livekit/sfu*` → 7880 (strip prefix), `/` → 8083.

## Ключевые решения и грабли

- **Медиа-порты**: LiveKit использует диапазон UDP **49200–49250** (уже открыт в SG/ufw вместе с TURN-relay),
  coturn сужен до **49160–49199** (не пересекаются). TCP-фолбэк LiveKit (7881) в ufw открыт, но в cloud.ru SG
  нужно правило — на 06.10.2026 API правил cloud.ru отдаёт 403, добавить через консоль при необходимости.
- **Грабли (мостовая сеть)**: при bridge-режиме диапазон ОБЯЗАН публиковаться в compose
  (`"49200-49250:49200-49250/udp"`) — без этого ICE-проверки умирают (Element X: «Failed to connect to LiveKit
  server / Internal Error»), т.к. UDP на этих портах не попадает в контейнер. DNAT-правила проверять:
  `iptables -t nat -S DOCKER | grep -c "dport 492"` (ожидаем 51).
- **lk-jwt → Synapse**: сервис валидирует openid через федерацию. Нужен `.well-known/matrix/server` на m. домене
  (`{"m.server":"m.msp-claude.online:443"}`); после добавления — **перезапустить msp-lk-jwt** (кэш discovery).
  Дополнительно в Caddy есть листенер `m.msp-claude.online:8448` (внутренний фолбэк).
- **Секреты**: `keys` в livekit.yaml и `LIVEKIT_KEY/SECRET` в compose — плейсхолдеры `__LK_KEY__`/`__LK_SECRET__`,
  заполняются при деплое **одинаковыми** значениями; проверять согласованность.
- **Synapse** (homeserver.yaml): блоки `experimental_features` (msc3266/4143/4222), `max_event_delay_duration`,
  `rc_message`, `rc_delayed_event_mgmt`, `matrix_rtc.transports[0].livekit_service_url`.
- **Element Web** (element-config.json): `element_call: {url, use_exclusively: true}` — все звонки идут через EC;
  пользователям нужен hard-refresh (Ctrl+Shift+R) чтобы подхватить новый config.
- Сквозной тест без клиента: `POST /_matrix/client/v3/user/<u>/openid/request_token` →
  `POST {url}/livekit/jwt/sfu/get` c `{"room": "...", "openid_token": {...}, "device_id": "..."}` → вернуть url+jwt.

## Обновление

```bash
cd /opt/rtc && docker compose up -d   # после правки livekit.yaml: docker restart msp-livekit
```
