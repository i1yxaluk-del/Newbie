#!/bin/bash
# ═══════════════════════════════════════════════════════════════════
# restic_backup.sh — Основной скрипт резервного копирования
# Файл: /opt/restic-scripts/backup.sh
#
# Запуск: автоматически через systemd timer (ежедневно 02:00)
# Ручной запуск: systemctl start restic-backup.service
# Лог: journalctl -u restic-backup -f  или  tail -f /var/log/restic-backup.log
# ═══════════════════════════════════════════════════════════════════
set -euo pipefail

# ── Конфигурация ───────────────────────────────────────────────────
LOG_FILE="/var/log/restic-backup.log"
EXCLUDE_FILE="/opt/restic-scripts/excludes.txt"
METRICS_DIR="/var/lib/node_exporter/textfile_collector"
METRICS_FILE="${METRICS_DIR}/restic_backup.prom"
HOSTNAME_SHORT=$(hostname -s)
TIMESTAMP_START=$(date +%s)
BACKUP_STATUS=0

# ── Загрузить переменные окружения ─────────────────────────────────
# Ожидается: AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY,
#            RESTIC_REPOSITORY, RESTIC_PASSWORD
if [[ -f /etc/restic/env.sh ]]; then
    # shellcheck disable=SC1091
    source /etc/restic/env.sh
else
    echo "[ERROR] Файл /etc/restic/env.sh не найден!" >&2
    exit 1
fi

# ── Функции ────────────────────────────────────────────────────────
log() {
    local level="${2:-INFO}"
    local ts
    ts=$(date '+%Y-%m-%d %H:%M:%S')
    local msg="[$ts] [${level}] $1"
    echo "$msg"
    echo "$msg" >> "$LOG_FILE"
}

write_metrics() {
    local status="$1"
    local timestamp="$2"
    local duration="${3:-0}"
    mkdir -p "$METRICS_DIR"
    cat > "$METRICS_FILE" << EOF
# HELP restic_backup_last_status Last backup exit status: 1=success, 0=failure, 2=running
# TYPE restic_backup_last_status gauge
restic_backup_last_status{host="${HOSTNAME_SHORT}",job="auto"} ${status}
# HELP restic_backup_last_timestamp_seconds Unix timestamp of last backup attempt
# TYPE restic_backup_last_timestamp_seconds gauge
restic_backup_last_timestamp_seconds{host="${HOSTNAME_SHORT}",job="auto"} ${timestamp}
# HELP restic_backup_duration_seconds Duration of last backup in seconds
# TYPE restic_backup_duration_seconds gauge
restic_backup_duration_seconds{host="${HOSTNAME_SHORT}",job="auto"} ${duration}
EOF
}

# Сразу пометить как "выполняется"
write_metrics 2 "$TIMESTAMP_START" 0

# ── Ротация лога ───────────────────────────────────────────────────
if [[ -f "$LOG_FILE" ]] && [[ $(wc -c < "$LOG_FILE") -gt 10485760 ]]; then
    mv "$LOG_FILE" "${LOG_FILE}.1"
    gzip -f "${LOG_FILE}.1" &
fi

# ── Начало ─────────────────────────────────────────────────────────
log "═══════ START BACKUP host=${HOSTNAME_SHORT} ═══════"
log "Repository: ${RESTIC_REPOSITORY}"

# ── Проверить доступность репозитория ──────────────────────────────
log "Проверяю доступность репозитория..."
if ! restic stats --quiet 2>/dev/null; then
    log "Репозиторий недоступен. Инициализирую..." WARN
    if restic init 2>&1 | tee -a "$LOG_FILE"; then
        log "Репозиторий инициализирован"
    else
        log "Не удалось инициализировать репозиторий" ERROR
        write_metrics 0 "$TIMESTAMP_START" 0
        exit 1
    fi
fi

