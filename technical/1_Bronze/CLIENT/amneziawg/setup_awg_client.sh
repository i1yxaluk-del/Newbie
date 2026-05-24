#!/bin/bash
# ═══════════════════════════════════════════════════════════════════
# setup_awg_client.sh — Настройка AmneziaWG VPN на клиентском Linux-сервере
# Запуск: sudo bash setup_awg_client.sh
#
# Скрипт:
#   1. Устанавливает AmneziaWG (форк WireGuard с обфускацией против РКН-DPI)
#   2. Генерирует ключевую пару
#   3. Выводит публичный ключ для передачи Исполнителю
#   4. Спрашивает у пользователя данные от Исполнителя (VPN IP, bastion pubkey,
#      bastion IP, параметры обфускации Jc/Jmin/Jmax/S1/S2/H1..H4)
#   5. Создаёт конфиг и запускает awg-quick@awg0-msp.
#
# ПОЧЕМУ AmneziaWG:
#   РКН-DPI ловит обычный WG handshake. AmneziaWG добавляет junk-пакеты
#   и рандомизирует длину init/response — DPI не видит сигнатуру.
#   Клиент и сервер ОБЯЗАТЕЛЬНО должны иметь ОДИНАКОВЫЕ Jc/Jmin/Jmax/S1/S2/H1..H4.
# ═══════════════════════════════════════════════════════════════════
set -euo pipefail

GREEN='\033[0;32m'; YELLOW='\033[1;33m'; RED='\033[0;31m'; CYAN='\033[0;36m'; NC='\033[0m'
ok()    { echo -e "${GREEN}✓${NC} $*"; }
info()  { echo -e "${CYAN}→${NC} $*"; }
warn()  { echo -e "${YELLOW}!${NC} $*"; }
err()   { echo -e "${RED}✗${NC} $*"; exit 1; }
ask()   { echo -e "${YELLOW}?${NC} $*"; }

[[ $EUID -ne 0 ]] && err "Запустить с sudo: sudo bash $0"

WG_IFACE="awg0-msp"   # Имя AmneziaWG интерфейса (не трогать awg0/wg0 если есть)
WG_DIR="/etc/amnezia/amneziawg"
WG_CONF="${WG_DIR}/${WG_IFACE}.conf"
WG_KEYS_DIR="${WG_DIR}"

mkdir -p "$WG_DIR"
chmod 700 "$WG_DIR"

echo ""
echo "═══════════════════════════════════════════════════════"
echo "  MSPShield AmneziaWG Client Setup"
echo "  Сервер: $(hostname -f)"
echo "═══════════════════════════════════════════════════════"

# ── Установить AmneziaWG ───────────────────────────────────────────
info "Устанавливаю AmneziaWG (PPA ppa:amnezia/ppa)..."

if [[ -f /etc/debian_version ]]; then
    if ! command -v add-apt-repository >/dev/null 2>&1; then
        apt-get update -qq
        apt-get install -y software-properties-common
    fi
    add-apt-repository -y ppa:amnezia/ppa
    apt-get update -qq
    apt-get install -y amneziawg-dkms amneziawg-tools
elif [[ -f /etc/redhat-release ]]; then
    warn "AmneziaWG на RHEL/CentOS — нет PPA, собираем из исходников."
    warn "См. https://github.com/amnezia-vpn/amneziawg-linux-kernel-module и amneziawg-tools."
    err "Автоматической установки для RHEL нет. Соберите вручную и запустите скрипт снова."
else
    err "Неизвестный дистрибутив. Установите AmneziaWG вручную."
fi
ok "AmneziaWG установлен: $(awg --version 2>&1 | head -1)"

# ── Генерация ключей ───────────────────────────────────────────────
info "Генерирую ключевую пару..."
cd "$WG_KEYS_DIR"

PRIV_KEY_FILE="${WG_KEYS_DIR}/${WG_IFACE}_private.key"
PUB_KEY_FILE="${WG_KEYS_DIR}/${WG_IFACE}_public.key"

awg genkey | tee "$PRIV_KEY_FILE" | awg pubkey > "$PUB_KEY_FILE"
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

