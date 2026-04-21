#!/bin/bash
# ═══════════════════════════════════════════════════════════════════
# weekly_report.sh — Автоматическая генерация еженедельного отчёта
# Файл: /usr/local/bin/weekly_report.sh
#
# Запуск: автоматически по cron (понедельник 09:00)
#   0 9 * * 1 root /usr/local/bin/weekly_report.sh
#
# Ручной запуск:
#   /usr/local/bin/weekly_report.sh [CLIENT_SLUG]
#   Если CLIENT_SLUG не указан — отчёт по всем клиентам
# ═══════════════════════════════════════════════════════════════════
set -euo pipefail

PROMETHEUS="http://localhost:9090"
REPORT_DIR="/opt/reports/weekly"
DATE_NOW=$(date '+%Y-%m-%d')
DATE_WEEK_AGO=$(date -d '7 days ago' '+%Y-%m-%d')
TELEGRAM_BOT="${TELEGRAM_BOT_TOKEN:-}"
TELEGRAM_CHAT="${TELEGRAM_CHAT_ID:-}"

# Загрузить переменные если есть
[[ -f /opt/monitoring/.env ]] && set -o allexport && source /opt/monitoring/.env && set +o allexport

mkdir -p "$REPORT_DIR"

# ── Функции ────────────────────────────────────────────────────────
prom_query() {
    local q="$1"
    curl -sf --max-time 15 \
        "${PROMETHEUS}/api/v1/query" \
        --data-urlencode "query=${q}" \
        2>/dev/null
}

prom_range() {
    local q="$1"
    local start="${2:-$(date -d '7 days ago' +%s)}"
    local end="${3:-$(date +%s)}"
    curl -sf --max-time 30 \
        "${PROMETHEUS}/api/v1/query_range" \
        --data-urlencode "query=${q}" \
        -d "start=${start}" \
        -d "end=${end}" \
        -d "step=3600" \
        2>/dev/null
}

parse_val() {
    # Извлечь значение из ответа Prometheus
    echo "$1" | python3 -c "
import sys, json
try:
    d = json.load(sys.stdin)
    results = d.get('data', {}).get('result', [])
    for r in results:
        val = r.get('value', r.get('values', [[0,0]])[-1])[1]
        labels = r.get('metric', {})
        client = labels.get('client_name', labels.get('client', '?'))
        inst = labels.get('instance', labels.get('host', '?'))
        print(f'{client}|{inst}|{val}')
except:
    pass
" 2>/dev/null
}

send_telegram() {
    local text="$1"
    [[ -z "$TELEGRAM_BOT" || -z "$TELEGRAM_CHAT" ]] && return 0
    curl -sf -X POST "https://api.telegram.org/bot${TELEGRAM_BOT}/sendMessage" \
        -d "chat_id=${TELEGRAM_CHAT}" \
        -d "text=${text}" \
        -d "parse_mode=HTML" \
        > /dev/null 2>&1 || true
}

