# SOP — Bronze · Сторона ИСПОЛНИТЕЛЯ
# Версия 2.0 | Апрель 2026
# ═══════════════════════════════════════════════════════════════════
#
# Документ описывает ВСЁ, что разворачивается на стороне ИСПОЛНИТЕЛЯ
# для обеспечения тарифа Bronze (и является фундаментом для Silver/Gold).
#
# Всё работает в Yandex Cloud (ru-central1), единая VM или разнесено.
# ═══════════════════════════════════════════════════════════════════

## СОДЕРЖАНИЕ

1. Архитектура Исполнителя
2. Развёртывание VM в Yandex Cloud
3. Базовая настройка ОС
4. WireGuard Bastion Server
5. Docker Compose — Мониторинг стек
6. Добавление клиента (скрипт)
7. Еженедельный отчёт
8. Обслуживание и мониторинг стека

---

## 1. АРХИТЕКТУРА

```
YANDEX CLOUD ru-central1-a
┌───────────────────────────────────────────────────────────────┐
│ msp-all-in-one VM (для старта: burst 5%, 2vCPU, 4GB, 40GB)  │
│                                                               │
│ ┌─────────────────────────────────────────────────────────┐  │
│ │ Docker Compose (profile: monitoring)                    │  │
│ │ ├── Prometheus    :9090  ← scrapes client exporters     │  │
│ │ ├── Alertmanager  :9093  ← routes alerts to Telegram    │  │
│ │ ├── Grafana       :3000  ← dashboards (не открыт наружу)│  │
│ │ ├── node-exporter :9100  ← метрики самой VM             │  │
│ │ └── cAdvisor      :8080  ← метрики Docker               │  │
│ └─────────────────────────────────────────────────────────┘  │
│                                                               │
│ На хосте (bare-metal):                                       │
│ ├── WireGuard :51820/udp   ← VPN для клиентов               │
│ ├── nftables               ← firewall                        │
│ ├── fail2ban               ← защита SSH                      │
│ └── SSH :22                ← только из доверенных IP         │
└───────────────────────────────────────────────────────────────┘
         ↑            ↑            ↑
    10.9.0.10    10.9.0.20    10.9.0.30     ← Клиенты через VPN
   (Bronze-1)  (Bronze-2)  (Bronze-3)

Yandex Object Storage:
└── backup-CLIENT_NAME/   ← restic репозитории клиентов
```

**Сетевая схема:**
```
Internet:51820 → WireGuard → 10.9.0.0/24 (внутренняя VPN-сеть)
                               ↕
                         Prometheus scrapes
                         9100 (Linux) / 9182 (Windows)
```

---

## 2. РАЗВЁРТЫВАНИЕ VM В YANDEX CLOUD

### 2.1 Подготовка

```bash
# Установить YC CLI
curl -sSL https://storage.yandexcloud.net/yandexcloud-yc/install.sh | bash
source ~/.bashrc
yc init

# Проверить
yc config list
```

### 2.2 Создать VM (all-in-one для старта)

```bash
# Параметры VM:
# - core-fraction 5 = burst VM (в 5-10 раз дешевле!)
#   достаточно для Bronze с <5 клиентами
# - preemptible = прерываемая, на 70% дешевле
#   НЕ подходит для production, только для теста
# Для production: убрать --preemptible и --core-fraction 5

# Получить список образов
yc compute image list --folder-id standard-images | grep ubuntu-22

# Создать VM
yc compute instance create \
  --name msp-monitoring \
  --zone ru-central1-a \
  --network-interface subnet-name=default-vpc,nat-ip-version=ipv4 \
  --create-boot-disk \
    image-family=ubuntu-2204-lts,\
    size=40,\
    type=network-ssd,\
    auto-delete=true \
  --cores 2 \
  --core-fraction 20 \
  --memory 4 \
  --ssh-key ~/.ssh/id_ed25519.pub \
  --metadata serial-port-enable=1

# Получить IP
MSP_IP=$(yc compute instance get msp-monitoring --format json | jq -r '.network_interfaces[0].primary_v4_address.one_to_one_nat.address')
echo "MSP VM IP: $MSP_IP"
```

### 2.3 Создать S3-bucket и ключи для бэкапов

