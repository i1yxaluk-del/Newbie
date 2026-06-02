#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────
# tenant_add.sh — добавить новую AmneziaWG-подсеть тенанта на bastion
# ─────────────────────────────────────────────────────────────
# RU: Запускается на bastion/landing-VM при онбординге нового клиента
# (Day 1-7, см. docs/onboarding/day_1_7_runbook.md).
# Генерирует:
#   • приватный/публичный ключ тенанта;
#   • peer-конфиг клиента (передаётся клиенту через Vaultwarden Send);
#   • PresharedKey для дополнительной защиты;
#   • AllowedIPs на тенант-CIDR.
# Обновляет /etc/amnezia/amneziawg/awg0.conf и применяет без drop'а
# существующих peer'ов (awg syncconf).
#
# Usage:  sudo tenant_add.sh <tenant_name> <tenant_cidr>
# Example: sudo tenant_add.sh acme 10.20.10.0/24
#
# Предпосылка: awg0 уже поднят через awg_bootstrap.sh.
# Сетевой план:
#   10.9.0.0/24 — management overlay (bastion + наши landing/mon).
#   10.20.0.0/16 — тенанты (каждый клиент = свой /24).
#
# Параметры обфускации AmneziaWG (Jc/Jmin/Jmax/S1/S2/H1..H4) берутся
# из server-config'а — у всех peer'ов они должны совпадать с сервером.
# ─────────────────────────────────────────────────────────────
set -euo pipefail

if [[ $EUID -ne 0 ]]; then
  echo "Must run as root" >&2
  exit 1
fi

TENANT="${1:-}"
CIDR="${2:-}"
if [[ -z "$TENANT" || -z "$CIDR" ]]; then
  echo "Usage: $0 <tenant_name> <tenant_cidr>" >&2
  exit 1
fi

AWG_DIR="/etc/amnezia/amneziawg/tenants/${TENANT}"
AWG_CONF="/etc/amnezia/amneziawg/awg0.conf"
SERVER_PUB="$(cat /etc/amnezia/amneziawg/server_public.key 2>/dev/null || true)"
LISTEN_PORT="${LISTEN_PORT:-443}"
ENDPOINT_HOST="${ENDPOINT_HOST:-bastion.msp-claude.online}"

# Параметры обфускации — должны совпадать с сервером.
# Берём из awg0.conf, чтобы не дублировать дефолты.
read_awg_param() {
  local key="$1"
  grep -E "^${key}\s*=" "$AWG_CONF" | head -1 | sed -E 's/^[^=]+=\s*//' | tr -d '[:space:]'
}
AWG_JC="$(read_awg_param Jc)"
AWG_JMIN="$(read_awg_param Jmin)"
AWG_JMAX="$(read_awg_param Jmax)"
AWG_S1="$(read_awg_param S1)"
AWG_S2="$(read_awg_param S2)"
AWG_H1="$(read_awg_param H1)"
AWG_H2="$(read_awg_param H2)"
AWG_H3="$(read_awg_param H3)"
AWG_H4="$(read_awg_param H4)"

if [[ -z "$SERVER_PUB" ]]; then
  echo "Server public key not found at /etc/amnezia/amneziawg/server_public.key" >&2
  echo "Run bootstrap first: scripts/awg_bootstrap.sh" >&2
  exit 1
fi

if [[ -d "$AWG_DIR" ]]; then
  echo "Tenant '$TENANT' already exists in $AWG_DIR" >&2
  exit 1
fi

mkdir -p "$AWG_DIR"
chmod 700 "$AWG_DIR"

# Derive first usable IP of tenant CIDR as the tenant's VPN address.
TENANT_IP="$(python3 -c "import ipaddress, sys; n=ipaddress.ip_network('$CIDR'); print(str(list(n.hosts())[0]))")"

umask 077
awg genkey | tee "$AWG_DIR/private.key" | awg pubkey > "$AWG_DIR/public.key"
PRIV="$(cat "$AWG_DIR/private.key")"
PUB="$(cat "$AWG_DIR/public.key")"
PSK="$(awg genpsk)"
echo "$PSK" > "$AWG_DIR/psk.key"
chmod 600 "$AWG_DIR"/*.key

cat >"$AWG_DIR/client.conf" <<EOF
# MSPShield tenant '$TENANT' · AmneziaWG client config
[Interface]
PrivateKey = $PRIV
Address    = ${TENANT_IP}/32
DNS        = 1.1.1.1

# AmneziaWG обфускация — должна совпадать с сервером.
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
PublicKey           = $SERVER_PUB
PresharedKey        = $PSK
Endpoint            = ${ENDPOINT_HOST}:${LISTEN_PORT}
AllowedIPs          = ${CIDR}, 10.9.0.0/24
PersistentKeepalive = 25
EOF

# Ensure no BOM (AmneziaWG Windows client fails with UTF-8 BOM)
sed -i '1s/^\xEF\xBB\xBF//' "$AWG_DIR/client.conf"

# Append tenant to server config
cat >>"$AWG_CONF" <<EOF

# tenant: $TENANT · added $(date -Iseconds)
[Peer]
PublicKey    = $PUB
PresharedKey = $PSK
AllowedIPs   = ${TENANT_IP}/32
EOF

# Apply without dropping existing peers
awg syncconf awg0 <(awg-quick strip awg0)

echo "✓ Tenant '$TENANT' provisioned."
echo "  Client config: $AWG_DIR/client.conf"
echo "  Transfer to client over a secure channel (Vaultwarden Send)."
echo ""
echo "  WINDOWS CLIENT: Import .conf into AmneziaWG for Windows."
echo "  Config goes to: C:\Program Files\AmneziaWG\Data\Configurations\"
echo "  Creates Wintun adapter awg0-msp (IP ${TENANT_IP}/32)."
echo ""
echo "  ВАЖНО: если на Windows-станции работает прокси-клиент (Necoray,"
echo "  NekoBox и т.д.), он ДОЛЖЕН быть в proxy-режиме (НЕ TUN), иначе"
echo "  TUN-адаптер прокси перехватит AWG UDP/443 handshake."
