#!/bin/bash
# ═══════════════════════════════════════════════════════════════════
# install_wazuh_agent.sh — Установка Wazuh Agent (Linux)
# Тариф: Gold | ОС: Ubuntu 20.04/22.04, Debian 11/12
# Запуск: sudo bash install_wazuh_agent.sh
#
# Переменные окружения:
#   WAZUH_MANAGER  — IP Wazuh Manager (по умолч. 10.9.0.3)
#   WAZUH_AGENT_NAME — имя агента (по умолч. hostname)
# ═══════════════════════════════════════════════════════════════════
set -euo pipefail

G='\033[0;32m'; Y='\033[1;33m'; R='\033[0;31m'; C='\033[0;36m'; NC='\033[0m'
ok()   { echo -e "${G}✓${NC} $*"; }
warn() { echo -e "${Y}!${NC} $*"; }
err()  { echo -e "${R}✗${NC} $*"; exit 1; }
info() { echo -e "${C}→${NC} $*"; }

[[ $EUID -ne 0 ]] && err "Запустить с sudo"

WAZUH_MANAGER="${WAZUH_MANAGER:-10.9.0.3}"
WAZUH_VERSION="${WAZUH_VERSION:-4.7.5}"
AGENT_NAME="${WAZUH_AGENT_NAME:-$(hostname -s)}"
AGENT_GROUP="${WAZUH_AGENT_GROUP:-default}"

echo "════════════════════════════════════════════"
echo " Wazuh Agent v${WAZUH_VERSION} installer"
echo " Manager: ${WAZUH_MANAGER}"
echo " Agent:   ${AGENT_NAME}"
echo "════════════════════════════════════════════"

# ── Проверить доступность Manager ─────────────────────────────────
info "Проверяю доступность Wazuh Manager..."
if ! curl -sf --max-time 5 "https://${WAZUH_MANAGER}:55000" -k &>/dev/null; then
    warn "Manager ${WAZUH_MANAGER}:55000 недоступен. Убедитесь, что VPN активен."
    warn "Продолжаю установку — агент подключится после доступности Manager."
fi

# ── Добавить репозиторий ──────────────────────────────────────────
info "Добавляю репозиторий Wazuh..."

# GPG ключ
if ! [[ -f /usr/share/keyrings/wazuh.gpg ]]; then
    curl -sS https://packages.wazuh.com/key/GPG-KEY-WAZUH \
        | gpg --no-default-keyring \
              --keyring gnupg-ring:/usr/share/keyrings/wazuh.gpg \
              --import
    chmod 644 /usr/share/keyrings/wazuh.gpg
fi

# Репозиторий
echo "deb [signed-by=/usr/share/keyrings/wazuh.gpg] https://packages.wazuh.com/4.x/apt/ stable main" \
    | tee /etc/apt/sources.list.d/wazuh.list > /dev/null

apt-get update -q
ok "Репозиторий добавлен"

# ── Установить Wazuh Agent ────────────────────────────────────────
info "Устанавливаю wazuh-agent..."
WAZUH_MANAGER="${WAZUH_MANAGER}" \
WAZUH_AGENT_NAME="${AGENT_NAME}" \
WAZUH_AGENT_GROUP="${AGENT_GROUP}" \
    apt-get install -y "wazuh-agent=${WAZUH_VERSION}-*"
ok "Wazuh Agent установлен"

