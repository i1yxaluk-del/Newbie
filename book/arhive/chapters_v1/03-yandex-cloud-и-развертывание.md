# Yandex Cloud и полное развёртывание VM

Облако предоставляет каталог, сеть, подсеть, адрес, диск и виртуальную машину. Эти сущности живут отдельно: удаление VM не гарантирует удаление диска, снимка или постоянного IP. Группа безопасности фильтрует трафик на уровне облака, `ufw` — внутри Linux, а слушающий сокет принадлежит конкретному процессу.

Развёртывание проходит воротами: подготовка VM, новый набор секретов, preflight, application stack, monitoring stack, Caddy, внутренние проверки, внешний TCP/TLS/HTTP, тестовый P1 и восстановление. DNS меняют последним. Команда, которая завершилась без ошибки, подтверждает только собственный шаг.

`cloud-init` готовит базовую систему при первом запуске, но не является доказательством готовности приложения. Перед закрытием публичного SSH проверяют AWG во второй сессии и аварийный путь возврата.

## Как работать с материалом

Сначала прочитайте объяснение главы. Затем откройте перечисленные файлы в рабочем репозитории и сопоставьте текст с текущим кодом. Команды изменения выполняйте на учебной среде. Разделы ниже включены полностью, поэтому глава одновременно служит учебником и справочником.

## Материал проекта: `docs/deployment/README.md`

<!-- SOURCE docs/deployment/README.md 59d8a3fab20d6a94 -->

## Развёртывание — оглавление

### Канонический pilot path

