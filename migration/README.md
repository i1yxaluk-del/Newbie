# Перенос MSPShield на новую VM

Этот runbook основан на фактическом переносе, но не содержит cloud IDs, IP, телефонов, chat ID и ключей. Исторические значения удалены: они не являются инструкцией и могли раскрывать инфраструктуру.

## Принципы

1. Новая VM и новый `.env` создаются заранее.
2. Переносятся данные, а не старые cloud credentials.
3. MAX session переносится отдельно и проверяется без отправки SMS.
4. DNS переключается только после локальных health checks.
5. Старая VM удаляется после периода наблюдения и подтверждённого backup.

## Состав переносимых данных

- `mongodump.archive.gz`;
- Vaultwarden data archive;
- Stalwart data только если сервис реально используется;
- restic repository credentials через защищённый канал;
- `max-session.tar.gz` с `max.db`;
- список DNS-записей без секретов.

Не переносить автоматически: старый `backend.env`, `deploy.env`, service-account JSON, Postbox API key и cloud access keys. Значения создаются/проверяются для новой среды вручную.

## Подготовка новой VM

- Docker/Compose и firewall;
- репозиторий в `/opt/msp/Newbie`;
- новый `backend/.env`;
- новый `deploy/yandex/monitoring/.env` с `MAX_PHONE`, `MAX_CHAT_ID`, `ALERTMANAGER_WEBHOOK_TOKEN`;
- DNS пока указывает на старую VM;
- SSH host key добавлен через `StrictHostKeyChecking=accept-new`.

## Backup старой VM

```bash
mkdir -p /tmp/migration
cd /opt/msp/Newbie/deploy/yandex
docker compose exec -T mongo mongodump --archive --gzip > /tmp/migration/mongodump.archive.gz
sudo tar czf /tmp/migration/max-session.tar.gz \
  -C /opt/msp/Newbie/deploy/yandex/monitoring max-session
```

Остальные volume архивируются только после остановки изменяющего их сервиса или через поддерживаемый приложением backup-механизм.

## Восстановление

```bash
sudo bash /tmp/migration/restore-on-vm.sh
```

Скрипт не должен перезаписывать новые `.env`. После запуска:

```bash
cd /opt/msp/Newbie/deploy/yandex/monitoring
sudo docker exec msp-max-alerter python -m max_alerter.auth
curl -fsS http://127.0.0.1:9095/health
curl -fsS http://127.0.0.1:9093/-/healthy
```

Если MAX session непригодна:

```bash
sudo docker exec -it msp-max-alerter python -m max_alerter.auth --authorize
```

## Gate переключения DNS

- [ ] `/api/health` отвечает локально;
- [ ] Mongo row count подтверждён;
- [ ] Vaultwarden открыт только через ожидаемый hostname;
- [ ] Prometheus и Alertmanager healthy;
- [ ] MAX session check возвращает 0;
- [ ] тестовый P1 дошёл в MAX;
- [ ] restic snapshot создан из новой VM;
- [ ] внешний скан не показывает служебные порты.

После DNS проверить HTTPS и форму. Старую VM держать выключенной, но не удалять до завершения согласованного периода наблюдения.

## Уроки фактического переноса

- включать `services/max_alerter` и frontend config в deploy bundle;
- после изменения `.env` использовать `up -d --force-recreate`, не `restart`;
- не полагаться на имя `msp-mongo-1`, использовать `docker compose ps -q mongo`;
- не переносить Let's Encrypt data без необходимости — Caddy может получить новый сертификат;
- исключать CRLF в shell scripts;
- проверять executable bit у entrypoint;
- не отключать SSH host-key verification;
- не публиковать полный inventory облака и ключи в runbook.


---

## Уроки миграции (сентябрь 2026)

> Дополнение: что упускали при переносе между серверами/аккаунтами.

1. **Stalwart: конфиг лежит в томе `stalwart-etc`** (`/etc/stalwart/config.json`), а данные — в `stalwart-data`. Бэкапить **оба** тома. Если сохранить только data — почта не поднимется без переинициализации (домен/ящики/DKIM создаются заново).
2. **Restic не покрывал Docker-тома.** Бэкап-скрипт исключал `/var/lib/docker`; добавили `/var/lib/docker/volumes` (кроме `msp_mongo-data` — MongoDB закрыта `mongodump`). Проверять состав снапшота (`restic ls latest`).
3. **Postbox API-ключ привязан к сервисному аккаунту `postbox-sender`** и должен иметь scope `yc.postbox.send`. После переноса ключи могли быть удалены — проверять `yc iam api-key list --service-account-id ajeq2njbvgqf0fohc2g1` и создавать новый при необходимости; в `.env` хранить ID ключа и секрет.
4. **Stalwart: SPIFFE/роли.** Отправку (`emailSend`) даёт роль `User`; у админской роли её нет. Логин в клиенте — полный адрес.
5. **Очередь Stalwart:** после смены креденшелов маршрута письма из очереди могут ретраиться со старыми ошибками — проверять `x:QueuedMessage/get`; стратегия маршрута применяется после рестарта контейнера.
6. **Preemptible VM**: получает новый IP/host keys; держать static IP и `-o StrictHostKeyChecking=no -o UserKnownHostsFile=NUL`.
7. **DNS-минимум:** `A mail.<domain>`, `TXT` SPF с `include:postbox.cloud.yandex.net`, `_dmarc`; DKIM — CNAME на `dkim.pstbx.ru` (Postbox) либо собственные ключи Stalwart (тогда их TXT). Ставить DMARC `p=quarantine` после стабилизации.
8. **Telegram с ВМ недоступен** (блокировка) — не закладывать его как единственный канал алертов на новом хосте.