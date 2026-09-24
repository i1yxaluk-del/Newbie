#!/usr/bin/env bash
# Назначение: создать согласованные backup-артефакты и отправить их в restic/S3.
# Где запускать: production VM от root через systemd timer.
# Побочные эффекты: Vaultwarden/Stalwart/MAX кратко останавливаются для snapshot.
# Проверка успеха: метрика restic_backup_success=1 и `restic snapshots --latest 1`.
# Откат: сервисы автоматически запускаются в trap даже при ошибке.
set -Eeuo pipefail

DEPLOY_DIR="${DEPLOY_DIR:-/opt/msp/Newbie/deploy/yandex}"
MONITORING_DIR="$DEPLOY_DIR/monitoring"
STAGING="${BACKUP_STAGING:-/opt/msp-backups/current}"
METRICS_FILE="/var/lib/node_exporter/textfile_collector/restic_backup.prom"
EXCLUDE_FILE="/opt/restic-scripts/excludes.txt"
LOG="/var/log/restic-backup.log"
HOST_LABEL="${BACKUP_HOST_LABEL:-node-01}"
REPO_LABEL="${BACKUP_REPO_LABEL:-mspshield-backups-new}"
STARTED_AT="$(date +%s)"
RESTART_MAIN=()
RESTART_MONITORING=()

log() { echo "[$(date -Iseconds)] $*" | tee -a "$LOG"; }
write_metrics() {
  mkdir -p "$(dirname "$METRICS_FILE")"
  cat > "${METRICS_FILE}.tmp" <<EOF
# HELP restic_backup_success Last backup result: 1=success, 0=failure, 2=running
# TYPE restic_backup_success gauge
restic_backup_success{host="$HOST_LABEL",repo="$REPO_LABEL"} $1
# HELP restic_backup_timestamp_seconds Unix timestamp of backup start
# TYPE restic_backup_timestamp_seconds gauge
restic_backup_timestamp_seconds{host="$HOST_LABEL",repo="$REPO_LABEL"} $2
# HELP restic_backup_size_bytes Bytes processed by the last successful backup
# TYPE restic_backup_size_bytes gauge
restic_backup_size_bytes{host="$HOST_LABEL",repo="$REPO_LABEL"} $3
EOF
  mv "${METRICS_FILE}.tmp" "$METRICS_FILE"
}
restart_services() {
  if ((${#RESTART_MAIN[@]})); then (cd "$DEPLOY_DIR" && docker compose --profile mail start "${RESTART_MAIN[@]}") || true; fi
  if ((${#RESTART_MONITORING[@]})); then (cd "$MONITORING_DIR" && docker compose start "${RESTART_MONITORING[@]}") || true; fi
}
trap restart_services EXIT

source /etc/restic/env.sh
: "${RESTIC_REPOSITORY:?RESTIC_REPOSITORY не задан}"
: "${RESTIC_PASSWORD:?RESTIC_PASSWORD не задан}"
command -v restic >/dev/null
command -v docker >/dev/null
write_metrics 2 "$STARTED_AT" 0
rm -rf "$STAGING"
mkdir -p "$STAGING/volumes"

log "Создаём обязательный согласованный mongodump"
MONGO_ID="$(docker compose -f "$DEPLOY_DIR/docker-compose.yml" ps -q mongo)"
[[ -n "$MONGO_ID" ]] || { log "ERROR: Mongo container не найден"; exit 1; }
docker exec "$MONGO_ID" mongodump --archive --gzip --quiet > "$STAGING/mongodump.archive.gz"
[[ -s "$STAGING/mongodump.archive.gz" ]] || { log "ERROR: mongodump пуст"; exit 1; }

# Файловые Docker volumes архивируются только при остановленном writer.
for service in vaultwarden stalwart; do
  if docker compose -f "$DEPLOY_DIR/docker-compose.yml" --profile mail ps -q "$service" | grep -q .; then
    RESTART_MAIN+=("$service")
    (cd "$DEPLOY_DIR" && docker compose --profile mail stop "$service")
  fi
done
if docker compose -f "$MONITORING_DIR/docker-compose.yml" ps -q max-alerter | grep -q .; then
  RESTART_MONITORING+=("max-alerter")
  (cd "$MONITORING_DIR" && docker compose stop max-alerter)
fi

archive_volume() {
  local volume="$1" output="$2"
  if docker volume inspect "$volume" >/dev/null 2>&1; then
    docker run --rm -v "$volume:/source:ro" -v "$STAGING/volumes:/backup" alpine:3.20 \
      tar czf "/backup/$output" -C /source .
  else
    log "INFO: volume $volume отсутствует, пропускаем"
  fi
}
archive_volume msp_vaultwarden-data vaultwarden-data.tar.gz
archive_volume msp_stalwart-etc stalwart-etc.tar.gz
archive_volume msp_stalwart-data stalwart-data.tar.gz
if [[ -d "$MONITORING_DIR/max-session" ]]; then
  tar czf "$STAGING/volumes/max-session.tar.gz" -C "$MONITORING_DIR" max-session
fi
restart_services
RESTART_MAIN=()
RESTART_MONITORING=()

# Не бэкапим /var/lib/docker/volumes напрямую: live-copy БД неконсистентна и дублирует данные.
PATHS=(/etc /home /root /opt /var/www /var/lib/caddy "$STAGING")
EXISTING=()
for path in "${PATHS[@]}"; do [[ -e "$path" ]] && EXISTING+=("$path"); done
log "Запускаем restic: ${EXISTING[*]}"
OUTPUT="$STAGING/restic-result.json"
if restic backup "${EXISTING[@]}" --exclude-file="$EXCLUDE_FILE" --tag auto --tag "$HOST_LABEL" --json | tee "$OUTPUT" >> "$LOG"; then
  BYTES="$(grep -E '"message_type":"summary"' "$OUTPUT" | tail -1 | grep -oE '"total_bytes_processed":[0-9]+' | cut -d: -f2 || true)"
  write_metrics 1 "$STARTED_AT" "${BYTES:-0}"
else
  write_metrics 0 "$STARTED_AT" 0
  exit 1
fi
restic forget --tag "$HOST_LABEL" --keep-daily 7 --keep-weekly 4 --keep-monthly 6 --keep-yearly 1 --prune
if [[ "$(date +%u)" == "7" ]]; then restic check; fi
log "Backup завершён успешно"