# ── Определить пути для бэкапа ─────────────────────────────────────
# Берём все существующие директории из списка
CANDIDATE_PATHS=(
    /etc
    /home
    /root
    /srv
    /opt
    /var/www
    /var/lib/postgresql
    /var/lib/mysql
    /var/lib/mongodb
)

BACKUP_PATHS=()
for p in "${CANDIDATE_PATHS[@]}"; do
    if [[ -d "$p" ]] && [[ -r "$p" ]]; then
        BACKUP_PATHS+=("$p")
    fi
done

if [[ ${#BACKUP_PATHS[@]} -eq 0 ]]; then
    log "Нет доступных директорий для бэкапа!" ERROR
    write_metrics 0 "$TIMESTAMP_START" 0
    exit 1
fi

log "Пути: ${BACKUP_PATHS[*]}"

# ── Создать бэкап ──────────────────────────────────────────────────
log "Запускаю резервное копирование..."
if restic backup \
    "${BACKUP_PATHS[@]}" \
    --exclude-file="$EXCLUDE_FILE" \
    --tag "auto" \
    --tag "$HOSTNAME_SHORT" \
    --compression auto \
    --pack-size 128 \
    2>&1 | tee -a "$LOG_FILE"; then
    BACKUP_STATUS=1
    log "Резервное копирование: УСПЕХ"
else
    BACKUP_STATUS=0
    log "Резервное копирование: ОШИБКА" ERROR
fi

# ── PostgreSQL dump (если запущен) ─────────────────────────────────
if command -v pg_dumpall &>/dev/null && systemctl is-active --quiet postgresql 2>/dev/null; then
    log "Создаю дамп PostgreSQL..."
    PG_DUMP_DIR="/tmp/pg_dump_$(date +%Y%m%d_%H%M%S)"
    mkdir -p "$PG_DUMP_DIR"

    if sudo -u postgres pg_dumpall --clean 2>>"$LOG_FILE" | sudo tee "${PG_DUMP_DIR}/all_databases.sql" >/dev/null; then
        if restic backup "$PG_DUMP_DIR" \
            --tag "pg-dump" \
            --tag "$HOSTNAME_SHORT" \
            2>&1 | tee -a "$LOG_FILE"; then
            log "PostgreSQL dump: УСПЕХ"
        else
            log "PostgreSQL dump upload: ОШИБКА" WARN
        fi
    else
        log "pg_dumpall: ОШИБКА" WARN
    fi

    rm -rf "$PG_DUMP_DIR"
fi

# ── Retention policy: удалить старые снапшоты ─────────────────────
log "Применяю retention policy..."
restic forget \
    --tag "$HOSTNAME_SHORT" \
    --keep-daily   7 \
    --keep-weekly  4 \
    --keep-monthly 6 \
    --keep-yearly  1 \
    --prune \
    --quiet \
    2>&1 | tee -a "$LOG_FILE"

# ── Проверка целостности (воскресенье) ─────────────────────────────
DAY_OF_WEEK=$(date +%u)
if [[ "$DAY_OF_WEEK" -eq 7 ]]; then
    log "Воскресенье — запускаю restic check..."
    if restic check --quiet 2>&1 | tee -a "$LOG_FILE"; then
        log "Проверка целостности: OK"
    else
        log "Проверка целостности: ОШИБКА (данные могут быть повреждены)" ERROR
    fi
fi

# ── Финальные метрики ──────────────────────────────────────────────
TIMESTAMP_END=$(date +%s)
DURATION=$(( TIMESTAMP_END - TIMESTAMP_START ))
write_metrics "$BACKUP_STATUS" "$TIMESTAMP_END" "$DURATION"

log "Длительность: ${DURATION}с"
log "Статус: $([ $BACKUP_STATUS -eq 1 ] && echo 'SUCCESS' || echo 'FAILED')"
log "═══════ END BACKUP ═══════"

# Выйти с ненулевым кодом при ошибке бэкапа
exit $(( 1 - BACKUP_STATUS ))
