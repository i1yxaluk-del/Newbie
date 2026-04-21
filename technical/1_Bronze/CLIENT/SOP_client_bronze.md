# SOP — Bronze · Сторона КЛИЕНТА
# Версия 2.0 | Апрель 2026
# ═══════════════════════════════════════════════════════════════════
#
# Документ описывает ВСЁ, что устанавливается и настраивается
# на серверах ЗАКАЗЧИКА в рамках тарифа Bronze.
#
# Принцип: на стороне клиента — только лёгкие агенты.
#           Всё тяжёлое (Prometheus, Grafana, хранилище) — у Исполнителя.
#
# ═══════════════════════════════════════════════════════════════════

## СОДЕРЖАНИЕ

1. Обзор архитектуры
2. Предварительные требования
3. WireGuard VPN-подключение
4. node_exporter (Linux)
5. windows_exporter (Windows)
6. restic Backup
7. Верификация и чеклист
8. Устранение проблем

---

## 1. АРХИТЕКТУРА (BRONZE — КЛИЕНТ)

```
СЕРВЕРЫ ЗАКАЗЧИКА                  YANDEX CLOUD (Исполнитель)
┌─────────────────────────┐        ┌──────────────────────────────┐
│ Linux-серверы            │        │ Monitoring VM                │
│ ├── node_exporter :9100  │◀──────▶│ ├── Prometheus :9090         │
│ ├── restic (backup)      │  VPN   │ ├── Grafana :3000            │
│ └── WireGuard client     │        │ ├── Alertmanager :9093       │
│                          │        │ └── Bastion WireGuard :51820 │
│ Windows-серверы          │        │                              │
│ ├── windows_exporter     │        │ Object Storage (S3)          │
│    :9182                 │        │ └── restic бэкапы клиента    │
│ ├── restic (backup)      │        └──────────────────────────────┘
│ └── WireGuard client     │
└─────────────────────────┘
```

**IP-схема VPN (10.9.0.0/24):**
- 10.9.0.1 — Bastion/Monitoring VM Исполнителя
- 10.9.0.10–19 — Клиент 1 (серверы)
- 10.9.0.20–29 — Клиент 2 (серверы)
- и т.д.

---

## 2. ПРЕДВАРИТЕЛЬНЫЕ ТРЕБОВАНИЯ

### Что нужно от Заказчика:
- [ ] SSH-доступ к Linux-серверам (ключ или пароль)
- [ ] RDP/WinRM-доступ к Windows-серверам
- [ ] Права администратора/sudo
- [ ] Открытый UDP-порт 51820 (WireGuard) исходящий из серверов
- [ ] Интернет-доступ с серверов (для загрузки агентов)

### Что подготавливает Исполнитель перед онбордингом:
- [ ] VPN-IP для каждого сервера (из диапазона 10.9.0.X)
- [ ] Публичный ключ Bastion WireGuard
- [ ] S3-bucket и ключи доступа для бэкапов
- [ ] Пароль restic-репозитория (сохранить в менеджере паролей!)

---

## 3. WIREGUARD VPN — ПОДКЛЮЧЕНИЕ КЛИЕНТА

### 3.1 Схема: зачем VPN

```
БЕЗ VPN (небезопасно):           С VPN (наш подход):
Internet → :9100 (открыт)        Internet → ЗАКРЫТО
Любой может собирать метрики      Prometheus → VPN → :9100
                                  Только Исполнитель видит метрики
```

### 3.2 Linux-сервер: установка WireGuard

