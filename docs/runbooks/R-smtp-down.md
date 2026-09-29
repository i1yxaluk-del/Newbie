# R-smtp-down · Почта недоступна

**Основной production path:** сервис → `postbox.cloud.yandex.net:465` implicit TLS. Stalwart — optional profile `mail`.

## Диагностика

1. Определить отправителя: backend, Alertmanager, Grafana, Vaultwarden или Stalwart.
2. `535 Authentication failed`: username должен быть ID API-ключа, не service-account ID.
3. `550 identity not verified`: проверить identity и DKIM CNAME из Postbox.
4. Для Stalwart проверить очередь `x:QueuedMessage/get` и отсутствие `bootstrap mode`.

## Восстановление

- После изменения `.env`: `docker compose up -d --force-recreate <service>`; `restart` env не перечитывает.
- Восстановленный `postbox-outbound` обновить через `x:MtaRoute/set`, затем перезапустить Stalwart.
- При bootstrap mode восстановить оба тома: `stalwart-etc` и `stalwart-data`.
- После фикса отправить контрольное письмо и сохранить message-id/ошибку без секретов.
