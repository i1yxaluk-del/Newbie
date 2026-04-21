# SOP — Gold · Сторона ИСПОЛНИТЕЛЯ
# Версия 3.0 | Апрель 2026
# ═══════════════════════════════════════════════════════════════════
#
# Gold Исполнитель = Silver Исполнитель + Wazuh VM + KSC + osTicket
#
# ПРИНЦИП: тяжелые сервисы (SIEM, indexer, dashboard) — на отдельной VM
#
# Для кого: Junior-инженер, выполняющий развёртывание инфраструктуры
# ═══════════════════════════════════════════════════════════════════

## СОДЕРЖАНИЕ

1. Архитектура Gold (Исполнитель)
2. Wazuh VM — создание и настройка
3. Wazuh Docker Compose — развёртывание
4. Wazuh Manager — конфигурация + Telegram
5. KSC — Kaspersky Security Center
6. osTicket — тикет-система
7. Gold alert rules
8. Верификация Gold Executor
9. Troubleshooting

---

## 1. АРХИТЕКТУРА GOLD (ИСПОЛНИТЕЛЬ)

```
YANDEX CLOUD
┌──────────────────────────────────────────────────────────────────┐
│ Monitoring VM (4 vCPU, 8 GB) — из Silver                         │
│ ├── Prometheus :9090                                              │
│ ├── Alertmanager :9093                                           │
│ ├── Grafana :3000                                                │
│ ├── Loki :3100                                                   │
│ └── node-exporter, cAdvisor                                      │
│                                                                  │
│ Automation VM (2 vCPU, 4 GB) — из Silver                         │
│ ├── Puppet Server :8140                                          │
│ ├── Ansible Control Node                                         │
│ └── Git                                                          │
│                                                                  │
│ Bastion VM — из Bronze                                           │
│ └── WireGuard :51820                                             │
│                                                                  │
│ Wazuh VM (8 vCPU, 16 GB, 100 GB SSD) ← NEW                     │
│ ├── Wazuh Manager :1514/1515                                     │
│ ├── Wazuh Indexer (OpenSearch) :9200                             │
│ ├── Wazuh Dashboard :443 (только VPN)                            │
│ ├── osTicket :8080 (только VPN)                                  │
│ └── KSC metrics exporter                                         │
│                                                                  │
│ Object Storage (S3)                                              │
│ └── backup-CLIENT_NAME/ (restic репозитории)                    │
└──────────────────────────────────────────────────────────────────┘
         ↑            ↑            ↑
    10.9.0.10    10.9.0.20    10.9.0.30
   (Gold-1)    (Gold-2)    (Gold-3)
```

**Стоимость Gold инфраструктуры Исполнителя:**
```
Monitoring VM:    ~3 800 ₽/мес
Automation VM:    ~1 900 ₽/мес
Bastion VM:       ~600 ₽/мес
Wazuh VM:         ~8 500 ₽/мес
Object Storage:   ~300 ₽/мес
─────────────────────────────────
Итого:            ~14 800 ₽/мес (оправдано при 15+ клиентах)
```

---

## 2. WAZUH VM — СОЗДАНИЕ

### 2.1 Требования

```
МИНИМУМ для Wazuh:
  CPU: 4 vCPU (рекомендуется 8 для >20 агентов)
  RAM: 8 GB (рекомендуется 16 GB)
  Disk: 100 GB SSD (indexer требует место для логов)
  OS: Ubuntu 22.04 LTS

КРИТИЧНО для OpenSearch (Wazuh Indexer):
  vm.max_map_count = 262144  ← ОБЯЗАТЕЛЬНО, иначе Indexer не запустится
  fs.file-max = 65536

Публичный IP: НЕ НУЖЕН (доступ только через VPN)
```

### 2.2 Создать VM

```bash
yc compute instance create \
  --name msp-wazuh \
  --zone ru-central1-a \
  --network-interface subnet-name=default-vpc,nat-ip-version=none \
  --create-boot-disk \
    image-family=ubuntu-2204-lts,\
    size=100,\
    type=network-ssd \
  --cores 8 \
  --core-fraction 100 \
  --memory 16 \
  --ssh-key ~/.ssh/id_ed25519.pub

WAZUH_IP=$(yc compute instance get msp-wazuh --format json | \
    jq -r '.network_interfaces[0].primary_v4_address.address')
echo "Wazuh VM internal IP: $WAZUH_IP"

# Подключиться через VPN (после настройки WireGuard peer):
ssh ubuntu@$WAZUH_IP
```

### 2.3 Настройка ОС

