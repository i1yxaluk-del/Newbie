#!/bin/bash
# ═══════════════════════════════════════════════════════════════════
# install_puppet_agent.sh — Установка Puppet Agent на Linux-сервер
# Тариф: Silver+ | ОС: Ubuntu 20.04/22.04, Debian 11/12
# Запуск: sudo bash install_puppet_agent.sh
#
# ЧТО ДЕЛАЕТ СКРИПТ:
#   1. Добавляет репозиторий Puppet Labs (puppet8)
#   2. Устанавливает puppet-agent
#   3. Настраивает /etc/puppetlabs/puppet/puppet.conf
#   4. Запускает первый run — запрос сертификата у Puppet Server
#
# ПОСЛЕ УСТАНОВКИ:
#   Исполнитель должен ПОДПИСАТЬ сертификат на Puppet Server:
#   puppetserver ca sign --certname <CERTNAME>
#
# ЗАЧЕМ PUPPET AGENT:
#   - Каждые 30 мин проверяет что конфиг сервера = эталон
#   - Если кто-то изменил sshd_config — Puppet вернёт обратно
#   - Если отключили node_exporter — Puppet включит обратно
#   - Это называется "desired state" — желаемое состояние
# ═══════════════════════════════════════════════════════════════════
set -euo pipefail

# ── Цвета ───────────────────────────────────────────────────────────
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; NC='\033[0m'
ok()   { echo -e "${GREEN}✓${NC} $*"; }
warn() { echo -e "${YELLOW}!${NC} $*"; }
err()  { echo -e "${RED}✗${NC} $*" >&2; exit 1; }

# ── Параметры ───────────────────────────────────────────────────────
# PUPPET_SERVER — hostname Puppet Server (должен резолвиться через DNS или /etc/hosts)
# CLIENT_CERTNAME — уникальное имя сертификата (обычно hostname сервера)
PUPPET_SERVER="${PUPPET_SERVER:-puppet-server.internal}"
CLIENT_CERTNAME="${CLIENT_CERTNAME:-$(hostname -f)}"

# ── Проверки ────────────────────────────────────────────────────────
[[ $EUID -ne 0 ]] && err "Запустить с sudo: sudo bash $0"

echo "────────────────────────────────────────────"
echo " Puppet Agent installer"
echo " Puppet Server: ${PUPPET_SERVER}"
echo " Certname: ${CLIENT_CERTNAME}"
echo "────────────────────────────────────────────"

# ── Шаг 1: Добавить репозиторий Puppet Labs ────────────────────────
# lsb_release -cs определяет кодовое имя дистрибутива (jammy, focal и т.д.)
CODENAME=$(lsb_release -cs 2>/dev/null || echo "jammy")
warn "Кодовое имя дистрибутива: ${CODENAME}"

wget -qO /tmp/puppet8-release.deb \
    "https://apt.puppetlabs.com/puppet8-release-${CODENAME}.deb"
dpkg -i /tmp/puppet8-release.deb
apt-get update -q
rm /tmp/puppet8-release.deb
ok "Репозиторий Puppet 8 добавлен"

# ── Шаг 2: Установить puppet-agent ─────────────────────────────────
apt-get install -y puppet-agent
ok "puppet-agent установлен"

# ── Шаг 3: Настроить puppet.conf ───────────────────────────────────
# certname — уникальное имя для этого агента
# server   — адрес Puppet Server
# runinterval — как часто агент проверяет конфигурацию (1800с = 30 мин)
# splay   — случайная задержка перед каждым run (чтобы не все агенты сразу)
# usecacheonfailure — использовать последний известный каталог если сервер недоступен
cat > /etc/puppetlabs/puppet/puppet.conf << EOF
[main]
certname = ${CLIENT_CERTNAME}
server   = ${PUPPET_SERVER}

[agent]
runinterval    = 1800    # 30 минут — частота проверок
report         = true    # Отправлять отчёты на Puppet Server
splay          = true    # Случайная задержка (0–300с) перед каждым run
splaylimit     = 300     # Максимум 5 минут случайной задержки
usecacheonfailure = true # Работать по кэшу если сервер недоступен
EOF

ok "puppet.conf настроен"

# ── Шаг 4: Добавить запись в /etc/hosts ────────────────────────────
# Puppet Server должен резолвиться по имени.
# Если есть внутренний DNS — не нужно. Если нет — добавляем в hosts.
if ! grep -q "${PUPPET_SERVER}" /etc/hosts 2>/dev/null; then
    echo "10.9.0.2 ${PUPPET_SERVER}" >> /etc/hosts
    ok "Добавлена запись в /etc/hosts: 10.9.0.2 ${PUPPET_SERVER}"
else
    warn "${PUPPET_SERVER} уже есть в /etc/hosts"
fi

# ── Шаг 5: Первый запуск — запрос сертификата ─────────────────────
echo ""
echo "Запрашиваю сертификат у Puppet Server..."
/opt/puppetlabs/bin/puppet agent --test --waitforcert 60 || true

echo ""
ok "Puppet Agent установлен"
echo ""
echo "⚠️  На Puppet Server (${PUPPET_SERVER}) нужно ПОДПИСАТЬ сертификат:"
echo "  puppetserver ca sign --certname ${CLIENT_CERTNAME}"
echo ""
echo "После подписания проверить:"
echo "  /opt/puppetlabs/bin/puppet agent --test --verbose"
echo ""
echo "Статус агента:"
echo "  systemctl status puppet"
echo "  /opt/puppetlabs/bin/puppet agent --configprint server"
