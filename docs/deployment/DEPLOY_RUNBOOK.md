# Deploy Runbook — production VM с нуля

Короткий порядок развёртывания MSPShield на одной production VM (Yandex Cloud).
Полная теория и архитектура: [`deploy/yandex/README.md`](../../deploy/yandex/README.md).
Уроки, превращённые в настройки: [`DEPLOYMENT_LESSONS.md`](DEPLOYMENT_LESSONS.md).

## 0. Пререквизиты (локально)

- `yc`-профиль с сервисным аккаунтом (пример: `msp-new`, ключ SA в `~/.config/yandex-cloud/config.yaml`).
- Домен `msp-claude.online`, SSH-ключ `~/.ssh/id_ed25519_yc_new`.
- Docker Desktop / 7-Zip не обязательны, но удобны.

## 1. ВМ в Yandex Cloud

```bash
yc compute instance create --name msp-cloud-vm \
  --zone ru-central1-a --create-boot-disk image-folder-id=standard-images,image-family=ubuntu-2204-lts \
  --preemptible --memory 4 --cores 2 \
  --network-interface subnet-name=default,nat-ip-version=ipv4 \
  --metadata-from-file user-data=deploy/yandex/cloud-init.yaml \
  --ssh-key ~/.ssh/id_ed25519_yc_new.pub
```

- `cloud-init.yaml` ставит Docker (+ `daemon.json` с `storage-driver: overlay2`), Caddy, пользователя.
- Зарезервировать **static IP** (preemptible иначе меняет IP).

## 2. Код на ВМ

```bash
ssh ubuntu@<IP>
sudo mkdir -p /opt/msp/Newbie && sudo chown ubuntu /opt/msp/Newbie
git clone https://github.com/i1yxaluk-del/Newbie.git /opt/msp/Newbie
```

> На чистой ВМ `unzip` должен быть установлен (его ставит `cloud-init.yaml`); иначе распаковка архива кода упадёт: `sudo apt-get install -y unzip`.

## 3. Env-файлы (3 шт.)

| Файл | Обязательно |
|---|---|
| `backend/.env` | `ADMIN_TOKEN` (`openssl rand -hex 32`), `MONGO_URL=mongodb://mongo:27017`, `DB_NAME=mspshield`, `TG_BOT_TOKEN`, `TG_CHAT_ID`, `TG_ALERT_CHAT_ID`; **доставка лидов**: `SMTP_HOST/PORT/USER/PASSWORD/FROM/FROM_NAME`, `LEAD_EMAIL_TO`, `KAITEN_DOMAIN/API_TOKEN/BOARD_ID/COLUMN_ID` (см. §14) |
| `deploy/yandex/.env` | `VAULTWARDEN_ADMIN_TOKEN`, `POSTBOX_API_KEY_ID`, `POSTBOX_API_KEY_SECRET`, `SMTP_USERNAME`, `SMTP_PASSWORD`, `SMTP_FROM`, `STALWART_ADMIN_PASSWORD` |
| `deploy/yandex/monitoring/.env` | `GRAFANA_ADMIN_USER/PASSWORD`, `ALERTMANAGER_WEBHOOK_TOKEN`, `SMTP_AUTH_USER`/`SMTP_AUTH_PASSWORD` (= ключ Postbox), `SMTP_HOST=postbox.cloud.yandex.net`, `SMTP_PORT=465`, `SMTP_USER/PASSWORD`, `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`, `MAX_PHONE`, `MAX_CHAT_ID`, `ALERT_EMAIL_TO`, `MAX_FAILURE_COOLDOWN` |

Формат: UTF-8 **без BOM**, LF (без CRLF).

## 4. Гейт

```bash
cd /opt/msp/Newbie && sudo bash scripts/deployment/preflight.sh --fix
# ожидаемо: PRE-FLIGHT OK
```

## 5. Стеки

```bash
cd /opt/msp/Newbie/deploy/yandex && docker compose up -d            # mongo, backend, vaultwarden (stalwart — только с --profile mail)
cd /opt/msp/Newbie/deploy/yandex/monitoring && docker compose up -d # prometheus, grafana, alertmanager, max-alerter…
```

