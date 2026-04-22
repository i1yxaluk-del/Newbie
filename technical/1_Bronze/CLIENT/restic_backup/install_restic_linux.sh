#!/bin/bash
# ═══════════════════════════════════════════════════════════════════
# install_restic_linux.sh — Установка restic backup на Linux
# Тариф: Bronze+ | ОС: Ubuntu/Debian/Astra Linux
# Запуск: sudo bash install_restic_linux.sh
# 
# ВАЖНО: перед запуском заполните /etc/restic/env.sh
#        (файл получить от Исполнителя)
# ═══════════════════════════════════════════════════════════════════
set -euo pipefail

GREEN='\033[0;32m'; YELLOW='\033[1;33m'; RED='\033[0;31m'; NC='\033[0m'
ok()   { echo -e "${GREEN}✓${NC} $*"; }
warn() { echo -e "${YELLOW}!${NC} $*"; }
err()  { echo -e "${RED}✗${NC} $*"; exit 1; }

RESTIC_VERSION="${RESTIC_VERSION:-0.16.4}"
SCRIPTS_DIR="/opt/restic-scripts"
ENV_FILE="/etc/restic/env.sh"
LOG_FILE="/var/log/restic-backup.log"
# shellcheck disable=SC2034  # используется скриптами бэкапа для node_exporter textfile collector
TEXTFILE_DIR="/var/lib/node_exporter/textfile_collector"

[[ $EUID -ne 0 ]] && err "Запустить с sudo"

echo "────────────────────────────────────────"
echo " restic installer v${RESTIC_VERSION}"
echo "────────────────────────────────────────"

# ── Установить restic ─────────────────────────────────────────────
if command -v restic &>/dev/null && restic version | grep -q "${RESTIC_VERSION}"; then
    ok "restic ${RESTIC_VERSION} уже установлен"
else
    echo "Скачиваю restic ${RESTIC_VERSION}..."

    ARCH="linux_amd64"
    URL="https://github.com/restic/restic/releases/download/v${RESTIC_VERSION}/restic_${RESTIC_VERSION}_${ARCH}.bz2"

    # Попробовать wget, затем curl
    TMP=$(mktemp)
    if command -v wget &>/dev/null; then
        wget -q "$URL" -O "${TMP}.bz2"
    else
        curl -sSL "$URL" -o "${TMP}.bz2"
    fi

    bunzip2 -c "${TMP}.bz2" > /usr/local/bin/restic
    chmod +x /usr/local/bin/restic
    rm -f "${TMP}" "${TMP}.bz2"
    ok "restic $(restic version | head -1) установлен"
fi

# ── Создать структуру ─────────────────────────────────────────────
mkdir -p "$SCRIPTS_DIR" /etc/restic
touch "$LOG_FILE"
chmod 640 "$LOG_FILE"

# ── Создать env.sh (шаблон, если нет) ────────────────────────────
if [[ ! -f "$ENV_FILE" ]]; then
    cat > "$ENV_FILE" << 'EOF'
# ═══════════════════════════════════════════════════════════════════
# restic env — ЗАПОЛНИТЬ ЗНАЧЕНИЯМИ ОТ ИСПОЛНИТЕЛЯ
# Файл строго конфиденциален: chmod 600 /etc/restic/env.sh
# ═══════════════════════════════════════════════════════════════════

# Ключи Yandex Object Storage (S3)
export AWS_ACCESS_KEY_ID="REPLACE_WITH_ACCESS_KEY"
export AWS_SECRET_ACCESS_KEY="REPLACE_WITH_SECRET_KEY"

# Путь к репозиторию (получить от Исполнителя)
export RESTIC_REPOSITORY="s3:https://storage.yandexcloud.net/BUCKET_NAME"

# Пароль репозитория (СОХРАНИТЬ В ОТДЕЛЬНОМ МЕСТЕ!)
export RESTIC_PASSWORD="REPLACE_WITH_REPO_PASSWORD"

# Опционально: ограничить пропускную способность (байт/с)
# export RESTIC_LIMIT_UPLOAD=10000
# export RESTIC_LIMIT_DOWNLOAD=10000
EOF
    chmod 600 "$ENV_FILE"
    warn "Создан шаблон ${ENV_FILE} — заполните значениями от Исполнителя!"
else
    ok "Файл ${ENV_FILE} уже существует"
fi