```bash
# 1. Установить пакеты
sudo apt update && sudo apt install -y wireguard wireguard-tools

# 2. Сгенерировать ключевую пару (ВЫПОЛНИТЬ НА КАЖДОМ СЕРВЕРЕ)
cd /tmp
wg genkey | tee server_private.key | wg pubkey > server_public.key
chmod 600 server_private.key

# 3. Показать публичный ключ — ОТПРАВИТЬ ИСПОЛНИТЕЛЮ
echo "=== ПУБЛИЧНЫЙ КЛЮЧ (отправить Исполнителю) ==="
cat server_public.key

# 4. Дождаться от Исполнителя:
#    - Assigned VPN IP (например: 10.9.0.10)
#    - Bastion публичный ключ
#    - Bastion публичный IP

# 5. Создать конфиг (заменить ЗНАЧЕНИЯ_В_УГЛОВЫХ_СКОБКАХ)
PRIV_KEY=$(cat /tmp/server_private.key)
CLIENT_VPN_IP="<10.9.0.XX>"         # Назначен Исполнителем
BASTION_PUBKEY="<BASTION_PUBKEY>"   # От Исполнителя
BASTION_IP="<BASTION_PUBLIC_IP>"    # От Исполнителя

sudo tee /etc/wireguard/wg0-msp.conf << EOF
[Interface]
PrivateKey = ${PRIV_KEY}
Address = ${CLIENT_VPN_IP}/32
DNS = 77.88.8.8, 77.88.8.1

[Peer]
PublicKey = ${BASTION_PUBKEY}
Endpoint = ${BASTION_IP}:51820
AllowedIPs = 10.9.0.0/24
PersistentKeepalive = 25
EOF

sudo chmod 600 /etc/wireguard/wg0-msp.conf

# 6. Запустить и включить автозапуск
sudo systemctl enable --now wg-quick@wg0-msp

# 7. Проверить
sudo wg show wg0-msp
ping -c 3 10.9.0.1  # Должен ответить Bastion
```

### 3.3 Windows-сервер: установка WireGuard

```powershell
# 1. Скачать официальный клиент с wireguard.com/install/
# или через winget:
winget install --id WireGuard.WireGuard

# 2. Запустить WireGuard GUI
# 3. "Add Tunnel" → "Add empty tunnel"
# 4. Скопировать содержимое wg0-msp.conf (шаблон от Исполнителя)
# 5. Нажать "Activate"
# 6. Проверить:
ping 10.9.0.1
```

**Шаблон конфига WireGuard для Windows** (заполняет Исполнитель):
```ini
[Interface]
PrivateKey = <GENERATED_PRIVATE_KEY>
Address = 10.9.0.XX/32
DNS = 77.88.8.8, 77.88.8.1

[Peer]
PublicKey = <BASTION_PUBLIC_KEY>
Endpoint = <BASTION_IP>:51820
AllowedIPs = 10.9.0.0/24
PersistentKeepalive = 25
```

---

## 4. NODE_EXPORTER — LINUX

### 4.1 Автоматическая установка (через Ansible — предпочтительно)

```bash
# На Automation VM Исполнителя:
ansible-playbook -i inventory/clients/CLIENT/hosts \
  playbooks/deploy_bronze.yml \
  --tags node_exporter \
  -v
```

### 4.2 Ручная установка (если Ansible недоступен)

```bash
# Запустить скрипт установки:
curl -sSL https://raw.githubusercontent.com/your-repo/msp/main/1_Bronze/CLIENT/node_exporter/install_linux.sh | sudo bash

# Или вручную:
NODE_EXPORTER_VERSION="1.7.0"

# Создать пользователя
sudo useradd --system --no-create-home --shell /sbin/nologin node_exporter

# Скачать
cd /tmp
wget -q "https://github.com/prometheus/node_exporter/releases/download/v${NODE_EXPORTER_VERSION}/node_exporter-${NODE_EXPORTER_VERSION}.linux-amd64.tar.gz"
tar xzf node_exporter-${NODE_EXPORTER_VERSION}.linux-amd64.tar.gz
sudo install -m 0755 node_exporter-${NODE_EXPORTER_VERSION}.linux-amd64/node_exporter /usr/local/bin/
rm -rf /tmp/node_exporter-*

# Директория для кастомных метрик
sudo mkdir -p /var/lib/node_exporter/textfile_collector
sudo chown node_exporter:node_exporter /var/lib/node_exporter/textfile_collector

# Systemd unit
sudo tee /etc/systemd/system/node_exporter.service << 'EOF'
[Unit]
Description=Prometheus Node Exporter
Documentation=https://github.com/prometheus/node_exporter
After=network.target

[Service]
Type=simple
User=node_exporter
Group=node_exporter
ExecStart=/usr/local/bin/node_exporter \
    --web.listen-address=:9100 \
    --web.telemetry-path=/metrics \
    --collector.filesystem.mount-points-exclude=^/(sys|proc|dev|host|etc)($$|/) \
    --collector.textfile.directory=/var/lib/node_exporter/textfile_collector \
    --no-collector.ipvs
Restart=on-failure
RestartSec=5s
NoNewPrivileges=true
ProtectSystem=strict
ProtectHome=read-only
PrivateTmp=true
ReadWritePaths=/var/lib/node_exporter/textfile_collector

[Install]
WantedBy=multi-user.target
EOF

# Firewall: открыть порт 9100 ТОЛЬКО из VPN
sudo ufw allow from 10.9.0.0/24 to any port 9100 proto tcp comment "node_exporter from MSP VPN"

# Запуск
sudo systemctl daemon-reload
sudo systemctl enable --now node_exporter

# Проверка
systemctl status node_exporter
curl -s http://localhost:9100/metrics | grep "^node_uname_info"
```

