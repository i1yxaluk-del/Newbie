#!/bin/bash
# ═══════════════════════════════════════════════════════════════════
# install_promtail.sh — Установка Promtail на Linux-сервер клиента
# Тариф: Silver+ | ОС: Ubuntu 20.04/22.04, Debian 11/12
# Запуск: sudo bash install_promtail.sh
#
# ЧТО ДЕЛАЕТ СКРИПТ:
#   1. Скачивает бинарник Promtail из GitHub
#   2. Создаёт конфиг /etc/promtail/config.yml
#   3. Создаёт systemd service для автозапуска
#   4. Запускает и проверяет
#
# ПЕРЕД ЗАПУСКОМ:
#   - AmneziaWG VPN уже настроен (см. SOP_client_bronze.md §3)
#   - Получить от Исполнителя: LOKI_URL (обычно http://10.9.0.1:3100)
#   - Получить от Исполнителя: CLIENT_SLUG (идентификатор клиента)
#
# КАК ПРОВЕРИТЬ ПОСЛЕ:
#   systemctl status promtail
#   curl http://localhost:9080/ready
#   В Grafana (у Исполнителя): Explore → {client="YOUR_SLUG"}
# ═══════════════════════════════════════════════════════════════════
set -euo pipefail

# ── Цвета для вывода ───────────────────────────────────────────────
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; NC='\033[0m'
ok()   { echo -e "${GREEN}✓${NC} $*"; }
warn() { echo -e "${YELLOW}!${NC} $*"; }
err()  { echo -e "${RED}✗${NC} $*" >&2; exit 1; }

# ── Параметры (можно переопределить через env) ─────────────────────
# PROMTAIL_VERSION — версия Promtail (совпадает с Loki)
# LOKI_URL        — адрес Loki ЧЕРЕЗ VPN (IP Bastion)
# CLIENT_SLUG     — короткий идентификатор клиента (латиница, без пробелов)
# CLIENT_NAME     — полное название клиента (для меток)
PROMTAIL_VERSION="${PROMTAIL_VERSION:-3.0.0}"
LOKI_URL="${LOKI_URL:-http://10.9.0.1:3100}"
CLIENT_SLUG="${CLIENT_SLUG:-unknown}"
CLIENT_NAME="${CLIENT_NAME:-Unknown Client}"
HOSTNAME_SHORT=$(hostname -s)

# ── Проверки ────────────────────────────────────────────────────────
[[ $EUID -ne 0 ]] && err "Запустить с sudo: sudo bash $0"
command -v curl &>/dev/null || apt-get install -y curl -qq
command -v unzip &>/dev/null || apt-get install -y unzip -qq

echo "────────────────────────────────────────────"
echo " Promtail installer v${PROMTAIL_VERSION}"
echo " Loki: ${LOKI_URL}"
echo " Client: ${CLIENT_SLUG} (${CLIENT_NAME})"
echo "────────────────────────────────────────────"

# ── Скачать Promtail ────────────────────────────────────────────────
ARCH="linux-amd64"
URL="https://github.com/grafana/loki/releases/download/v${PROMTAIL_VERSION}/promtail-${ARCH}.zip"
TMP=$(mktemp -d)
trap 'rm -rf "$TMP"' EXIT

echo "Скачиваю promtail v${PROMTAIL_VERSION}..."
curl -sSL "$URL" -o "${TMP}/promtail.zip"
unzip -q "${TMP}/promtail.zip" -d "${TMP}/"
install -m 0755 "${TMP}/promtail-${ARCH}" /usr/local/bin/promtail
ok "Promtail бинарник установлен в /usr/local/bin/promtail"

# ── Конфигурация ────────────────────────────────────────────────────
mkdir -p /etc/promtail
mkdir -p /var/lib/promtail

cat > /etc/promtail/config.yml << EOF
# ════════════════════════════════════════════════════════════════
# Promtail config — собирает логи и отправляет в Loki
# Редактировать: /etc/promtail/config.yml
# После изменения: systemctl restart promtail
# ════════════════════════════════════════════════════════════════

server:
  http_listen_port: 9080      # Порт для проверки готовности
  grpc_listen_port: 0         # gRPC отключен (не нужен)
  log_level: warn

positions:
  # positions.yaml — файл, где Promtail запоминает
  # ДО КАКОГО МЕСТА уже прочитал каждый лог-файл.
  # Если удалить — Promtail начнёт читать логи с начала!
  filename: /var/lib/promtail/positions.yaml

clients:
  - url: ${LOKI_URL}/loki/api/v1/push
    tenant_id: ${CLIENT_SLUG}
    # Настройки повторных попыток при недоступности Loki
    backoff_config:
      min_period: 500ms
      max_period: 5m
      max_retries: 10