# ── Генерация отчёта ───────────────────────────────────────────────
generate_report() {
    local CLIENT_FILTER="${1:-}"
    local REPORT_FILE="${REPORT_DIR}/weekly_${DATE_NOW}${CLIENT_FILTER:+_$CLIENT_FILTER}.md"

    cat > "$REPORT_FILE" << EOF
# MSPShield Weekly Report
**Период:** ${DATE_WEEK_AGO} → ${DATE_NOW}
**Сгенерирован:** $(date '+%d.%m.%Y %H:%M:%S')
${CLIENT_FILTER:+**Клиент:** $CLIENT_FILTER}

---

## 📊 ДОСТУПНОСТЬ СЕРВЕРОВ

EOF

    # Текущий статус всех targets
    local TARGETS_DATA
    TARGETS_DATA=$(prom_query "up${CLIENT_FILTER:+{client='$CLIENT_FILTER'}}")
    echo "| Сервер | Статус | Клиент |" >> "$REPORT_FILE"
    echo "|--------|--------|--------|" >> "$REPORT_FILE"

    echo "$TARGETS_DATA" | python3 -c "
import sys, json
d = json.load(sys.stdin)
results = d.get('data', {}).get('result', [])
for r in results:
    m = r.get('metric', {})
    val = r.get('value', [0,'0'])[1]
    status = '✅ UP' if val == '1' else '❌ DOWN'
    inst = m.get('instance', '?')
    client = m.get('client_name', m.get('client', '?'))
    print(f'| \`{inst}\` | {status} | {client} |')
" 2>/dev/null >> "$REPORT_FILE" || echo "| — | Нет данных | — |" >> "$REPORT_FILE"

    cat >> "$REPORT_FILE" << 'EOF'

---

## 💾 СОСТОЯНИЕ БЭКАПОВ

EOF
    echo "| Сервер | Статус | Последний бэкап | Клиент |" >> "$REPORT_FILE"
    echo "|--------|--------|-----------------|--------|" >> "$REPORT_FILE"

    local BACKUP_DATA
    BACKUP_DATA=$(prom_query "restic_backup_last_status${CLIENT_FILTER:+{client='$CLIENT_FILTER'}}")

    echo "$BACKUP_DATA" | python3 -c "
import sys, json, datetime
d = json.load(sys.stdin)
results = d.get('data', {}).get('result', [])
for r in results:
    m = r.get('metric', {})
    val = r.get('value', [0,'0'])[1]
    status = '✅ OK' if val == '1' else '❌ ОШИБКА'
    host   = m.get('host', '?')
    client = m.get('client_name', m.get('client', '?'))
    print(f'| \`{host}\` | {status} | — | {client} |')
" 2>/dev/null >> "$REPORT_FILE" || echo "| — | Нет данных | — | — |" >> "$REPORT_FILE"

    cat >> "$REPORT_FILE" << 'EOF'

---

## 💿 ИСПОЛЬЗОВАНИЕ ДИСКОВ

EOF
    echo "| Сервер | Раздел | Использовано | Статус |" >> "$REPORT_FILE"
    echo "|--------|--------|-------------|--------|" >> "$REPORT_FILE"

    local DISK_DATA
    DISK_DATA=$(prom_query '(1 - node_filesystem_avail_bytes{fstype!~"tmpfs|overlay|squashfs|devtmpfs"}/node_filesystem_size_bytes)*100')

    echo "$DISK_DATA" | python3 -c "
import sys, json
d = json.load(sys.stdin)
results = d.get('data', {}).get('result', [])
for r in results:
    m = r.get('metric', {})
    val = float(r.get('value', [0,'0'])[1])
    inst = m.get('instance', '?')
    mp   = m.get('mountpoint', '?')
    if val > 60:
        status = '🔴 КРИТИЧНО' if val > 90 else '⚠️ Внимание'
    else:
        status = '✅ OK'
    print(f'| \`{inst}\` | \`{mp}\` | {val:.1f}% | {status} |')
" 2>/dev/null | sort -t'|' -k4 -r >> "$REPORT_FILE" || echo "| — | — | — | — |" >> "$REPORT_FILE"

    cat >> "$REPORT_FILE" << 'EOF'

---

## ⚠️ АЛЕРТЫ ЗА НЕДЕЛЮ

EOF

    local ALERTS_DATA
    ALERTS_DATA=$(curl -sf --max-time 10 "${PROMETHEUS%:9090*}:9093/api/v1/alerts" 2>/dev/null || echo '{"data":{"alerts":[]}}')

    local ALERT_COUNT
    ALERT_COUNT=$(echo "$ALERTS_DATA" | python3 -c "
import sys, json
d = json.load(sys.stdin)
alerts = d.get('data', {}).get('alerts', [])
firing = [a for a in alerts if a.get('status', {}).get('state') == 'firing']
print(f'Активных алертов сейчас: **{len(firing)}**')
for a in firing[:10]:
    name = a.get('labels', {}).get('alertname', '?')
    sev  = a.get('labels', {}).get('severity', '?')
    inst = a.get('labels', {}).get('instance', '?')
    client = a.get('labels', {}).get('client_name', '?')
    print(f'- 🔴 [{sev.upper()}] {name} — {inst} ({client})')
" 2>/dev/null)
    echo "$ALERT_COUNT" >> "$REPORT_FILE"

    cat >> "$REPORT_FILE" << EOF

---

## 📋 РЕКОМЕНДАЦИИ

$(generate_recommendations)

---

## ℹ️ ИНФОРМАЦИЯ

- **Следующий отчёт:** $(date -d 'next monday' '+%d.%m.%Y')
- **Prometheus:** http://10.9.0.1:9090
- **Grafana:** http://10.9.0.1:3000
- **Контакт:** Telegram @msp_support

*Отчёт сгенерирован автоматически системой MSPShield*
EOF

    echo "$REPORT_FILE"
}

generate_recommendations() {
    local recs=""

    # Проверить диски > 80%
    local HIGH_DISK
    HIGH_DISK=$(prom_query '(1-node_filesystem_avail_bytes{fstype!~"tmpfs|overlay"}/node_filesystem_size_bytes)*100>80' | \
        python3 -c "
import sys, json
d = json.load(sys.stdin)
r = d.get('data',{}).get('result',[])
if r: print(f'- ⚠️ {len(r)} разделов заполнены более 80% — требуется очистка или расширение')
" 2>/dev/null)
    [[ -n "$HIGH_DISK" ]] && recs+="$HIGH_DISK\n"

    # Проверить бэкапы
    local FAILED_BACKUP
    FAILED_BACKUP=$(prom_query 'restic_backup_last_status==0' | \
        python3 -c "
import sys, json
d = json.load(sys.stdin)
r = d.get('data',{}).get('result',[])
if r: print(f'- 🔴 {len(r)} серверов с неудачными бэкапами — ТРЕБУЕТ НЕМЕДЛЕННОГО ВНИМАНИЯ')
" 2>/dev/null)
    [[ -n "$FAILED_BACKUP" ]] && recs+="$FAILED_BACKUP\n"

    # Проверить SSL < 30 дней
    local SSL_EXPIRING
    SSL_EXPIRING=$(prom_query '(probe_ssl_earliest_cert_expiry-time())/86400<30' | \
        python3 -c "
import sys, json
d = json.load(sys.stdin)
r = d.get('data',{}).get('result',[])
if r: print(f'- ⚠️ SSL-сертификаты истекают менее чем через 30 дней: {len(r)} сайтов')
" 2>/dev/null)
    [[ -n "$SSL_EXPIRING" ]] && recs+="$SSL_EXPIRING\n"

    [[ -z "$recs" ]] && echo "- ✅ Критических рекомендаций нет" || echo -e "$recs"
}

# ── Main ───────────────────────────────────────────────────────────
main() {
    local CLIENT="${1:-}"

    echo "Генерирую отчёт $([ -n "$CLIENT" ] && echo "для клиента $CLIENT" || echo "по всем клиентам")..."

    local REPORT
    REPORT=$(generate_report "$CLIENT")

    echo ""
    echo "═══════════════════════════════════════════"
    cat "$REPORT"
    echo "═══════════════════════════════════════════"
    echo ""
    echo "Отчёт сохранён: $REPORT"

    # Отправить краткую сводку в Telegram
    if [[ -n "$TELEGRAM_BOT" ]]; then
        local SUMMARY
        SUMMARY=$(head -30 "$REPORT" | grep -E "^(#|##|\-|✅|❌|⚠️|🔴)" | head -20)
        send_telegram "📊 <b>MSPShield Weekly Report</b>
${DATE_WEEK_AGO} → ${DATE_NOW}

${SUMMARY}

📄 Полный отчёт сохранён на сервере."
        echo "Краткая сводка отправлена в Telegram"
    fi
}

main "$@"
