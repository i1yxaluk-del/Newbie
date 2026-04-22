#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────
# wg_bootstrap.sh — первичная инициализация WireGuard на bastion
# ─────────────────────────────────────────────────────────────
# RU: Запускается ОДИН РАЗ на свежем bastion'е (mspshield-bastion),
# сразу после terraform apply. Генерирует приватный и публичный
# ключи сервера, создаёт /etc/wireguard/wg0.conf с адресом
# 10.10.0.1/16 и включает systemd-сервис wg-quick@wg0.
#
# После этого добавлять тенантов — tenant_add.sh.
#
# Идемпотентно: если /etc/wireguard/wg0.conf уже существует — выходит.
# ─────────────────────────────────────────────────────────────
set -euo pipefail
if [[ $EUID -ne 0 ]]; then echo "root only"; exit 1; fi

WG="/etc/wireguard"
CONF="$WG/wg0.conf"
if [[ -f "$CONF" ]]; then
  echo "$CONF already exists; bootstrap aborted."
  exit 0
fi

umask 077
mkdir -p "$WG" "$WG/tenants"
wg genkey | tee "$WG/server_private.key" | wg pubkey > "$WG/server_public.key"
chmod 600 "$WG"/*.key

cat >"$CONF" <<EOF
[Interface]
Address    = 10.10.0.1/16
ListenPort = 51820
PrivateKey = $(cat "$WG/server_private.key")
SaveConfig = false

PostUp   = iptables -A FORWARD -i wg0 -j ACCEPT; iptables -t nat -A POSTROUTING -o eth0 -j MASQUERADE
PostDown = iptables -D FORWARD -i wg0 -j ACCEPT; iptables -t nat -D POSTROUTING -o eth0 -j MASQUERADE
EOF

systemctl enable --now wg-quick@wg0
echo "✓ wg0 is up."
wg show