### 4.3 Верификация

```bash
# Локально:
curl -s http://localhost:9100/metrics | grep -E "^(node_cpu|node_memory|node_filesystem)" | head -5

# С Bastion (должно работать после VPN):
curl -s http://10.9.0.XX:9100/metrics | head -3
```

---

## 5. WINDOWS_EXPORTER

### 5.1 Автоматическая установка (через Ansible + WinRM)

```bash
# На Automation VM:
ansible-playbook -i inventory/clients/CLIENT/hosts \
  playbooks/deploy_bronze.yml \
  --tags windows_exporter \
  -v
```

### 5.2 Ручная установка (PowerShell от Administrator)

```powershell
# Запустить install_windows.ps1 или вручную:

$VERSION = "0.25.1"
$MSI_URL = "https://github.com/prometheus-community/windows_exporter/releases/download/v${VERSION}/windows_exporter-${VERSION}-amd64.msi"
$MSI_PATH = "$env:TEMP\windows_exporter.msi"

# Скачать MSI
Invoke-WebRequest -Uri $MSI_URL -OutFile $MSI_PATH -UseBasicParsing

# Установить с нужными коллекторами
# Collectors:
#   cpu       — загрузка процессора
#   memory    — использование RAM
#   logical_disk — свободное место на дисках
#   service   — статус Windows-служб (КРИТИЧНО для 1С, SQL, AD)
#   process   — метрики процессов (rphost, sqlservr)
#   system    — общие системные метрики (uptime)
#   net       — сетевые интерфейсы
#   os        — информация об ОС
#   textfile  — кастомные метрики (скрипты бэкапа, 1С)

Start-Process msiexec.exe -ArgumentList @(
    "/i", $MSI_PATH,
    "/quiet", "/norestart",
    'ENABLED_COLLECTORS="cpu,memory,logical_disk,service,process,system,net,os,textfile"',
    'LISTEN_PORT=9182',
    'EXTRA_FLAGS="--collector.textfile.directory=C:\Program Files\windows_exporter\textfile_collector"'
) -Wait -NoNewWindow

# Создать директорию для textfile_collector
New-Item -ItemType Directory -Force -Path "C:\Program Files\windows_exporter\textfile_collector" | Out-Null

# Настроить Firewall — разрешить ТОЛЬКО из VPN-подсети
Remove-NetFirewallRule -DisplayName "windows_exporter MSP" -ErrorAction SilentlyContinue
New-NetFirewallRule `
    -DisplayName "windows_exporter MSP" `
    -Direction Inbound `
    -Protocol TCP `
    -LocalPort 9182 `
    -RemoteAddress "10.9.0.0/24" `
    -Action Allow `
    -Profile Any

# Убедиться что служба запущена
Start-Service windows_exporter -ErrorAction SilentlyContinue
Set-Service windows_exporter -StartupType Automatic

# Удалить MSI
Remove-Item $MSI_PATH -Force

# Проверка
Get-Service windows_exporter | Select-Object Name, Status, StartType
Invoke-WebRequest -Uri "http://localhost:9182/metrics" -UseBasicParsing | Select-Object -ExpandProperty StatusCode
```

### 5.3 Textfile Collector для 1С

```powershell
# Скрипт мониторинга сессий 1С
# Файл: C:\msp-scripts\monitor_1c.ps1

