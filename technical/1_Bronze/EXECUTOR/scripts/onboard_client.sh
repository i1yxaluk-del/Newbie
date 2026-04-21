#!/bin/bash
# ═══════════════════════════════════════════════════════════════════
# onboard_client.sh — Интерактивный скрипт онбординга нового клиента
# Файл: /usr/local/bin/onboard_client.sh
#
# Запуск: sudo bash onboard_client.sh
# Что делает:
#   1. Запрашивает данные о клиенте
#   2. Создаёт структуру в Ansible inventory
#   3. Генерирует WireGuard peer
#   4. Создаёт S3 bucket для бэкапов
#   5. Добавляет клиента в Prometheus
#   6. Выводит инструкцию для передачи клиенту
# ═══════════════════════════════════════════════════════════════════
set -euo pipefail

# ── Цвета ─────────────────────────────────────────────────────────
G='\033[0;32m'; Y='\033[1;33m'; R='\033[0;31m'; C='\033[0;36m'; B='\033[1m'; NC='\033[0m'
ok()   { echo -e "${G}✓${NC} $*"; }
warn() { echo -e "${Y}!${NC} $*"; }
err()  { echo -e "${R}✗${NC} $*"; exit 1; }
info() { echo -e "${C}→${NC} $*"; }
hdr()  { echo -e "\n${B}═══ $* ═══${NC}"; }

# ── Проверки ──────────────────────────────────────────────────────
[[ $EUID -ne 0 ]] && err "Запустить с sudo"
command -v wg &>/dev/null      || err "WireGuard не установлен"
command -v python3 &>/dev/null || err "Python3 не установлен"

PROMETHEUS_CFG="/opt/monitoring/prometheus/prometheus.yml"
ANSIBLE_DIR="/opt/ansible"
BASTION_PUBKEY_FILE="/etc/wireguard/server_public.key"
BASTION_IP=$(curl -sf --max-time 5 https://checkip.amazonaws.com 2>/dev/null || echo "UNKNOWN")

[[ ! -f "$BASTION_PUBKEY_FILE" ]] && err "Файл $BASTION_PUBKEY_FILE не найден. Сначала настройте Bastion."

BASTION_PUBKEY=$(cat "$BASTION_PUBKEY_FILE")

# ════════════════════════════════════════════════════════════════════
# ШАГ 1: Данные о клиенте
# ════════════════════════════════════════════════════════════════════
hdr "НОВЫЙ КЛИЕНТ"

read -rp "Slug клиента (латиница, без пробелов, пример: company1): " CLIENT_SLUG
read -rp "Полное название клиента: " CLIENT_NAME
echo "Тарифы: 1=Bronze  2=Silver  3=Gold"
read -rp "Тариф [1]: " TIER_NUM
TIER="bronze"
case "${TIER_NUM:-1}" in
    2) TIER="silver" ;;
    3) TIER="gold" ;;
esac

# Найти свободный VPN IP диапазон
EXISTING_IPS=$(wg show wg0 2>/dev/null | grep "allowed ips" | grep -oP '10\.9\.0\.\K\d+' | sort -n || echo "")
NEXT_IP=10
for ip in $EXISTING_IPS; do
    if [[ $ip -ge $NEXT_IP ]]; then
        NEXT_IP=$(( ip + 1 ))
    fi
done
SUGGESTED_START="10.9.0.${NEXT_IP}"

read -rp "VPN IP первого сервера [${SUGGESTED_START}]: " VPN_IP_1
VPN_IP_1="${VPN_IP_1:-$SUGGESTED_START}"

read -rp "Количество дополнительных серверов (0-10) [0]: " EXTRA_SERVERS
EXTRA_SERVERS="${EXTRA_SERVERS:-0}"

read -rp "Email контактного лица: " CLIENT_EMAIL
read -rp "Telegram контактного лица (@username): " CLIENT_TG

echo ""
info "Клиент: ${CLIENT_NAME} (${CLIENT_SLUG})"
info "Тариф: ${TIER}"
info "VPN: ${VPN_IP_1} и далее"
read -rp "Продолжить? [Y/n]: " CONFIRM
[[ "${CONFIRM:-Y}" =~ ^[Nn] ]] && echo "Отменено." && exit 0

# ════════════════════════════════════════════════════════════════════
# ШАГ 2: WireGuard peer
# ════════════════════════════════════════════════════════════════════
hdr "WIREGUARD VPN"

WG_TMP=$(mktemp -d)
trap 'rm -rf "$WG_TMP"' EXIT

CLIENT_PRIV_KEY=$(wg genkey)
CLIENT_PUB_KEY=$(echo "$CLIENT_PRIV_KEY" | wg pubkey)

info "Добавляю peer ${VPN_IP_1} в WireGuard..."

# Добавить в конфиг wg0
cat >> /etc/wireguard/wg0.conf << EOF

# === ${CLIENT_NAME} (${CLIENT_SLUG}) — Добавлен: $(date '+%Y-%m-%d') ===
[Peer]
PublicKey  = ${CLIENT_PUB_KEY}
AllowedIPs = ${VPN_IP_1}/32
EOF

