#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────
# awg_bootstrap.sh — первичная инициализация AmneziaWG на bastion/landing-VM
# ─────────────────────────────────────────────────────────────
# RU: Запускается ОДИН РАЗ на свежей VM (mspshield-bastion или
# совмещённая landing+bastion VM), сразу после terraform apply или
# cloud-init. Генерирует приватный/публичный ключи сервера, создаёт
# /etc/amnezia/amneziawg/awg0.conf с адресом 10.10.0.1/16, добавляет
# AmneziaWG-обфускацию (Jc/Jmin/Jmax/S1/S2/H1..H4) и включает
# systemd-сервис awg-quick@awg0.
#
# Почему AmneziaWG, а не WireGuard:
#   РКН-DPI ловит обычный WireGuard handshake. AmneziaWG = форк WG
#   с обфускацией handshake. Drop-in superset, тот же netlink, kernel.
#
# Почему UDP/443:
#   У нас один публичный IP на старте. Caddy занимает TCP/443 (лендинг).
#   AmneziaWG на UDP/443 не конфликтует с Caddy — разные протоколы.
#
# После этого добавлять тенантов — tenant_add.sh.
#
# Идемпотентно: если /etc/amnezia/amneziawg/awg0.conf уже существует —
# выходит без изменений.
# ─────────────────────────────────────────────────────────────
set -euo pipefail
if [[ $EUID -ne 0 ]]; then echo "root only"; exit 1; fi

AWG_DIR="/etc/amnezia/amneziawg"
CONF="$AWG_DIR/awg0.conf"
LISTEN_PORT="${LISTEN_PORT:-443}"
VPN_NET="${VPN_NET:-10.10.0.1/16}"

# Проверка что AmneziaWG установлен (PPA ppa:amnezia/ppa или собран вручную).
if ! command -v awg >/dev/null 2>&1; then
  echo "ERROR: 'awg' not found. Install AmneziaWG first:" >&2
  echo "  sudo add-apt-repository ppa:amnezia/ppa" >&2
  echo "  sudo apt-get update" >&2
  echo "  sudo apt-get install -y amneziawg-dkms amneziawg-tools" >&2
  exit 1
fi

if [[ -f "$CONF" ]]; then
  echo "$CONF already exists; bootstrap aborted."
  exit 0
fi

umask 077
mkdir -p "$AWG_DIR" "$AWG_DIR/tenants"
awg genkey | tee "$AWG_DIR/server_private.key" | awg pubkey > "$AWG_DIR/server_public.key"
chmod 600 "$AWG_DIR"/*.key

# AmneziaWG-обфускация: одинаковый профиль для всех клиентов всего деплоя.
# Меняем ТОЛЬКО если РКН-DPI начнёт ловить с текущими значениями — иначе
# каждое изменение требует обновлять конфиги у всех существующих клиентов.
# Подробнее: https://docs.amnezia.org/documentation/amnezia-wg
AWG_JC="${AWG_JC:-4}"
AWG_JMIN="${AWG_JMIN:-50}"
AWG_JMAX="${AWG_JMAX:-1000}"
AWG_S1="${AWG_S1:-86}"
AWG_S2="${AWG_S2:-574}"
AWG_H1="${AWG_H1:-1779539752}"
AWG_H2="${AWG_H2:-1138729192}"
AWG_H3="${AWG_H3:-2050378563}"
AWG_H4="${AWG_H4:-8345423}"

cat >"$CONF" <<EOF
[Interface]
Address    = ${VPN_NET}
ListenPort = ${LISTEN_PORT}
PrivateKey = $(cat "$AWG_DIR/server_private.key")
SaveConfig = false

# AmneziaWG обфускация (общий профиль для всех peers).
Jc   = ${AWG_JC}
Jmin = ${AWG_JMIN}
Jmax = ${AWG_JMAX}
S1   = ${AWG_S1}
S2   = ${AWG_S2}
H1   = ${AWG_H1}
H2   = ${AWG_H2}
H3   = ${AWG_H3}
H4   = ${AWG_H4}

PostUp   = iptables -A FORWARD -i awg0 -j ACCEPT; iptables -t nat -A POSTROUTING -o eth0 -j MASQUERADE
PostDown = iptables -D FORWARD -i awg0 -j ACCEPT; iptables -t nat -D POSTROUTING -o eth0 -j MASQUERADE
EOF

systemctl enable --now awg-quick@awg0
echo "✓ awg0 is up on UDP/${LISTEN_PORT}."
awg show