$MetricsDir = "C:\Program Files\windows_exporter\textfile_collector"
$OutFile = "$MetricsDir\1c_sessions.prom"

# Количество активных процессов rphost (каждый = рабочий процесс 1С)
$rphostCount = (Get-Process -Name "rphost" -ErrorAction SilentlyContinue | Measure-Object).Count
$rphostMem   = (Get-Process -Name "rphost" -ErrorAction SilentlyContinue | Measure-Object WorkingSet64 -Sum).Sum / 1MB

$content = @"
# HELP onec_rphost_count Number of active 1C rphost processes
# TYPE onec_rphost_count gauge
onec_rphost_count{host="$env:COMPUTERNAME"} $rphostCount
# HELP onec_rphost_memory_mb Total RAM used by 1C rphost processes (MB)
# TYPE onec_rphost_memory_mb gauge
onec_rphost_memory_mb{host="$env:COMPUTERNAME"} $([math]::Round($rphostMem, 1))
"@

Set-Content -Path $OutFile -Value $content -Encoding UTF8

# Добавить в Task Scheduler:
# Действие: powershell.exe -ExecutionPolicy Bypass -File "C:\msp-scripts\monitor_1c.ps1"
# Расписание: каждые 5 минут
```

---

## 6. RESTIC BACKUP

### 6.1 Подготовка (делает Исполнитель)

Перед установкой restic на сервер клиента Исполнитель:
1. Создаёт S3-bucket: `yc storage bucket create --name backup-CLIENT_NAME`
2. Создаёт ключи доступа
3. Генерирует и сохраняет пароль репозитория: `openssl rand -hex 32`
4. Передаёт клиенту: `env.sh` с ключами и паролем (через защищённый канал)

### 6.2 Установка на Linux

```bash
# Запустить install_linux.sh или вручную:

RESTIC_VERSION="0.16.4"

# Установка
sudo wget -q -O /usr/local/bin/restic \
  "https://github.com/restic/restic/releases/download/v${RESTIC_VERSION}/restic_${RESTIC_VERSION}_linux_amd64.bz2" | \
  bunzip2 -c | sudo tee /usr/local/bin/restic > /dev/null

# Альтернатива (через apt):
# sudo apt install -y restic

sudo chmod +x /usr/local/bin/restic
restic version

# Создать директории
sudo mkdir -p /opt/restic-scripts
sudo mkdir -p /etc/restic

# Файл с переменными окружения (ЗАПОЛНИТЬ РЕАЛЬНЫМИ ЗНАЧЕНИЯМИ)
sudo tee /etc/restic/env.sh << 'EOF'
export AWS_ACCESS_KEY_ID="ЗАМЕНИТЬ_НА_РЕАЛЬНЫЙ_КЛЮЧ"
export AWS_SECRET_ACCESS_KEY="ЗАМЕНИТЬ_НА_РЕАЛЬНЫЙ_СЕКРЕТ"
export RESTIC_REPOSITORY="s3:https://storage.yandexcloud.net/BUCKET_NAME"
export RESTIC_PASSWORD="ЗАМЕНИТЬ_НА_ПАРОЛЬ_РЕПОЗИТОРИЯ"
EOF
sudo chmod 600 /etc/restic/env.sh

# Файл исключений
sudo tee /opt/restic-scripts/excludes.txt << 'EOF'
/proc
/sys
/dev
/run
/tmp
/var/cache
/var/tmp
/var/lib/docker
/lost+found
*.sock
*.pid
*.swap
/var/lib/apt/lists
EOF

# Скрипт бэкапа
sudo tee /opt/restic-scripts/backup.sh << 'SCRIPT'
#!/bin/bash
set -euo pipefail

LOG="/var/log/restic-backup.log"
METRICS_DIR="/var/lib/node_exporter/textfile_collector"
METRICS_FILE="${METRICS_DIR}/restic_backup.prom"
TIMESTAMP=$(date +%s)
HOSTNAME=$(hostname -f)

log() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" | tee -a "$LOG"; }

# Загрузить переменные
source /etc/restic/env.sh

log "=== START BACKUP ==="

