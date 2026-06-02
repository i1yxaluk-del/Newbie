#!/usr/bin/env bash
# ═══════════════════════════════════════════════════════════════════
# setup-on-vm.sh — выполняется на ВМ через SSH из deploy.ps1 после
# того как cloud-init завершил базовую подготовку и код залит в
# /opt/msp/Newbie.
#
# Этапы:
#   1. Генерация secrets → backend/.env + ~/msp-deploy-secrets.txt
#   2. Frontend: yarn install + yarn build → /var/www/landing
#   3. Caddyfile установка + reload
#   4. docker compose build + up (mongo + backend + stalwart)
#   5. Healthcheck /api/health
#   6. Вывод DNS-инструкций
# ═══════════════════════════════════════════════════════════════════

set -euo pipefail

REPO_DIR="/opt/msp/Newbie"
DEPLOY_DIR="$REPO_DIR/deploy/yandex"
BACKEND_DIR="$REPO_DIR/backend"
FRONTEND_DIR="$REPO_DIR/frontend"
WEB_ROOT="/var/www/landing"
SECRETS_FILE="$HOME/msp-deploy-secrets.txt"
LOG_FILE="/var/log/msp-deploy.log"

DOMAIN="${MSP_DOMAIN:-msp-claude.online}"
# ВАЖНО: дефолт домена должен ТОЧНО совпадать с DNS!
# У нас была опечатка mcp-claude.online вместо msp-claude.online —
# Caddy получил staging-сертификаты, а браузеры их не приняли.
# Если меняешь дефолт — проверь что A-запись в DNS указывает на IP ВМ.

log() {
  echo "[$(date -u +%H:%M:%S)] $*" | tee -a "$LOG_FILE"
}

log "═══ setup-on-vm.sh START · domain=$DOMAIN ═══"

# ─── 1. Базовая проверка окружения ─────────────────────────────────
if [ ! -d "$REPO_DIR" ]; then
  log "ERROR: репозиторий не загружен в $REPO_DIR"
  exit 1
fi

# Ждём пока cloud-init закончит (если ещё не закончил)
while [ ! -f /var/log/msp-deploy.base-ready ]; do
  log "Жду base provisioning (cloud-init)..."
  sleep 5
done

# ─── 2. Генерация secrets ──────────────────────────────────────────
log "▶ Генерация secrets..."

gen_hex() { openssl rand -hex 32; }
gen_pass() { openssl rand -base64 24 | tr -d '/+=' | head -c 24; }

ADMIN_TOKEN=$(gen_hex)
MAX_WEBHOOK_SECRET=$(gen_hex)
ALERTMANAGER_WEBHOOK_TOKEN=$(gen_hex)
STALWART_ADMIN_PASSWORD=$(gen_pass)
MAIL_ADMIN_PASSWORD=$(gen_pass)
MAIL_SALES_PASSWORD=$(gen_pass)
MAIL_ALERT_PASSWORD=$(gen_pass)
VAULTWARDEN_ADMIN_TOKEN=$(gen_hex)

# backend/.env — секреты приложения
if [ ! -f "$BACKEND_DIR/.env" ]; then
  cat > "$BACKEND_DIR/.env" <<EOF
# Сгенерировано $(date -u +"%Y-%m-%dT%H:%M:%SZ") при первом деплое.
# Не редактировать вручную — пересоздание потеряет данные.

# ─── MongoDB ───
MONGO_URL=mongodb://mongo:27017
DB_NAME=mspshield

# ─── Auth / Admin ───
ADMIN_TOKEN=$ADMIN_TOKEN

# ─── CORS ───
CORS_ORIGINS=https://$DOMAIN,https://www.$DOMAIN

# ─── MAX Bot (заполните после регистрации @MasterBot) ───
MAX_BOT_TOKEN=
MAX_BOT_USERNAME=
MAX_ALERT_CHAT_ID=
MAX_WEBHOOK_SECRET=$MAX_WEBHOOK_SECRET

# ─── Telegram (опционально) ───
TG_BOT_TOKEN=
TG_CHAT_ID=
TG_ALERT_CHAT_ID=

