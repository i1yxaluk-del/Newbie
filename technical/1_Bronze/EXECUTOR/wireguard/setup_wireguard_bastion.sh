#!/bin/bash
# ═══════════════════════════════════════════════════════════════════
# setup_wireguard_bastion.sh — Настройка WireGuard Bastion Server
# Файл: /usr/local/bin/setup_wireguard_bastion.sh
# Запуск: sudo bash setup_wireguard_bastion.sh
#
# Выполняется ОДИН РАЗ на Bastion VM при первоначальной настройке
# ═══════════════════════════════════════════════════════════════════
set -euo pipefail

G='\033[0;32m'; Y='\033[1;33m'; C='\033[0;36m'; NC='\033[0m'
ok()   { echo -e "${G}✓${NC} $*"; }
info() { echo -e "${C}→${NC} $*"; }
warn() { echo -e "${Y}!${NC} $*"; }

[[ $EUID -ne 0 ]] && { echo "sudo required"; exit 1; }

WG_IFACE="wg0"
WG_PORT="51820"
VPN_NET="10.9.0.0/24"
VPN_IP="10.9.0.1"
WG_DIR="/etc/wireguard"

echo "════════════════════════════════════════════"
echo " MSPShield WireGuard Bastion Setup"
echo " Interface: ${WG_IFACE} | Port: ${WG_PORT}"
echo " VPN Network: ${VPN_NET}"
echo "════════════════════════════════════════════"

# ── Установить WireGuard ───────────────────────────────────────────
info "Устанавливаю WireGuard..."
apt-get update -qq
apt-get install -y wireguard wireguard-tools iptables
ok "WireGuard $(wg --version)"

# ── Включить IP Forwarding ─────────────────────────────────────────
info "Включаю IP forwarding..."
cat > /etc/sysctl.d/99-wireguard.conf << 'EOF'
net.ipv4.ip_forward = 1
net.ipv6.conf.all.forwarding = 1
EOF
sysctl -p /etc/sysctl.d/99-wireguard.conf
ok "IP forwarding включён"

# ── Определить основной сетевой интерфейс ─────────────────────────
MAIN_IFACE=$(ip route get 8.8.8.8 2>/dev/null | awk '{for(i=1;i<=NF;i++) if($i=="dev") print $(i+1)}' | head -1)
MAIN_IFACE="${MAIN_IFACE:-eth0}"
info "Основной интерфейс: ${MAIN_IFACE}"

# ── Генерация ключей сервера ───────────────────────────────────────
info "Генерирую ключевую пару Bastion..."
mkdir -p "$WG_DIR"
chmod 700 "$WG_DIR"

wg genkey | tee "${WG_DIR}/server_private.key" | wg pubkey > "${WG_DIR}/server_public.key"
chmod 600 "${WG_DIR}/server_private.key"
chmod 644 "${WG_DIR}/server_public.key"

SERVER_PRIVKEY=$(cat "${WG_DIR}/server_private.key")
SERVER_PUBKEY=$(cat "${WG_DIR}/server_public.key")
ok "Ключи сгенерированы"

# ── Создать конфиг WireGuard ───────────────────────────────────────
info "Создаю /etc/wireguard/${WG_IFACE}.conf..."
cat > "${WG_DIR}/${WG_IFACE}.conf" << EOF
# ══════════════════════════════════════════════════════
# WireGuard Bastion Server — MSPShield
# Создан: $(date '+%Y-%m-%d %H:%M:%S')
# ══════════════════════════════════════════════════════

[Interface]
PrivateKey = ${SERVER_PRIVKEY}
Address    = ${VPN_IP}/24
ListenPort = ${WG_PORT}
SaveConfig = false

# NAT: позволить клиентам VPN выходить через основной интерфейс
PostUp   = iptables -A FORWARD -i %i -j ACCEPT; \
           iptables -A FORWARD -o %i -j ACCEPT; \
           iptables -t nat -A POSTROUTING -o ${MAIN_IFACE} -j MASQUERADE
PostDown = iptables -D FORWARD -i %i -j ACCEPT; \
           iptables -D FORWARD -o %i -j ACCEPT; \
           iptables -t nat -D POSTROUTING -o ${MAIN_IFACE} -j MASQUERADE

