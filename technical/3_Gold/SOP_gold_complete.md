# SOP — Gold · Клиент + Исполнитель (УСТАРЕВШИЙ — используйте SOP_client_gold.md + SOP_executor_gold.md)
# Версия 2.0 | Апрель 2026
# ═══════════════════════════════════════════════════════════════════
#
# ВНИМАНИЕ: Этот файл УСТАРЕЛ. Используйте:
#   Клиент:    3_Gold/CLIENT/SOP_client_gold.md
#   Исполнитель: 3_Gold/EXECUTOR/SOP_executor_gold.md
#
# Gold = Silver + безопасность (Wazuh SIEM) + Kaspersky + тикет-система
# + приоритетный SLA P1 до 1 часа + стратегические сессии
#
# ═══════════════════════════════════════════════════════════════════

---
# ЧАСТЬ 1: КЛИЕНТ
---

## 1. WAZUH AGENT (Linux + Windows)

### 1.1 Что такое Wazuh в контексте MSP

```
Wazuh — open-source SIEM-платформа. В нашей архитектуре:

Wazuh Agent (на сервере клиента)
  ├── Собирает: системные логи, события аутентификации
  ├── Мониторит: изменения файлов (FIM — File Integrity Monitoring)
  ├── Сканирует: уязвимости (CVE database)
  └── Отправляет → Wazuh Manager (у Исполнителя)

Wazuh Manager + Indexer + Dashboard (у Исполнителя)
  ├── Хранит и анализирует события
  ├── Запускает правила детектирования
  ├── Генерирует алерты → Alertmanager → Telegram
  └── Dashboard доступен Исполнителю через VPN

ВАЖНО:
  Wazuh — слой ОБНАРУЖЕНИЯ, не предотвращения.
  Wazuh НЕ заменяет антивирус, firewall, hardening.
  Wazuh — ОДНА из мер комплексной защиты.
```

### 1.2 Установка Wazuh Agent (Linux)

```bash
#!/bin/bash
# install_wazuh_agent_linux.sh
set -euo pipefail

WAZUH_MANAGER="${WAZUH_MANAGER:-10.9.0.3}"  # IP Wazuh Manager через VPN
WAZUH_VERSION="4.7.5"

echo "Устанавливаю Wazuh Agent v${WAZUH_VERSION}..."
echo "Manager: ${WAZUH_MANAGER}"

# ── Добавить репозиторий ──────────────────────────────────────────
curl -s https://packages.wazuh.com/key/GPG-KEY-WAZUH | \
    gpg --no-default-keyring --keyring gnupg-ring:/usr/share/keyrings/wazuh.gpg --import
chmod 644 /usr/share/keyrings/wazuh.gpg

echo "deb [signed-by=/usr/share/keyrings/wazuh.gpg] https://packages.wazuh.com/4.x/apt/ stable main" \
    > /etc/apt/sources.list.d/wazuh.list

apt-get update -q
apt-get install -y wazuh-agent

# ── Настроить адрес Manager ───────────────────────────────────────
sed -i "s|<address>MANAGER_IP</address>|<address>${WAZUH_MANAGER}</address>|g" \
    /var/ossec/etc/ossec.conf

# Установить имя агента
AGENT_NAME=$(hostname -s)
sed -i "s|<agent_name>.*</agent_name>|<agent_name>${AGENT_NAME}</agent_name>|g" \
    /var/ossec/etc/ossec.conf 2>/dev/null || true

# ── Настройка FIM (мониторинг важных файлов) ──────────────────────
cat > /var/ossec/etc/shared/agent.conf << 'EOF'
<agent_config>
  <syscheck>
    <disabled>no</disabled>
    <frequency>43200</frequency>
    <!-- Критичные конфиги -->
    <directories check_all="yes">/etc</directories>
    <directories check_all="yes">/var/ossec/etc</directories>
    <!-- Веб-файлы (если есть) -->
    <directories check_all="yes" report_changes="yes">/var/www</directories>
    <!-- Бинарники системы -->
    <directories check_all="yes">/bin,/sbin,/usr/bin,/usr/sbin</directories>
    <!-- Исключения -->
    <ignore>/etc/mtab</ignore>
    <ignore>/etc/hosts.deny</ignore>
    <ignore>/etc/mail/statistics</ignore>
    <ignore>/etc/random-seed</ignore>
    <ignore>/etc/random.seed</ignore>
    <ignore>/etc/adjtime</ignore>
    <ignore>/etc/httpd/logs</ignore>
    <ignore type="sregex">.log$|.swp$|.tmp$</ignore>
  </syscheck>

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

  <wodle name="vulnerability-detector">
    <disabled>no</disabled>
    <interval>1d</interval>
    <run_on_start>yes</run_on_start>
  </wodle>
</agent_config>
EOF

# ── Запустить ─────────────────────────────────────────────────────
systemctl daemon-reload
systemctl enable --now wazuh-agent

sleep 5
/var/ossec/bin/wazuh-control status

echo ""
echo "✓ Wazuh Agent установлен"
echo "  Проверить регистрацию на Manager:"
echo "  ssh wazuh-vm 'docker exec wazuh.manager /var/ossec/bin/agent_control -l'"
```

