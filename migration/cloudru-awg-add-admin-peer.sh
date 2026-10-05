#!/usr/bin/env bash
# Добавляет peer админской станции (10.9.0.2) с СУЩЕСТВУЮЩИМ ключом из awg-admin.conf,
# чтобы клиентский конфиг менялся только в части Endpoint/PublicKey сервера.
set -uo pipefail
CLIENT_PRIV="wLwgaGWKDWdt9ZCl84onnFzq5MRjzU9jDRartJlPzVc="
CLIENT_PUB=$(printf '%s' "$CLIENT_PRIV" | awg pubkey)
PSK="k/fZNtP4Upy8dWDmWZ+9hJLJUB6/xEmo7D+KACNaAus="
CONF=/etc/amnezia/amneziawg/awg0.conf

echo "CLIENT_PUB=$CLIENT_PUB"
if grep -qF "$CLIENT_PUB" "$CONF"; then
  echo "peer уже присутствует"
else
  cat >>"$CONF" <<EOF

# admin workstation (10.9.0.2) — $(date -Iseconds)
[Peer]
PublicKey    = $CLIENT_PUB
PresharedKey = $PSK
AllowedIPs   = 10.9.0.2/32
EOF
  awg syncconf awg0 <(awg-quick strip awg0)
  echo "peer добавлен"
fi

echo "=== ufw ==="
ufw allow 443/udp comment 'AmneziaWG VPN' || true
ufw allow from 10.9.0.0/24 to any port 22 proto tcp comment 'SSH via AmneziaWG' || true
ufw status verbose | head -20

echo "=== awg show ==="
awg show
echo "=== awg0 addr ==="
ip -brief addr show awg0
echo DONE