# Применить без перезапуска
wg set wg0 peer "$CLIENT_PUB_KEY" allowed-ips "${VPN_IP_1}/32"

ok "WireGuard peer добавлен: ${VPN_IP_1}"

# Добавить дополнительные серверы
EXTRA_IPS=()
if [[ "$EXTRA_SERVERS" -gt 0 ]]; then
    CURRENT_IP="$NEXT_IP"
    for i in $(seq 1 "$EXTRA_SERVERS"); do
        CURRENT_IP=$(( CURRENT_IP + i ))
        EXTRA_IP="10.9.0.${CURRENT_IP}"
        EXTRA_PRIV=$(wg genkey)
        EXTRA_PUB=$(echo "$EXTRA_PRIV" | wg pubkey)
        EXTRA_IPS+=("$EXTRA_IP:$EXTRA_PRIV:$EXTRA_PUB")

        cat >> /etc/wireguard/wg0.conf << EOF

# === ${CLIENT_SLUG} server-$(printf "%02d" $i) ===
[Peer]
PublicKey  = ${EXTRA_PUB}
AllowedIPs = ${EXTRA_IP}/32
EOF
        wg set wg0 peer "$EXTRA_PUB" allowed-ips "${EXTRA_IP}/32"
        ok "Дополнительный peer: ${EXTRA_IP}"
    done
fi

wg-quick save wg0

# ════════════════════════════════════════════════════════════════════
# ШАГ 3: Ansible inventory
# ════════════════════════════════════════════════════════════════════
hdr "ANSIBLE INVENTORY"

CLIENT_DIR="${ANSIBLE_DIR}/inventory/clients/${CLIENT_SLUG}"
mkdir -p "$CLIENT_DIR"

# Сгенерировать пароль репозитория restic
RESTIC_PASSWORD=$(openssl rand -hex 32)

cat > "${CLIENT_DIR}/vars.yml" << EOF
---
# Сгенерировано: $(date '+%Y-%m-%d %H:%M:%S')
client_slug:  "${CLIENT_SLUG}"
client_name:  "${CLIENT_NAME}"
client_tier:  "${TIER}"

msp_vpn_subnet:  "10.9.0.0/24"
loki_url:        "http://10.9.0.1:3100"
puppet_server:   "puppet-server.internal"
wazuh_manager:   "10.9.0.3"

node_exporter_version:    "1.7.0"
windows_exporter_version: "0.25.1"
restic_version:           "0.16.4"
promtail_version:         "3.0.0"

node_exporter_port:    9100
windows_exporter_port: 9182
promtail_port:         9080

# Бэкап — заполнить реальными S3-ключами
restic_s3_access_key:  "REPLACE_WITH_ACCESS_KEY"
restic_s3_secret_key:  "REPLACE_WITH_SECRET_KEY"
restic_s3_bucket:      "backup-${CLIENT_SLUG}"
restic_repo_password:  "${RESTIC_PASSWORD}"

restic_backup_paths:
  - /etc
  - /home
  - /root
  - /srv
  - /opt
  - /var/www

client_contact_email:    "${CLIENT_EMAIL}"
client_contact_telegram: "${CLIENT_TG}"
client_onboarded_at:     "$(date '+%Y-%m-%d')"
EOF

cat > "${CLIENT_DIR}/hosts" << EOF
# Inventory: ${CLIENT_NAME}
# Создан: $(date '+%Y-%m-%d')
# Тариф: ${TIER}

[client_linux]
# server-01  ansible_host=${VPN_IP_1}  ansible_user=ubuntu

[client_windows]
# 1c-01  ansible_host=10.9.0.XX  ansible_user=Administrator  ansible_connection=winrm  ansible_winrm_transport=ntlm  ansible_winrm_server_cert_validation=ignore

[client_all:children]
client_linux
client_windows

[client_all:vars]
ansible_ssh_common_args='-o StrictHostKeyChecking=no -o ConnectTimeout=30'
ansible_ssh_private_key_file=~/.ssh/id_ed25519
EOF

ok "Ansible inventory создан: ${CLIENT_DIR}/"

# ════════════════════════════════════════════════════════════════════
# ШАГ 4: S3 Bucket (если yc доступен)
# ════════════════════════════════════════════════════════════════════
hdr "YANDEX CLOUD S3"

if command -v yc &>/dev/null; then
    info "Создаю S3 bucket backup-${CLIENT_SLUG}..."
    if yc storage bucket create --name "backup-${CLIENT_SLUG}" 2>/dev/null; then
        ok "Bucket создан: backup-${CLIENT_SLUG}"
    else
        warn "Bucket уже существует или ошибка"
    fi
else
    warn "yc CLI не найден. Создайте bucket вручную: backup-${CLIENT_SLUG}"
fi

# ════════════════════════════════════════════════════════════════════
# ШАГ 5: Prometheus
# ════════════════════════════════════════════════════════════════════
hdr "PROMETHEUS"

