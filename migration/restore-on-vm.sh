#!/usr/bin/env bash
# Назначение: восстановить Mongo, Vaultwarden, Stalwart и MAX на подготовленной новой VM.
# Где запускать: новая VM от root после deploy preflight.
# Важно: старые .env/cloud credentials не восстанавливаются.
# Откат: snapshot новой VM, созданный до запуска.
set -Eeuo pipefail

MIGRATION_DIR="${MIGRATION_DIR:-/tmp/migration}"
REPO_DIR="${REPO_DIR:-/opt/msp/Newbie}"
DEPLOY_DIR="$REPO_DIR/deploy/yandex"
MONITORING_DIR="$DEPLOY_DIR/monitoring"
log() { echo "[$(date -Iseconds)] $*" | tee -a /var/log/msp-migration.log; }
[[ -s "$MIGRATION_DIR/mongodump.archive.gz" ]] || { log "ERROR: нет mongodump.archive.gz"; exit 1; }
[[ -s "$DEPLOY_DIR/.env" && -s "$MONITORING_DIR/.env" ]] || { log "ERROR: сначала создайте новые .env"; exit 1; }

(cd "$MONITORING_DIR" && docker compose down) || true
(cd "$DEPLOY_DIR" && docker compose --profile mail down) || true
cd "$DEPLOY_DIR"
docker compose up -d mongo
MONGO_ID="$(docker compose ps -q mongo)"
for _ in $(seq 1 30); do docker exec "$MONGO_ID" mongosh --quiet --eval "db.adminCommand('ping').ok" 2>/dev/null | grep -q 1 && break; sleep 3; done
docker exec "$MONGO_ID" mongosh --quiet --eval "db.adminCommand('ping').ok" | grep -q 1
docker exec -i "$MONGO_ID" mongorestore --archive --gzip --drop < "$MIGRATION_DIR/mongodump.archive.gz"

restore_volume() {
  local archive="$1" volume="$2"
  [[ -s "$MIGRATION_DIR/$archive" ]] || { log "INFO: $archive отсутствует"; return; }
  docker volume create "$volume" >/dev/null
  docker run --rm -v "$volume:/target" -v "$MIGRATION_DIR:/backup:ro" alpine:3.20 \
    sh -c "rm -rf /target/* && tar xzf /backup/$archive -C /target"
}
restore_volume vaultwarden-data.tar.gz msp_vaultwarden-data
restore_volume stalwart-etc.tar.gz msp_stalwart-etc
restore_volume stalwart-data.tar.gz msp_stalwart-data

if [[ -s "$MIGRATION_DIR/max-session.tar.gz" ]]; then
  rm -rf "$MONITORING_DIR/max-session"
  tar xzf "$MIGRATION_DIR/max-session.tar.gz" -C "$MONITORING_DIR"
  chmod 700 "$MONITORING_DIR/max-session"
  chmod 600 "$MONITORING_DIR/max-session/max.db" 2>/dev/null || true
fi

(cd "$DEPLOY_DIR" && docker compose up -d)
# Stalwart запускается только если mail profile используется осознанно.
if [[ -s "$MIGRATION_DIR/stalwart-etc.tar.gz" ]]; then (cd "$DEPLOY_DIR" && docker compose --profile mail up -d stalwart); fi
(cd "$MONITORING_DIR" && chmod +x alertmanager/entrypoint.sh && docker compose up -d --build)

curl -fsS --retry 30 --retry-delay 3 http://127.0.0.1:8001/api/health >/dev/null
curl -fsS http://127.0.0.1:9093/-/healthy >/dev/null
curl -fsS http://127.0.0.1:9095/health >/dev/null
if ! docker exec msp-max-alerter python -m max_alerter.auth; then
  log "WARN: MAX session требует ручной авторизации: docker exec -it msp-max-alerter python -m max_alerter.auth --authorize"
fi
log "Restore завершён. До DNS switch обязательны тест P1, restore evidence и новый restic snapshot."