# ══════════════════════════════════════════════════════
# PEERS КЛИЕНТОВ — добавлять через onboard_client.sh
# или вручную:
#   sudo add_vpn_peer.sh CLIENT_SLUG 10.9.0.XX "PUBKEY"
# ══════════════════════════════════════════════════════

# ШАБЛОН (раскомментировать и заполнить):
# [Peer]
# # Клиент: ООО Пример — server-01
# PublicKey  = CLIENT_PUBLIC_KEY_HERE
# AllowedIPs = 10.9.0.10/32
EOF
chmod 600 "${WG_DIR}/${WG_IFACE}.conf"
ok "Конфиг создан: ${WG_DIR}/${WG_IFACE}.conf"

# ── Скрипт добавления peer ─────────────────────────────────────────
cat > /usr/local/bin/add_vpn_peer.sh << 'SCRIPT'
#!/bin/bash
# Использование: add_vpn_peer.sh CLIENT_SLUG VPN_IP CLIENT_PUBKEY
# Пример:        add_vpn_peer.sh company1 10.9.0.10 "abc123pubkey..."

set -euo pipefail
CLIENT="${1:?Usage: $0 CLIENT_SLUG VPN_IP CLIENT_PUBKEY}"
VPN_IP="${2:?}"
CLIENT_PUBKEY="${3:?}"
WG_CONF="/etc/wireguard/wg0.conf"

cat >> "$WG_CONF" << EOF

[Peer]
# Client: ${CLIENT} — Added: $(date '+%Y-%m-%d')
PublicKey  = ${CLIENT_PUBKEY}
AllowedIPs = ${VPN_IP}/32
EOF

# Hot reload (без перезапуска)
wg set wg0 peer "$CLIENT_PUBKEY" allowed-ips "${VPN_IP}/32"
echo "✓ Peer добавлен: ${CLIENT} → ${VPN_IP}"
SCRIPT
chmod +x /usr/local/bin/add_vpn_peer.sh

# ── UFW ───────────────────────────────────────────────────────────
info "Настраиваю UFW..."
ufw default deny incoming
ufw default allow outgoing
ufw allow 22/tcp   comment "SSH"
ufw allow "${WG_PORT}/udp" comment "WireGuard VPN"
# Мониторинг-сервисы — только через VPN
# НЕ открывать 3000, 9090, 3100 наружу!
ufw --force enable
ok "UFW настроен"

# ── Запустить WireGuard ────────────────────────────────────────────
info "Запускаю WireGuard..."
systemctl enable --now "wg-quick@${WG_IFACE}"
sleep 2

if ip link show "$WG_IFACE" | grep -q UP; then
    ok "WireGuard ${WG_IFACE} запущен"
else
    warn "WireGuard запущен, но статус неопределён. Проверьте: wg show ${WG_IFACE}"
fi

# ── Финал ─────────────────────────────────────────────────────────
PUBLIC_IP=$(curl -sf --max-time 5 https://checkip.amazonaws.com 2>/dev/null || echo "UNKNOWN")

echo ""
echo "════════════════════════════════════════════"
echo " ✅ WireGuard Bastion готов!"
echo ""
echo " Публичный IP:  ${PUBLIC_IP}"
echo " VPN IP:        ${VPN_IP}"
echo " Порт:          ${WG_PORT}/udp"
echo ""
echo " ⭐ ПУБЛИЧНЫЙ КЛЮЧ (передать клиентам):"
echo " ${SERVER_PUBKEY}"
echo ""
echo " Статус:  wg show ${WG_IFACE}"
echo " Клиенты: cat ${WG_DIR}/${WG_IFACE}.conf"
echo " Добавить клиента: add_vpn_peer.sh SLUG IP PUBKEY"
echo "════════════════════════════════════════════"

# Сохранить в файл
cat > "${WG_DIR}/bastion_info.txt" << EOF
# MSPShield Bastion Info
# Created: $(date '+%Y-%m-%d %H:%M:%S')
Public IP:  ${PUBLIC_IP}
VPN IP:     ${VPN_IP}
Port:       ${WG_PORT}
Public Key: ${SERVER_PUBKEY}
Interface:  ${WG_IFACE}
EOF
chmod 600 "${WG_DIR}/bastion_info.txt"
ok "Информация сохранена: ${WG_DIR}/bastion_info.txt"