```bash
# Сервисный аккаунт для бэкапов
yc iam service-account create --name msp-backup-sa

# Назначить роль на папку
FOLDER_ID=$(yc config get folder-id)
SA_ID=$(yc iam service-account get msp-backup-sa --format json | jq -r '.id')

yc resource-manager folder add-access-binding $FOLDER_ID \
  --role storage.editor \
  --subject serviceAccount:$SA_ID

# Создать статический ключ (S3-совместимый)
yc iam access-key create --service-account-name msp-backup-sa \
  --format json | tee ~/msp-s3-keys.json

# Посмотреть ключи
cat ~/msp-s3-keys.json | jq '{key_id: .access_key.key_id, secret: .secret}'

# Создать bucket для клиента (при онбординге)
create_client_bucket() {
    local CLIENT=$1
    yc storage bucket create \
        --name "backup-${CLIENT}" \
        --default-storage-class standard \
        --max-size 107374182400  # 100 GB
    echo "Bucket создан: backup-${CLIENT}"
}
# Пример: create_client_bucket "company-name"
```

---

## 3. БАЗОВАЯ НАСТРОЙКА ОС

```bash
# Подключиться
ssh ubuntu@$MSP_IP

# ── Обновление ────────────────────────────────────────────────────
sudo apt update && sudo apt upgrade -y
sudo apt install -y \
    curl wget git nano htop iotop \
    chrony ufw fail2ban jq \
    wireguard wireguard-tools

# ── Часовой пояс ──────────────────────────────────────────────────
sudo timedatectl set-timezone Europe/Moscow
sudo systemctl enable --now chrony
chronyc tracking

# ── SSH Hardening ──────────────────────────────────────────────────
sudo sed -i 's/^#*PermitRootLogin.*/PermitRootLogin no/' /etc/ssh/sshd_config
sudo sed -i 's/^#*PasswordAuthentication.*/PasswordAuthentication no/' /etc/ssh/sshd_config
sudo sed -i 's/^#*MaxAuthTries.*/MaxAuthTries 3/' /etc/ssh/sshd_config
sudo systemctl restart sshd

# ── fail2ban ──────────────────────────────────────────────────────
sudo tee /etc/fail2ban/jail.local << 'EOF'
[DEFAULT]
bantime  = 3600
findtime = 600
maxretry = 5

[sshd]
enabled = true
port    = ssh
logpath = %(sshd_log)s
backend = %(syslog_backend)s
EOF
sudo systemctl enable --now fail2ban

# ── UFW Firewall ──────────────────────────────────────────────────
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow 22/tcp comment "SSH"
sudo ufw allow 51820/udp comment "WireGuard VPN"
# Grafana только через VPN — НЕ открывать наружу!
# sudo ufw allow 3000/tcp  ← НЕ ДЕЛАТЬ!
sudo ufw --force enable
sudo ufw status verbose

# ── Docker ────────────────────────────────────────────────────────
curl -fsSL https://get.docker.com | sudo sh
sudo usermod -aG docker $USER
newgrp docker
docker --version
```

---

## 4. WIREGUARD BASTION SERVER

### 4.1 Генерация ключей сервера

```bash
cd /etc/wireguard

# Генерация
sudo wg genkey | sudo tee server_private.key | sudo wg pubkey | sudo tee server_public.key
sudo chmod 600 server_private.key

# Показать публичный ключ (нужен клиентам)
echo "=== BASTION PUBLIC KEY ==="
sudo cat server_public.key

# Сохранить в переменную
SERVER_PUBKEY=$(sudo cat server_public.key)
```

### 4.2 Конфигурация WireGuard сервера

```bash
sudo tee /etc/wireguard/wg0.conf << EOF
[Interface]
PrivateKey = $(sudo cat /etc/wireguard/server_private.key)
Address = 10.9.0.1/24
ListenPort = 51820
SaveConfig = false
PostUp   = iptables -A FORWARD -i %i -j ACCEPT; iptables -t nat -A POSTROUTING -o eth0 -j MASQUERADE
PostDown = iptables -D FORWARD -i %i -j ACCEPT; iptables -t nat -D POSTROUTING -o eth0 -j MASQUERADE

# === PEERS КЛИЕНТОВ (добавлять при онбординге) ===
# [Peer]
# PublicKey = <CLIENT_PUBLIC_KEY>
# AllowedIPs = 10.9.0.10/32
# PresharedKey = <OPTIONAL_PSK>
EOF
sudo chmod 600 /etc/wireguard/wg0.conf

# Включить IP forwarding
echo "net.ipv4.ip_forward=1" | sudo tee /etc/sysctl.d/99-wireguard.conf
sudo sysctl -p /etc/sysctl.d/99-wireguard.conf

# Запустить
sudo systemctl enable --now wg-quick@wg0
sudo wg show wg0
```