# Определить пути для бэкапа
BACKUP_PATHS="/etc /home /root /opt /srv /var/www"

# Запустить бэкап
if restic backup $BACKUP_PATHS \
    --exclude-file=/opt/restic-scripts/excludes.txt \
    --tag "auto" \
    --tag "$(hostname)" \
    --verbose 2>&1 | tee -a "$LOG"; then

    STATUS=1
    log "SUCCESS"
else
    STATUS=0
    log "FAILED"
fi

# Очистить старые снапшоты
restic forget \
    --keep-daily 7 \
    --keep-weekly 4 \
    --keep-monthly 6 \
    --keep-yearly 1 \
    --prune 2>&1 | tee -a "$LOG"

# Записать метрики для Prometheus
mkdir -p "$METRICS_DIR"
cat > "$METRICS_FILE" << EOF
# HELP restic_backup_last_status Status of last restic backup (1=success, 0=failure)
# TYPE restic_backup_last_status gauge
restic_backup_last_status{host="${HOSTNAME}"} ${STATUS}
# HELP restic_backup_last_timestamp_seconds Unix timestamp of last backup attempt
# TYPE restic_backup_last_timestamp_seconds gauge
restic_backup_last_timestamp_seconds{host="${HOSTNAME}"} ${TIMESTAMP}
EOF

log "=== END BACKUP (status=${STATUS}) ==="
SCRIPT
sudo chmod +x /opt/restic-scripts/backup.sh

# Systemd service
sudo tee /etc/systemd/system/restic-backup.service << 'EOF'
[Unit]
Description=Restic Backup to Yandex Object Storage
After=network-online.target
Wants=network-online.target

[Service]
Type=oneshot
EnvironmentFile=/etc/restic/env.sh
ExecStart=/opt/restic-scripts/backup.sh
Nice=19
IOSchedulingClass=idle
TimeoutStartSec=7200
StandardOutput=journal
StandardError=journal
SyslogIdentifier=restic-backup

[Install]
WantedBy=multi-user.target
EOF

# Systemd timer (ежедневно в 02:00, randomized +/- 5 мин)
sudo tee /etc/systemd/system/restic-backup.timer << 'EOF'
[Unit]
Description=Restic Backup Timer
Requires=restic-backup.service

[Timer]
OnCalendar=*-*-* 02:00:00
RandomizedDelaySec=300
Persistent=true
AccuracySec=1s

[Install]
WantedBy=timers.target
EOF

# Инициализировать репозиторий (ОДИН РАЗ!)
source /etc/restic/env.sh
restic init
echo "Репозиторий инициализирован: $(date)"

# Запустить
sudo systemctl daemon-reload
sudo systemctl enable --now restic-backup.timer

# Тест
sudo systemctl start restic-backup.service
sudo systemctl status restic-backup.service
restic snapshots
```

### 6.3 Установка на Windows

```powershell
# Скрипт: install_windows.ps1

$ResticVersion = "0.16.4"
$ResticDir = "C:\Program Files\restic"
$ScriptsDir = "C:\msp-scripts"
$LogDir = "C:\ProgramData\msp-logs"

# Создать директории
New-Item -ItemType Directory -Force -Path $ResticDir, $ScriptsDir, $LogDir | Out-Null

# Скачать restic
$ResticURL = "https://github.com/restic/restic/releases/download/v${ResticVersion}/restic_${ResticVersion}_windows_amd64.zip"
$ZipPath = "$env:TEMP\restic.zip"
Invoke-WebRequest -Uri $ResticURL -OutFile $ZipPath -UseBasicParsing
Expand-Archive -Path $ZipPath -DestinationPath $ResticDir -Force
Remove-Item $ZipPath

# Переименовать exe
$exeFile = Get-ChildItem "$ResticDir\restic*.exe" | Select-Object -First 1
Rename-Item $exeFile.FullName "$ResticDir\restic.exe" -Force

# Добавить в PATH
$EnvPath = [System.Environment]::GetEnvironmentVariable("Path", "Machine")
if ($EnvPath -notlike "*$ResticDir*") {
    [System.Environment]::SetEnvironmentVariable("Path", "$EnvPath;$ResticDir", "Machine")
}