## 6. Caddy

```bash
sudo systemctl enable --now caddy
```

Caddyfile уже в репозитории (`deploy/yandex/Caddyfile`): домены + Let's Encrypt.

**Автоматика**: `deploy/yandex/setup-on-vm.sh` сам ставит Caddyfile, подставляет `MSP_DOMAIN`
(sed + systemd override в `/etc/systemd/system/caddy.service.d/override.conf`) и прогоняет `caddy validate`.

**Внимание (урок миграции 28.09)**: сразу после cloud-init в `/etc/caddy/Caddyfile` лежит заглушка
`respond "provisioning in progress..." 503`. Пока она на месте — сайт отдаёт 503.
Проверка после деплоя: `grep -c provisioning /etc/caddy/Caddyfile` → `0`.
Если Caddy не стартует с «server block without any key» — не подставлен `MSP_DOMAIN` (см. выше).

## 7. Stalwart (если нужна почта)

1. SSH-tunnel: `ssh -L 8080:127.0.0.1:8080 ubuntu@<IP>` → `http://localhost:8080/admin`.
2. Wizard: hostname `mail.<domain>`, хранилище RocksDB, админ-аккаунт.
3. Домен + ящики `admin@`, `sales@`, `alert@` (пароли — в secrets).
4. Маршрут: `postbox-outbound` → `postbox.cloud.yandex.net:465` implicit TLS, auth = ключ Postbox.
5. **MTA → Outbound → Strategy → Routing**: `IF is_local_domain(rcpt_domain) THEN 'local' ELSE 'postbox-outbound'`.
6. **Перезапустить контейнер Stalwart** (стратегия применяется после рестарта).
7. DKIM: подпись делает Postbox — опубликовать CNAME `<selector>._domainkey → <selector>.dkim.pstbx.ru` из консоли Postbox (собственный ключ Stalwart не нужен).
8. TLS: импортировать сертификаты Caddy для `mail.<domain>` (авто-ACME Stalwart недоступен — 443 занят Caddy).

## 8. DNS (у регистратора)

```
A     msp-claude.online        <IP>
A     mail.<domain>            <IP>
A     mon.<domain>             <IP>   (Grafana)
MX    msp-claude.online        mail.<domain> (10)
TXT   msp-claude.online        v=spf1 a ip4:<IP> include:postbox.cloud.yandex.net ~all
TXT   _dmarc                   v=DMARC1; p=quarantine; rua=mailto:admin@<domain>
CNAME <selector>._domainkey    → <selector>.dkim.pstbx.ru   (Postbox; точные имена из консоли)
```

**Перед переключением DNS (урок миграции 28.09)**: проверь TCP-доступность публичного IP ВМ
**из сети целевого региона** (из РФ): `nc -vz <IP> 22 && curl -sS --connect-timeout 5 -o /dev/null -w '%{http_code}' http://<IP>/`.
Если ICMP проходит, а TCP — нет, адрес/маршрут заблокирован: пересоздай зарезервированный адрес
в другом пуле и только потом меняй DNS A-записи.

## 9. Alertmanager

Entrypoint сам подставит `SMTP_AUTH_USER/PASSWORD` и `ALERTMANAGER_WEBHOOK_TOKEN`. Проверка:

```bash
docker exec msp-alertmanager grep smtp_auth /etc/alertmanager/alertmanager.yml
```

## 10. vm_watcher (операторская Windows-станция)

```powershell
Copy-Item services\vm_watcher\* C:\Users\<user>\vm_watcher\
# конфиг: C:\Users\<user>\.config\mspshield\vm-watcher.json (по config.example.json)
powershell -File C:\Users\<user>\vm_watcher\install.ps1
```

## 11. restic + S3

`/etc/restic/env.sh` (RESTIC_REPOSITORY/PASSWORD, S3-ключи), таймер `restic-backup.timer`.
Тест: `sudo bash /opt/restic-scripts/backup.sh` → `restic_backup_success=1` в Grafana.