### 1.3 Установка Wazuh Agent (Windows)

```powershell
# install_wazuh_agent_windows.ps1
param(
    [string]$WazuhManager = "10.9.0.3",
    [string]$WazuhVersion = "4.7.5"
)

$MsiUrl  = "https://packages.wazuh.com/4.x/windows/wazuh-agent-${WazuhVersion}-1.msi"
$MsiPath = "$env:TEMP\wazuh-agent.msi"

Write-Host "Скачиваю Wazuh Agent v${WazuhVersion}..."
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
Invoke-WebRequest -Uri $MsiUrl -OutFile $MsiPath -UseBasicParsing

$AgentName = $env:COMPUTERNAME

Write-Host "Устанавливаю..."
Start-Process msiexec.exe -ArgumentList @(
    "/i", $MsiPath,
    "/quiet",
    "/norestart",
    "WAZUH_MANAGER=$WazuhManager",
    "WAZUH_AGENT_NAME=$AgentName"
) -Wait

# Добавить FIM правила для 1С (если есть)
$OsSecConf = "C:\Program Files (x86)\ossec-agent\ossec.conf"
if (Test-Path $OsSecConf) {
    # Добавить мониторинг 1С директорий
    $extraConf = @"
  <syscheck>
    <!-- 1С Enterprise directories -->
    <directories check_all="yes">C:\Program Files\1cv8</directories>
    <directories check_all="yes">C:\Program Files (x86)\1cv8</directories>
    <!-- Базы данных 1С -->
    <directories check_all="yes" report_changes="no">C:\Users\*\AppData\Roaming\1C</directories>
    <!-- Windows system -->
    <directories check_all="yes">C:\Windows\System32\drivers\etc</directories>
    <!-- Исключения -->
    <ignore type="sregex">.log$</ignore>
    <ignore type="sregex">.tmp$</ignore>
  </syscheck>
"@
    Write-Host "FIM конфигурация для 1С добавлена"
}

# Запустить службу
Start-Service OssecSvc -ErrorAction SilentlyContinue
Set-Service OssecSvc -StartupType Automatic

Get-Service OssecSvc | Select-Object Name, Status, StartType

Remove-Item $MsiPath -Force
Write-Host "✓ Wazuh Agent установлен"
```

---

## 2. KASPERSKY ENDPOINT SECURITY (Windows)

### 2.1 Развёртывание через GPO (рекомендуется)