### 4.3 Скрипт добавления клиента (add_peer.sh)

```bash
sudo tee /usr/local/bin/add_vpn_peer.sh << 'SCRIPT'
#!/bin/bash
# add_vpn_peer.sh CLIENT_SLUG VPN_IP CLIENT_PUBKEY
# Пример: add_vpn_peer.sh company1 10.9.0.10 "abc123..."

set -euo pipefail

CLIENT="${1:?Usage: $0 CLIENT_SLUG VPN_IP CLIENT_PUBKEY}"
VPN_IP="${2:?}"
CLIENT_PUBKEY="${3:?}"

CONFIG="/etc/wireguard/wg0.conf"

# Добавить peer в конфиг
cat >> "$CONFIG" << EOF

# === ${CLIENT} ===
[Peer]
PublicKey = ${CLIENT_PUBKEY}
AllowedIPs = ${VPN_IP}/32
EOF

# Применить без перезапуска
wg set wg0 peer "$CLIENT_PUBKEY" allowed-ips "${VPN_IP}/32"

echo "✓ Peer добавлен: ${CLIENT} → ${VPN_IP}"
echo "  Проверка: wg show wg0"
SCRIPT
sudo chmod +x /usr/local/bin/add_vpn_peer.sh
```

---

## 5. DOCKER COMPOSE — МОНИТОРИНГ СТЕК

### 5.1 Создать структуру

```bash
sudo mkdir -p /opt/monitoring/{prometheus/rules,alertmanager,grafana/provisioning/{datasources,dashboards},loki}
sudo chown -R ubuntu:ubuntu /opt/monitoring
cd /opt/monitoring
```

### 5.2 .env файл

```bash
cat > /opt/monitoring/.env << 'EOF'
# ════════════════════════════════════════════
# MSP Monitoring Stack — Environment Variables
# ЗАМЕНИТЬ ВСЕ ЗНАЧЕНИЯ ПЕРЕД ЗАПУСКОМ!
# ════════════════════════════════════════════

# Версии образов (зафиксированные для стабильности)
PROMETHEUS_VERSION=v2.51.0
ALERTMANAGER_VERSION=v0.27.0
GRAFANA_VERSION=10.4.2
NODE_EXPORTER_VERSION=v1.7.0
CADVISOR_VERSION=v0.49.1
LOKI_VERSION=3.0.0
PROMTAIL_VERSION=3.0.0

# Grafana — генерировать пароль автоматически!
# НЕ писать пароль вручную — использовать: openssl rand -base64 32
GRAFANA_ADMIN_USER=admin
GRAFANA_ADMIN_PASSWORD=$(openssl rand -base64 32)

# Telegram для алертов
# Создать бота: @BotFather → /newbot
# Получить chat_id: написать боту → curl https://api.telegram.org/bot<TOKEN>/getUpdates
TELEGRAM_BOT_TOKEN=REPLACE_WITH_BOT_TOKEN
TELEGRAM_CHAT_ID=REPLACE_WITH_CHAT_ID

# Email (резервный канал)
SMTP_HOST=smtp.yandex.ru:587
SMTP_FROM=alerts@your-domain.ru
SMTP_USER=alerts@your-domain.ru
SMTP_PASSWORD=REPLACE_WITH_EMAIL_PASSWORD
ALERT_EMAIL_TO=admin@your-domain.ru
EOF
chmod 600 /opt/monitoring/.env
echo "✓ .env создан — заполните значения!"
```

### 5.3 docker-compose.yml