```bash
# ── КРИТИЧНО: параметры ядра для OpenSearch ────────────────────────
# OpenSearch (Indexer) требует эти настройки, иначе не запустится!
echo "vm.max_map_count=262144" | sudo tee -a /etc/sysctl.conf
echo "fs.file-max=65536" | sudo tee -a /etc/sysctl.conf
sudo sysctl -p
sysctl vm.max_map_count  # Должно быть 262144

# ── Базовые пакеты ─────────────────────────────────────────────────
sudo apt update && sudo apt install -y \
    docker.io docker-compose-plugin curl git jq htop

sudo usermod -aG docker ubuntu
newgrp docker
docker --version

# ── Добавить VPN IP (10.9.0.3) через WireGuard ────────────────────
# На Bastion выполнить: add_vpn_peer.sh msp-wazuh 10.9.0.3 "WAZUH_PUBKEY"
# На Wazuh VM настроить WireGuard client (как в SOP_client_bronze.md §3)
```

---

## 3. WAZUH DOCKER COMPOSE

### 3.1 Создать структуру

```bash
sudo mkdir -p /opt/wazuh
sudo chown -R ubuntu:ubuntu /opt/wazuh
cd /opt/wazuh
```

### 3.2 Docker Compose файл

```bash
cat > /opt/wazuh/docker-compose.yml << 'EOF'
# Wazuh 4.7 Docker Compose
# Три контейнера: Manager + Indexer + Dashboard
# Источник: https://github.com/wazuh/wazuh-docker

version: "3.8"

networks:
  wazuh:
    driver: bridge

volumes:
  wazuh_api_configuration:
  wazuh_etc:
  wazuh_logs:
  wazuh_queue:
  wazuh_var_multigroups:
  wazuh_integrations:
  wazuh_active_response:
  wazuh_agentless:
  wazuh_wodles:
  filebeat_etc:
  filebeat_var:
  wazuh_indexer_data:

services:

  # ── Wazuh Manager ────────────────────────────────────────────────
  # Принимает подключения от агентов (порт 1514/1515)
  # Запускает правила детектирования
  # Отправляет алерты в Telegram
  wazuh.manager:
    image: wazuh/wazuh-manager:4.7.5
    container_name: wazuh-manager
    restart: unless-stopped
    ulimits:
      memlock:
        soft: -1
        hard: -1
      nofile:
        soft: 655360
        hard: 655360
    ports:
      - "1514:1514"          # Agent TCP — агенты подключаются сюда
      - "1514:1514/udp"      # Agent UDP
      - "1515:1515"          # Agent enrollment — регистрация новых агентов
      - "514:514/udp"        # Syslog — приём логов по syslog
      - "55000:55000"        # REST API — управление Manager через API
    environment:
      INDEXER_URL: https://wazuh.indexer:9200
      INDEXER_USERNAME: admin
      INDEXER_PASSWORD: ${WAZUH_INDEXER_PASSWORD:?WAZUH_INDEXER_PASSWORD must be set in .env}
      FILEBEAT_SSL_VERIFICATION_MODE: full
      SSL_CERTIFICATE_AUTHORITIES: /etc/ssl/root-ca.pem
      SSL_CERTIFICATE: /etc/ssl/filebeat.pem
      SSL_KEY: /etc/ssl/filebeat.key
      API_USERNAME: wazuh-wui
      API_PASSWORD: ${WAZUH_API_PASSWORD:?WAZUH_API_PASSWORD must be set in .env}
    volumes:
      - wazuh_api_configuration:/var/ossec/api/configuration
      - wazuh_etc:/var/ossec/etc
      - wazuh_logs:/var/ossec/logs
      - wazuh_queue:/var/ossec/queue
      - wazuh_var_multigroups:/var/ossec/var/multigroups
      - wazuh_integrations:/var/ossec/integrations
      - wazuh_active_response:/var/ossec/active-response/bin
      - wazuh_agentless:/var/ossec/agentless
      - wazuh_wodles:/var/ossec/wodles
      - filebeat_etc:/etc/filebeat
      - filebeat_var:/var/lib/filebeat
    networks: [wazuh]

  # ── Wazuh Indexer (OpenSearch) ───────────────────────────────────
  # Хранит все события и логи
  # Требует vm.max_map_count=262144 (настроено в §2.3)
  wazuh.indexer:
    image: wazuh/wazuh-indexer:4.7.5
    container_name: wazuh-indexer
    restart: unless-stopped
    ports:
      - "9200:9200"
    environment:
      OPENSEARCH_JAVA_OPTS: "-Xms4g -Xmx4g"  # 4 GB JVM heap
    ulimits:
      memlock:
        soft: -1
        hard: -1
      nofile:
        soft: 65536
        hard: 65536
    volumes:
      - wazuh_indexer_data:/var/lib/wazuh-indexer
    networks: [wazuh]

  # ── Wazuh Dashboard ─────────────────────────────────────────────
  # Веб-интерфейс для анализа событий
  # ДОСТУПЕН ТОЛЬКО ЧЕРЕЗ VPN (10.9.0.3:443)
  wazuh.dashboard:
    image: wazuh/wazuh-dashboard:4.7.5
    container_name: wazuh-dashboard
    restart: unless-stopped
    ports:
      - "10.9.0.3:443:443"   # ТОЛЬКО VPN! Не открывать наружу!
    environment:
      INDEXER_USERNAME: admin
      INDEXER_PASSWORD: ${WAZUH_INDEXER_PASSWORD:?WAZUH_INDEXER_PASSWORD must be set in .env}
      WAZUH_API_URL: https://wazuh.manager
      DASHBOARD_USERNAME: kibanaserver
      DASHBOARD_PASSWORD: ${WAZUH_DASHBOARD_PASSWORD:?WAZUH_DASHBOARD_PASSWORD must be set in .env}
      API_USERNAME: wazuh-wui
      API_PASSWORD: ${WAZUH_API_PASSWORD:?WAZUH_API_PASSWORD must be set in .env}
    depends_on:
      - wazuh.indexer
    networks: [wazuh]
EOF
```

