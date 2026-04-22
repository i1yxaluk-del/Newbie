#!/bin/bash
# ═══════════════════════════════════════════════════════════════════
# verify_all.sh — Полная верификация MSP-стека (Исполнитель)
# Файл: /usr/local/bin/verify_all.sh
#
# Запуск: bash verify_all.sh [bronze|silver|gold]
# По умолчанию: проверяет всё что установлено
# ═══════════════════════════════════════════════════════════════════
set -euo pipefail

TIER="${1:-all}"
PROMETHEUS="http://localhost:9090"
FAILED=0
PASSED=0

# Цвета для вывода (часть используется в заголовках ниже по коду)
# shellcheck disable=SC2034  # Y зарезервирован для будущих WARN-сообщений
G='\033[0;32m'
R='\033[0;31m'
# shellcheck disable=SC2034
Y='\033[1;33m'
C='\033[0;36m'
B='\033[1m'
NC='\033[0m'

check() {
    local name="$1"
    local cmd="$2"

    if eval "$cmd" &>/dev/null; then
        echo -e "  ${G}✓${NC} ${name}"
        (( PASSED++ )) || true
    else
        echo -e "  ${R}✗${NC} ${name}"
        (( FAILED++ )) || true
    fi
}

check_http() {
    local name="$1"
    local url="$2"
    local expected_code="${3:-200}"

    local code
    code=$(curl -sf -o /dev/null -w "%{http_code}" --max-time 10 "$url" 2>/dev/null || echo "000")
    if [[ "$code" == "$expected_code" ]] || [[ "$code" == "200" ]]; then
        echo -e "  ${G}✓${NC} ${name} (HTTP ${code})"
        (( PASSED++ )) || true
    else
        echo -e "  ${R}✗${NC} ${name} (HTTP ${code}, ожидалось ${expected_code})"
        (( FAILED++ )) || true
    fi
}

# shellcheck disable=SC2120
check_prom_targets() {
    local filter="${1:-}"
    local data
    data=$(curl -sf --max-time 10 "${PROMETHEUS}/api/v1/targets" 2>/dev/null || echo '{}')

    echo "$data" | python3 -c "
import sys, json
d = json.load(sys.stdin)
targets = d.get('data', {}).get('activeTargets', [])
filter_str = '$filter'
for t in targets:
    labels = t.get('labels', {})
    if filter_str and filter_str not in str(labels):
        continue
    job    = labels.get('job', '?')
    inst   = labels.get('instance', '?')
    health = t.get('health', '?')
    color  = '\033[0;32m' if health == 'up' else '\033[0;31m'
    symbol = '✓' if health == 'up' else '✗'
    print(f'  {color}{symbol}\033[0m {job:<40} {inst:<30} [{health}]')
" 2>/dev/null || echo "  ⚠️  Prometheus недоступен"
}