```bash
cat > /opt/monitoring/docker-compose.yml << 'EOF'
# ════════════════════════════════════════════════════════════════
# MSP Monitoring Stack — Docker Compose
# Профили: monitoring (Bronze), silver (Silver+)
# Запуск Bronze: docker compose --profile monitoring up -d
# Запуск Silver: docker compose --profile silver up -d
# ════════════════════════════════════════════════════════════════
version: "3.8"

networks:
  monitoring:
    name: msp-monitoring
    driver: bridge

volumes:
  prometheus_data:
    name: msp-prometheus-data
  grafana_data:
    name: msp-grafana-data
  loki_data:
    name: msp-loki-data

services:

  # ── Prometheus ─────────────────────────────────────────────────
  prometheus:
    image: prom/prometheus:${PROMETHEUS_VERSION:-v2.51.0}
    container_name: msp-prometheus
    restart: unless-stopped
    profiles: [monitoring, silver, gold]
    user: "65534:65534"
    volumes:
      - prometheus_data:/prometheus
      - ./prometheus/prometheus.yml:/etc/prometheus/prometheus.yml:ro
      - ./prometheus/rules:/etc/prometheus/rules:ro
    command:
      - "--config.file=/etc/prometheus/prometheus.yml"
      - "--storage.tsdb.path=/prometheus"
      - "--storage.tsdb.retention.time=45d"
      - "--storage.tsdb.retention.size=8GB"
      - "--storage.tsdb.wal-compression"
      - "--web.enable-lifecycle"
      - "--web.enable-admin-api"
      - "--query.timeout=60s"
    ports:
      - "127.0.0.1:9090:9090"  # Только localhost + VPN
    networks: [monitoring]
    healthcheck:
      test: ["CMD", "wget", "-qO-", "http://localhost:9090/-/healthy"]
      interval: 30s
      timeout: 10s
      retries: 3
    deploy:
      resources:
        limits:
          memory: 2G
        reservations:
          memory: 512M
    logging:
      driver: json-file
      options:
        max-size: "10m"
        max-file: "3"

  # ── Alertmanager ────────────────────────────────────────────────
  alertmanager:
    image: prom/alertmanager:${ALERTMANAGER_VERSION:-v0.27.0}
    container_name: msp-alertmanager
    restart: unless-stopped
    profiles: [monitoring, silver, gold]
    volumes:
      - ./alertmanager/alertmanager.yml:/etc/alertmanager/alertmanager.yml:ro
    command:
      - "--config.file=/etc/alertmanager/alertmanager.yml"
      - "--storage.path=/alertmanager"
      - "--web.external-url=http://10.9.0.1:9093"
    ports:
      - "127.0.0.1:9093:9093"
    networks: [monitoring]
    deploy:
      resources:
        limits:
          memory: 256M
    logging:
      driver: json-file
      options:
        max-size: "5m"
        max-file: "2"

  # ── Grafana ─────────────────────────────────────────────────────
  grafana:
    image: grafana/grafana:${GRAFANA_VERSION:-10.4.2}
    container_name: msp-grafana
    restart: unless-stopped
    profiles: [monitoring, silver, gold]
    user: "472:472"
    volumes:
      - grafana_data:/var/lib/grafana
      - ./grafana/provisioning:/etc/grafana/provisioning:ro
    environment:
      - GF_SECURITY_ADMIN_USER=${GRAFANA_ADMIN_USER:?GRAFANA_ADMIN_USER must be set in .env}
      - GF_SECURITY_ADMIN_PASSWORD=${GRAFANA_ADMIN_PASSWORD:?GRAFANA_ADMIN_PASSWORD must be set in .env}
      - GF_USERS_ALLOW_SIGN_UP=false
      - GF_AUTH_ANONYMOUS_ENABLED=false
      - GF_SERVER_ROOT_URL=http://10.9.0.1:3000
      - GF_ALERTING_ENABLED=false
      - GF_UNIFIED_ALERTING_ENABLED=false
      - GF_SECURITY_DISABLE_GRAVATAR=true
      - GF_ANALYTICS_REPORTING_ENABLED=false
      - GF_ANALYTICS_CHECK_FOR_UPDATES=false
    ports:
      - "10.9.0.1:3000:3000"  # Только через VPN!
    networks: [monitoring]
    depends_on:
      prometheus:
        condition: service_healthy
    deploy:
      resources:
        limits:
          memory: 512M
    logging:
      driver: json-file
      options:
        max-size: "10m"
        max-file: "3"

  # ── Node Exporter (VM Исполнителя) ─────────────────────────────
  node-exporter:
    image: prom/node-exporter:${NODE_EXPORTER_VERSION:-v1.7.0}
    container_name: msp-node-exporter
    restart: unless-stopped
    profiles: [monitoring, silver, gold]
    pid: host
    volumes:
      - /proc:/host/proc:ro
      - /sys:/host/sys:ro
      - /:/rootfs:ro
    command:
      - "--path.procfs=/host/proc"
      - "--path.sysfs=/host/sys"
      - "--path.rootfs=/rootfs"
      - "--collector.filesystem.mount-points-exclude=^/(sys|proc|dev|host|etc)($$|/)"
    networks: [monitoring]
    deploy:
      resources:
        limits:
          memory: 128M

  # ── cAdvisor (Docker metrics) ───────────────────────────────────
  cadvisor:
    image: gcr.io/cadvisor/cadvisor:${CADVISOR_VERSION:-v0.49.1}
    container_name: msp-cadvisor
    restart: unless-stopped
    profiles: [monitoring, silver, gold]
    privileged: true
    volumes:
      - /:/rootfs:ro
      - /var/run:/var/run:ro
      - /sys:/sys:ro
      - /var/lib/docker:/var/lib/docker:ro
      - /dev/disk:/dev/disk:ro
    command:
      - "--housekeeping_interval=30s"
      - "--max_housekeeping_interval=35s"
      - "--event_storage_event_limit=default=0"
      - "--event_storage_age_limit=default=0"
      - "--disable_metrics=percpu,sched,tcp,udp,disk,diskIO,accelerator,hugetlb,referenced_memory,cpu_topology,resctrl"
      - "--docker_only=true"
    networks: [monitoring]
    deploy:
      resources:
        limits:
          memory: 256M

  # ── Loki (Silver/Gold) ─────────────────────────────────────────
  loki:
    image: grafana/loki:${LOKI_VERSION:-3.0.0}
    container_name: msp-loki
    restart: unless-stopped
    profiles: [silver, gold]
    user: "10001:10001"
    volumes:
      - loki_data:/loki
      - ./loki/loki-config.yml:/etc/loki/local-config.yaml:ro
    command: -config.file=/etc/loki/local-config.yaml
    ports:
      - "10.9.0.1:3100:3100"  # Только через VPN
    networks: [monitoring]
    deploy:
      resources:
        limits:
          memory: 1G
EOF
echo "✓ docker-compose.yml создан"
```

