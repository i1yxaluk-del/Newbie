#!/bin/bash
# ═══════════════════════════════════════════════════════════════════
# install_linux.sh — Установка node_exporter на Linux-сервер клиента
# Тариф: Bronze+ | ОС: Ubuntu 20.04/22.04, Debian 11/12
# Запуск: sudo bash install_linux.sh
# ═══════════════════════════════════════════════════════════════════
set -euo pipefail

# ── Цвета для вывода ──────────────────────────────────────────────
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; NC='\033[0m'
ok()   { echo -e "${GREEN}✓${NC} $*"; }
warn() { echo -e "${YELLOW}!${NC} $*"; }
err()  { echo -e "${RED}✗${NC} $*" >&2; exit 1; }

# ── Параметры ─────────────────────────────────────────────────────
NODE_EXPORTER_VERSION="${NODE_EXPORTER_VERSION:-1.7.0}"
LISTEN_PORT="${LISTEN_PORT:-9100}"
VPN_SUBNET="${VPN_SUBNET:-10.9.0.0/24}"
ARCH="amd64"
INSTALL_DIR="/usr/local/bin"
TEXTFILE_DIR="/var/lib/node_exporter/textfile_collector"

# ── Проверки ──────────────────────────────────────────────────────
[[ $EUID -ne 0 ]] && err "Запустить с sudo"
command -v curl &>/dev/null || apt-get install -y curl -qq

echo "────────────────────────────────────────────"
echo " node_exporter installer v${NODE_EXPORTER_VERSION}"
echo " Port: ${LISTEN_PORT} | VPN: ${VPN_SUBNET}"
echo "────────────────────────────────────────────"

# ── Пользователь ──────────────────────────────────────────────────
if ! id node_exporter &>/dev/null; then
    useradd --system --no-create-home --shell /sbin/nologin node_exporter
    ok "Создан пользователь node_exporter"
fi

# ── Скачать и установить ─────────────────────────────────────────
TARBALL="node_exporter-${NODE_EXPORTER_VERSION}.linux-${ARCH}.tar.gz"
URL="https://github.com/prometheus/node_exporter/releases/download/v${NODE_EXPORTER_VERSION}/${TARBALL}"
TMP_DIR=$(mktemp -d)
trap 'rm -rf "$TMP_DIR"' EXIT

echo "Скачиваю ${URL}..."
curl -sSL "${URL}" -o "${TMP_DIR}/${TARBALL}"
tar -xzf "${TMP_DIR}/${TARBALL}" -C "${TMP_DIR}"
install -m 0755 "${TMP_DIR}/node_exporter-${NODE_EXPORTER_VERSION}.linux-${ARCH}/node_exporter" "${INSTALL_DIR}/node_exporter"
ok "node_exporter ${NODE_EXPORTER_VERSION} установлен в ${INSTALL_DIR}"

# ── Директория textfile ───────────────────────────────────────────
mkdir -p "${TEXTFILE_DIR}"
chown node_exporter:node_exporter "${TEXTFILE_DIR}"
chmod 755 "${TEXTFILE_DIR}"
ok "Директория textfile_collector создана: ${TEXTFILE_DIR}"

# ── Systemd unit ──────────────────────────────────────────────────
cat > /etc/systemd/system/node_exporter.service << EOF
[Unit]
Description=Prometheus Node Exporter
Documentation=https://github.com/prometheus/node_exporter
After=network.target
Wants=network.target

[Service]
Type=simple
User=node_exporter
Group=node_exporter
ExecStart=${INSTALL_DIR}/node_exporter \\
    --web.listen-address=:${LISTEN_PORT} \\
    --web.telemetry-path=/metrics \\
    --collector.filesystem.mount-points-exclude=^/(sys|proc|dev|host|etc)(\\$\\$|/) \\
    --collector.textfile.directory=${TEXTFILE_DIR} \\
    --no-collector.ipvs \\
    --no-collector.arp
Restart=on-failure
RestartSec=5s
NoNewPrivileges=true
ProtectSystem=strict
ProtectHome=read-only
PrivateTmp=true
ReadWritePaths=${TEXTFILE_DIR}

[Install]
WantedBy=multi-user.target
EOF
ok "Systemd unit создан"

# ── Firewall ──────────────────────────────────────────────────────
if command -v ufw &>/dev/null; then
    # Удалить старое правило (если есть), добавить новое
    ufw delete allow "${LISTEN_PORT}/tcp" 2>/dev/null || true
    ufw allow from "${VPN_SUBNET}" to any port "${LISTEN_PORT}" proto tcp \
        comment "node_exporter from MSP VPN" 2>/dev/null || warn "UFW: добавить вручную"
    ok "UFW: порт ${LISTEN_PORT} открыт для ${VPN_SUBNET}"
elif command -v iptables &>/dev/null; then
    iptables -I INPUT -s "${VPN_SUBNET}" -p tcp --dport "${LISTEN_PORT}" -j ACCEPT 2>/dev/null || true
    warn "iptables: правило добавлено (сохраните через netfilter-persistent)"
else
    warn "Firewall не обнаружен. Откройте порт ${LISTEN_PORT} для ${VPN_SUBNET} вручную"
fi

# ── Запуск ────────────────────────────────────────────────────────
systemctl daemon-reload
systemctl enable node_exporter
systemctl restart node_exporter
sleep 2

# ── Проверка ──────────────────────────────────────────────────────
if systemctl is-active --quiet node_exporter; then
    METRIC_COUNT=$(curl -s http://localhost:"${LISTEN_PORT}"/metrics 2>/dev/null | grep -c "^[^#]" || echo 0)
    ok "node_exporter запущен, отдаёт ${METRIC_COUNT} метрик"
else
    err "node_exporter не запустился. Проверьте: journalctl -u node_exporter -n 50"
fi

echo ""
echo "────────────────────────────────────────────"
echo " Установка завершена!"
echo " Метрики: http://$(hostname -I | awk '{print $1}'):${LISTEN_PORT}/metrics"
echo " Из VPN:  http://$(ip addr show awg0-msp 2>/dev/null | grep 'inet ' | awk '{print $2}' | cut -d/ -f1):${LISTEN_PORT}/metrics"
echo ""
echo " Следующий шаг:"
echo " Сообщите Исполнителю VPN-IP для добавления в Prometheus"
echo "────────────────────────────────────────────"