# Файл конфигурации бэкапа
$EnvFile = "C:\msp-scripts\backup-env.ps1"
@'
# ЗАПОЛНИТЬ РЕАЛЬНЫМИ ЗНАЧЕНИЯМИ (получить от Исполнителя)
$env:AWS_ACCESS_KEY_ID     = "REPLACE_WITH_REAL_KEY"
$env:AWS_SECRET_ACCESS_KEY = "REPLACE_WITH_REAL_SECRET"
$env:RESTIC_REPOSITORY     = "s3:https://storage.yandexcloud.net/BUCKET_NAME"
$env:RESTIC_PASSWORD       = "REPLACE_WITH_REPO_PASSWORD"
'@ | Set-Content $EnvFile -Encoding UTF8

# Скрипт бэкапа
@'
# MSP Backup Script для Windows
# Файл: C:\msp-scripts\backup.ps1

param([switch]$Force)

# Загрузить конфигурацию
. "C:\msp-scripts\backup-env.ps1"

$LogFile    = "C:\ProgramData\msp-logs\restic-backup.log"
$MetricsDir = "C:\Program Files\windows_exporter\textfile_collector"
$MetricsFile= "$MetricsDir\restic_backup.prom"
$Hostname   = $env:COMPUTERNAME
$Timestamp  = [DateTimeOffset]::UtcNow.ToUnixTimeSeconds()

function Log { param($msg) $line = "[$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')] $msg"; Add-Content $LogFile $line; Write-Output $line }

Log "=== START BACKUP ==="

# Пути для бэкапа (настроить под реальную инфраструктуру)
$BackupPaths = @("C:\Users", "C:\inetpub", "C:\Backup")

# Исключения
$ExcludeArgs = @(
    "--exclude", "*.tmp",
    "--exclude", "*.log",
    "--exclude", "pagefile.sys",
    "--exclude", "hiberfil.sys",
    "--exclude", "$env:WINDIR\Temp"
)

# Запуск бэкапа
$Args = @("backup") + $BackupPaths + $ExcludeArgs + @("--tag", "auto", "--tag", $Hostname, "--verbose")
& "C:\Program Files\restic\restic.exe" @Args 2>&1 | Tee-Object -FilePath $LogFile -Append

$Status = if ($LASTEXITCODE -eq 0) { 1 } else { 0 }

if ($Status -eq 0) {
    Log "BACKUP FAILED! Exit code: $LASTEXITCODE"
} else {
    Log "BACKUP SUCCESS"
}

# Очистить старые снапшоты
& "C:\Program Files\restic\restic.exe" forget --keep-daily 7 --keep-weekly 4 --keep-monthly 6 --prune 2>&1 | Tee-Object -FilePath $LogFile -Append

# Записать метрики
if (-not (Test-Path $MetricsDir)) { New-Item -ItemType Directory -Force -Path $MetricsDir | Out-Null }

@"
# HELP restic_backup_last_status Status of last backup (1=success 0=failure)
# TYPE restic_backup_last_status gauge
restic_backup_last_status{host="$Hostname"} $Status
# HELP restic_backup_last_timestamp_seconds Unix timestamp of last attempt
# TYPE restic_backup_last_timestamp_seconds gauge
restic_backup_last_timestamp_seconds{host="$Hostname"} $Timestamp
"@ | Set-Content $MetricsFile -Encoding UTF8

Log "=== END BACKUP (status=$Status) ==="
'@ | Set-Content "$ScriptsDir\backup.ps1" -Encoding UTF8

# Создать Scheduled Task (ежедневно в 02:00)
$Action  = New-ScheduledTaskAction -Execute "powershell.exe" -Argument "-NonInteractive -ExecutionPolicy Bypass -File `"C:\msp-scripts\backup.ps1`""
$Trigger = New-ScheduledTaskTrigger -Daily -At "02:00"
$Settings= New-ScheduledTaskSettingsSet -ExecutionTimeLimit (New-TimeSpan -Hours 4) -RunOnlyIfNetworkAvailable $true

Register-ScheduledTask `
    -TaskName "MSP-ResticBackup" `
    -Action $Action `
    -Trigger $Trigger `
    -Settings $Settings `
    -User "SYSTEM" `
    -RunLevel Highest `
    -Force | Out-Null