# ── Файл исключений ───────────────────────────────────────────────
cat > "${SCRIPTS_DIR}/excludes.txt" << 'EOF'
# restic exclude-file — что НЕ бэкапить
/proc
/sys
/dev
/run
/tmp
/var/cache
/var/tmp
/var/lib/docker
/var/lib/lxc
/var/lib/lxcfs
/var/lib/machines
/var/lib/systemd/coredump
/lost+found
/snap
/mnt
/media
*.sock
*.pid
*.lock
.git
node_modules
__pycache__
*.pyc
*.log.gz
EOF
ok "Файл исключений: ${SCRIPTS_DIR}/excludes.txt"

# ── Основной скрипт бэкапа ───────────────────────────────────────
cat > "${SCRIPTS_DIR}/backup.sh" << 'SCRIPT'
#!/bin/bash
# ═══════════════════════════════════════════════════════════════════
# backup.sh — Скрипт резервного копирования (Bronze)
# Запускается через systemd timer ежедневно в 02:00
# ═══════════════════════════════════════════════════════════════════
set -euo pipefail

LOG="/var/log/restic-backup.log"
METRICS_DIR="/var/lib/node_exporter/textfile_collector"
METRICS_FILE="${METRICS_DIR}/restic_backup.prom"
EXCLUDE_FILE="/opt/restic-scripts/excludes.txt"
HOSTNAME=$(hostname -f)
TIMESTAMP=$(date +%s)
STATUS=0

# Загрузить переменные
source /etc/restic/env.sh

log() {
    local msg="[$(date '+%Y-%m-%d %H:%M:%S')] $*"
    echo "$msg"
    echo "$msg" >> "$LOG"
}

# ── Функция: записать метрики ──────────────────────────────────────
write_metrics() {
    local status=$1
    local timestamp=$2
    mkdir -p "$METRICS_DIR"
    cat > "$METRICS_FILE" << EOF
# HELP restic_backup_last_status 1=success 0=failure
# TYPE restic_backup_last_status gauge
restic_backup_last_status{host="${HOSTNAME}"} ${status}
# HELP restic_backup_last_timestamp_seconds Unix timestamp of last attempt
# TYPE restic_backup_last_timestamp_seconds gauge
restic_backup_last_timestamp_seconds{host="${HOSTNAME}"} ${timestamp}
EOF
}

# Записать "in progress" метрику в начале
write_metrics 2 "$TIMESTAMP"  # 2 = in progress

log "=== START BACKUP host=${HOSTNAME} ==="

# ── Пути для бэкапа ───────────────────────────────────────────────
# Настроить под реальную инфраструктуру клиента
BACKUP_PATHS=(
    "/etc"
    "/home"
    "/root"
    "/srv"
    "/opt"
    "/var/www"
    "/var/lib/postgresql"  # Закомментировать, если нет PostgreSQL
)

# Фильтр существующих путей
EXISTING_PATHS=()
for p in "${BACKUP_PATHS[@]}"; do
    if [[ -d "$p" ]]; then
        EXISTING_PATHS+=("$p")
    fi
done

