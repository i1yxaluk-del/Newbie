#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────
# tenant_add.sh — добавить новую WireGuard-подсеть тенанта на bastion
# ─────────────────────────────────────────────────────────────
# RU: Запускается на mspshield-bastion при онбординге нового клиента
# (Day 1-7, см. docs/onboarding/day_1_7_runbook.md).
# Генерирует:
#   • приватный/публичный ключ тенанта;
#   • peer-конфиг клиента (передаётся клиенту защищённым каналом);
#   • PresharedKey для дополнительной защиты;
#   • AllowedIPs на тенант-CIDR.
# Обновляет /etc/wireguard/wg0.conf и перезагружает интерфейс.
#
# Usage:  sudo tenant_add.sh <tenant_name> <tenant_cidr>
# Example: sudo tenant_add.sh acme 10.20.10.0/24
#
# Предпосылка: wg0 уже поднят через wg_bootstrap.sh.
# Сетевой план:
#   10.10.0.0/16 — management overlay (bastion + наши landing/mon).
#   10.20.0.0/16 — тенанты (каждый клиент = свой /24).
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

WG_DIR="/etc/wireguard/tenants/${TENANT}"
WG_CONF="/etc/wireguard/wg0.conf"
SERVER_PUB="$(cat /etc/wireguard/server_public.key 2>/dev/null || true)"
LISTEN_PORT="51820"
ENDPOINT_HOST="${ENDPOINT_HOST:-bastion.msp-claude.online}"

if [[ -z "$SERVER_PUB" ]]; then
  echo "Server public key not found at /etc/wireguard/server_public.key" >&2
  echo "Run bootstrap first: scripts/wg_bootstrap.sh" >&2
  exit 1
fi

if [[ -d "$WG_DIR" ]]; then
  echo "Tenant '$TENANT' already exists in $WG_DIR" >&2
  exit 1
fi

mkdir -p "$WG_DIR"
chmod 700 "$WG_DIR"

# Derive first usable IP of tenant CIDR as the tenant's VPN address.
TENANT_IP="$(python3 -c "import ipaddress, sys; n=ipaddress.ip_network('$CIDR'); print(str(list(n.hosts())[0]))")"

umask 077
wg genkey | tee "$WG_DIR/private.key" | wg pubkey > "$WG_DIR/public.key"
PRIV="$(cat "$WG_DIR/private.key")"
PUB="$(cat "$WG_DIR/public.key")"
PSK="$(wg genpsk)"
echo "$PSK" > "$WG_DIR/psk.key"
chmod 600 "$WG_DIR"/*.key

cat >"$WG_DIR/client.conf" <<EOF
# MSPShield tenant '$TENANT'
[Interface]
PrivateKey = $PRIV
Address    = ${TENANT_IP}/32
DNS        = 1.1.1.1

[Peer]
PublicKey           = $SERVER_PUB
PresharedKey        = $PSK
Endpoint            = ${ENDPOINT_HOST}:${LISTEN_PORT}
AllowedIPs          = ${CIDR}, 10.10.0.0/16
PersistentKeepalive = 25
EOF

# Append tenant to server config
cat >>"$WG_CONF" <<EOF

# tenant: $TENANT · added $(date -Iseconds)
[Peer]
PublicKey    = $PUB
PresharedKey = $PSK
AllowedIPs   = ${TENANT_IP}/32
EOF

# Apply without dropping existing peers
wg syncconf wg0 <(wg-quick strip wg0)

echo "✓ Tenant '$TENANT' provisioned."
echo "  Client config: $WG_DIR/client.conf"
echo "  Transfer to client over a secure channel (Vaultwarden Send)."
