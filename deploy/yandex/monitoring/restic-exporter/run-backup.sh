#!/usr/bin/env bash
# ═══════════════════════════════════════════════════════════════════
# run-backup.sh — Обёртка для restic backup с автоматической эмиссией
#                 метрик в Prometheus
# ═══════════════════════════════════════════════════════════════════
#
# ЗАПУСК (через cron):
#   0 3 * * * /opt/backups/run-backup.sh web-01 main /etc /var/www
#
# Аргументы:
#   $1 — host (метка для метрик)
#   $2 — repo name (метка для метрик)
#   $3..N — пути для бэкапа
#
# Переменные окружения (читаются из /etc/backup.env):
#   RESTIC_REPOSITORY  — s3:s3.yandexcloud.net/msp-backups
#   RESTIC_PASSWORD    — пароль шифрования (AES-256)
#   AWS_ACCESS_KEY_ID  — Yandex IAM key
#   AWS_SECRET_ACCESS_KEY
# ═══════════════════════════════════════════════════════════════════

set -euo pipefail

# Загружаем секреты
[ -f /etc/backup.env ] && . /etc/backup.env

HOST="${1:?usage: $0 <host> <repo> <path>...}"
REPO="${2:?missing repo}"
shift 2
PATHS=("$@")
[ ${#PATHS[@]} -eq 0 ] && { echo "no paths to backup" >&2; exit 2; }

METRICS_SCRIPT="$(dirname "$0")/restic-metrics.sh"
LOG="/var/log/restic/${HOST}-${REPO}.log"
mkdir -p "$(dirname "$LOG")"

echo "═══ $(date -Iseconds) — backup ${HOST}/${REPO} ═══" | tee -a "$LOG"

# Запускаем restic, ловим exit code
set +e
restic backup \
--tag "host=${HOST}" \
--tag "auto" \
--host "${HOST}" \
--json \
"${PATHS[@]}" \
2>&1 | tee -a "$LOG"
EXIT_CODE=${PIPESTATUS[0]}
set -e

# Извлекаем размер из JSON-вывода (последний "summary"-event)
BYTES=$(grep -E '^\{"message_type":"summary"' "$LOG" | tail -1 \
    | grep -oE '"total_bytes_processed":[0-9]+' \
    | cut -d: -f2 || echo "0")
BYTES="${BYTES:-0}"

# Эмитим метрики
"$METRICS_SCRIPT" backup "$HOST" "$REPO" "$EXIT_CODE" "$BYTES"

echo "═══ exit=${EXIT_CODE} bytes=${BYTES} ═══" | tee -a "$LOG"

# Ротация лога — оставляем последние 30 дней
find "$(dirname "$LOG")" -name "*.log" -mtime +30 -delete

exit "$EXIT_CODE"