```powershell
# kes_deploy_gpo.ps1 — Установка KES через Group Policy
# Запускать на Domain Controller от Domain Admin

# Предварительные требования:
# 1. KSC (Kaspersky Security Center) развёрнут у Исполнителя
# 2. Пакет установки скачан из KSC и скопирован в SYSVOL
# 3. Лицензия активирована на KSC

$KesInstallerPath = "\\domain.local\SYSVOL\domain.local\msp-tools\kes_setup.exe"
$KesResponseFile  = "\\domain.local\SYSVOL\domain.local\msp-tools\kes.ini"

# Создать GPO для установки KES
$Gpo = New-GPO -Name "MSP-KES-Deploy"

# Настроить Software Installation через GPO:
# Computer Configuration → Software Settings → Software Installation → New Package
# Путь: \\domain.local\SYSVOL\domain.local\msp-tools\kes.msi

# Привязать GPO к OU с серверами
New-GPLink -Name "MSP-KES-Deploy" -Target "OU=Servers,DC=domain,DC=local"

Write-Host "GPO MSP-KES-Deploy создан и привязан"
Write-Host "KES установится при следующем обновлении политик (gpupdate /force)"
```

### 2.2 Мониторинг KES через windows_exporter

```powershell
# Скрипт для textfile_collector: monitor_kes.ps1
# Проверяет статус Kaspersky Endpoint Security

$MetricsDir = "C:\Program Files\windows_exporter\textfile_collector"
$OutFile    = "$MetricsDir\kaspersky.prom"
$Hostname   = $env:COMPUTERNAME

# Статус службы KES
$kesSvc = Get-Service -Name "AVP*" -ErrorAction SilentlyContinue | Select-Object -First 1
$kesRunning = if ($kesSvc -and $kesSvc.Status -eq "Running") { 1 } else { 0 }

# Дата последнего обновления баз (из реестра)
$kesRegPath = "HKLM:\SOFTWARE\KasperskyLab\*\*\Statistics\*"
$lastUpdate = try {
    $reg = Get-ItemProperty $kesRegPath -ErrorAction Stop
    $ts = $reg.LastSuccessfulUpdate
    if ($ts) { [DateTimeOffset]::FromFileTime($ts).ToUnixTimeSeconds() } else { 0 }
} catch { 0 }

# Возраст баз в часах
$dbAgeHours = if ($lastUpdate -gt 0) {
    [math]::Round(([DateTimeOffset]::UtcNow.ToUnixTimeSeconds() - $lastUpdate) / 3600, 1)
} else { -1 }

@"
# HELP kaspersky_service_running 1=running 0=stopped
# TYPE kaspersky_service_running gauge
kaspersky_service_running{host="$Hostname"} $kesRunning
# HELP kaspersky_database_age_hours Age of antivirus databases in hours
# TYPE kaspersky_database_age_hours gauge
kaspersky_database_age_hours{host="$Hostname"} $dbAgeHours
# HELP kaspersky_last_update_timestamp Unix timestamp of last database update
# TYPE kaspersky_last_update_timestamp gauge
kaspersky_last_update_timestamp{host="$Hostname"} $lastUpdate
"@ | Set-Content $OutFile -Encoding UTF8
```

---
# ЧАСТЬ 2: ИСПОЛНИТЕЛЬ (GOLD)
---

## 3. WAZUH SIEM — РАЗВЁРТЫВАНИЕ

### 3.1 Wazuh VM требования и создание

```bash
# Wazuh требует минимум 4 vCPU / 8 GB RAM
# OpenSearch (Indexer) требует vm.max_map_count >= 262144

# Создать Wazuh VM
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

WAZUH_IP=$(yc compute instance get msp-wazuh --format json | jq -r '.network_interfaces[0].primary_v4_address.address')
echo "Wazuh VM IP: $WAZUH_IP"

# Назначить VPN IP (например, 10.9.0.3)
# Добавить peer в WireGuard на Bastion...
```

### 3.2 Настройка ОС для Wazuh

```bash
# На Wazuh VM:

# Обязательно для OpenSearch
echo "vm.max_map_count=262144" | sudo tee -a /etc/sysctl.conf
echo "fs.file-max=65536" | sudo tee -a /etc/sysctl.conf
sudo sysctl -p
sysctl vm.max_map_count  # Должно быть 262144

# Базовые пакеты
sudo apt update && sudo apt install -y docker.io docker-compose-plugin curl git jq

sudo usermod -aG docker ubuntu
newgrp docker
```

