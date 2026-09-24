#!/usr/bin/env bash
# Назначение: восстановить данные на уже подготовленной новой VM.
# Важно: скрипт не переносит старые .env и cloud credentials.
# Откат: до запуска создайте snapshot новой VM; при ошибке восстановите snapshot.
set -euo pipefail

MIGRATION_DIR="${MIGRATION_DIR:-/tmp/migration}"
REPO_DIR="${REPO_DIR:-/opt/msp/Newbie}"
DEPLOY_DIR="$REPO_DIR/deploy/yandex"
MONITORING_DIR="$DEPLOY_DIR/monitoring"
LOG="/var/log/msp-migration.log"
log() { echo "[$(date -Iseconds)] $*" | tee -a "$LOG"; }
require_file() { [[ -s "$1" ]] || { log "ERROR: отсутствует $1"; exit 1; }; }

require_file "$MIGRATION_DIR/mongodump.archive.gz"
[[ -f "$DEPLOY_DIR/docker-compose.yml" ]] || { log "ERROR: deploy не подготовлен"; exit 1; }
[[ -f "$DEPLOY_DIR/.env" ]] || { log "ERROR: сначала создайте новый deploy .env"; exit 1; }
[[ -f "$MONITORING_DIR/.env" ]] || { log "ERROR: сначала создайте monitoring .env"; exit 1; }

docker info >/dev/null
log "Останавливаем application и monitoring stacks"
(cd "$MONITORING_DIR" && docker compose down) || true
(cd "$DEPLOY_DIR" && docker compose down) || true

log "Запускаем MongoDB и определяем container ID через Compose"
cd "$DEPLOY_DIR"
docker compose up -d mongo
MONGO_ID="$(docker compose ps -q mongo)"
[[ -n "$MONGO_ID" ]] || { log "ERROR: Mongo container не найден"; exit 1; }
for _ in $(seq 1 30); do
  docker exec "$MONGO_ID" mongosh --quiet --eval "db.adminCommand('ping').ok" 2>/dev/null | grep -q 1 && break
  sleep 3
done
docker exec "$MONGO_ID" mongosh --quiet --eval "db.adminCommand('ping').ok" | grep -q 1
docker exec -i "$MONGO_ID" mongorestore --archive --gzip --drop < "$MIGRATION_DIR/mongodump.archive.gz"

log "Восстанавливаем MAX session, если архив передан"
if [[ -s "$MIGRATION_DIR/max-session.tar.gz" ]]; then
  mkdir -p "$MONITORING_DIR/max-session"
  tar xzf "$MIGRATION_DIR/max-session.tar.gz" -C "$MONITORING_DIR"
  chmod 700 "$MONITORING_DIR/max-session"
  chmod 600 "$MONITORING_DIR/max-session/max.db" 2>/dev/null || true
fi

log "Восстанавливаем Vaultwarden data, если архив передан"
if [[ -s "$MIGRATION_DIR/vaultwarden-data.tar.gz" ]]; then
  docker volume create msp_vaultwarden-data >/dev/null
  docker run --rm -v msp_vaultwarden-data:/data -v "$MIGRATION_DIR:/backup:ro" alpine \
    sh -c 'rm -rf /data/* && tar xzf /backup/vaultwarden-data.tar.gz -C /data'
fi

log "Запускаем стеки с новой конфигурацией"
(cd "$DEPLOY_DIR" && docker compose up -d)
(cd "$MONITORING_DIR" && chmod +x alertmanager/entrypoint.sh && docker compose up -d --build)

log "Проверяем health и MAX session без SMS"
for _ in $(seq 1 30); do
  curl -fsS http://127.0.0.1:8001/api/health >/dev/null 2>&1 && break
  sleep 3
done
curl -fsS http://127.0.0.1:8001/api/health >/dev/null
curl -fsS http://127.0.0.1:9093/-/healthy >/dev/null
curl -fsS http://127.0.0.1:9095/health >/dev/null
if ! docker exec msp-max-alerter python -m max_alerter.auth; then
  log "WARN: MAX session требует ручной авторизации"
  log "sudo docker exec -it msp-max-alerter python -m max_alerter.auth --authorize"
fi
log "Restore завершён. До DNS switch выполните тестовый P1 и новый restic backup."
