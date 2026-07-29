#!/usr/bin/env bash
set -euo pipefail

MIGRATION_DIR="/tmp/migration"
REPO_DIR="/opt/msp/Newbie"
DEPLOY_DIR="$REPO_DIR/deploy/yandex"
BACKEND_DIR="$REPO_DIR/backend"
LOG="/var/log/msp-migration.log"

log() { echo "[$(date -u +%H:%M:%S)] $*" | tee -a "$LOG"; }

log "═══ MIGRATION RESTORE START ═══"

if [ ! -d "$MIGRATION_DIR" ]; then
  log "ERROR: $MIGRATION_DIR не найден. Загрузите файлы миграции на ВМ."
  exit 1
fi

log "▶ Ожидание docker..."
for i in $(seq 1 30); do
  if docker info &>/dev/null; then break; fi
  sleep 5
done
docker info &>/dev/null || { log "ERROR: docker не готов"; exit 1; }

log "▶ Остановка контейнеров..."
cd "$DEPLOY_DIR"
docker compose down 2>/dev/null || true
if [ -f "$DEPLOY_DIR/monitoring/docker-compose.yml" ]; then
  cd "$DEPLOY_DIR/monitoring"
  docker compose down 2>/dev/null || true
fi

log "▶ Восстановление MongoDB..."
cd "$DEPLOY_DIR"
docker compose up -d mongo
sleep 10
for i in $(seq 1 30); do
  if docker exec msp-mongo-1 mongosh --quiet --eval "db.adminCommand('ping').ok" 2>/dev/null | grep -q 1; then
    break
  fi
  sleep 3
done
docker exec -i msp-mongo-1 mongorestore --archive --gzip --drop < "$MIGRATION_DIR/mongodump.archive.gz"
log "  MongoDB: $(docker exec msp-mongo-1 mongosh --quiet --eval 'db.getSiblingDB("mspshield").leads.countDocuments()' 2>/dev/null) leads"

log "▶ Восстановление Stalwart..."
STALWART_ETC_VOL=$(docker volume ls --format '{{.Name}}' | grep stalwart-etc | head -1)
STALWART_DATA_VOL=$(docker volume ls --format '{{.Name}}' | grep stalwart-data | head -1)
if [ -n "$STALWART_ETC_VOL" ] && [ -s "$MIGRATION_DIR/stalwart-etc.tar.gz" ]; then
  docker run --rm -v "${STALWART_ETC_VOL}:/data" -v "$MIGRATION_DIR:/backup" alpine \
    sh -c "rm -rf /data/* && tar xzf /backup/stalwart-etc.tar.gz -C /data"
  log "  stalwart-etc восстановлен"
fi
if [ -n "$STALWART_DATA_VOL" ] && [ -s "$MIGRATION_DIR/stalwart-data.tar.gz" ]; then
  docker run --rm -v "${STALWART_DATA_VOL}:/data" -v "$MIGRATION_DIR:/backup" alpine \
    sh -c "rm -rf /data/* && tar xzf /backup/stalwart-data.tar.gz -C /data"
  log "  stalwart-data восстановлен"
fi

log "▶ Восстановление Vaultwarden..."
VAULT_VOL=$(docker volume ls --format '{{.Name}}' | grep vaultwarden-data | head -1)
if [ -n "$VAULT_VOL" ] && [ -s "$MIGRATION_DIR/vaultwarden-data.tar.gz" ]; then
  docker run --rm -v "${VAULT_VOL}:/data" -v "$MIGRATION_DIR:/backup" alpine \
    sh -c "rm -rf /data/* && tar xzf /backup/vaultwarden-data.tar.gz -C /data"
  log "  vaultwarden-data восстановлен"
fi

log "▶ Восстановление Caddy (SSL-сертификаты)..."
if [ -s "$MIGRATION_DIR/caddy-data.tar.gz" ]; then
  sudo mkdir -p /var/lib/caddy
  sudo tar xzf "$MIGRATION_DIR/caddy-data.tar.gz" -C /var/lib/caddy
  sudo chown -R caddy:caddy /var/lib/caddy 2>/dev/null || true
  log "  Caddy data восстановлен (сертификаты LE)"
