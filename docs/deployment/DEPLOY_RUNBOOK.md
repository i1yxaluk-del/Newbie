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

## 3. Env-файлы (3 шт.)

| Файл | Обязательно |
|---|---|
| `backend/.env` | `ADMIN_TOKEN` (`openssl rand -hex 32`), `MONGO_URL=mongodb://mongo:27017`, `DB_NAME=mspshield`, `TG_BOT_TOKEN`, `TG_CHAT_ID`, `TG_ALERT_CHAT_ID` |
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

## 7. Stalwart (если нужна почта)

1. SSH-tunnel: `ssh -L 8080:127.0.0.1:8080 ubuntu@<IP>` → `http://localhost:8080/admin`.
2. Wizard: hostname `mail.<domain>`, хранилище RocksDB, админ-аккаунт.
3. Домен + ящики `admin@`, `sales@`, `alert@` (пароли — в secrets).
4. Маршрут: `postbox-outbound` → `postbox.cloud.yandex.net:465` implicit TLS, auth = ключ Postbox.
5. **MTA → Outbound → Strategy → Routing**: `IF is_local_domain(rcpt_domain) THEN 'local' ELSE 'postbox-outbound'`.
6. **Перезапустить контейнер Stalwart** (стратегия применяется после рестарта).
7. DKIM: сгенерировать ключ → TXT-запись `v1-*._domainkey` у регистратора.
8. TLS: импортировать сертификаты Caddy для `mail.<domain>` (авто-ACME Stalwart недоступен — 443 занят Caddy).

## 8. DNS (у регистратора)

```
A     msp-claude.online        <IP>
A     mail.<domain>            <IP>
A     mon.<domain>             <IP>   (Grafana)
MX    msp-claude.online        mail.<domain> (10)
TXT   msp-claude.online        v=spf1 a ip4:<IP> include:postbox.cloud.yandex.net ~all
TXT   _dmarc                   v=DMARC1; p=quarantine; rua=mailto:admin@<domain>
CNAME <selector>._domainkey    (ключ DKIM Stalwart или Postbox)
```

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

## 12. Верификация

- `https://msp-claude.online` → 200, `/api/health` → ok.
- `https://mon.<domain>` → Grafana.
- Тестовое письмо: наружу (не в спам) и внутрь (`alert@`).
- Тестовый P1-алерт → MAX/email.
- `sudo bash scripts/deployment/preflight.sh` → PRE-FLIGHT OK.