### 3.3 .env файл

```bash
cat > /opt/wazuh/.env << 'EOF'
# ════════════════════════════════════════════
# Wazuh passwords — генерировать автоматически!
# НЕ писать пароли вручную — использовать генератор
# ════════════════════════════════════════════
WAZUH_INDEXER_PASSWORD=$(openssl rand -base64 24)
WAZUH_API_PASSWORD=$(openssl rand -base64 24)
WAZUH_DASHBOARD_PASSWORD=$(openssl rand -base64 24)
EOF
chmod 600 /opt/wazuh/.env
```

### 3.4 Запуск

```bash
cd /opt/wazuh
docker compose up -d

# Дождаться инициализации (3–5 минут, Indexer стартует медленно)
echo "Ожидаем инициализации Wazuh..."
sleep 120

# Проверить
docker compose ps
curl -sk https://localhost:9200 -u admin:$(grep WAZUH_INDEXER_PASSWORD /opt/wazuh/.env | cut -d= -f2) | head -5

echo "Wazuh Dashboard: https://10.9.0.3:443"
echo "  Логин: admin / <WAZUH_INDEXER_PASSWORD>"
```

---

## 4. WAZUH MANAGER — КОНФИГУРАЦИЯ + TELEGRAM

### 4.1 ossec.conf — главный конфиг Manager

```bash
# Полный ossec.conf находится в: 3_Gold/EXECUTOR/wazuh/wazuh_manager_ossec.conf
# Скопировать в контейнер:
docker cp wazuh_manager_ossec.conf wazuh-manager:/var/ossec/etc/ossec.conf
docker restart wazuh-manager
```

### 4.2 Интеграция Wazuh → Telegram

```bash
# custom-telegram.py — скрипт отправки алертов Wazuh в Telegram
# Работает внутри контейнера wazuh-manager

cat > /tmp/custom-telegram.py << 'SCRIPT'
#!/usr/bin/env python3
"""
Wazuh → Telegram интеграция
Файл: /var/ossec/integrations/custom-telegram

КАК РАБОТАЕТ:
1. Wazuh Manager генерирует алерт (правило сработало)
2. Если level >= 7 — скрипт формирует сообщение и отправляет в Telegram
3. level 7-11 = WARNING, level 12+ = CRITICAL

ПЕРЕМЕННЫЕ ОКРУЖЕНИЯ (из docker-compose или .env):
  TELEGRAM_BOT_TOKEN — токен бота от @BotFather
  TELEGRAM_CHAT_ID   — ID чата куда отправлять алерты
"""
import sys
import json
import requests
import os

alert_file = open(sys.argv[1])
alert = json.loads(alert_file.read())
alert_file.close()

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
CHAT_ID   = os.getenv("TELEGRAM_CHAT_ID", "")

if not BOT_TOKEN or not CHAT_ID:
    sys.exit(0)

level = alert.get("rule", {}).get("level", 0)
rule  = alert.get("rule", {}).get("description", "Unknown")
agent = alert.get("agent", {}).get("name", "Unknown")

if level < 7:
    sys.exit(0)

severity = "CRITICAL" if level >= 12 else "WARNING"
message  = f"[{severity}] Wazuh Security Alert\nAgent: {agent}\nRule: {rule}\nLevel: {level}"

try:
    requests.post(
        f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
        json={"chat_id": CHAT_ID, "text": message},
        timeout=10
    )
except Exception as e:
    print(f"Telegram error: {e}")
SCRIPT

# Скопировать в контейнер
docker cp /tmp/custom-telegram.py wazuh-manager:/var/ossec/integrations/custom-telegram
docker exec wazuh-manager chmod 750 /var/ossec/integrations/custom-telegram
docker exec wazuh-manager chown root:wazuh /var/ossec/integrations/custom-telegram

echo "Telegram интеграция установлена"
```