### 3.3 Docker Compose для Wazuh

```bash
mkdir -p /opt/wazuh
cat > /opt/wazuh/docker-compose.yml << 'EOF'
# Wazuh 4.7 Docker Compose
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
      - "1514:1514"        # Agent TCP
      - "1514:1514/udp"    # Agent UDP
      - "1515:1515"        # Agent enrollment
      - "514:514/udp"      # Syslog
      - "55000:55000"      # REST API
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

  wazuh.indexer:
    image: wazuh/wazuh-indexer:4.7.5
    container_name: wazuh-indexer
    restart: unless-stopped
    ports:
      - "9200:9200"
    environment:
      OPENSEARCH_JAVA_OPTS: "-Xms4g -Xmx4g"
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

  wazuh.dashboard:
    image: wazuh/wazuh-dashboard:4.7.5
    container_name: wazuh-dashboard
    restart: unless-stopped
    ports:
      - "10.9.0.3:443:443"  # Только через VPN!
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

# .env файл
cat > /opt/wazuh/.env << 'EOF'
WAZUH_INDEXER_PASSWORD=REPLACE_STRONG_PASSWORD_HERE
WAZUH_API_PASSWORD=REPLACE_API_PASSWORD_HERE
WAZUH_DASHBOARD_PASSWORD=REPLACE_DASHBOARD_PASSWORD_HERE
EOF
chmod 600 /opt/wazuh/.env

# Запустить
cd /opt/wazuh
docker compose up -d

# Дождаться инициализации (3-5 минут)
echo "Ожидаем инициализации Wazuh..."
sleep 120

# Проверить
docker compose ps
curl -sk https://localhost:9200 -u admin:$(grep WAZUH_INDEXER_PASSWORD /opt/wazuh/.env | cut -d= -f2) | head -5

echo "✓ Wazuh Dashboard: https://10.9.0.3:443"
echo "  Логин: admin / $WAZUH_INDEXER_PASSWORD"
```

---

## 4. ИНТЕГРАЦИЯ WAZUH → ALERTMANAGER

```bash
# На Wazuh Manager — добавить интеграцию с Prometheus/Telegram

cat > /tmp/custom-telegram.py << 'SCRIPT'
#!/usr/bin/env python3
"""
Wazuh → Telegram интеграция
Файл: /var/ossec/integrations/custom-telegram
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

# Формат алерта
level = alert.get("rule", {}).get("level", 0)
rule  = alert.get("rule", {}).get("description", "Unknown")
agent = alert.get("agent", {}).get("name", "Unknown")
data  = alert.get("data", {})

if level < 7:  # Игнорировать низко-приоритетные
    sys.exit(0)

severity = "🔴 CRITICAL" if level >= 12 else "⚠️ WARNING"
message  = f"""
{severity} Wazuh Security Alert

🖥 Agent: {agent}
📋 Rule:  {rule}
📊 Level: {level}
"""

try:
    requests.post(
        f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
        json={"chat_id": CHAT_ID, "text": message},
        timeout=10
    )
except Exception as e:
    print(f"Error: {e}")
SCRIPT

# Скопировать в контейнер
docker cp /tmp/custom-telegram.py wazuh-manager:/var/ossec/integrations/custom-telegram
docker exec wazuh-manager chmod 750 /var/ossec/integrations/custom-telegram
```

---

## 5. OSTICKET — ТИКЕТ-СИСТЕМА