# ── Настройка FIM (File Integrity Monitoring) ─────────────────────
info "Настраиваю FIM..."
cat > /var/ossec/etc/ossec.conf.d/fim_custom.xml << 'EOF'
<!-- MSPShield: кастомные FIM правила -->
<ossec_config>
  <syscheck>
    <disabled>no</disabled>
    <frequency>43200</frequency>

    <!-- КРИТИЧНЫЕ СИСТЕМНЫЕ ФАЙЛЫ -->
    <directories check_all="yes" report_changes="yes">/etc</directories>
    <directories check_all="yes">/bin</directories>
    <directories check_all="yes">/sbin</directories>
    <directories check_all="yes">/usr/bin</directories>
    <directories check_all="yes">/usr/sbin</directories>
    <directories check_all="yes" report_changes="yes">/var/www</directories>
    <directories check_all="yes">/root/.ssh</directories>
    <directories check_all="yes">/home/*/.ssh</directories>

    <!-- MSP-специфика -->
    <directories check_all="yes">/opt/restic-scripts</directories>
    <directories check_all="yes">/etc/wireguard</directories>

    <!-- ИСКЛЮЧЕНИЯ -->
    <ignore>/etc/mtab</ignore>
    <ignore>/etc/mnttab</ignore>
    <ignore>/etc/hosts.deny</ignore>
    <ignore>/etc/mail/statistics</ignore>
    <ignore>/etc/random-seed</ignore>
    <ignore>/etc/adjtime</ignore>
    <ignore type="sregex">.log$</ignore>
    <ignore type="sregex">.tmp$</ignore>
    <ignore type="sregex">.swp$</ignore>
  </syscheck>

  <!-- Rootcheck -->
  <rootcheck>
    <disabled>no</disabled>
    <check_files>yes</check_files>
    <check_trojans>yes</check_trojans>
    <check_dev>yes</check_dev>
    <check_sys>yes</check_sys>
    <check_pids>yes</check_pids>
    <check_ports>yes</check_ports>
    <check_if>yes</check_if>
  </rootcheck>

  <!-- Vulnerability Detector -->
  <wodle name="vulnerability-detector">
    <disabled>no</disabled>
    <interval>1d</interval>
    <run_on_start>yes</run_on_start>
    <provider name="canonical">
      <enabled>yes</enabled>
      <os>focal</os>
      <os>jammy</os>
      <update_interval>1h</update_interval>
    </provider>
    <provider name="debian">
      <enabled>yes</enabled>
      <os>bullseye</os>
      <os>bookworm</os>
      <update_interval>1h</update_interval>
    </provider>
  </wodle>
</ossec_config>
EOF
ok "FIM конфигурация создана"

# ── Настроить Manager IP ──────────────────────────────────────────
sed -i "s|<address>MANAGER_IP</address>|<address>${WAZUH_MANAGER}</address>|g" \
    /var/ossec/etc/ossec.conf
ok "Manager IP установлен: ${WAZUH_MANAGER}"

# ── UFW: разрешить соединение с Manager ───────────────────────────
if command -v ufw &>/dev/null; then
    ufw allow out to "${WAZUH_MANAGER}" port 1514 proto tcp comment "Wazuh Manager"
    ufw allow out to "${WAZUH_MANAGER}" port 1514 proto udp comment "Wazuh Manager UDP"
    ufw allow out to "${WAZUH_MANAGER}" port 1515 proto tcp comment "Wazuh enrollment"
    ok "UFW: разрешены порты 1514, 1515 → ${WAZUH_MANAGER}"
fi

# ── Запустить ─────────────────────────────────────────────────────
systemctl daemon-reload
systemctl enable --now wazuh-agent
sleep 5

# ── Проверка ──────────────────────────────────────────────────────
if /var/ossec/bin/wazuh-control status 2>/dev/null | grep -q "running"; then
    ok "Wazuh Agent запущен"
else
    warn "Wazuh Agent не запустился полностью. Проверьте: systemctl status wazuh-agent"
fi

echo ""
echo "════════════════════════════════════════════"
echo " ✅ Wazuh Agent установлен!"
echo ""
echo " Проверить регистрацию на Manager:"
echo "   ssh executor-vm"
echo "   docker exec wazuh-manager /var/ossec/bin/agent_control -l | grep ${AGENT_NAME}"
echo ""
echo " Логи агента:"
echo "   tail -f /var/ossec/logs/ossec.log"
echo "   journalctl -u wazuh-agent -f"
echo "════════════════════════════════════════════"
