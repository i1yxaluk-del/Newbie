#!/usr/bin/env bash
# ═══════════════════════════════════════════════════════════════════
# restic-metrics.sh — Экспортёр метрик restic в Prometheus textfile
# ═══════════════════════════════════════════════════════════════════
#
# ЗАЧЕМ: restic не отдаёт метрики напрямую. node-exporter с флагом
#   --collector.textfile.directory=/var/lib/node_exporter/textfile
# забирает любые *.prom файлы из директории и публикует на /metrics.
#
# КАК ВЫЗЫВАТЬ:
#   1. После каждого `restic backup` (в обёртке cron):
#        restic-metrics.sh backup <host> <repo> <exit_code> <bytes>
#   2. После `restic check`:
#        restic-metrics.sh verify <host> <repo> <exit_code>
#   3. После DR-drill (R-11):
#        restic-metrics.sh restore_test <host> <repo> <exit_code> <bytes>
#
# ПРИМЕР интеграции в cron:
#   0 3 * * * /opt/backups/run-backup.sh web-01 && \
#             /opt/backups/restic-metrics.sh backup web-01 main 0 1288490188
#
# Файл пишется атомарно (через .tmp + mv) — node-exporter не прочитает
# полузаписанный prom-файл.
# ═══════════════════════════════════════════════════════════════════

set -euo pipefail

TEXTFILE_DIR="${TEXTFILE_DIR:-/var/lib/node_exporter/textfile}"
mkdir -p "$TEXTFILE_DIR"

CMD="${1:?usage: $0 {backup|verify|restore_test} <host> <repo> <exit_code> [bytes]}"
HOST="${2:?missing host}"
REPO="${3:?missing repo}"
EXIT_CODE="${4:?missing exit_code}"
BYTES="${5:-0}"

NOW="$(date +%s)"
SUCCESS=0
[ "$EXIT_CODE" = "0" ] && SUCCESS=1

OUT="${TEXTFILE_DIR}/restic_${CMD}_${HOST}.prom"
TMP="${OUT}.tmp"

case "$CMD" in
backup)
    cat > "$TMP" <<EOF
# HELP restic_backup_success Last restic backup result (1=ok, 0=fail)
# TYPE restic_backup_success gauge
restic_backup_success{host="${HOST}",repo="${REPO}"} ${SUCCESS}

# HELP restic_backup_timestamp_seconds Unix time of last restic backup
# TYPE restic_backup_timestamp_seconds gauge
restic_backup_timestamp_seconds{host="${HOST}",repo="${REPO}"} ${NOW}

# HELP restic_backup_size_bytes Size of last restic backup in bytes
# TYPE restic_backup_size_bytes gauge
restic_backup_size_bytes{host="${HOST}",repo="${REPO}"} ${BYTES}

# HELP restic_backup_exit_code Exit code of last restic backup
# TYPE restic_backup_exit_code gauge
restic_backup_exit_code{host="${HOST}",repo="${REPO}"} ${EXIT_CODE}
EOF
    ;;

verify)
    cat > "$TMP" <<EOF
# HELP restic_verify_success Last restic check result (1=ok, 0=fail)
# TYPE restic_verify_success gauge
restic_verify_success{host="${HOST}",repo="${REPO}"} ${SUCCESS}

# HELP restic_verify_timestamp_seconds Unix time of last restic check
# TYPE restic_verify_timestamp_seconds gauge
restic_verify_timestamp_seconds{host="${HOST}",repo="${REPO}"} ${NOW}

# HELP restic_verify_exit_code Exit code of last restic check
# TYPE restic_verify_exit_code gauge
restic_verify_exit_code{host="${HOST}",repo="${REPO}"} ${EXIT_CODE}
EOF
    ;;

restore_test)
    cat > "$TMP" <<EOF
# HELP restic_restore_test_success Last restore-test result (1=ok, 0=fail)
# TYPE restic_restore_test_success gauge
restic_restore_test_success{host="${HOST}",repo="${REPO}"} ${SUCCESS}

# HELP restic_restore_test_timestamp_seconds Unix time of last restore-test
# TYPE restic_restore_test_timestamp_seconds gauge
restic_restore_test_timestamp_seconds{host="${HOST}",repo="${REPO}"} ${NOW}

# HELP restic_restore_test_bytes Bytes restored during last test
# TYPE restic_restore_test_bytes gauge
restic_restore_test_bytes{host="${HOST}",repo="${REPO}"} ${BYTES}

# HELP restic_restore_test_exit_code Exit code of last restore-test
# TYPE restic_restore_test_exit_code gauge
restic_restore_test_exit_code{host="${HOST}",repo="${REPO}"} ${EXIT_CODE}
EOF
    ;;

*)
    echo "unknown command: $CMD" >&2
    echo "usage: $0 {backup|verify|restore_test} <host> <repo> <exit_code> [bytes]" >&2
    exit 2
    ;;
esac

# Атомарный rename — node-exporter не увидит полузаписанный файл
mv "$TMP" "$OUT"

echo "wrote $OUT (success=${SUCCESS}, ts=${NOW})"