### 5.4 Конфигурация Prometheus

```bash
cat > /opt/monitoring/prometheus/prometheus.yml << 'EOF'
# ════════════════════════════════════════════════════════════════
# prometheus.yml — Конфигурация сбора метрик
# Добавлять клиентов в конец файла при онбординге
# ════════════════════════════════════════════════════════════════
global:
  scrape_interval:     15s
  evaluation_interval: 15s
  scrape_timeout:      10s
  external_labels:
    region: 'ru-central1'
    msp: 'primary'

alerting:
  alertmanagers:
    - static_configs:
        - targets: ['alertmanager:9093']
      timeout: 10s
      api_version: v2

rule_files:
  - "/etc/prometheus/rules/*.yml"

scrape_configs:

  # ── Инфраструктура Исполнителя ─────────────────────────────────
  - job_name: 'prometheus'
    static_configs:
      - targets: ['localhost:9090']
        labels: {role: 'monitoring', owner: 'executor'}

  - job_name: 'alertmanager'
    static_configs:
      - targets: ['alertmanager:9093']
        labels: {role: 'monitoring', owner: 'executor'}

  - job_name: 'grafana'
    static_configs:
      - targets: ['grafana:3000']
        labels: {role: 'monitoring', owner: 'executor'}

  - job_name: 'node-exporter-host'
    static_configs:
      - targets: ['node-exporter:9100']
        labels: {role: 'monitoring-host', owner: 'executor', instance: 'msp-vm'}

  - job_name: 'cadvisor'
    static_configs:
      - targets: ['cadvisor:8080']
        labels: {role: 'docker', owner: 'executor'}

  # ════════════════════════════════════════════════════════════════
  # КЛИЕНТЫ — добавлять при онбординге (см. скрипт add_client.sh)
  # ════════════════════════════════════════════════════════════════

  # ШАБЛОН (раскомментировать и заменить CLIENT_SLUG):
  # - job_name: 'client-CLIENT_SLUG-linux'
  #   scrape_interval: 30s
  #   scrape_timeout: 25s
  #   static_configs:
  #     - targets:
  #         - '10.9.0.10:9100'
  #       labels:
  #         client: 'CLIENT_SLUG'
  #         client_name: 'ООО Название'
  #         tier: 'bronze'
  #         env: 'production'
  #   metric_relabel_configs:
  #     # Убрать технические go_ метрики (экономия места)
  #     - source_labels: [__name__]
  #       regex: 'go_.*'
  #       action: drop
  #
  # - job_name: 'client-CLIENT_SLUG-windows'
  #   scrape_interval: 30s
  #   static_configs:
  #     - targets:
  #         - '10.9.0.20:9182'
  #       labels:
  #         client: 'CLIENT_SLUG'
  #         client_name: 'ООО Название'
  #         tier: 'bronze'
  #         env: 'production'
  #
  # - job_name: 'client-CLIENT_SLUG-blackbox-http'
  #   metrics_path: /probe
  #   params:
  #     module: [http_2xx]
  #   static_configs:
  #     - targets:
  #         - 'https://site.ru'
  #       labels:
  #         client: 'CLIENT_SLUG'
  #         tier: 'bronze'
  #   relabel_configs:
  #     - source_labels: [__address__]
  #       target_label: __param_target
  #     - source_labels: [__param_target]
  #       target_label: instance
  #     - target_label: __address__
  #       replacement: 'localhost:9115'
EOF
```