```bash
mkdir -p /opt/osticket
cat > /opt/osticket/docker-compose.yml << 'EOF'
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

  osticket:
    image: osticket/osticket:latest
    container_name: osticket-app
    restart: unless-stopped
    ports:
      - "10.9.0.1:8080:80"  # Только через VPN
    environment:
      MYSQL_HOST: db
      MYSQL_DB: osticket
      MYSQL_USER: osticket
      MYSQL_PASSWORD: ${DB_PASS:?DB_PASS must be set in .env}
      ADMIN_EMAIL: ${ADMIN_EMAIL:-admin@msp.local}
    volumes:
      - osticket_data:/var/www/html/include/ost-config.php
    depends_on:
      - db
    networks: [osticket]
EOF

cat > /opt/osticket/.env << 'EOF'
DB_ROOT_PASS=REPLACE_ROOT_PASSWORD
DB_PASS=REPLACE_DB_PASSWORD
ADMIN_EMAIL=admin@your-domain.ru
EOF
chmod 600 /opt/osticket/.env

cd /opt/osticket
docker compose up -d

echo "✓ osTicket: http://10.9.0.1:8080"
echo "  Завершить установку через веб-интерфейс"
```

---

## 6. ALERT RULES — GOLD (добавочные к Bronze)

```yaml
# Файл: /opt/monitoring/prometheus/rules/gold_alerts.yml

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
          summary: "⚠️ {{ $labels.client_name }} | Wazuh Agent неактивен: {{ $labels.agent_name }}"
          description: |
            Wazuh Agent перестал отправлять данные.
            Проверить на сервере: /var/ossec/bin/wazuh-control status
            На Manager: docker exec wazuh-manager /var/ossec/bin/agent_control -l

      - alert: KasperskyNotRunning
        expr: kaspersky_service_running == 0
        for: 10m
        labels:
          severity: critical
          category: security
        annotations:
          summary: "🔴 {{ $labels.client_name }} | Kaspersky не работает: {{ $labels.host }}"
          description: |
            Антивирусная служба остановлена!
            PowerShell: Start-Service AVP* ; Get-Service AVP*

      - alert: KasperskyDatabaseOld
        expr: kaspersky_database_age_hours > 48
        for: 1h
        labels:
          severity: warning
          category: security
        annotations:
          summary: "⚠️ {{ $labels.client_name }} | Базы Kaspersky устарели: {{ $value | printf \"%.0f\" }} ч"
          description: "Запустить обновление баз через KSC Console или вручную на сервере."

      - alert: HighFailedLoginsLinux
        expr: |
          sum by(instance, client, client_name) (
            rate(node_textfile_scrape_error[5m])
          ) > 10
        for: 5m
        labels:
          severity: warning
          category: security
        annotations:
          summary: "⚠️ {{ $labels.client_name }} | Много неудачных входов SSH: {{ $labels.instance }}"

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
          summary: "⚠️ SLA: алерт не закрыт более 45 минут (P1 SLA = 1 час)"
          description: "Проверить все активные алерты и принять меры."
```

---

## 7. ЧЕКЛИСТ ВЕРИФИКАЦИИ GOLD

```bash
#!/bin/bash
echo "=== ВЕРИФИКАЦИЯ GOLD ==="

# Bronze + Silver
echo "─── Bronze + Silver ───"
systemctl is-active node_exporter   && echo "✅ node_exporter" || echo "❌"
systemctl is-active restic-backup.timer && echo "✅ backup timer" || echo "❌"
systemctl is-active promtail        && echo "✅ promtail" || echo "❌"
systemctl is-active puppet          && echo "✅ puppet" || echo "❌"

# Gold: Wazuh
echo ""
echo "─── Gold компоненты ───"
systemctl is-active wazuh-agent 2>/dev/null && \
    echo "✅ Wazuh Agent" || echo "❌ Wazuh Agent"

/var/ossec/bin/wazuh-control status 2>/dev/null | grep -q "wazuh-modulesd running" && \
    echo "✅ Wazuh модули активны" || echo "⚠️ Wazuh модули"

# Windows: проверить через PowerShell
# Get-Service "OssecSvc" | Select-Object Status
# Get-Service "AVP*" | Select-Object Name, Status

echo ""
echo "=== ВЕРИФИКАЦИЯ ЗАВЕРШЕНА ==="
```