# ════════════════════════════════════════════════════════════════════
# BRONZE — ОСНОВНОЙ СТЕК
# ════════════════════════════════════════════════════════════════════
check_bronze() {
    echo -e "\n${B}══ BRONZE: Docker Compose стек ══${NC}"

    check "Docker запущен" "docker info"
    check "Контейнер prometheus" "docker inspect msp-prometheus --format '{{.State.Running}}' | grep -q true"
    check "Контейнер alertmanager" "docker inspect msp-alertmanager --format '{{.State.Running}}' | grep -q true"
    check "Контейнер grafana" "docker inspect msp-grafana --format '{{.State.Running}}' | grep -q true"
    check "Контейнер blackbox" "docker inspect msp-blackbox --format '{{.State.Running}}' | grep -q true"
    check "Контейнер node-exporter" "docker inspect msp-node-exporter --format '{{.State.Running}}' | grep -q true"

    echo -e "\n${B}══ BRONZE: API Health Checks ══${NC}"
    check_http "Prometheus /healthy" "http://localhost:9090/-/healthy"
    check_http "Alertmanager /healthy" "http://localhost:9093/-/healthy"
    check_http "Grafana /api/health" "http://10.9.0.1:3000/api/health"
    check_http "Blackbox /metrics" "http://localhost:9115/metrics"

    echo -e "\n${B}══ BRONZE: WireGuard VPN ══${NC}"
    check "WireGuard интерфейс wg0" "ip link show wg0"
    check "VPN IP 10.9.0.1 настроен" "ip addr show wg0 | grep -q '10.9.0.1'"

    local PEERS
    PEERS=$(sudo wg show wg0 2>/dev/null | grep -c "^peer:" || echo "0")
    echo -e "  ${C}→${NC} Зарегистрированных VPN peers: ${PEERS}"

    echo -e "\n${B}══ BRONZE: Prometheus Alert Rules ══${NC}"
    local RULES
    RULES=$(curl -sf "${PROMETHEUS}/api/v1/rules" 2>/dev/null | \
        python3 -c "
import sys, json
d = json.load(sys.stdin)
groups = d.get('data', {}).get('groups', [])
total = sum(len(g.get('rules', [])) for g in groups)
firing = sum(1 for g in groups for r in g.get('rules', []) if r.get('state') == 'firing')
print(f'{total} правил загружено, {firing} активных алертов')
" 2>/dev/null || echo "недоступно")
    echo -e "  ${C}→${NC} Правила: ${RULES}"

    echo -e "\n${B}══ BRONZE: Prometheus Targets ══${NC}"
    check_prom_targets
}

# ════════════════════════════════════════════════════════════════════
# SILVER — LOKI + PUPPET
# ════════════════════════════════════════════════════════════════════
check_silver() {
    echo -e "\n${B}══ SILVER: Loki ══${NC}"
    check "Контейнер loki" "docker inspect msp-loki --format '{{.State.Running}}' | grep -q true"
    check_http "Loki /ready" "http://localhost:3100/ready"
    check_http "Loki /metrics" "http://localhost:3100/metrics"

    local LOKI_STREAMS
    LOKI_STREAMS=$(curl -sf "http://localhost:3100/metrics" 2>/dev/null | \
        grep "loki_ingester_streams_created_total" | awk '{print $2}' | head -1 || echo "0")
    echo -e "  ${C}→${NC} Loki потоков создано: ${LOKI_STREAMS:-0}"

    echo -e "\n${B}══ SILVER: Puppet Server ══${NC}"
    check "Puppet Server процесс" "systemctl is-active puppetserver"
    check_http "Puppet Server /status" "https://localhost:8140/status/v1/simple" "200"

    local PUPPET_CERTS
    PUPPET_CERTS=$(puppetserver ca list --all 2>/dev/null | grep -c "Signed" || echo "0")
    echo -e "  ${C}→${NC} Puppet подписанных сертификатов: ${PUPPET_CERTS}"

    echo -e "\n${B}══ SILVER: Ansible ══${NC}"
    check "Ansible установлен" "command -v ansible-playbook"
    check "Ansible inventory" "test -d /opt/ansible/inventory/clients"

    local CLIENT_COUNT
    CLIENT_COUNT=$(find /opt/ansible/inventory/clients -name hosts 2>/dev/null | wc -l || echo "0")
    echo -e "  ${C}→${NC} Клиентов в inventory: ${CLIENT_COUNT}"
}

# ════════════════════════════════════════════════════════════════════
# GOLD — WAZUH + OSTICKET
# ════════════════════════════════════════════════════════════════════
check_gold() {
    echo -e "\n${B}══ GOLD: Wazuh ══${NC}"
    check "Wazuh Manager контейнер" "docker inspect wazuh-manager --format '{{.State.Running}}' | grep -q true"
    check "Wazuh Indexer контейнер" "docker inspect wazuh-indexer --format '{{.State.Running}}' | grep -q true"
    check "Wazuh Dashboard контейнер" "docker inspect wazuh-dashboard --format '{{.State.Running}}' | grep -q true"

    echo -e "\n${B}══ GOLD: osTicket ══${NC}"
    check "osTicket контейнер" "docker inspect osticket-web --format '{{.State.Running}}' | grep -q true"
    check_http "osTicket Web" "http://10.9.0.1:8080" "200"

    echo -e "\n${B}══ GOLD: Wazuh Agents ══${NC}"
    local WAZUH_AGENTS
    WAZUH_AGENTS=$(docker exec wazuh-manager /var/ossec/bin/agent_control -l 2>/dev/null | \
        grep -c "Active" || echo "недоступно")
    echo -e "  ${C}→${NC} Wazuh активных агентов: ${WAZUH_AGENTS}"
}

# ════════════════════════════════════════════════════════════════════
# MAIN
# ════════════════════════════════════════════════════════════════════
echo ""
echo -e "${B}════════════════════════════════════════════════${NC}"
echo -e "${B}  MSPShield Stack Verification${NC}"
echo -e "${B}  $(date '+%d.%m.%Y %H:%M:%S')${NC}"
echo -e "${B}════════════════════════════════════════════════${NC}"

case "$TIER" in
    bronze) check_bronze ;;
    silver) check_bronze; check_silver ;;
    gold)   check_bronze; check_silver; check_gold ;;
    all)
        check_bronze
        # Silver только если Loki запущен
        docker inspect msp-loki &>/dev/null 2>&1 && check_silver || true
        # Gold только если Wazuh запущен
        docker inspect wazuh-manager &>/dev/null 2>&1 && check_gold || true
        ;;
    *) echo "Использование: $0 [bronze|silver|gold|all]"; exit 1 ;;
esac

# ── Итог ──────────────────────────────────────────────────────────
echo ""
echo -e "${B}════════════════════════════════════════════════${NC}"
echo -e "  Пройдено: ${G}${PASSED}${NC}  |  Провалено: ${R}${FAILED}${NC}"
echo -e "${B}════════════════════════════════════════════════${NC}"
echo ""

if [[ $FAILED -gt 0 ]]; then
    echo -e "${R}⚠️  Обнаружены проблемы. Проверьте вывод выше.${NC}"
    exit 1
else
    echo -e "${G}✅ Все проверки пройдены.${NC}"
    exit 0
fi