**При переезде ВМ в новый аккаунт (урок 28.09)**: S3-ключи старого аккаунта не подходят к новому
бакету (`SignatureDoesNotMatch`) — выпусти новый статический ключ SA (`yc iam access-key create --service-account-name restic-backup`),
обнови `/etc/restic/env.sh` и выполни `restic init` в новом бакете.

## 12. Верификация

- `https://msp-claude.online` → 200, `/api/health` → ok.
- `https://mon.<domain>` → Grafana.
- Тестовое письмо: наружу (не в спам) и внутрь (`alert@`).
- Тестовый P1-алерт → MAX/email.
- `sudo bash scripts/deployment/preflight.sh` → PRE-FLIGHT OK.
- Публичный IP доступен по TCP из целевой сети (см. §8).
- Stalwart не в bootstrap: `docker logs msp-stalwart-1 | grep -c 'bootstrap mode'` → `0` (актуально при миграции).
- При восстановлении из бэкапа `du -sh` томов ≈ размеру бэкапа (см. MIGRATION_RUNBOOK §9.4).
- Форма заявки: тест → письмо на `LEAD_EMAIL_TO` + карточка в Kaiten «Новая» (см. §14).

## 13. Харденинг SSH (после того как AWG-туннель проверен)

По умолчанию публичный SSH открыт с 0.0.0.0/0 — иначе нельзя развернуть ВМ до поднятия AWG.
После проверки туннеля закрываем публичный вход: остаётся только `10.9.0.0/24`:

```bash
# на ВМ: оставить SSH только из VPN-подсети
sudo ufw delete allow 22/tcp          # удалит и v4, и v6 «Anywhere»
sudo ufw status numbered | grep 22    # должен остаться только "22/tcp ALLOW IN 10.9.0.0/24"

# на рабочей станции (yc):
yc vpc security-group update-rules --id <sg-id> --delete-rule-id <ssh-rule-id>
```

Проверка: `nc -vz <IP> 22` снаружи → таймаут; `ssh ubuntu@10.9.0.1` через туннель → работает.

**Аварийный возврат доступа** (если туннель сломался, а зайти нужно):

```bash
yc vpc security-group update-rules --id <sg-id> \
  --add-rule "direction=ingress,protocol=tcp,port=22,v4-cidrs=0.0.0.0/0"
# на ВМ: sudo ufw allow 22/tcp  — и после ремонта снова закрыть
```

Применено на production 28.09.2026: публичный 22 закрыт на уровнях SG и ufw.

## 14. Интеграции лидов (Postbox SMTP + Kaiten)

После подъёма стека заполните в `backend/.env` доставку заявок (в проде нужны обе секции):

```env
# Почта (лиды) — прямой Postbox
SMTP_HOST=postbox.cloud.yandex.net
SMTP_PORT=465
SMTP_USER=<POSTBOX_API_KEY_ID из deploy/.env>
SMTP_PASSWORD=<POSTBOX_API_KEY_SECRET>
SMTP_FROM=sales@msp-claude.online
SMTP_FROM_NAME=MSPShield
LEAD_EMAIL_TO=sales@msp-claude.online,admin@msp-claude.online

# Kaiten CRM
KAITEN_DOMAIN=<workspace>.kaiten.ru
KAITEN_API_TOKEN=<токен с /profile/api-key>
KAITEN_BOARD_ID=<id доски>
KAITEN_COLUMN_ID=<id колонки «Новая»>
```

Пока переменных нет — каналы молча выключены (`is_enabled()=false`), заявка остаётся только в Mongo.

Перезапуск и проверка:

```bash
cd /opt/msp/Newbie/deploy/yandex && docker compose up -d --force-recreate backend
curl -s http://127.0.0.1:8001/api/integrations/status   # ожидаемо kaiten:true
# тестовая заявка на https://<domain>/api/leads → в логах "lead email sent" и "kaiten card created"
docker logs msp-backend-1 --since 3m | grep -Ei "lead|kaiten|email"
```

Текущий прод-конфиг Kaiten: `maksivanovza.kaiten.ru`, доска Lead Pipeline `1773682`, колонка «Новая» `6129074` (подробнее — `docs/KAITEN_SETUP.md`).