if [[ ${#EXISTING_PATHS[@]} -eq 0 ]]; then
    log "ERROR: нет директорий для бэкапа"
    write_metrics 0 "$TIMESTAMP"
    exit 1
fi

log "Пути для бэкапа: ${EXISTING_PATHS[*]}"

# ── Резервное копирование ─────────────────────────────────────────
if restic backup \
    "${EXISTING_PATHS[@]}" \
    --exclude-file="$EXCLUDE_FILE" \
    --tag "auto" \
    --tag "$HOSTNAME" \
    --compression auto \
    --json 2>&1 | tee -a "$LOG" | tail -20; then
    STATUS=1
    log "BACKUP SUCCESS"
else
    STATUS=0
    log "BACKUP FAILED"
fi

# ── Retention policy: очистить старые снапшоты ────────────────────
log "Применяю retention policy..."
restic forget \
    --tag "$HOSTNAME" \
    --keep-daily 7 \
    --keep-weekly 4 \
    --keep-monthly 6 \
    --keep-yearly 1 \
    --prune \
    --compact 2>&1 | tee -a "$LOG" | grep -E "^(Applying|removed|stats:)"

# ── Еженедельная проверка целостности (в воскресенье) ─────────────
if [[ $(date +%u) -eq 7 ]]; then
    log "Воскресенье: проверка целостности репозитория..."
    if restic check 2>&1 | tee -a "$LOG"; then
        log "CHECK OK"
    else
        log "CHECK FAILED — возможно повреждение репозитория"
        # Не меняем STATUS, это не фатально
    fi
fi

# ── Записать финальные метрики ────────────────────────────────────
write_metrics "$STATUS" "$TIMESTAMP"

log "=== END BACKUP status=${STATUS} ==="

# Завершить с ненулевым кодом при ошибке
exit $(( 1 - STATUS ))
SCRIPT
chmod +x "${SCRIPTS_DIR}/backup.sh"
ok "Скрипт бэкапа: ${SCRIPTS_DIR}/backup.sh"

# ── Скрипт проверки бэкапа (для еженедельного отчёта) ────────────
cat > "${SCRIPTS_DIR}/verify_backup.sh" << 'SCRIPT'
#!/bin/bash
# verify_backup.sh — Тестовое восстановление файла
# Запускать раз в неделю для проверки работоспособности бэкапов

source /etc/restic/env.sh

RESTORE_DIR="/tmp/msp_restore_test_$(date +%Y%m%d)"
TEST_FILE="/etc/hostname"

echo "=== ТЕСТ ВОССТАНОВЛЕНИЯ $(date) ==="
echo "Тестовый файл: $TEST_FILE"

# Найти последний снапшот
LATEST=$(restic snapshots --json | python3 -c "import sys,json; snaps=json.load(sys.stdin); print(snaps[-1]['id'] if snaps else '')")
if [[ -z "$LATEST" ]]; then
    echo "FAIL: нет снапшотов"
    exit 1
fi
echo "Снапшот: $LATEST"

# Восстановить тестовый файл
mkdir -p "$RESTORE_DIR"
if restic restore "$LATEST" --target "$RESTORE_DIR" --include "$TEST_FILE"; then
    RESTORED="${RESTORE_DIR}${TEST_FILE}"
    if [[ -f "$RESTORED" ]]; then
        echo "PASS: файл восстановлен $(stat -c%s "$RESTORED") байт"
        diff "$TEST_FILE" "$RESTORED" && echo "PASS: содержимое совпадает" || echo "WARN: содержимое отличается"
    else
        echo "FAIL: файл не найден после восстановления"
    fi
else
    echo "FAIL: команда restic restore упала"
fi

rm -rf "$RESTORE_DIR"
echo "=== ТЕСТ ЗАВЕРШЁН ==="
SCRIPT
chmod +x "${SCRIPTS_DIR}/verify_backup.sh"

# ── Systemd service ───────────────────────────────────────────────
cat > /etc/systemd/system/restic-backup.service << EOF
[Unit]
Description=MSP Restic Backup
Documentation=https://restic.net
After=network-online.target
Wants=network-online.target

[Service]
Type=oneshot
EnvironmentFile=${ENV_FILE}
ExecStart=${SCRIPTS_DIR}/backup.sh
Nice=19
IOSchedulingClass=best-effort
IOSchedulingPriority=7
TimeoutStartSec=7200
StandardOutput=journal+console
StandardError=journal+console
SyslogIdentifier=restic-backup
EOF
ok "Systemd service создан"

# ── Systemd timer ─────────────────────────────────────────────────
cat > /etc/systemd/system/restic-backup.timer << 'EOF'
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
ok "Systemd timer создан (02:00 ежедневно)"

# ── Инициализировать репозиторий ──────────────────────────────────
# shellcheck disable=SC1090  # ENV_FILE задаётся в runtime, не резолвится статически
source "$ENV_FILE" 2>/dev/null || true

if [[ "$AWS_ACCESS_KEY_ID" == "REPLACE"* ]]; then
    warn "env.sh не заполнен — инициализацию репозитория выполнить после заполнения:"
    warn "  source ${ENV_FILE} && restic init"
else
    echo "Инициализирую restic репозиторий..."
    if restic init 2>&1; then
        ok "Репозиторий инициализирован: $RESTIC_REPOSITORY"
    else
        warn "Репозиторий уже существует или ошибка — проверьте логи"
    fi
fi

# ── Запустить ─────────────────────────────────────────────────────
systemctl daemon-reload
systemctl enable restic-backup.timer
systemctl start restic-backup.timer

echo ""
echo "────────────────────────────────────────"
echo " Установка завершена!"
echo ""
echo " Следующий шаг:"
echo " 1. Заполнить ${ENV_FILE}"
echo " 2. Запустить первый бэкап: systemctl start restic-backup.service"
echo " 3. Проверить: systemctl status restic-backup.service"
echo "────────────────────────────────────────"