### 5.5 Grafana provisioning

```bash
# Datasource
cat > /opt/monitoring/grafana/provisioning/datasources/prometheus.yml << 'EOF'
apiVersion: 1
datasources:
  - name: Prometheus
    type: prometheus
    access: proxy
    url: http://prometheus:9090
    isDefault: true
    editable: false
    jsonData:
      timeInterval: "15s"
      httpMethod: POST
      exemplarTraceIdDestinations: []
EOF

# Dashboard provisioning
cat > /opt/monitoring/grafana/provisioning/dashboards/default.yml << 'EOF'
apiVersion: 1
providers:
  - name: 'MSP Dashboards'
    orgId: 1
    folder: 'MSP'
    type: file
    disableDeletion: false
    editable: true
    updateIntervalSeconds: 30
    options:
      path: /var/lib/grafana/dashboards
      foldersFromFilesStructure: false
EOF
```

### 5.6 Запуск стека

```bash
cd /opt/monitoring

# Проверить конфиги
docker run --rm -v ./prometheus:/prometheus prom/prometheus:v2.51.0 \
  promtool check config /prometheus/prometheus.yml

# Запустить (Bronze)
docker compose --profile monitoring up -d

# Проверить
docker compose ps
docker compose logs --tail=30 prometheus
curl -s http://localhost:9090/-/healthy
curl -s http://localhost:9093/-/healthy

# Открыть Grafana через VPN: http://10.9.0.1:3000
```

---

## 6. СКРИПТ ДОБАВЛЕНИЯ КЛИЕНТА