fi

log "▶ Восстановление secrets (.env)..."
if [ -f "$MIGRATION_DIR/backend.env.bak" ]; then
  sudo cp "$MIGRATION_DIR/backend.env.bak" "$BACKEND_DIR/.env"
  sudo chown root:root "$BACKEND_DIR/.env"
  sudo chmod 600 "$BACKEND_DIR/.env"
  log "  backend/.env восстановлен"
fi
if [ -f "$MIGRATION_DIR/deploy.env.bak" ]; then
  sudo cp "$MIGRATION_DIR/deploy.env.bak" "$DEPLOY_DIR/.env"
  log "  deploy/yandex/.env восстановлен"
fi

log "▶ Восстановление restic (бэкапы)..."
if [ -f "$MIGRATION_DIR/restic-env.sh" ]; then
  sudo mkdir -p /etc/restic /opt/restic-scripts
  sudo cp "$MIGRATION_DIR/restic-env.sh" /etc/restic/env.sh
  sudo chmod 600 /etc/restic/env.sh
  sudo cp "$MIGRATION_DIR/restic-backup.sh" /opt/restic-scripts/backup.sh
  sudo chmod +x /opt/restic-scripts/backup.sh
  if [ -f "$MIGRATION_DIR/restic-excludes.txt" ]; then
    sudo cp "$MIGRATION_DIR/restic-excludes.txt" /opt/restic-scripts/excludes.txt
  fi
  sudo cp /dev/stdin /etc/systemd/system/restic-backup.service <<'EOF'
[Unit]
Description=MSP Restic Backup
After=network-online.target
Wants=network-online.target

[Service]
Type=oneshot
EnvironmentFile=/etc/restic/env.sh
ExecStart=/opt/restic-scripts/backup.sh
Nice=19
IOSchedulingClass=best-effort
IOSchedulingPriority=7
TimeoutStartSec=7200
StandardOutput=journal+console
StandardError=journal+console
SyslogIdentifier=restic-backup
EOF
  sudo cp /dev/stdin /etc/systemd/system/restic-backup.timer <<'EOF'
[Unit]
Description=MSP Restic Backup Timer
Requires=restic-backup.service

[Timer]
OnCalendar=*-*-* 02:00:00
RandomizedDelaySec=5min
Persistent=true
AccuracySec=30s

[Install]
WantedBy=timers.target
EOF
  sudo systemctl daemon-reload
  sudo systemctl enable --now restic-backup.timer
  log "  restic backup timer активирован (ежедневно 02:00)"
fi

log "▶ Запуск всех контейнеров..."
cd "$DEPLOY_DIR"
docker compose up -d
sleep 5
if [ -f "$DEPLOY_DIR/monitoring/docker-compose.yml" ]; then
  cd "$DEPLOY_DIR/monitoring"
  docker compose up -d
fi

log "▶ Перезапуск Caddy..."
sudo systemctl restart caddy

log "▶ Ожидание healthcheck (30s)..."
sleep 30

HEALTH=$(curl -sS http://127.0.0.1:8001/api/health 2>/dev/null || echo "FAIL")
log "  /api/health → $HEALTH"

CONTAINERS=$(docker ps --format '{{.Names}}' | wc -l)
log "  Контейнеров запущено: $CONTAINERS"

log "═══ MIGRATION RESTORE COMPLETE ═══"
log ""
log "Следующие шаги:"
log "  1. Обновить DNS A-записи на новый IP"
log "  2. Проверить: curl https://msp-claude.online/api/health"
log "  3. Проверить почту: ssh -L 8080:127.0.0.1:8080 ubuntu@<IP> → http://localhost:8080/admin"
log "  4. Проверить Vaultwarden: https://vault.msp-claude.online"
log "  5. Проверить Grafana: https://mon.msp-claude.online"