| Шаг | Документ / инструмент |
|---:|---|
| 1 | [`local_dev.md`](https://github.com/i1yxaluk-del/Newbie/blob/main/docs/deployment/local_dev.md) — локальная проверка приложения |
| 2 | [DEPLOY_RUNBOOK.md](https://github.com/i1yxaluk-del/Newbie/blob/main/docs/deployment/DEPLOY_RUNBOOK.md) — пошаговое развёртывание VM с нуля |
| 2 | [`../../deploy/yandex/README.md`](https://github.com/i1yxaluk-del/Newbie/blob/main/deploy/yandex/README.md) — одна production VM |
| 3 | [`../../scripts/deployment/preflight.sh`](https://github.com/i1yxaluk-del/Newbie/blob/main/scripts/deployment/preflight.sh) — env/Compose/security gate |
| 4 | [`DEPLOYMENT_LESSONS.md`](https://github.com/i1yxaluk-del/Newbie/blob/main/docs/deployment/DEPLOYMENT_LESSONS.md) — уроки, превращённые в controls |
| 5 | [`../../migration/README.md`](https://github.com/i1yxaluk-del/Newbie/blob/main/migration/README.md) — перенос VM |
| 5 | [MIGRATION_RUNBOOK.md](https://github.com/i1yxaluk-del/Newbie/blob/main/docs/deployment/MIGRATION_RUNBOOK.md) — пошаговая миграция на новую VM |
| 6 | [`disaster_recovery.md`](https://github.com/i1yxaluk-del/Newbie/blob/main/docs/deployment/disaster_recovery.md) — восстановление |
| 7 | [`troubleshooting.md`](https://github.com/i1yxaluk-del/Newbie/blob/main/docs/deployment/troubleshooting.md) — диагностика |

### Другие сценарии

- [`landing_production.md`](https://github.com/i1yxaluk-del/Newbie/blob/main/docs/deployment/landing_production.md) — Terraform/Ansible вариант; использовать только после отдельного решения перейти с single-VM pilot.
- [`tenant_onboarding.md`](https://github.com/i1yxaluk-del/Newbie/blob/main/docs/deployment/tenant_onboarding.md) — подключение клиентского tenant после подписанного scope.
- [`secrets_management.md`](https://github.com/i1yxaluk-del/Newbie/blob/main/docs/deployment/secrets_management.md) — секреты и ротация.
- [VAULTWARDEN_ORG_RUNBOOK.md](https://github.com/i1yxaluk-del/Newbie/blob/main/docs/deployment/VAULTWARDEN_ORG_RUNBOOK.md) — организация, коллекции и импорт секретов Vaultwarden

### Не смешивать

- backend MAX Bot API для лидов и `msp-max-alerter` для monitoring alerts;
- infrastructure deployment и client onboarding;
- snapshot/backup и доказанный restore;
- исторические команды из postmortem и текущий runbook.

При конфликте документации приоритет: root `README` → этот index → canonical runbook → code/CI.


## Материал проекта: `docs/deployment/DEPLOY_RUNBOOK.md`

<!-- SOURCE docs/deployment/DEPLOY_RUNBOOK.md 31ae0ee10b4d07fe -->

## Deploy Runbook — production VM с нуля

Короткий порядок развёртывания MSPShield на одной production VM (Yandex Cloud).
Полная теория и архитектура: [`deploy/yandex/README.md`](https://github.com/i1yxaluk-del/Newbie/blob/main/deploy/yandex/README.md).
Уроки, превращённые в настройки: [`DEPLOYMENT_LESSONS.md`](https://github.com/i1yxaluk-del/Newbie/blob/main/docs/deployment/DEPLOYMENT_LESSONS.md).

### 0. Пререквизиты (локально)

- `yc`-профиль с сервисным аккаунтом (пример: `msp-new`, ключ SA в `~/.config/yandex-cloud/config.yaml`).
- Домен `msp-claude.online`, SSH-ключ `~/.ssh/id_ed25519_yc_new`.
- Docker Desktop / 7-Zip не обязательны, но удобны.

### 1. ВМ в Yandex Cloud

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

### 2. Код на ВМ

```bash
ssh ubuntu@<IP>
sudo mkdir -p /opt/msp/Newbie && sudo chown ubuntu /opt/msp/Newbie
git clone https://github.com/i1yxaluk-del/Newbie.git /opt/msp/Newbie
```

> На чистой ВМ `unzip` должен быть установлен (его ставит `cloud-init.yaml`); иначе распаковка архива кода упадёт: `sudo apt-get install -y unzip`.

### 3. Env-файлы (3 шт.)

| Файл | Обязательно |
|---|---|
| `backend/.env` | `ADMIN_TOKEN` (`openssl rand -hex 32`), `MONGO_URL=mongodb://mongo:27017`, `DB_NAME=mspshield`, `TG_BOT_TOKEN`, `TG_CHAT_ID`, `TG_ALERT_CHAT_ID`; **доставка лидов**: `SMTP_HOST/PORT/USER/PASSWORD/FROM/FROM_NAME`, `LEAD_EMAIL_TO`, `KAITEN_DOMAIN/API_TOKEN/BOARD_ID/COLUMN_ID` (см. §14) |
| `deploy/yandex/.env` | `VAULTWARDEN_ADMIN_TOKEN`, `POSTBOX_API_KEY_ID`, `POSTBOX_API_KEY_SECRET`, `SMTP_USERNAME`, `SMTP_PASSWORD`, `SMTP_FROM`, `STALWART_ADMIN_PASSWORD` |
| `deploy/yandex/monitoring/.env` | `GRAFANA_ADMIN_USER/PASSWORD`, `ALERTMANAGER_WEBHOOK_TOKEN`, `SMTP_AUTH_USER`/`SMTP_AUTH_PASSWORD` (= ключ Postbox), `SMTP_HOST=postbox.cloud.yandex.net`, `SMTP_PORT=465`, `SMTP_USER/PASSWORD`, `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`, `MAX_PHONE`, `MAX_CHAT_ID`, `ALERT_EMAIL_TO`, `MAX_FAILURE_COOLDOWN` |

Формат: UTF-8 **без BOM**, LF (без CRLF).

### 4. Гейт

```bash
cd /opt/msp/Newbie && sudo bash scripts/deployment/preflight.sh --fix
## ожидаемо: PRE-FLIGHT OK
```

### 5. Стеки

```bash
cd /opt/msp/Newbie/deploy/yandex && docker compose up -d            # mongo, backend, vaultwarden (stalwart — только с --profile mail)
cd /opt/msp/Newbie/deploy/yandex/monitoring && docker compose up -d # prometheus, grafana, alertmanager, max-alerter…
```

### 6. Caddy

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

### 7. Stalwart (если нужна почта)

1. SSH-tunnel: `ssh -L 8080:127.0.0.1:8080 ubuntu@<IP>` → `http://localhost:8080/admin`.
2. Wizard: hostname `mail.<domain>`, хранилище RocksDB, админ-аккаунт.
3. Домен + ящики `admin@`, `sales@`, `alert@` (пароли — в secrets).
4. Маршрут: `postbox-outbound` → `postbox.cloud.yandex.net:465` implicit TLS, auth = ключ Postbox.
5. **MTA → Outbound → Strategy → Routing**: `IF is_local_domain(rcpt_domain) THEN 'local' ELSE 'postbox-outbound'`.
6. **Перезапустить контейнер Stalwart** (стратегия применяется после рестарта).
7. DKIM: подпись делает Postbox — опубликовать CNAME `<selector>._domainkey → <selector>.dkim.pstbx.ru` из консоли Postbox (собственный ключ Stalwart не нужен).
8. TLS: импортировать сертификаты Caddy для `mail.<domain>` (авто-ACME Stalwart недоступен — 443 занят Caddy).

### 8. DNS (у регистратора)

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

### 9. Alertmanager

Entrypoint сам подставит `SMTP_AUTH_USER/PASSWORD` и `ALERTMANAGER_WEBHOOK_TOKEN`. Проверка:

```bash
docker exec msp-alertmanager grep smtp_auth /etc/alertmanager/alertmanager.yml
```

### 10. vm_watcher (операторская Windows-станция)

```powershell
Copy-Item services\vm_watcher\* C:\Users\<user>\vm_watcher\
## конфиг: C:\Users\<user>\.config\mspshield\vm-watcher.json (по config.example.json)
powershell -File C:\Users\<user>\vm_watcher\install.ps1
```

### 11. restic + S3

`/etc/restic/env.sh` (RESTIC_REPOSITORY/PASSWORD, S3-ключи), таймер `restic-backup.timer`.
Тест: `sudo bash /opt/restic-scripts/backup.sh` → `restic_backup_success=1` в Grafana.

**При переезде ВМ в новый аккаунт (урок 28.09)**: S3-ключи старого аккаунта не подходят к новому
бакету (`SignatureDoesNotMatch`) — выпусти новый статический ключ SA (`yc iam access-key create --service-account-name restic-backup`),
обнови `/etc/restic/env.sh` и выполни `restic init` в новом бакете.

### 12. Верификация

- `https://msp-claude.online` → 200, `/api/health` → ok.
- `https://mon.<domain>` → Grafana.
- Тестовое письмо: наружу (не в спам) и внутрь (`alert@`).
- Тестовый P1-алерт → MAX/email.
- `sudo bash scripts/deployment/preflight.sh` → PRE-FLIGHT OK.
- Публичный IP доступен по TCP из целевой сети (см. §8).
- Stalwart не в bootstrap: `docker logs msp-stalwart-1 | grep -c 'bootstrap mode'` → `0` (актуально при миграции).
- При восстановлении из бэкапа `du -sh` томов ≈ размеру бэкапа (см. MIGRATION_RUNBOOK §9.4).
- Форма заявки: тест → письмо на `LEAD_EMAIL_TO` + карточка в Kaiten «Новая» (см. §14).

### 13. Харденинг SSH (после того как AWG-туннель проверен)

По умолчанию публичный SSH открыт с 0.0.0.0/0 — иначе нельзя развернуть ВМ до поднятия AWG.
После проверки туннеля закрываем публичный вход: остаётся только `10.9.0.0/24`:

```bash
## на ВМ: оставить SSH только из VPN-подсети
sudo ufw delete allow 22/tcp          # удалит и v4, и v6 «Anywhere»
sudo ufw status numbered | grep 22    # должен остаться только "22/tcp ALLOW IN 10.9.0.0/24"

## на рабочей станции (yc):
yc vpc security-group update-rules --id <sg-id> --delete-rule-id <ssh-rule-id>
```

Проверка: `nc -vz <IP> 22` снаружи → таймаут; `ssh ubuntu@10.9.0.1` через туннель → работает.

**Аварийный возврат доступа** (если туннель сломался, а зайти нужно):

```bash
yc vpc security-group update-rules --id <sg-id> \
  --add-rule "direction=ingress,protocol=tcp,port=22,v4-cidrs=0.0.0.0/0"
## на ВМ: sudo ufw allow 22/tcp  — и после ремонта снова закрыть
```

Применено на production 28.09.2026: публичный 22 закрыт на уровнях SG и ufw.

### 14. Интеграции лидов (Postbox SMTP + Kaiten)

После подъёма стека заполните в `backend/.env` доставку заявок (в проде нужны обе секции):

```env
## Почта (лиды) — прямой Postbox
SMTP_HOST=postbox.cloud.yandex.net
SMTP_PORT=465
SMTP_USER=<POSTBOX_API_KEY_ID из deploy/.env>
SMTP_PASSWORD=<POSTBOX_API_KEY_SECRET>
SMTP_FROM=sales@msp-claude.online
SMTP_FROM_NAME=MSPShield
LEAD_EMAIL_TO=sales@msp-claude.online,admin@msp-claude.online

## Kaiten CRM
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
## тестовая заявка на https://<domain>/api/leads → в логах "lead email sent" и "kaiten card created"
docker logs msp-backend-1 --since 3m | grep -Ei "lead|kaiten|email"
```

Текущий прод-конфиг Kaiten: `maksivanovza.kaiten.ru`, доска Lead Pipeline `1773682`, колонка «Новая» `6129074` (подробнее — `docs/KAITEN_SETUP.md`).


## Материал проекта: `docs/deployment/DEPLOYMENT_LESSONS.md`

<!-- SOURCE docs/deployment/DEPLOYMENT_LESSONS.md 04d419ee5d922675 -->

## Уроки deployment и migration — применённые решения

Документ отделяет наблюдение от внедрённого контроля. Формулировка «урок учтён» допустима только при наличии кода, проверки и runbook.

### Матрица

| Урок | Риск | Внедрённый контроль | Проверка |
|---|---|---|---|
| `.env` с BOM/CRLF | первый ключ не читается | `scripts/deployment/preflight.sh` | preflight завершается ошибкой |
| пустой `ADMIN_TOKEN` | backend 503 | preflight требует непустое значение | `/api/health`, login test |
| SMTP user без password в Compose | Alertmanager crash/535 | override требует обе переменные | `docker compose config`, AM health |
| entrypoint теряет executable bit | container permission denied | preflight `--fix` + CI `bash -n` | `test -x` |
| raw backup `/var/lib/docker/volumes` | неконсистентные БД | короткая остановка writers + tar staging | restore lab |
| Mongo container name меняется | backup/restore падает | `docker compose ps -q mongo` | CI static gate |
| потерян `stalwart-etc` | домены/DKIM не восстановить | архивируются оба Stalwart volume | clean restore |
| потерян MAX `max.db` | повторная SMS-авторизация | отдельный session archive | `auth` без `--authorize` |
| Telegram блокируется с VM | потеря единственного канала | MAX + Postbox; Telegram только fallback/local watcher | тестовый P1 |
| ICMP закрыт Security Group | ложный VM-down | VM watcher проверяет TCP/443 | workstation lab |
| `YC_CONFIG_DIR` игнорируется | watcher не видит профиль | yc использует профиль пользователя | `yc config list` |
| изменился SSH host key | MITM или небезопасный bypass | `accept-new` только для первого подключения; замену сверять в console | migration gate |
| environment state попал в Git | раскрытие topology | `.deploy-state.json` удалён и ignored | repo validator |

### Перед deploy

```bash
bash scripts/deployment/preflight.sh
```

### После deploy

```bash
curl -fsS http://127.0.0.1:8001/api/health
curl -fsS http://127.0.0.1:9090/-/healthy
curl -fsS http://127.0.0.1:9093/-/healthy
curl -fsS http://127.0.0.1:9095/health
sudo docker exec msp-max-alerter python -m max_alerter.auth
```

Затем отправить контролируемый P1, проверить MAX и email, создать новый backup и выполнить test restore в чистом окружении.


### Уроки миграции 28.09.2026 (проверено на реальном переезде)

| Тема | Симптом | Системный контроль | Проверка |
|---|---|---|---|
| Новый публичный IP недостижим из целевого региона | сайт «не работает» (TCP timeout), ICMP ок | smoke-тест TCP из РФ до DNS switch; иначе пересоздать адрес в другом пуле | `curl`/`nc` с российской машины |
| Одиночная ВМ + bastion | лишняя ВМ и путаница | bastion — временный; удалять сразу после прямого доступа | `yc compute instance list` = 1 |
| Caddy-placeholder от cloud-init | 503 «provisioning» | сверять `/etc/caddy/Caddyfile` с репозиторием при деплое | `curl -I https://<domain>` |
| Caddyfile без `MSP_DOMAIN` | caddy не стартует: «server block without any key» | env/systemd override для юнита Caddy | `caddy validate` |
| restore-on-vm и раскладка артефактов | тома молча не восстановлены | класть артефакты плоско в `MIGRATION_DIR`; копировать через `sudo sh -c 'cp …'` | `ls /tmp/migration`; `du -sh` томов |
| Пустой `stalwart-data` | Stalwart в bootstrap-режиме (нет ящиков) | восстанавливать ОБА тома; конфиг хранится в RocksDB | grep «bootstrap» в логе; ящики на месте |
| restic: ключи привязаны к аккаунту/бакету | `SignatureDoesNotMatch` на новом бакете | новый access key + `restic init` при переезде аккаунта | `restic snapshots` |
| Postbox: ключ + DKIM заново | `550 identity not verified`; отправка не идёт | пересоздать API-ключ; DKIM — CNAME из консоли (→ `<selector>.dkim.pstbx.ru`), дождаться verified | тестовое письмо через SMTP |
| Stalwart-релей: креды маршрута не обновляются из .env | письма копятся молча; в очереди `535 Authentication failed` | обновить `x:MtaRoute/set` + **рестарт** Stalwart (MIGRATION_RUNBOOK §9.9) | письмо на `check-auth@verifier.port25.com` |
| Amnezia PPA после переноса | apt «is not signed» | ключ в `/etc/apt/trusted.gpg.d/`, без `signed-by` в list | `apt-get update` exit 0 |
| AWG: SG/ufw без UDP/443 | рукопожатие не проходит | gate: UDP 443 на SG + ufw allow; SSH-from-VPN правило | `awg show latest-handshakes` |
| cloud-init: IPv6-зеркала, битый NodeSource, нет unzip | apt/распаковка падают | ForceIPv4; чистить лишние apt-репозитории; доустановка утилит | `apt-get update`, `unzip -v` |
| `key.json` невалиден | yc CLI не работает | проверка JSON до автоматизации | `yc config list` |


## Материал проекта: `deploy/yandex/cloud-init.yaml`

<!-- SOURCE deploy/yandex/cloud-init.yaml 02e6ceba0068b46f -->

```yaml
#cloud-config
# ═══════════════════════════════════════════════════════════════════
# Yandex Cloud · базовый bootstrap ВМ под МСП Облако (msp-claude.online).
# Этот файл — только ОС-уровень: установка Docker, Node, Caddy, git.
# Само приложение (код, .env, билд, запуск контейнеров) выкладывается
# через SSH из PowerShell-обёртки `deploy.ps1` после готовности VM.
# ═══════════════════════════════════════════════════════════════════

# Замена SSH-ключа Devin/PowerShell-скрипта: подменяется при рендере
# из deploy.ps1 на реальный ~/.ssh/id_ed25519_yc_new.pub.
users:
  - name: ubuntu
    sudo: ALL=(ALL) NOPASSWD:ALL
    shell: /bin/bash
    ssh_authorized_keys:
      - __SSH_PUBKEY__

# Установка пакетов
package_update: true
package_upgrade: false  # пропускаем upgrade на старте — ускоряет boot
packages:
  - ca-certificates
  - curl
  - gnupg
  - git
  - jq
  - ufw
  - python3-pip
  - python3-venv
  - openssl
  - unzip

# Файлы, которые нужны до первого запуска runcmd
write_files:
  # Сигнальный маркер "cloud-init начался" — deploy.ps1 опрашивает /var/log/msp-deploy.*
  - path: /var/log/msp-deploy.started
    content: |
      cloud-init started
    owner: root:root
    permissions: '0644'

  # APT-репозитории добавляются через runcmd (apt-key deprecated, нужны keyrings)
  # Docker official GPG ставится в /etc/apt/keyrings/docker.gpg

  # Минимальный /etc/caddy/Caddyfile — будет переопределён скриптом setup-on-vm.sh
  # после загрузки кода. На этом этапе важно только чтобы Caddy не падал.
  - path: /etc/caddy/Caddyfile
    content: |
      :80 {
        respond "MSP Cloud · provisioning in progress..." 503
      }
    owner: root:root
    permissions: '0644'

  # Docker daemon config — принудительно overlay2 вместо overlayfs.
  # ВАЖНО: Ubuntu 22.04 + Docker 29+ по умолчанию использует overlayfs
  # (containerd snapshotter). cAdvisor не может читать layerdb/mounts/
  # с этим драйвером — все контейнеры невидимы в Grafana.
  # Фикс: storage-driver: overlay2 → классический overlay2 с layerdb.
  # Побочный эффект: Docker пересоздаёт хранилище при первом рестарте
  # (образы нужно re-pull, volumes не теряются).
  - path: /etc/docker/daemon.json
    content: |
      {"storage-driver": "overlay2"}
    owner: root:root
    permissions: '0644'

  # APT: форсируем IPv4 (урок миграции 28.09): IPv6-зеркала на части сетей YC
  # недоступны и ломают apt уже на этапе package_update.
  - path: /etc/apt/apt.conf.d/99force-ipv4
    content: |
      Acquire::ForceIPv4 "true";
    owner: root:root
    permissions: '0644'

# Запуск установки. Каждая команда логируется в /var/log/cloud-init-output.log.
runcmd:
  # 1. Docker repo + Docker Engine + Compose v2 plugin
  # ВАЖНО: $VERSION_CODENAME раскрывается cloud-init корректно,
  # но если cloud-init не подставляет — замени на jammy (Ubuntu 22.04).
  # Мы столкнулись с багом: на некоторых образах YC переменная
  # $VERSION_CODENAME пустая → docker.list содержит пустое имя
  # дистрибутива → apt-get update падает. Фикс: хардкод jammy.
  - install -m 0755 -d /etc/apt/keyrings
  - curl -4fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
  - chmod a+r /etc/apt/keyrings/docker.asc
  - |
    echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] \
    https://download.docker.com/linux/ubuntu jammy stable" \
    > /etc/apt/sources.list.d/docker.list

  # 2. Caddy official repo (автоматический SSL через Let's Encrypt)
  - |
    curl -4fsSL https://dl.cloudsmith.io/public/caddy/stable/gpg.key \
    | gpg --dearmor -o /usr/share/keyrings/caddy-stable-archive-keyring.gpg
  - |
    curl -4fsSL https://dl.cloudsmith.io/public/caddy/stable/debian.deb.txt \
    > /etc/apt/sources.list.d/caddy-stable.list

  # 3. NodeSource Node.js 20 LTS (для yarn build фронта)
  - |
    curl -4fsSL https://deb.nodesource.com/gpgkey/nodesource-repo.gpg.key \
    | gpg --dearmor -o /etc/apt/keyrings/nodesource.gpg
  - |
    echo "deb [signed-by=/etc/apt/keyrings/nodesource.gpg] \
    https://deb.nodesource.com/node_20.x nodistro main" \
    > /etc/apt/sources.list.d/nodesource.list

  - apt-get update
  - DEBIAN_FRONTEND=noninteractive apt-get install -y
      docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
      caddy
      nodejs

  # 4. Yarn через corepack (входит в Node 20)
  - corepack enable
  - corepack prepare yarn@stable --activate

  # 5. Docker group для ubuntu
  - usermod -aG docker ubuntu

  # 6. Firewall: SSH + HTTP/S + почтовые порты Stalwart (submit-only режим).
  #    Порт 25 НЕ открываем — Yandex Cloud блокирует TCP/25 на публичных
  #    IP VPC. Inbound MX-приём не работает (MX-запись домена должна
  #    указывать на внешний провайдер: Yandex 360, Mailgun routes и т.п.).
  #    См. deploy/yandex/STALWART_RELAY_MODE.md
  #
  #    UDP/443 — AmneziaWG (для bastion-функции на этой же VM).
  #    Не конфликтует с TCP/443 у Caddy — разные протоколы.
  #    Харденинг: после проверки AWG закрыть публичный SSH (DEPLOY_RUNBOOK §13).
  #    См. docs/runbooks/R-08.md и technical/0_Common/amneziawg/.
  - ufw default deny incoming
  - ufw default allow outgoing
  - ufw allow 22/tcp     comment 'SSH'
  - ufw allow 80/tcp     comment 'Caddy HTTP / ACME challenge'
  - ufw allow 443/tcp    comment 'Caddy HTTPS / лендинг + API'
  - ufw allow 443/udp    comment 'AmneziaWG VPN (обфускация против РКН-DPI)'
  - ufw allow 465/tcp    comment 'Stalwart SMTPS submission (implicit TLS)'
  - ufw allow 587/tcp    comment 'Stalwart STARTTLS submission'
  - ufw allow 143/tcp    comment 'Stalwart IMAP STARTTLS'
  - ufw allow 993/tcp    comment 'Stalwart IMAPS (TLS)'
  - ufw allow 4190/tcp   comment 'Stalwart ManageSieve'
  - ufw allow from 10.9.0.0/24 to any port 22 proto tcp comment 'SSH via AmneziaWG VPN'
  - ufw --force enable

  # 7. Создание директории приложения (PowerShell-скрипт зальёт сюда репо)
  - mkdir -p /opt/msp
  - chown -R ubuntu:ubuntu /opt/msp

  # 8. logrotate для будущих логов приложения
  - |
    cat > /etc/logrotate.d/msp-app <<'EOF'
    /var/log/msp-deploy.log {
      daily
      rotate 14
      compress
      missingok
      notifempty
    }
    EOF

  # 9. Включаем systemd-сервисы
  - systemctl enable --now docker
  - systemctl enable --now caddy

  # 10. AmneziaWG (PPA ppa:amnezia/ppa) — установка пакетов.
  #     Самый факт запуска сервиса — в awg_bootstrap.sh (ручной ONE-TIME шаг),
  #     чтобы не генерировать ключи в cloud-init (невосстанавливаемые без бэкапа).
  - DEBIAN_FRONTEND=noninteractive apt-get install -y software-properties-common
  - add-apt-repository -y ppa:amnezia/ppa
  - apt-get update
  - DEBIAN_FRONTEND=noninteractive apt-get install -y amneziawg-dkms amneziawg-tools qrencode
  - sysctl -w net.ipv4.ip_forward=1
  - echo 'net.ipv4.ip_forward=1' > /etc/sysctl.d/99-awg.conf

  # 11. Базовая валидация (урок миграции 28.09): маркер готовности пишем только если
  #     docker/caddy/node/unzip реально на месте — иначе deploy.ps1 лучше явно
  #     дождётся таймаута, чем продолжит на полусобранной ВМ.
  - |
    miss=""
    for b in docker caddy node curl git jq unzip python3; do
      command -v "$b" >/dev/null 2>&1 || miss="$miss $b"
    done
    if [ -n "$miss" ]; then
      echo "BASE-VALIDATION FAILED: missing:$miss" >> /var/log/msp-deploy.log
      exit 1
    fi
    case "$(node -v)" in
      v20*) ;;
      *) echo "BASE-VALIDATION WARN: node $(node -v) — ожидался v20" >> /var/log/msp-deploy.log ;;
    esac
    echo "BASE-VALIDATION OK: node=$(node -v), docker=$(docker --version)" >> /var/log/msp-deploy.log
    touch /var/log/msp-deploy.base-ready
    date -u +"%Y-%m-%dT%H:%M:%SZ base provisioning done" >> /var/log/msp-deploy.log

# Финальный шаг — если что-то упало, отметить ошибку явно.
final_message: |
  cloud-init finished at $TIMESTAMP. Base OS provisioning done.
  deploy.ps1 will continue with code upload + app start.

```

## Практический результат

Перескажите цепочку своими словами, выполните безопасную лабораторную работу и сохраните команды без секретов, фактический результат и способ отката. Если результат отличается от текста, остановитесь: сначала исправляется расхождение, а не подгоняется отчёт.
