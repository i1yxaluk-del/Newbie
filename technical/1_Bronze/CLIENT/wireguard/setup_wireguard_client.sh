#!/bin/bash
# ═══════════════════════════════════════════════════════════════════
# setup_wireguard_client.sh — Настройка WireGuard VPN на клиентском Linux-сервере
# Запуск: sudo bash setup_wireguard_client.sh
#
# Скрипт:
#   1. Устанавливает WireGuard
#   2. Генерирует ключевую пару
#   3. Выводит публичный ключ для передачи Исполнителю
#   4. Создаёт конфиг после получения данных от Исполнителя
# ═══════════════════════════════════════════════════════════════════
set -euo pipefail

GREEN='\033[0;32m'; YELLOW='\033[1;33m'; RED='\033[0;31m'; CYAN='\033[0;36m'; NC='\033[0m'
ok()    { echo -e "${GREEN}✓${NC} $*"; }
info()  { echo -e "${CYAN}→${NC} $*"; }
warn()  { echo -e "${YELLOW}!${NC} $*"; }
err()   { echo -e "${RED}✗${NC} $*"; exit 1; }
ask()   { echo -e "${YELLOW}?${NC} $*"; }

[[ $EUID -ne 0 ]] && err "Запустить с sudo: sudo bash $0"

WG_IFACE="wg0-msp"   # Имя WireGuard интерфейса (не трогать wg0 если он есть)
WG_CONF="/etc/wireguard/${WG_IFACE}.conf"
WG_KEYS_DIR="/etc/wireguard"

echo ""
echo "═══════════════════════════════════════════════════════"
echo "  MSPShield WireGuard Client Setup"
echo "  Сервер: $(hostname -f)"
echo "═══════════════════════════════════════════════════════"

# ── Установить WireGuard ───────────────────────────────────────────
info "Устанавливаю WireGuard..."

if [[ -f /etc/debian_version ]]; then
    apt-get update -qq
    apt-get install -y wireguard wireguard-tools
elif [[ -f /etc/redhat-release ]]; then
    yum install -y epel-release 2>/dev/null || true
    yum install -y wireguard-tools
else
    err "Неизвестный дистрибутив. Установите WireGuard вручную."
fi
ok "WireGuard установлен: $(wg --version)"

# ── Генерация ключей ───────────────────────────────────────────────
info "Генерирую ключевую пару..."
cd "$WG_KEYS_DIR"

PRIV_KEY_FILE="${WG_KEYS_DIR}/${WG_IFACE}_private.key"
PUB_KEY_FILE="${WG_KEYS_DIR}/${WG_IFACE}_public.key"

wg genkey | tee "$PRIV_KEY_FILE" | wg pubkey > "$PUB_KEY_FILE"
chmod 600 "$PRIV_KEY_FILE"
chmod 644 "$PUB_KEY_FILE"

PRIV_KEY=$(cat "$PRIV_KEY_FILE")
PUB_KEY=$(cat "$PUB_KEY_FILE")

ok "Ключи сгенерированы"

# ── Показать публичный ключ ────────────────────────────────────────
echo ""
echo "╔══════════════════════════════════════════════════════════╗"
echo "║  ПУБЛИЧНЫЙ КЛЮЧ — отправьте Исполнителю                 ║"
echo "╠══════════════════════════════════════════════════════════╣"
echo "║  Сервер: $(hostname -f | head -c 50)"
echo "║  IP: $(hostname -I | awk '{print $1}')"
echo "║  PubKey: ${PUB_KEY}"
echo "╚══════════════════════════════════════════════════════════╝"
echo ""

# ── Получить данные от Исполнителя ────────────────────────────────
echo "Исполнитель пришлёт:"
echo "  - Ваш VPN IP (например: 10.9.0.10)"
echo "  - Публичный ключ Bastion"
echo "  - Публичный IP Bastion"
echo ""
ask "Введите VPN IP этого сервера (от Исполнителя):"
read -r CLIENT_VPN_IP

ask "Введите публичный ключ Bastion (от Исполнителя):"
read -r BASTION_PUBKEY

ask "Введите публичный IP Bastion (от Исполнителя):"
read -r BASTION_IP

# ── Создать конфиг ─────────────────────────────────────────────────
info "Создаю конфигурацию ${WG_CONF}..."

cat > "$WG_CONF" << EOF
# WireGuard VPN — MSPShield
# Создан: $(date '+%Y-%m-%d %H:%M:%S')
# Сервер: $(hostname -f)

[Interface]
PrivateKey = ${PRIV_KEY}
Address    = ${CLIENT_VPN_IP}/32
DNS        = 77.88.8.8, 77.88.8.1

[Peer]
# Bastion MSPShield
PublicKey            = ${BASTION_PUBKEY}
Endpoint             = ${BASTION_IP}:51820
AllowedIPs           = 10.9.0.0/24
PersistentKeepalive  = 25
EOF

chmod 600 "$WG_CONF"
ok "Конфиг создан: ${WG_CONF}"

# ── Запустить туннель ──────────────────────────────────────────────
info "Запускаю WireGuard туннель..."
systemctl enable --now wg-quick@${WG_IFACE} 2>&1 || {
    # Попробовать через wg-quick напрямую
    wg-quick up "${WG_IFACE}"
}

sleep 3

# ── Проверить ─────────────────────────────────────────────────────
echo ""
info "Проверяю соединение..."
WG_STATUS=$(wg show "${WG_IFACE}" 2>/dev/null)

if echo "$WG_STATUS" | grep -q "latest handshake"; then
    HANDSHAKE=$(echo "$WG_STATUS" | grep "latest handshake" | awk '{print $3,$4}')
    ok "Handshake: ${HANDSHAKE}"
else
    warn "Handshake пока нет. Ждём 10 секунд..."
    sleep 10
    wg show "${WG_IFACE}" | grep -q "latest handshake" && ok "Handshake установлен" || \
        warn "Handshake не установлен. Проверьте настройки на Bastion."
fi

# Ping Bastion
if ping -c 3 -W 5 10.9.0.1 &>/dev/null; then
    ok "Ping 10.9.0.1 (Bastion): OK"
else
    warn "Ping Bastion не проходит. VPN может быть настроен неверно."
fi

# ── Сохранить информацию ───────────────────────────────────────────
INFO_FILE="/etc/wireguard/msp_vpn_info.txt"
cat > "$INFO_FILE" << EOF
# MSPShield VPN Info
Created:     $(date '+%Y-%m-%d %H:%M:%S')
Server:      $(hostname -f)
VPN IP:      ${CLIENT_VPN_IP}
Interface:   ${WG_IFACE}
Bastion IP:  ${BASTION_IP}
Public Key:  ${PUB_KEY}
EOF
chmod 600 "$INFO_FILE"

echo ""
echo "═══════════════════════════════════════════════════════"
echo "  ✅ WireGuard VPN настроен!"
echo ""
echo "  VPN IP этого сервера: ${CLIENT_VPN_IP}"
echo "  Интерфейс: ${WG_IFACE}"
echo ""
echo "  Статус: wg show ${WG_IFACE}"
echo "  Логи:   journalctl -u wg-quick@${WG_IFACE} -f"
echo "  Стоп:   systemctl stop wg-quick@${WG_IFACE}"
echo "═══════════════════════════════════════════════════════"