```bash
sudo tee /usr/local/bin/add_client.sh << 'SCRIPT'
#!/bin/bash
# add_client.sh — Добавить нового клиента Bronze
# Использование: add_client.sh CLIENT_SLUG "ООО Название" TIER
# Пример: add_client.sh example "ООО Пример" bronze

set -euo pipefail

CLIENT_SLUG="${1:?Usage: $0 CLIENT_SLUG 'Client Name' TIER}"
CLIENT_NAME="${2:?}"
TIER="${3:-bronze}"
PROMETHEUS_CFG="/opt/monitoring/prometheus/prometheus.yml"

echo "=== Добавление клиента: ${CLIENT_NAME} (${CLIENT_SLUG}) ==="

# ── Запросить VPN IPs ────────────────────────────────────────────
echo ""
read -p "VPN IP первого Linux-сервера (или Enter чтобы пропустить): " LINUX_IP1
read -p "VPN IP второго Linux-сервера (или Enter): " LINUX_IP2
read -p "VPN IP первого Windows-сервера (или Enter): " WIN_IP1
read -p "URL сайта для HTTP-проверки (или Enter): " SITE_URL

# ── Добавить в Prometheus ────────────────────────────────────────
{
echo ""
echo "  # ════════════════════════════════"
echo "  # КЛИЕНТ: ${CLIENT_NAME} (${TIER})"
echo "  # Добавлен: $(date '+%Y-%m-%d')"
echo "  # ════════════════════════════════"
} >> "$PROMETHEUS_CFG"

if [[ -n "$LINUX_IP1" ]]; then
cat >> "$PROMETHEUS_CFG" << EOF

  - job_name: 'client-${CLIENT_SLUG}-linux'
    scrape_interval: 30s
    scrape_timeout: 25s
    static_configs:
      - targets:
          - '${LINUX_IP1}:9100'
$([ -n "$LINUX_IP2" ] && echo "          - '${LINUX_IP2}:9100'")
        labels:
          client: '${CLIENT_SLUG}'
          client_name: '${CLIENT_NAME}'
          tier: '${TIER}'
          env: 'production'
    metric_relabel_configs:
      - source_labels: [__name__]
        regex: 'go_.*'
        action: drop
EOF
fi

if [[ -n "$WIN_IP1" ]]; then
cat >> "$PROMETHEUS_CFG" << EOF

  - job_name: 'client-${CLIENT_SLUG}-windows'
    scrape_interval: 30s
    static_configs:
      - targets:
          - '${WIN_IP1}:9182'
        labels:
          client: '${CLIENT_SLUG}'
          client_name: '${CLIENT_NAME}'
          tier: '${TIER}'
          env: 'production'
EOF
fi

if [[ -n "$SITE_URL" ]]; then
cat >> "$PROMETHEUS_CFG" << EOF

  - job_name: 'client-${CLIENT_SLUG}-http'
    metrics_path: /probe
    params:
      module: [http_2xx]
    static_configs:
      - targets:
          - '${SITE_URL}'
        labels:
          client: '${CLIENT_SLUG}'
          tier: '${TIER}'
    relabel_configs:
      - source_labels: [__address__]
        target_label: __param_target
      - source_labels: [__param_target]
        target_label: instance
      - target_label: __address__
        replacement: 'localhost:9115'
EOF
fi

# ── Создать S3 bucket ────────────────────────────────────────────
echo ""
read -p "Создать S3 bucket для бэкапов? [y/N]: " CREATE_BUCKET
if [[ "$CREATE_BUCKET" =~ ^[Yy]$ ]]; then
    yc storage bucket create --name "backup-${CLIENT_SLUG}" 2>/dev/null || echo "Bucket уже существует"
    echo "✓ Bucket: backup-${CLIENT_SLUG}"
fi

# ── Перезагрузить Prometheus ─────────────────────────────────────
echo ""
echo "Перезагружаю Prometheus конфиг..."
curl -s -X POST http://localhost:9090/-/reload
sleep 2

# ── Проверить targets ────────────────────────────────────────────
TARGETS=$(curl -s http://localhost:9090/api/v1/targets | \
    python3 -c "
import sys,json
d=json.load(sys.stdin)
targets=[t for t in d['data']['activeTargets'] if '${CLIENT_SLUG}' in str(t.get('labels',''))]
for t in targets:
    print(f\"  {'✓' if t['health']=='up' else '✗'} {t['labels'].get('job','?')} → {t['health']}\")
")
echo ""
echo "=== Targets клиента ${CLIENT_SLUG} ==="
echo "$TARGETS"
echo ""
echo "✅ Клиент ${CLIENT_NAME} добавлен!"
echo "   Grafana: http://10.9.0.1:3000"
echo "   Prometheus: http://10.9.0.1:9090/targets"
SCRIPT
sudo chmod +x /usr/local/bin/add_client.sh
```

---

## 7. ЕЖЕНЕДЕЛЬНЫЙ ОТЧЁТ