---

## 5. KSC — KASPERSKY SECURITY CENTER

### 5.1 Развёртывание

```
KSC — централизованная консоль управления Kaspersky.
Позволяет:
  ✓ Устанавливать KES на устройства удалённо
  ✓ Управлять политиками антивируса
  ✓ Мониторить статус защиты
  ✓ Отслеживать обновления баз

ВАРИАНТЫ развёртывания:
  A) KSC Cloud Console (SaaS от Kaspersky) — проще, но требует лицензии
  B) Локальный KSC Server — на VM в Yandex Cloud

Подробное руководство: 3_Gold/EXECUTOR/ksc/ksc_setup_guide.md
```

### 5.2 KSC Metrics Exporter

```bash
# Python-скрипт для экспорта метрик из KSC в Prometheus
# См. ksc_setup_guide.md — раздел "Python KSC metrics exporter"
# Скрипт запускается как systemd service на Automation VM
# Порт: 9101 (metrics endpoint)
```

---

## 6. OSTICKET — ТИКЕТ-СИСТЕМА

### 6.1 Docker Compose

```bash
mkdir -p /opt/osticket
cat > /opt/osticket/docker-compose.yml << 'EOF'
# osTicket — тикет-система для отслеживания инцидентов
# ДОСТУПЕН ТОЛЬКО ЧЕРЕЗ VPN (10.9.0.1:8080)

version: "3.8"

networks:
  osticket:
    driver: bridge

volumes:
  osticket_db:
  osticket_data:

services:
  db:
    image: mariadb:10.11
    container_name: osticket-db
    restart: unless-stopped
    environment:
      MYSQL_ROOT_PASSWORD: ${DB_ROOT_PASS:?DB_ROOT_PASS must be set in .env}
      MYSQL_DATABASE: osticket
      MYSQL_USER: osticket
      MYSQL_PASSWORD: ${DB_PASS:?DB_PASS must be set in .env}
    volumes:
      - osticket_db:/var/lib/mysql
    networks: [osticket]
    healthcheck:
      test: ["CMD", "mysqladmin", "ping", "-h", "localhost"]
      interval: 30s
      timeout: 10s
      retries: 3

  osticket:
    image: osticket/osticket:latest
    container_name: osticket-app
    restart: unless-stopped
    ports:
      - "10.9.0.1:8080:80"    # ТОЛЬКО VPN!
    environment:
      MYSQL_HOST: db
      MYSQL_DB: osticket
      MYSQL_USER: osticket
      MYSQL_PASSWORD: ${DB_PASS:?DB_PASS must be set in .env}
      ADMIN_EMAIL: ${ADMIN_EMAIL:-admin@msp.local}
    volumes:
      - osticket_data:/var/www/html/include/ost-config.php
    depends_on:
      db:
        condition: service_healthy
    networks: [osticket]
    deploy:
      resources:
        limits: { memory: 512M }
EOF

cat > /opt/osticket/.env << 'EOF'
DB_ROOT_PASS=$(openssl rand -base64 24)
DB_PASS=$(openssl rand -base64 24)
ADMIN_EMAIL=admin@your-domain.ru
EOF
chmod 600 /opt/osticket/.env

cd /opt/osticket
docker compose up -d

echo "osTicket: http://10.9.0.1:8080"
echo "Завершить установку через веб-интерфейс"
```

---

## 7. GOLD ALERT RULES

