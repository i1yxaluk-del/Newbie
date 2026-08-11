#!/bin/bash
set -euo pipefail

LOG="/var/log/restic-backup.log"
METRICS_DIR="/var/lib/node_exporter/textfile_collector"
METRICS_FILE="${METRICS_DIR}/restic_backup.prom"
EXCLUDE_FILE="/opt/restic-scripts/excludes.txt"
HOSTNAME="node-01"
# REPO — только ЛЕЙБЛ для метрик Prometheus (name соответствует новому бакету
# mspshield-backups-new). Сам репозиторий restic берётся из RESTIC_REPOSITORY
# в /etc/restic/env.sh (source ниже) — REPO в команды restic НЕ передаётся.
REPO="mspshield-backups-new"
TIMESTAMP=$(date +%s)
STATUS=0
BYTES=0
MONGO_DUMP_DIR="/opt/msp-backups/mongodump"

# УРОК миграции 2: имя Mongo-контейнера не стабильно (msp-mongo-1 → др.).
# Получаем ID через docker compose ps -q mongo; фолбэк — поиск по имени.
MONGO_COMPOSE_FILE="/opt/msp/Newbie/deploy/yandex/docker-compose.yml"
MONGO_CONTAINER=""
if [ -f "$MONGO_COMPOSE_FILE" ]; then
    MONGO_CONTAINER=$(docker compose -f "$MONGO_COMPOSE_FILE" ps -q mongo 2>/dev/null | head -1)
fi
if [ -z "$MONGO_CONTAINER" ]; then
    MONGO_CONTAINER=$(docker ps --filter "name=mongo" --format '{{.Names}}' | head -1)
fi

source /etc/restic/env.sh

log() {
    local msg="[$(date '+%Y-%m-%d %H:%M:%S')] $*"
    echo "$msg"
    echo "$msg" >> "$LOG"
}

write_metrics() {
    local status=$1
    local timestamp=$2
    local bytes=$3
    mkdir -p "$METRICS_DIR"
    local tmp="${METRICS_FILE}.tmp"
    cat > "$tmp" << EOF
# HELP restic_backup_success Last restic backup result (1=ok, 0=fail, 2=in-progress)
# TYPE restic_backup_success gauge
restic_backup_success{host="${HOSTNAME}",repo="${REPO}"} ${status}
# HELP restic_backup_timestamp_seconds Unix time of last restic backup
# TYPE restic_backup_timestamp_seconds gauge
restic_backup_timestamp_seconds{host="${HOSTNAME}",repo="${REPO}"} ${timestamp}
# HELP restic_backup_size_bytes Size of last restic backup in bytes
# TYPE restic_backup_size_bytes gauge
restic_backup_size_bytes{host="${HOSTNAME}",repo="${REPO}"} ${bytes}
EOF
    mv "$tmp" "$METRICS_FILE"
}

write_metrics 2 "$TIMESTAMP" 0

log "=== START BACKUP host=${HOSTNAME} repo=${REPO} ==="

# ── mongodump: consistent logical backup of MongoDB ──────────────
# Файловый бэкап Volume (WiredTiger) даёт неконсистентный срез —
# mongodump подключается к работающему mongod и снимает согласованный
# дамп всех баз. Дамп сохраняется в /opt/msp-backups/mongodump/,
# затем restic упаковывает его в S3 вместе с остальными файлами.
log "Running mongodump..."
mkdir -p "$MONGO_DUMP_DIR"
rm -rf "${MONGO_DUMP_DIR:?}"/*

if [ -n "$MONGO_CONTAINER" ] && docker exec "$MONGO_CONTAINER" mongodump \
    --out /tmp/mongodump \
    --quiet 2>&1 | tee -a "$LOG"; then

    docker cp "${MONGO_CONTAINER}:/tmp/mongodump/." "$MONGO_DUMP_DIR/"
    docker exec "$MONGO_CONTAINER" rm -rf /tmp/mongodump
    log "mongodump SUCCESS → ${MONGO_DUMP_DIR}"
else
    log "mongodump SKIPPED/FAILED (container='${MONGO_CONTAINER:-not found}') — continuing with restic (mongo dump may be stale)"
fi

# ── restic: file backup to S3 ───────────────────────────────────
# ВНИМАНИЕ: /var/lib/docker/volumes НЕ включён — MongoDB бэкапится
# через mongodump выше (консистентный логический дамп).
# Docker volumes остальных сервисов (caddy, grafana и т.д.) бэкапятся
# отдельно через их собственные конфиги/дампы при необходимости.
BACKUP_PATHS=(
    "/etc"
    "/home"
    "/root"
    "/opt"
    "/var/www"
    "/var/lib/caddy"
    "$MONGO_DUMP_DIR"
)

EXISTING_PATHS=()
for p in "${BACKUP_PATHS[@]}"; do
    if [[ -d "$p" ]]; then
        EXISTING_PATHS+=("$p")
    fi
done

if [[ ${#EXISTING_PATHS[@]} -eq 0 ]]; then
    log "ERROR: no directories to backup"
    write_metrics 0 "$TIMESTAMP" 0
    exit 1
fi

log "Paths: ${EXISTING_PATHS[*]}"

# УРОК миграции 1: restic из Ubuntu 22.04 НЕ поддерживает --compression auto
# (флаг появился в 0.17+ / только в новых версиях). Флаг убран — используем
# дефолтную политику сжатия репозитория.
if restic backup \
    "${EXISTING_PATHS[@]}" \
    --exclude-file="$EXCLUDE_FILE" \
    --tag "auto" \
    --tag "$HOSTNAME" \
    --json 2>&1 | tee -a "$LOG"; then
    STATUS=1
    BYTES=$(grep -E '^\{"message_type":"summary"' "$LOG" | tail -1 \
        | grep -oE '"total_bytes_processed":[0-9]+' \
        | cut -d: -f2 || echo "0")
    BYTES="${BYTES:-0}"
    log "BACKUP SUCCESS bytes=${BYTES}"
else
    STATUS=0
    BYTES=0
    log "BACKUP FAILED"
fi

log "Applying retention policy..."
restic forget \
    --tag "$HOSTNAME" \
    --keep-daily 7 \
    --keep-weekly 4 \
    --keep-monthly 6 \
    --keep-yearly 1 \
    --prune \
    --compact 2>&1 | tee -a "$LOG" | grep -E "^(Applying|removed|stats:)" || true

if [[ $(date +%u) -eq 7 ]]; then
    log "Sunday: repository integrity check..."
    if restic check 2>&1 | tee -a "$LOG"; then
        log "CHECK OK"
    else
        log "CHECK FAILED"
    fi
fi

write_metrics "$STATUS" "$TIMESTAMP" "$BYTES"

log "=== END BACKUP status=${STATUS} bytes=${BYTES} ==="

exit $(( 1 - STATUS ))