# ─── Alertmanager → MAX/Telegram ───
ALERTMANAGER_WEBHOOK_TOKEN=$ALERTMANAGER_WEBHOOK_TOKEN
ALERT_CHANNELS=max,telegram
ALERT_RESOLVED_NOTIFY=true

# ─── Kaiten CRM (опционально) ───
KAITEN_DOMAIN=
KAITEN_API_TOKEN=
KAITEN_BOARD_ID=
KAITEN_COLUMN_ID=
KAITEN_LANE_ID=

# ─── SMTP (Stalwart, localhost для бэка) ───
SMTP_HOST=stalwart
SMTP_PORT=587
SMTP_USER=alert@$DOMAIN
SMTP_PASSWORD=$MAIL_ALERT_PASSWORD
SMTP_FROM=alert@$DOMAIN
EOF
  log "  backend/.env создан"
else
  log "  backend/.env уже существует — оставляю как есть"
fi

# frontend/.env — REACT_APP_BACKEND_URL пустой → same-origin через Caddy
if [ ! -f "$FRONTEND_DIR/.env" ]; then
  cat > "$FRONTEND_DIR/.env" <<EOF
# REACT_APP_BACKEND_URL пустой = фронт ходит на тот же origin что и сам.
# Caddy прокинет /api/* на бэк.
REACT_APP_BACKEND_URL=
EOF
  log "  frontend/.env создан"
fi

# Сохраняем все пароли в ОДИН файл (.txt в home ubuntu, chmod 600)
cat > "$SECRETS_FILE" <<EOF
═══════════════════════════════════════════════════════════════════
МСП Облако · $DOMAIN · ПАРОЛИ
$(date -u +"%Y-%m-%dT%H:%M:%SZ")

ВНИМАНИЕ: этот файл существует только на ВМ.
СКОПИРУЙТЕ его себе и УДАЛИТЕ с ВМ после первого входа.
═══════════════════════════════════════════════════════════════════

[Backend admin]
URL:              https://$DOMAIN/admin
ADMIN_TOKEN:      $ADMIN_TOKEN

[Stalwart admin WebUI]
URL:              http://localhost:8080/admin (через SSH tunnel)
SSH-tunnel:       ssh -L 8080:localhost:8080 ubuntu@<IP>
Username:         admin
Password:         $STALWART_ADMIN_PASSWORD

[Email accounts — создаются в Stalwart wizard, эти пароли подставьте]
admin@$DOMAIN     $MAIL_ADMIN_PASSWORD
sales@$DOMAIN     $MAIL_SALES_PASSWORD
alert@$DOMAIN     $MAIL_ALERT_PASSWORD

[Webhook tokens — для интеграций]
MAX_WEBHOOK_SECRET           $MAX_WEBHOOK_SECRET
ALERTMANAGER_WEBHOOK_TOKEN   $ALERTMANAGER_WEBHOOK_TOKEN

[Vaultwarden]
URL:              https://vault.$DOMAIN/admin
VAULTWARDEN_ADMIN_TOKEN: $VAULTWARDEN_ADMIN_TOKEN

[Postbox outbound relay]
POSTBOX_API_KEY_ID / POSTBOX_API_KEY_SECRET are not generated automatically.
Create them in Yandex Cloud Postbox and add them to:
  $DEPLOY_DIR/.env

═══════════════════════════════════════════════════════════════════
EOF
chmod 600 "$SECRETS_FILE"
log "  Пароли сохранены в $SECRETS_FILE (chmod 600)"

# Экспортим для docker-compose substitutions.
cat > "$DEPLOY_DIR/.env" <<EOF
STALWART_ADMIN_PASSWORD=$STALWART_ADMIN_PASSWORD
VAULTWARDEN_ADMIN_TOKEN=$VAULTWARDEN_ADMIN_TOKEN
VAULTWARDEN_DOMAIN=https://vault.$DOMAIN

# Yandex Cloud Postbox outbound relay. Fill before first Stalwart bootstrap
# or configure the route later via Stalwart Admin UI.
POSTBOX_API_KEY_ID=
POSTBOX_API_KEY_SECRET=
EOF
chmod 600 "$DEPLOY_DIR/.env"

# ─── 3. Frontend build ─────────────────────────────────────────────
log "▶ Frontend build (yarn install + yarn build)..."