```yaml
# Файл: /opt/monitoring/prometheus/rules/gold_alerts.yml
# Добавляется к bronze_alerts.yml и silver_alerts.yml

groups:
  - name: gold_security
    rules:

      - alert: WazuhAgentDown
        expr: |
          wazuh_agent_status{status!="Active"} == 1
        for: 5m
        labels:
          severity: warning
          category: security
        annotations:
          summary: "Wazuh Agent неактивен: {{ $labels.agent_name }}"
          description: |
            Wazuh Agent перестал отправлять данные.
            Проверить на сервере: systemctl status wazuh-agent
            На Manager: docker exec wazuh-manager /var/ossec/bin/agent_control -l

      - alert: KasperskyNotRunning
        expr: kaspersky_service_running == 0
        for: 10m
        labels:
          severity: critical
          category: security
        annotations:
          summary: "Kaspersky НЕ работает: {{ $labels.host }}"
          description: |
            Антивирусная служба остановлена!
            PowerShell: Start-Service AVP*

      - alert: KasperskyDatabaseOld
        expr: kaspersky_database_age_hours > 48
        for: 1h
        labels:
          severity: warning
          category: security
        annotations:
          summary: "Базы Kaspersky устарели: {{ $value | printf \"%.0f\" }} ч"
          description: "Запустить обновление через KSC или вручную."

  - name: gold_sla
    rules:
      - alert: SLAReactionTimeAtRisk
        expr: |
          (time() - alertmanager_alerts_firing_timestamp_seconds) > 2700
          and on() up{job="alertmanager"} == 1
        for: 0m
        labels:
          severity: critical
          category: sla
        annotations:
          summary: "SLA: алерт не закрыт более 45 минут (P1 = 1 час)"
          description: "Принять меры НЕМЕДЛЕННО — Gold SLA P1 = 1 час 24/7"
```

---

## 8. ВЕРИФИКАЦИЯ GOLD EXECUTOR

```bash
#!/bin/bash
echo "=== ВЕРИФИКАЦИЯ GOLD EXECUTOR ==="

# ── Bronze + Silver (из verify_all.sh) ──────────────────────────────
echo "─── Bronze + Silver стек ───"
docker inspect msp-prometheus --format '{{.State.Running}}' 2>/dev/null | grep -q true && echo "OK Prometheus" || echo "FAIL"
docker inspect msp-loki --format '{{.State.Running}}' 2>/dev/null | grep -q true && echo "OK Loki" || echo "FAIL"

# ── Gold: Wazuh ────────────────────────────────────────────────────
echo ""
echo "─── Gold: Wazuh ───"
docker inspect wazuh-manager --format '{{.State.Running}}' 2>/dev/null | grep -q true && echo "OK Wazuh Manager" || echo "FAIL"
docker inspect wazuh-indexer --format '{{.State.Running}}' 2>/dev/null | grep -q true && echo "OK Wazuh Indexer" || echo "FAIL"
docker inspect wazuh-dashboard --format '{{.State.Running}}' 2>/dev/null | grep -q true && echo "OK Wazuh Dashboard" || echo "FAIL"

# Агенты
AGENTS=$(docker exec wazuh-manager /var/ossec/bin/agent_control -l 2>/dev/null | grep -c "Active" || echo "?")
echo "Wazuh активных агентов: $AGENTS"

# ── Gold: osTicket ─────────────────────────────────────────────────
echo ""
echo "─── Gold: osTicket ───"
docker inspect osticket-app --format '{{.State.Running}}' 2>/dev/null | grep -q true && echo "OK osTicket" || echo "FAIL"

echo ""
echo "=== ВЕРИФИКАЦИЯ ЗАВЕРШЕНА ==="
```

---

## 9. TROUBLESHOOTING GOLD EXECUTOR

| Проблема | Диагностика | Решение |
|---|---|---|
| Wazuh Indexer не стартует | `docker logs wazuh-indexer 2>&1 \| tail -50` | Проверить `sysctl vm.max_map_count` = 262144, RAM >= 8GB |
| Wazuh Manager не принимает агентов | `docker exec wazuh-manager /var/ossec/bin/agent_control -l` | Проверить порты 1514/1515 доступны из VPN; перезапустить: `docker restart wazuh-manager` |
| Dashboard недоступен | `curl -sk https://10.9.0.3:443` | Проверить что VPN IP 10.9.0.3 настроен на Wazuh VM |
| Telegram интеграция не работает | `docker logs wazuh-manager 2>&1 \| grep telegram` | Проверить TELEGRAM_BOT_TOKEN и CHAT_ID в env |
| osTicket ошибка БД | `docker logs osticket-db 2>&1 \| tail -30` | `docker restart osticket-db`, подождать healthcheck |
| KSC не подключается | Проверить сеть между KSC и агентами | KSC должен быть доступен по сети из клиентской сети |
| Gold alerts не загружены | `curl -s localhost:9090/api/v1/rules \| python3 -m json.tool \| grep gold` | Скопировать `gold_alerts.yml` в `/opt/monitoring/prometheus/rules/`, перезагрузить Prometheus |