echo ""
echo "AmneziaWG-обфускация (ОБЯЗАТЕЛЬНО должна совпадать с Bastion):"
echo "Исполнитель пришлёт 9 чисел: Jc, Jmin, Jmax, S1, S2, H1, H2, H3, H4."
echo "Дефолтные значения в скобках — просто Enter если их же прислал Исполнитель."
read -rp "Jc   [4]:          " AWG_JC;   AWG_JC="${AWG_JC:-4}"
read -rp "Jmin [50]:         " AWG_JMIN; AWG_JMIN="${AWG_JMIN:-50}"
read -rp "Jmax [1000]:       " AWG_JMAX; AWG_JMAX="${AWG_JMAX:-1000}"
read -rp "S1   [86]:         " AWG_S1;   AWG_S1="${AWG_S1:-86}"
read -rp "S2   [574]:        " AWG_S2;   AWG_S2="${AWG_S2:-574}"
read -rp "H1   [1779539752]: " AWG_H1;   AWG_H1="${AWG_H1:-1779539752}"
read -rp "H2   [1138729192]: " AWG_H2;   AWG_H2="${AWG_H2:-1138729192}"
read -rp "H3   [2050378563]: " AWG_H3;   AWG_H3="${AWG_H3:-2050378563}"
read -rp "H4   [8345423]:    " AWG_H4;   AWG_H4="${AWG_H4:-8345423}"

# ── Создать конфиг ─────────────────────────────────────────────────
info "Создаю конфигурацию ${WG_CONF}..."

cat > "$WG_CONF" << EOF
# AmneziaWG VPN — MSPShield
# Создан: $(date '+%Y-%m-%d %H:%M:%S')
# Сервер: $(hostname -f)

[Interface]
PrivateKey = ${PRIV_KEY}
Address    = ${CLIENT_VPN_IP}/32
DNS        = 77.88.8.8, 77.88.8.1

# AmneziaWG обфускация — ДОЛЖНО совпадать с Bastion'ом.
Jc   = ${AWG_JC}
Jmin = ${AWG_JMIN}
Jmax = ${AWG_JMAX}
S1   = ${AWG_S1}
S2   = ${AWG_S2}
H1   = ${AWG_H1}
H2   = ${AWG_H2}
H3   = ${AWG_H3}
H4   = ${AWG_H4}

[Peer]
# Bastion MSPShield (AmneziaWG на UDP/443)
PublicKey            = ${BASTION_PUBKEY}
Endpoint             = ${BASTION_IP}:443
AllowedIPs           = 10.9.0.0/24
PersistentKeepalive  = 25
EOF

chmod 600 "$WG_CONF"
ok "Конфиг создан: ${WG_CONF}"

# ── Запустить туннель ──────────────────────────────────────────────
info "Запускаю AmneziaWG туннель..."
systemctl enable --now awg-quick@${WG_IFACE} 2>&1 || {
    # Попробовать через awg-quick напрямую
    awg-quick up "${WG_IFACE}"
}

sleep 3

# ── Проверить ─────────────────────────────────────────────────────
echo ""
info "Проверяю соединение..."
WG_STATUS=$(awg show "${WG_IFACE}" 2>/dev/null)

if echo "$WG_STATUS" | grep -q "latest handshake"; then
    HANDSHAKE=$(echo "$WG_STATUS" | grep "latest handshake" | awk '{print $3,$4}')
    ok "Handshake: ${HANDSHAKE}"
else
    warn "Handshake пока нет. Ждём 10 секунд..."
    sleep 10
    awg show "${WG_IFACE}" | grep -q "latest handshake" && ok "Handshake установлен" || \
        warn "Handshake не установлен. Проверьте настройки на Bastion и параметры Jc/Jmin/Jmax/S1/S2/H1..H4."
fi

# Ping Bastion
if ping -c 3 -W 5 10.9.0.1 &>/dev/null; then
    ok "Ping 10.9.0.1 (Bastion): OK"
else
    warn "Ping Bastion не проходит. VPN может быть настроен неверно."
fi

# ── Сохранить информацию ───────────────────────────────────────────
INFO_FILE="${WG_DIR}/msp_vpn_info.txt"
cat > "$INFO_FILE" << EOF
# MSPShield AmneziaWG VPN Info
Created:     $(date '+%Y-%m-%d %H:%M:%S')
Server:      $(hostname -f)
VPN IP:      ${CLIENT_VPN_IP}
Interface:   ${WG_IFACE}
Bastion IP:  ${BASTION_IP}:443/udp
Public Key:  ${PUB_KEY}

# AmneziaWG обфускация (должна совпадать с Bastion):
Jc=${AWG_JC}
Jmin=${AWG_JMIN}
Jmax=${AWG_JMAX}
S1=${AWG_S1}
S2=${AWG_S2}
H1=${AWG_H1}
H2=${AWG_H2}
H3=${AWG_H3}
H4=${AWG_H4}
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