scrape_configs:

  # ── Системные логи (/var/log/syslog) ───────────────────────────
  - job_name: system
    static_configs:
      - targets: [localhost]
        labels:
          job: varlog
          host: "${HOSTNAME_SHORT}"
          client: "${CLIENT_SLUG}"
          client_name: "${CLIENT_NAME}"
          __path__: /var/log/syslog
    # Multiline — объединять многострочные записи лога
    pipeline_stages:
      - multiline:
          firstline: '^\d{4}-\d{2}-\d{2}'   # Строка начинается с даты
          max_wait_time: 3s

  # ── Логи аутентификации (SSH входы, sudo) ──────────────────────
  # КРИТИЧНО: здесь видны брутфорс-атаки, sudo-команды
  - job_name: auth
    static_configs:
      - targets: [localhost]
        labels:
          job: auth
          host: "${HOSTNAME_SHORT}"
          client: "${CLIENT_SLUG}"
          __path__: /var/log/auth.log

  # ── Логи Nginx (если установлен) ───────────────────────────────
  # Раскомментировать если на сервере есть Nginx
  # - job_name: nginx
  #   static_configs:
  #     - targets: [localhost]
  #       labels:
  #         job: nginx
  #         host: "${HOSTNAME_SHORT}"
  #         client: "${CLIENT_SLUG}"
  #         __path__: /var/log/nginx/*.log
  #   pipeline_stages:
  #     - match:
  #         selector: '{job="nginx"}'
  #         stages:
  #           - regex:
  #               expression: '^(?P<remote_addr>\S+) - (?P<remote_user>\S+) \[(?P<time_local>[^\]]+)\] "(?P<method>\S+) (?P<request>[^"]+)" (?P<status>\d+) (?P<body_bytes_sent>\d+)'
  #           - labels:
  #               status:
  #               method:

  # ── Логи PostgreSQL (если установлен) ──────────────────────────
  # Раскомментировать если на сервере есть PostgreSQL
  # - job_name: postgresql
  #   static_configs:
  #     - targets: [localhost]
  #       labels:
  #         job: postgresql
  #         host: "${HOSTNAME_SHORT}"
  #         client: "${CLIENT_SLUG}"
  #         __path__: /var/log/postgresql/*.log
EOF

ok "Конфигурация создана: /etc/promtail/config.yml"

# ── Права на директорию positions ──────────────────────────────────
chown nobody:nogroup /var/lib/promtail 2>/dev/null || true

# ── Systemd unit ────────────────────────────────────────────────────
cat > /etc/systemd/system/promtail.service << 'EOF'
[Unit]
Description=Promtail Log Shipper
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
ExecStart=/usr/local/bin/promtail -config.file=/etc/promtail/config.yml
Restart=on-failure
RestartSec=5s
StandardOutput=journal
StandardError=journal
SyslogIdentifier=promtail

[Install]
WantedBy=multi-user.target
EOF

ok "Systemd unit создан"

# ── UFW (если используется) ─────────────────────────────────────────
# Promtail не открывает порты наружу — он сам отправляет данные в Loki
# Но порт 9080 нужен для проверки /ready (из VPN):
if command -v ufw &>/dev/null; then
    ufw allow from 10.9.0.0/24 to any port 9080 proto tcp \
        comment "Promtail ready from MSP VPN" 2>/dev/null || warn "UFW: добавить вручную"
    ok "UFW: порт 9080 открыт для VPN"
fi

# ── Запуск ──────────────────────────────────────────────────────────
systemctl daemon-reload
systemctl enable --now promtail
sleep 3

# ── Проверка ────────────────────────────────────────────────────────
if systemctl is-active --quiet promtail; then
    ok "Promtail запущен и работает"
else
    err "Promtail не запустился. Проверьте: journalctl -u promtail -n 50"
fi

# Проверить что Promtail готов отправлять логи
if curl -s --max-time 5 http://localhost:9080/ready | grep -q "ready"; then
    ok "Promtail готов к отправке логов в Loki"
else
    warn "Promtail /ready не отвечает — возможно Loki недоступен"
    warn "Проверить VPN: ping 10.9.0.1"
fi

echo ""
echo "────────────────────────────────────────────"
echo " Установка завершена!"
echo " Проверка:  curl http://localhost:9080/ready"
echo " Логи:      journalctl -u promtail -f"
echo " Конфиг:    /etc/promtail/config.yml"
echo ""
echo " В Grafana (Исполнитель):"
echo "   Explore → {client=\"${CLIENT_SLUG}\"}"
echo "────────────────────────────────────────────"