```bash
cat > /usr/local/bin/weekly_report.sh << 'SCRIPT'
#!/bin/bash
# weekly_report.sh — Генерация еженедельного отчёта
# Запускать по понедельникам через cron: 0 8 * * 1 root /usr/local/bin/weekly_report.sh

PROMETHEUS="http://localhost:9090"
REPORT_DATE=$(date '+%d.%m.%Y')
PERIOD_START=$(date -d '7 days ago' '+%Y-%m-%d')

query() {
    local q="$1"
    curl -s "${PROMETHEUS}/api/v1/query?query=$(python3 -c "import urllib.parse; print(urllib.parse.quote('${q}'))")" | \
        python3 -c "import sys,json; d=json.load(sys.stdin); [print(f\"{r['metric'].get('client_name','?')}: {float(r['value'][1]):.1f}\") for r in d['data']['result']]" 2>/dev/null
}

echo "═══════════════════════════════════════════════"
echo "  MSP WEEKLY REPORT — ${REPORT_DATE}"
echo "  Период: ${PERIOD_START} → $(date '+%Y-%m-%d')"
echo "═══════════════════════════════════════════════"
echo ""

echo "📊 ДОСТУПНОСТЬ СЕРВЕРОВ"
curl -s "${PROMETHEUS}/api/v1/query?query=up" | \
    python3 -c "
import sys,json
d=json.load(sys.stdin)
for r in d['data']['result']:
    status = '✓ UP' if r['value'][1]=='1' else '✗ DOWN'
    client = r['metric'].get('client_name', r['metric'].get('client', '?'))
    inst   = r['metric'].get('instance','?')
    print(f'  {status:6} {client:30} {inst}')
"

echo ""
echo "💾 СТАТУС БЭКАПОВ"
curl -s "${PROMETHEUS}/api/v1/query?query=restic_backup_last_status" | \
    python3 -c "
import sys,json,datetime
d=json.load(sys.stdin)
for r in d['data']['result']:
    status = '✓ OK  ' if r['value'][1]=='1' else '✗ FAIL'
    host   = r['metric'].get('host','?')
    print(f'  {status} {host}')
"

echo ""
echo "💿 ИСПОЛЬЗОВАНИЕ ДИСКОВ (>70%)"
curl -s "${PROMETHEUS}/api/v1/query?query=(1-node_filesystem_avail_bytes{fstype!~\"tmpfs|overlay\"}/node_filesystem_size_bytes)*100>70" | \
    python3 -c "
import sys,json
d=json.load(sys.stdin)
if not d['data']['result']:
    print('  ✓ Все диски в норме')
for r in d['data']['result']:
    pct  = float(r['value'][1])
    inst = r['metric'].get('instance','?')
    mp   = r['metric'].get('mountpoint','?')
    clt  = r['metric'].get('client_name','?')
    print(f'  ⚠ {pct:.1f}% — {clt} / {inst}:{mp}')
"

echo ""
echo "═══════════════════════════════════════════════"
echo "  Следующий отчёт: $(date -d 'next monday' '+%d.%m.%Y')"
echo "═══════════════════════════════════════════════"
SCRIPT
chmod +x /usr/local/bin/weekly_report.sh

# Cron для автоматического отчёта
echo "0 8 * * 1 root /usr/local/bin/weekly_report.sh" | sudo tee /etc/cron.d/msp-weekly-report
```

---

## 8. ОБСЛУЖИВАНИЕ СТЕКА

### Обновление версий образов

```bash
cd /opt/monitoring

# Обновить образ (пример: prometheus)
# 1. Изменить версию в .env
# 2. Пересоздать контейнер
docker compose pull prometheus
docker compose up -d prometheus
docker compose logs --tail=20 prometheus
```

### Снапшот VM перед обновлениями

```bash
# Создать снапшот перед любыми изменениями
DISK_ID=$(yc compute instance get msp-monitoring --format json | jq -r '.boot_disk.disk_id')
yc compute snapshot create \
  --name "msp-$(date +%Y%m%d)" \
  --source-disk-id $DISK_ID \
  --async
echo "Снапшот создаётся в фоне"
```

### Мониторинг самого стека

```bash
# Проверка здоровья всех контейнеров
docker compose ps
docker stats --no-stream

# Место в volumes
docker system df -v

# Prometheus TSDB stats
curl -s http://localhost:9090/api/v1/status/tsdb | python3 -m json.tool | grep -E "(headChunks|numSeries|sizeBytes)" | head -10
```