cd "$FRONTEND_DIR"
# corepack уже активирован в cloud-init, yarn должен работать
yarn install --frozen-lockfile 2>&1 | tee -a "$LOG_FILE"
yarn build 2>&1 | tee -a "$LOG_FILE"

# Очищаем старый docroot и копируем свежий билд
sudo mkdir -p "$WEB_ROOT"
sudo rm -rf "$WEB_ROOT"/*
sudo cp -r build/* "$WEB_ROOT/"
sudo chown -R caddy:caddy "$WEB_ROOT"
log "  Фронт залит в $WEB_ROOT ($(du -sh "$WEB_ROOT" | cut -f1))"

# ─── 4. Caddyfile ──────────────────────────────────────────────────
log "▶ Caddyfile установка..."

# Подкладываем наш Caddyfile с подстановкой {$MSP_DOMAIN} → реальный домен.
# ВАЖНО: Caddy НЕ поддерживает env-var подстановку в именах серверных
# блоков (sudo сбрасывает переменные окружения). Поэтому делаем sed:
sudo install -m 0644 "$DEPLOY_DIR/Caddyfile" /etc/caddy/Caddyfile
sudo sed -i "s/{\$MSP_DOMAIN}/$DOMAIN/g" /etc/caddy/Caddyfile

# Проверяем что не осталось неразрешённых плейсхолдеров
if grep -q '{\$MSP_DOMAIN}' /etc/caddy/Caddyfile; then
  log "ERROR: в Caddyfile остался плейсхолдер {\$MSP_DOMAIN} — sed не сработал"
  grep '{\$MSP_DOMAIN}' /etc/caddy/Caddyfile | tee -a "$LOG_FILE"
  exit 1
fi

sudo mkdir -p /etc/systemd/system/caddy.service.d
sudo tee /etc/systemd/system/caddy.service.d/override.conf > /dev/null <<EOF
[Service]
Environment="MSP_DOMAIN=$DOMAIN"
EOF

sudo systemctl daemon-reload

if sudo caddy validate --config /etc/caddy/Caddyfile --adapter caddyfile 2>&1 | tee -a "$LOG_FILE"; then
  sudo systemctl restart caddy
  log "  Caddy перезапущен"
else
  log "ERROR: Caddyfile невалидный, Caddy НЕ перезапущен"
  exit 1
fi

# ─── 5. Docker compose: build + up ─────────────────────────────────
log "▶ Docker compose build + up..."

cd "$DEPLOY_DIR"

# Останавливаем старые контейнеры если есть (idempotent)
docker compose down 2>&1 | tee -a "$LOG_FILE" || true

# Билдим и поднимаем
docker compose build 2>&1 | tee -a "$LOG_FILE"
docker compose up -d 2>&1 | tee -a "$LOG_FILE"

# ─── 6. Healthcheck backend ────────────────────────────────────────
log "▶ Ждём готовности backend /api/health..."

for i in {1..60}; do
  if curl -fsS http://127.0.0.1:8001/api/health > /dev/null 2>&1; then
    log "  ✓ Backend готов (попытка $i)"
    break
  fi
  if [ "$i" = "60" ]; then
    log "ERROR: Backend не отвечает после 5 минут"
    docker compose logs backend | tail -50 | tee -a "$LOG_FILE"
    exit 1
  fi
  sleep 5
done

# ─── 7. Healthcheck Stalwart ───────────────────────────────────────
log "▶ Ждём готовности Stalwart admin :8080..."

for i in {1..30}; do
  if curl -fsS http://127.0.0.1:8080/ > /dev/null 2>&1; then
    log "  ✓ Stalwart готов (попытка $i)"
    break
  fi
  if [ "$i" = "30" ]; then
    log "WARN: Stalwart не отвечает после 2.5 минут — проверьте 'docker logs msp-stalwart-1'"
  fi
  sleep 5
done

# ─── 8. Маркер готовности для deploy.ps1 ───────────────────────────
touch /var/log/msp-deploy.app-ready
log "═══ setup-on-vm.sh DONE · $(date -u +"%Y-%m-%dT%H:%M:%SZ") ═══"