if [[ -f "$PROMETHEUS_CFG" ]]; then
    # Проверить, нет ли уже такого клиента
    if grep -q "client-${CLIENT_SLUG}" "$PROMETHEUS_CFG"; then
        warn "Клиент ${CLIENT_SLUG} уже есть в Prometheus"
    else
        cat >> "$PROMETHEUS_CFG" << EOF

  # ═══════════════════════════════════════════
  # КЛИЕНТ: ${CLIENT_NAME} (${TIER})
  # Добавлен: $(date '+%Y-%m-%d')
  # VPN: ${VPN_IP_1}
  # ═══════════════════════════════════════════
  - job_name: 'client-${CLIENT_SLUG}-linux'
    scrape_interval: 30s
    static_configs:
      - targets:
          - '${VPN_IP_1}:9100'
        labels:
          client:      '${CLIENT_SLUG}'
          client_name: '${CLIENT_NAME}'
          tier:        '${TIER}'
          env:         'production'
EOF
        # Hot reload
        curl -sf -X POST http://localhost:9090/-/reload 2>/dev/null && \
            ok "Prometheus конфиг перезагружен" || warn "Prometheus reload: ошибка"
    fi
else
    warn "Prometheus конфиг не найден: $PROMETHEUS_CFG"
fi

# ════════════════════════════════════════════════════════════════════
# ШАГ 6: Генерация WireGuard конфигов для клиента
# ════════════════════════════════════════════════════════════════════
hdr "КОНФИГИ ДЛЯ КЛИЕНТА"

CLIENT_CONFIGS_DIR="${CLIENT_DIR}/wireguard_configs"
mkdir -p "$CLIENT_CONFIGS_DIR"

# Первый сервер
cat > "${CLIENT_CONFIGS_DIR}/server-01.conf" << EOF
# WireGuard конфиг для ${CLIENT_NAME} — server-01
# Сохранить в /etc/wireguard/wg0-msp.conf

[Interface]
PrivateKey = ${CLIENT_PRIV_KEY}
Address    = ${VPN_IP_1}/32
DNS        = 77.88.8.8, 77.88.8.1

[Peer]
# MSPShield Bastion
PublicKey           = ${BASTION_PUBKEY}
Endpoint            = ${BASTION_IP}:51820
AllowedIPs          = 10.9.0.0/24
PersistentKeepalive = 25
EOF
chmod 600 "${CLIENT_CONFIGS_DIR}/server-01.conf"

# Дополнительные серверы
IDX=2
for ENTRY in "${EXTRA_IPS[@]:-}"; do
    [[ -z "$ENTRY" ]] && continue
    IFS=':' read -r IP PRIV PUB <<< "$ENTRY"
    cat > "${CLIENT_CONFIGS_DIR}/server-$(printf '%02d' $IDX).conf" << EOF
# WireGuard конфиг для ${CLIENT_NAME} — server-$(printf '%02d' $IDX)
[Interface]
PrivateKey = ${PRIV}
Address    = ${IP}/32
DNS        = 77.88.8.8, 77.88.8.1

[Peer]
PublicKey           = ${BASTION_PUBKEY}
Endpoint            = ${BASTION_IP}:51820
AllowedIPs          = 10.9.0.0/24
PersistentKeepalive = 25
EOF
    chmod 600 "${CLIENT_CONFIGS_DIR}/server-$(printf '%02d' $IDX).conf"
    IDX=$(( IDX + 1 ))
done

ok "WireGuard конфиги сохранены в: ${CLIENT_CONFIGS_DIR}/"

# ════════════════════════════════════════════════════════════════════
# ИТОГ
# ════════════════════════════════════════════════════════════════════
hdr "ГОТОВО"

echo ""
echo "╔══════════════════════════════════════════════════════════════╗"
echo "║  КЛИЕНТ ДОБАВЛЕН: ${CLIENT_NAME}"
echo "║  Тариф: ${TIER} | VPN: ${VPN_IP_1}"
echo "╠══════════════════════════════════════════════════════════════╣"
echo "║  СЛЕДУЮЩИЕ ШАГИ:"
echo "║"
echo "║  1. Отправить клиенту:"
echo "║     - WireGuard конфиги из: ${CLIENT_CONFIGS_DIR}/"
echo "║     - Инструкцию: SOP_client_bronze.md"
echo "║"
echo "║  2. Заполнить hosts в: ${CLIENT_DIR}/hosts"
echo "║     (добавить реальные IP серверов)"
echo "║"
echo "║  3. Запустить Ansible после VPN-подключения:"
echo "║     ansible-playbook playbooks/deploy_bronze.yml \\"
echo "║       -i inventory/clients/${CLIENT_SLUG}/hosts \\"
echo "║       -e client_slug=${CLIENT_SLUG} \\"
echo "║       -v"
echo "║"
echo "║  4. Обновить vars.yml с реальными S3-ключами"
echo "║"
echo "║  5. Проверить targets:"
echo "║     http://10.9.0.1:9090/targets"
echo "╚══════════════════════════════════════════════════════════════╝"
echo ""
echo "restic repo password: ${RESTIC_PASSWORD}"
echo "(Сохранить в менеджере паролей!)"
echo ""