# Инициализировать репозиторий (ОДИН РАЗ)
. "C:\msp-scripts\backup-env.ps1"
& "C:\Program Files\restic\restic.exe" init

Write-Host "✅ Backup настроен. Первый запуск: $(Get-Date -Format 'yyyy-MM-dd') 02:00"
```

---

## 7. ЧЕКЛИСТ ВЕРИФИКАЦИИ (Bronze Client)

```bash
#!/bin/bash
# Запускать на каждом сервере после установки

echo "=== ВЕРИФИКАЦИЯ BRONZE CLIENT ==="
echo "Сервер: $(hostname)"
echo "Дата: $(date)"
echo ""

# 1. WireGuard VPN
echo -n "1. WireGuard VPN... "
if sudo wg show wg0-msp 2>/dev/null | grep -q "latest handshake"; then
    HS=$(sudo wg show wg0-msp | grep "latest handshake" | awk '{print $3,$4,$5}')
    echo "✅ OK (handshake: $HS)"
else
    echo "❌ ПРОБЛЕМА — туннель не активен"
fi

# 2. Связь с Bastion
echo -n "2. Связь с Bastion... "
if ping -c 2 -W 3 10.9.0.1 &>/dev/null; then
    echo "✅ OK"
else
    echo "❌ ПРОБЛЕМА — нет ответа от 10.9.0.1"
fi

# 3. node_exporter
echo -n "3. node_exporter... "
if systemctl is-active --quiet node_exporter; then
    METRICS=$(curl -s http://localhost:9100/metrics | wc -l)
    echo "✅ OK (${METRICS} метрик)"
else
    echo "❌ ПРОБЛЕМА — сервис не запущен"
fi

# 4. Метрики доступны из VPN
echo -n "4. Метрики из VPN... "
MY_VPN_IP=$(ip addr show wg0-msp 2>/dev/null | grep "inet " | awk '{print $2}' | cut -d/ -f1)
if curl -s --max-time 5 "http://${MY_VPN_IP}:9100/metrics" | head -1 | grep -q "^#"; then
    echo "✅ OK (IP: ${MY_VPN_IP})"
else
    echo "❌ ПРОБЛЕМА — метрики недоступны из VPN"
fi

# 5. Restic backup service
echo -n "5. Restic timer... "
if systemctl is-enabled --quiet restic-backup.timer; then
    NEXT=$(systemctl list-timers restic-backup.timer --no-legend | awk '{print $1,$2}')
    echo "✅ OK (следующий запуск: $NEXT)"
else
    echo "❌ ПРОБЛЕМА — таймер не включён"
fi

# 6. Репозиторий бэкапов
echo -n "6. Restic репозиторий... "
source /etc/restic/env.sh 2>/dev/null
if restic snapshots --quiet 2>/dev/null | head -1; then
    SNAP_COUNT=$(restic snapshots --quiet 2>/dev/null | grep -c "^[a-f0-9]" || echo 0)
    echo "✅ OK (снапшотов: $SNAP_COUNT)"
else
    echo "❌ ПРОБЛЕМА — репозиторий недоступен"
fi

echo ""
echo "=== ВЕРИФИКАЦИЯ ЗАВЕРШЕНА ==="
```

---

## 8. УСТРАНЕНИЕ ПРОБЛЕМ

| Проблема | Диагностика | Решение |
|---|---|---|
| VPN нет handshake | `sudo wg show wg0-msp` | Проверить endpoint IP/port, перезапустить: `systemctl restart wg-quick@wg0-msp` |
| node_exporter не запускается | `journalctl -u node_exporter -n 50` | Проверить права, пересоздать systemd unit |
| Метрики недоступны из VPN | `ufw status` | Добавить правило: `ufw allow from 10.9.0.0/24 to any port 9100` |
| Бэкап падает | `journalctl -u restic-backup -n 100` | Проверить ключи S3, свободное место, сеть |
| S3 недоступен | `curl -I https://storage.yandexcloud.net` | Проверить интернет, DNS, ключи в env.sh |
| Порт 9100 занят | `ss -tlnp \| grep 9100` | Убить конкурирующий процесс |
