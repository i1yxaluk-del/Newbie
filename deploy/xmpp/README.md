# XMPP-стек MSPShield (Prosody)

Полностью автономный XMPP-сервер на нашей ВМ. **Третьих лиц нет**: федерация (s2s) выключена,
сервер никуда не обращается. Звонки — через наш coturn, push — через наш ntfy.

## Что где

| Компонент | Значение |
|---|---|
| Домен (JID) | `x.msp-claude.online` — адрес вида `user@x.msp-claude.online` |
| Конференции | `con.msp-claude.online` |
| Подключение клиентов | `x.msp-claude.online:5222` (STARTTLS) |
| HTTP (файлы, websocket) | `https://x.msp-claude.online/` → Caddy → Prosody:5280 |
| Каталог на ВМ | `/opt/xmpp` |
| TURN для звонков | `turn.msp-claude.online:3478` (сервис coturn на ВМ) |
| Push | ntfy (UnifiedPush), контейнер `jami-ntfy` |

## Установка клиента (Android)

**Conversations** — из F-Droid или APK (Google Play в РФ может быть недоступен).
Затем: «Добавить аккаунт» → «Дополнительно» → ввести JID и пароль. Адрес сервера определится
автоматически по домену JID.

## Создание учёток

Публичная регистрация **выключена** — учётки создаёт администратор:

```bash
# на ВМ
sudo docker exec -u prosody msp-prosody prosodyctl register <логин> x.msp-claude.online <пароль>
```
> ⚠️ Обязательно с `-u prosody`: Prosody отказывается работать под root и `prosodyctl` тоже.

Пароль администратора лежит в `/root/.xmpp-admin.txt`.

## Эксплуатация

```bash
cd /opt/xmpp
sudo docker compose ps            # состояние
sudo docker compose logs -f       # логи
sudo docker compose restart       # перезапуск
sudo docker compose down          # остановить
```

Полное развёртывание с нуля (включая Caddy-блоки и копирование сертификатов):
```bash
sudo bash /opt/msp/Newbie/deploy/xmpp/deploy.sh
```

## Особенности, на которые мы наступили

1. **Официальный образ `prosody/prosody` на Docker Hub заброшен** — там версия 0.11.9 (2021),
   в которой нет `http_upload`, `mam`, `smacks`, `cloud_notify`. Поэтому образ собирается
   из официального репозитория prosody.im (Dockerfile в этом каталоге).
2. **Prosody не запускается под root** — «Danger, Will Robinson!». В `entrypoint.sh` права
   сбрасываются через `setpriv` на пользователя `prosody`.
3. **`muc` и `muc_mam` нельзя указывать в глобальном `modules_enabled`** — только на компоненте,
   иначе ошибка инициализации и трейсбек.
4. **`http_upload` в Prosody 13 вынесен из ядра** — ставится пакетом `prosody-modules`
   (или догружается из community-репозитория, см. Dockerfile).
5. **Сертификаты берём у Caddy** (свой ACME не нужен): Caddy выпускает для `x.` и `con.`,
   deploy.sh копирует их в `/opt/xmpp/certs`. При продлении сертификата Caddy файлы в контейнере
   нужно обновлять — см. раздел «Автопродление» ниже.

## Автопродление сертификатов

Caddy сам продлевает сертификаты. Чтобы Prosody подхватывал новые файлы, добавьте в cron ВМ:

```bash
# /etc/cron.d/xmpp-certs
0 4 * * * root for d in x.msp-claude.online con.msp-claude.online; do \
  b=/var/lib/caddy/.local/share/caddy/certificates/acme-v02.api.letsencrypt.org-directory/$d; \
  [ -f "$b/$d.crt" ] && cp "$b/$d.crt" /opt/xmpp/certs/$d.crt && cp "$b/$d.key" /opt/xmpp/certs/$d.key && \
  chmod 644 /opt/xmpp/certs/$d.crt && chmod 640 /opt/xmpp/certs/$d.key; done; \
  cd /opt/xmpp && docker compose restart prosody
```

## Медиа: как не забивать сервер

В `prosody.cfg.lua` задано:
- `http_upload_file_size_limit = 100 МБ` — лимит на файл;
- `http_upload_expire_after = 7 дней` — сервер сам удаляет старые файлы.

Если нужен режим «медиа вообще не на сервере» — уберите модуль `http_upload` из конфига:
тогда клиенты (Conversations) будут передавать файлы напрямую между устройствами (Jingle FT),
но получить файл можно будет только когда отправитель онлайн.

## Догонка 06.10.2026: Conversations не подключался — 5222 закрыт в Security Group

Симптом: Conversations «нет соединения с сервером», при этом в логах Prosody видны попытки.

Причина: 5222 был открыт в ufw на ВМ, но **не в Security Group Cloud.ru**. Проверка «доступности снаружи» прошлого прогона делалась с самой ВМ и вводила в заблуждение.

Исправление (через API Cloud.ru, проект `e39dc535-25e8-4d64-9572-885b08a1f37e`):
- SG ВМ `SSH-access_ru.AZ-3` (`5dc08e55-6819-4e23-92ad-47f18cb61b6a`)
- POST `/api/v1/security-groups/<sg>/rules`: ingress / IPv4 / tcp / `5222:5222` / `0.0.0.0/0` / «XMPP-c2s Conversations» → rule id `8e46038f-b3b3-44a4-bfdf-42a8e6f7bd27`

Проверено снаружи: TCP → `<starttls><required/>` → TLSv1.3 → SASL (SCRAM-SHA-1-PLUS / PLAIN) → `<success/>` на тестовой учётке — полный путь клиента работает.

Healthcheck контейнера: `prosodyctl status` в контейнере (запуск с `-F`) всегда падал («no pidfile option») → контейнер был `unhealthy`. Заменено на lua-socket TCP-проверку:
`test: ["CMD-SHELL", "lua -e "local s=require('socket'); local c=s.connect('127.0.0.1',5222); if c then c:close(); os.exit(0) else os.exit(1) end""]`

На заметку: SRV-записей `_xmpp-client._tcp.x` нет — клиенты используют fallback (A-запись + 5222). Можно добавить позже.
