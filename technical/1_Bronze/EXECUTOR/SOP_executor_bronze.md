# SOP — Bronze · Сторона ИСПОЛНИТЕЛЯ
# Версия 3.0 | PowerShell-first (Windows 10 admin workstation)
# ═══════════════════════════════════════════════════════════════════
#
# Документ описывает ВСЁ, что разворачивается на стороне ИСПОЛНИТЕЛЯ
# для обеспечения тарифа Bronze (и является фундаментом для Silver/Gold).
#
# Архитектура (без изменений):
#   - Рабочая станция администратора: Windows 10 / 11 + PowerShell
#   - Cloud-площадка: Yandex Cloud (ru-central1), Ubuntu 22.04 LTS VM
#   - Клиенты: Linux/Windows, подключаются по WireGuard
#
# Все блоки бывают двух типов:
#   • PowerShell (` ```powershell `) — выполняются на Win10 ноутбуке.
#   • Bash (` ```bash `) — выполняются на Ubuntu VM (через SSH-сессию,
#     которую открывает PowerShell). Bash-блоки запускаются либо после
#     `ssh ubuntu@$VmIp`, либо через here-string `$bash | ssh ... bash -s`.
# ═══════════════════════════════════════════════════════════════════

## СОДЕРЖАНИЕ

0. Рабочая станция администратора (Windows 10)
1. Архитектура Исполнителя
2. Развёртывание VM в Yandex Cloud (из PowerShell)
3. Базовая настройка ОС (Ubuntu VM)
4. WireGuard Bastion Server
5. Docker Compose — Мониторинг стек
6. Добавление клиента (PowerShell-обёртка + bash-скрипт на VM)
7. Еженедельный отчёт
8. Обслуживание и мониторинг стека

---

## 0. РАБОЧАЯ СТАНЦИЯ АДМИНИСТРАТОРА (Windows 10)

### 0.1. Что должно быть установлено

| Компонент          | Источник                                                | Проверка                         |
|--------------------|----------------------------------------------------------|----------------------------------|
| Windows            | 10 build 1803+ / Windows 11                              | `winver`                         |
| PowerShell         | 5.1 (встроен) или 7+ (`winget install Microsoft.PowerShell`) | `$PSVersionTable.PSVersion`      |
| OpenSSH Client     | Встроен в Win10 1803+ (`Settings → Apps → Optional features`) | `Get-Command ssh`                |
| `yc` CLI           | См. §0.3                                                 | `yc version`                     |
| Git for Windows    | `winget install Git.Git`                                 | `git --version`                  |
| tar                | Встроен в Win10 17063+                                   | `tar --version`                  |

### 0.2. Профиль PowerShell и кодировка

Русские/UTF-8 символы в выводе требуют корректной кодировки консоли — иначе
получите `вњ“`, `вЊ©` и `ArgumentOutOfRangeException` в скриптах:

```powershell
# Один раз — в $PROFILE
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$OutputEncoding = [System.Text.Encoding]::UTF8

# Проверка
[Console]::OutputEncoding.CodePage   # должно быть 65001
```

Откройте профиль:
```powershell
if (-not (Test-Path $PROFILE)) { New-Item -ItemType File -Path $PROFILE -Force }
notepad $PROFILE
```

### 0.3. Установка `yc` CLI на Windows

```powershell
# Через PowerShell (официальный installer Яндекса для Windows)
Invoke-WebRequest -Uri "https://storage.yandexcloud.net/yandexcloud-yc/install.ps1" `
    -OutFile "$env:TEMP\yc-install.ps1"
& powershell -ExecutionPolicy Bypass -File "$env:TEMP\yc-install.ps1"

# Перезапустить PowerShell-сессию, затем проверить:
yc version
yc init   # OAuth-авторизация в браузере
yc config list
```

### 0.4. SSH-ключ для управления VM

```powershell
# Ключ для управления Yandex Cloud VM
$SshKeyDir = "$env:USERPROFILE\.ssh"
if (-not (Test-Path $SshKeyDir)) { New-Item -ItemType Directory -Path $SshKeyDir -Force }

ssh-keygen -t ed25519 -f "$SshKeyDir\id_ed25519_yc" -N '""' -C "msp-admin@$env:COMPUTERNAME"

# Публичный ключ — будем класть в `--ssh-key` при создании VM
Get-Content "$SshKeyDir\id_ed25519_yc.pub"
```

### 0.5. Шаблон рабочих переменных (положить в $PROFILE)

```powershell
# Постоянные переменные сессии — для всех команд ниже
$Env:MSP_FOLDER_ID = "<folder-id-из-yc-config-list>"
$Env:MSP_ZONE      = "ru-central1-a"
$Env:MSP_SSH_KEY   = "$env:USERPROFILE\.ssh\id_ed25519_yc"
$Env:MSP_VM_NAME   = "msp-monitoring"

# Helper-функция: открыть SSH в управляющую VM
function msp-ssh { ssh -i $Env:MSP_SSH_KEY ubuntu@$Env:MSP_VM_IP @args }

# Helper: выполнить bash-блок на VM через here-string
function msp-bash {
    param([Parameter(Mandatory)][string]$Script)
    $Script | ssh -i $Env:MSP_SSH_KEY ubuntu@$Env:MSP_VM_IP bash -s
}
```

---

## 1. АРХИТЕКТУРА

```
WINDOWS 10 АДМИН-СТАНЦИЯ                       YANDEX CLOUD ru-central1-a
┌──────────────────────────┐                   ┌───────────────────────────────────────────────────────────────┐
│  PowerShell 5.1 / 7      │   yc CLI / SSH    │ msp-monitoring VM (burst 5-20%, 2vCPU, 4GB, 40GB)             │
│   yc CLI                 │ ─────────────────▶│                                                               │
│   OpenSSH client         │                   │ ┌─────────────────────────────────────────────────────────┐  │
│   Git for Windows        │                   │ │ Docker Compose (profile: monitoring)                    │  │
└──────────────────────────┘                   │ │ ├── Prometheus    :9090  ← scrapes client exporters     │  │
                                               │ │ ├── Alertmanager  :9093  ← routes alerts to Telegram    │  │
                                               │ │ ├── Grafana       :3000  ← dashboards (не открыт наружу)│  │
                                               │ │ ├── node-exporter :9100  ← метрики самой VM             │  │
                                               │ │ └── cAdvisor      :8080  ← метрики Docker               │  │
                                               │ └─────────────────────────────────────────────────────────┘  │
                                               │                                                               │
                                               │ Хост (Ubuntu 22.04 LTS):                                     │
                                               │ ├── WireGuard :51820/udp   ← VPN для клиентов               │
                                               │ ├── ufw / nftables         ← firewall                        │
                                               │ ├── fail2ban               ← защита SSH                      │
                                               │ └── SSH :22                ← только из доверенных IP         │
                                               └───────────────────────────────────────────────────────────────┘
                                                        ↑            ↑            ↑
                                                   10.9.0.10    10.9.0.20    10.9.0.30     ← Клиенты через VPN
                                                  (Bronze-1)  (Bronze-2)  (Bronze-3)

                                               Yandex Object Storage:
                                               └── backup-CLIENT_NAME/   ← restic репозитории клиентов
```

---

## 2. РАЗВЁРТЫВАНИЕ VM В YANDEX CLOUD (из PowerShell)

### 2.1. OAuth-авторизация и folder

```powershell
yc init                                                     # OAuth в браузере
yc config list                                              # запомните folder-id

# Или явно:
$folderId = (yc config get folder-id).Trim()
$Env:MSP_FOLDER_ID = $folderId
```

### 2.2. Создание VM (one-liner)

```powershell
$SshPubKey = Get-Content "$Env:MSP_SSH_KEY.pub" -Raw

yc compute instance create `
    --name $Env:MSP_VM_NAME `
    --folder-id $Env:MSP_FOLDER_ID `
    --zone $Env:MSP_ZONE `
    --network-interface "subnet-name=default,nat-ip-version=ipv4" `
    --create-boot-disk "image-family=ubuntu-2204-lts,size=40GB,type=network-ssd,auto-delete=true" `
    --cores 2 `
    --core-fraction 20 `
    --memory 4GB `
    --ssh-key "$Env:MSP_SSH_KEY.pub" `
    --metadata serial-port-enable=1

# Получить public IP
$vm = yc compute instance get $Env:MSP_VM_NAME --format json | ConvertFrom-Json
$Env:MSP_VM_IP = $vm.network_interfaces[0].primary_v4_address.one_to_one_nat.address
Write-Host "VM IP: $Env:MSP_VM_IP"
```

> `core-fraction 20` = «burst до 20%», подходит для Bronze с <5 клиентами.
> Для production без burst — уберите `--core-fraction`.
> Для тестов добавьте `--preemptible` (прерываемая, скидка 70%, **не для prod**).

### 2.3. S3-bucket и ключи для restic-бэкапов

```powershell
# Сервисный аккаунт
yc iam service-account create --name msp-backup-sa --folder-id $Env:MSP_FOLDER_ID

$saId = (yc iam service-account get msp-backup-sa --folder-id $Env:MSP_FOLDER_ID --format json | ConvertFrom-Json).id

# Роль на каталог
yc resource-manager folder add-access-binding $Env:MSP_FOLDER_ID `
    --role storage.editor `
    --subject "serviceAccount:$saId"

# Статический S3-ключ
$keys = yc iam access-key create --service-account-name msp-backup-sa --format json | ConvertFrom-Json

# Сохранить в защищённом каталоге (НЕ коммитить!)
$secretsDir = "$env:USERPROFILE\.msp-secrets"
if (-not (Test-Path $secretsDir)) { New-Item -ItemType Directory -Path $secretsDir -Force | Out-Null }
$keys | ConvertTo-Json -Depth 5 | Set-Content "$secretsDir\s3-keys.json" -Encoding UTF8
Write-Host "Access-key ID:  $($keys.access_key.key_id)"
Write-Host "Secret saved:   $secretsDir\s3-keys.json"
```

Создание bucket-а под клиента (повторяется при каждом онбординге):
```powershell
function New-MspBackupBucket {
    param([Parameter(Mandatory)][string]$ClientSlug)
    yc storage bucket create `
        --name "backup-$ClientSlug" `
        --default-storage-class standard `
        --max-size 107374182400        # 100 GB
    Write-Host "Bucket: backup-$ClientSlug"
}
# Пример: New-MspBackupBucket -ClientSlug company-name
```

---

## 3. БАЗОВАЯ НАСТРОЙКА ОС (Ubuntu VM)

PowerShell открывает SSH-сессию; всё, что внутри here-string — выполняется
на Linux:

```powershell
$bash = @'
set -euo pipefail

# Обновление
sudo apt update && sudo apt upgrade -y
sudo apt install -y \
    curl wget git nano htop iotop \
    chrony ufw fail2ban jq \
    wireguard wireguard-tools

# Часовой пояс
sudo timedatectl set-timezone Europe/Moscow
sudo systemctl enable --now chrony
chronyc tracking || true

# SSH hardening
sudo sed -i 's/^#*PermitRootLogin.*/PermitRootLogin no/'         /etc/ssh/sshd_config
sudo sed -i 's/^#*PasswordAuthentication.*/PasswordAuthentication no/' /etc/ssh/sshd_config
sudo sed -i 's/^#*MaxAuthTries.*/MaxAuthTries 3/'                /etc/ssh/sshd_config
sudo systemctl restart sshd

# fail2ban
sudo tee /etc/fail2ban/jail.local >/dev/null << 'EOF'
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

# UFW Firewall
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow 22/tcp     comment "SSH"
sudo ufw allow 51820/udp  comment "WireGuard VPN"
sudo ufw --force enable
sudo ufw status verbose

# Docker
curl -fsSL https://get.docker.com | sudo sh
sudo usermod -aG docker ubuntu
docker --version
'@
$bash | ssh -i $Env:MSP_SSH_KEY ubuntu@$Env:MSP_VM_IP bash -s
```

Дальше для удобства можно открывать обычный интерактивный SSH:
```powershell
ssh -i $Env:MSP_SSH_KEY ubuntu@$Env:MSP_VM_IP
```

---

## 4. WIREGUARD BASTION SERVER

### 4.1. Генерация ключей сервера (на VM)

```powershell
$bash = @'
set -euo pipefail
cd /etc/wireguard
sudo wg genkey | sudo tee server_private.key | sudo wg pubkey | sudo tee server_public.key >/dev/null
sudo chmod 600 server_private.key

echo "=== BASTION PUBLIC KEY ==="
sudo cat server_public.key
'@
$bash | ssh -i $Env:MSP_SSH_KEY ubuntu@$Env:MSP_VM_IP bash -s
```

Сохраните вывод в безопасное место:
```powershell
$ServerPubKey = (msp-bash 'sudo cat /etc/wireguard/server_public.key').Trim()
$ServerPubKey | Set-Content "$env:USERPROFILE\.msp-secrets\bastion_pubkey.txt"
```

### 4.2. Конфигурация WireGuard

```powershell
$bash = @'
set -euo pipefail

PRIV=$(sudo cat /etc/wireguard/server_private.key)

sudo tee /etc/wireguard/wg0.conf >/dev/null << EOF
[Interface]
PrivateKey = $PRIV
Address    = 10.9.0.1/24
ListenPort = 51820
SaveConfig = false
PostUp     = iptables -A FORWARD -i %i -j ACCEPT; iptables -t nat -A POSTROUTING -o eth0 -j MASQUERADE
PostDown   = iptables -D FORWARD -i %i -j ACCEPT; iptables -t nat -D POSTROUTING -o eth0 -j MASQUERADE

# === PEERS КЛИЕНТОВ (добавлять при онбординге) ===
EOF
sudo chmod 600 /etc/wireguard/wg0.conf

echo "net.ipv4.ip_forward=1" | sudo tee /etc/sysctl.d/99-wireguard.conf
sudo sysctl -p /etc/sysctl.d/99-wireguard.conf

sudo systemctl enable --now wg-quick@wg0
sudo wg show wg0
'@
$bash | ssh -i $Env:MSP_SSH_KEY ubuntu@$Env:MSP_VM_IP bash -s
```

### 4.3. Скрипт добавления peer-а на VM

```powershell
$addPeer = @'
sudo tee /usr/local/bin/add_vpn_peer.sh >/dev/null << 'SCRIPT'
#!/bin/bash
# add_vpn_peer.sh CLIENT_SLUG VPN_IP CLIENT_PUBKEY
set -euo pipefail
CLIENT="${1:?Usage: $0 CLIENT_SLUG VPN_IP CLIENT_PUBKEY}"
VPN_IP="${2:?}"
CLIENT_PUBKEY="${3:?}"
CONFIG="/etc/wireguard/wg0.conf"

cat >> "$CONFIG" << EOF

# === ${CLIENT} ===
[Peer]
PublicKey  = ${CLIENT_PUBKEY}
AllowedIPs = ${VPN_IP}/32
EOF

wg set wg0 peer "$CLIENT_PUBKEY" allowed-ips "${VPN_IP}/32"
echo "OK: ${CLIENT} -> ${VPN_IP}"
SCRIPT
sudo chmod +x /usr/local/bin/add_vpn_peer.sh
'@
$addPeer | ssh -i $Env:MSP_SSH_KEY ubuntu@$Env:MSP_VM_IP bash -s
```

PowerShell-обёртка для запуска (с Win10-ноутбука):
```powershell
function Add-MspVpnPeer {
    param(
        [Parameter(Mandatory)][string]$ClientSlug,
        [Parameter(Mandatory)][string]$VpnIp,
        [Parameter(Mandatory)][string]$ClientPubKey
    )
    $cmd = "sudo /usr/local/bin/add_vpn_peer.sh '$ClientSlug' '$VpnIp' '$ClientPubKey'"
    ssh -i $Env:MSP_SSH_KEY ubuntu@$Env:MSP_VM_IP $cmd
}
# Пример: Add-MspVpnPeer -ClientSlug company1 -VpnIp 10.9.0.10 -ClientPubKey 'abc123...'
```

---

## 5. DOCKER COMPOSE — МОНИТОРИНГ СТЕК

### 5.1. Подготовка структуры

```powershell
msp-bash 'sudo mkdir -p /opt/monitoring/{prometheus/rules,alertmanager,grafana/provisioning/{datasources,dashboards},loki}'
msp-bash 'sudo chown -R ubuntu:ubuntu /opt/monitoring'
```

### 5.2. Локальное редактирование + scp на VM

Конфиги хранятся в репозитории `i1yxaluk-del/Newbie`. Клонируйте локально и
заливайте на VM:

```powershell
git clone https://github.com/i1yxaluk-del/Newbie $env:USERPROFILE\Newbie
cd $env:USERPROFILE\Newbie\technical\1_Bronze\EXECUTOR\monitoring-stack

# Залить весь каталог на VM (через scp с тем же ключом)
scp -i $Env:MSP_SSH_KEY -r .\* ubuntu@$Env:MSP_VM_IP:/opt/monitoring/
```

### 5.3. .env (генерация на VM)

```powershell
$envScript = @'
cd /opt/monitoring
GRAFANA_PWD=$(openssl rand -base64 32)
cat > .env << EOF
PROMETHEUS_VERSION=v2.51.0
ALERTMANAGER_VERSION=v0.27.0
GRAFANA_VERSION=10.4.2
NODE_EXPORTER_VERSION=v1.7.0
CADVISOR_VERSION=v0.49.1
LOKI_VERSION=3.0.0
PROMTAIL_VERSION=3.0.0

GRAFANA_ADMIN_USER=admin
GRAFANA_ADMIN_PASSWORD=$GRAFANA_PWD

TELEGRAM_BOT_TOKEN=REPLACE_WITH_BOT_TOKEN
TELEGRAM_CHAT_ID=REPLACE_WITH_CHAT_ID

# Email backup-канал (через Stalwart submit-only :587, не :25 — Yandex Cloud)
SMTP_HOST=stalwart:587
SMTP_FROM=alerts@your-domain.ru
SMTP_USER=alerts@your-domain.ru
SMTP_PASSWORD=REPLACE_WITH_PASSWORD
ALERT_EMAIL_TO=admin@your-domain.ru
EOF
chmod 600 .env
echo "Grafana admin password: $GRAFANA_PWD"
'@
$envScript | ssh -i $Env:MSP_SSH_KEY ubuntu@$Env:MSP_VM_IP bash -s
```

> SMTP в .env указывает на `stalwart:587` — это контейнер из
> `deploy/yandex/docker-compose.yml`. Снаружи через `:25` слать нельзя
> (Yandex Cloud блокирует), подробности — в `deploy/yandex/STALWART_RELAY_MODE.md`.

### 5.4. docker-compose.yml

> Полный файл `docker-compose.yml` лежит в репо `i1yxaluk-del/Newbie`
> (каталог `technical/1_Bronze/EXECUTOR/monitoring-stack/`). Если правите
> через PowerShell — редактируйте локально и пересылайте через `scp`.

Ключевые блоки (Prometheus / Alertmanager / Grafana / node-exporter / cAdvisor)
без изменений; профили `monitoring`, `silver`, `gold`. Loki включается через
профиль `silver`.

### 5.5. Запуск стека

```powershell
$bash = @'
set -euo pipefail
cd /opt/monitoring

# Валидация конфига Prometheus
docker run --rm -v ./prometheus:/prometheus prom/prometheus:v2.51.0 \
    promtool check config /prometheus/prometheus.yml

# Запуск (Bronze)
docker compose --profile monitoring up -d

docker compose ps
docker compose logs --tail=30 prometheus

curl -fsS http://localhost:9090/-/healthy && echo "Prometheus OK"
curl -fsS http://localhost:9093/-/healthy && echo "Alertmanager OK"
'@
$bash | ssh -i $Env:MSP_SSH_KEY ubuntu@$Env:MSP_VM_IP bash -s
```

### 5.6. Доступ к Grafana с Windows-станции

Grafana слушает только VPN-интерфейс (`10.9.0.1:3000`). Открыть с Windows
можно через SSH-tunnel:

```powershell
# В отдельном окне PowerShell — туннель не закрывать пока работаешь
ssh -i $Env:MSP_SSH_KEY -L 3000:10.9.0.1:3000 ubuntu@$Env:MSP_VM_IP

# В браузере: http://localhost:3000
```

---

## 6. ДОБАВЛЕНИЕ КЛИЕНТА

### 6.1. PowerShell-обёртка (на Win10)

```powershell
function Add-MspClient {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory)][string]$ClientSlug,
        [Parameter(Mandatory)][string]$ClientName,
        [ValidateSet('bronze','silver','gold')][string]$Tier = 'bronze',
        [string]$LinuxIp1, [string]$LinuxIp2,
        [string]$WindowsIp1,
        [string]$SiteUrl,
        [switch]$CreateBucket
    )

    if ($CreateBucket) { New-MspBackupBucket -ClientSlug $ClientSlug }

    # Передаём всё на VM как параметры и зовём bash-скрипт add_client.sh
    $cmd = "sudo /usr/local/bin/add_client.sh '$ClientSlug' '$ClientName' '$Tier' " +
           "'$LinuxIp1' '$LinuxIp2' '$WindowsIp1' '$SiteUrl'"
    ssh -i $Env:MSP_SSH_KEY ubuntu@$Env:MSP_VM_IP $cmd
}
```

### 6.2. Серверный bash-скрипт (один раз, на VM)

```powershell
$bash = @'
sudo tee /usr/local/bin/add_client.sh >/dev/null << 'SCRIPT'
#!/bin/bash
# add_client.sh CLIENT_SLUG CLIENT_NAME TIER LINUX_IP1 LINUX_IP2 WIN_IP1 SITE_URL
set -euo pipefail

CLIENT_SLUG="${1:?}"
CLIENT_NAME="${2:?}"
TIER="${3:-bronze}"
LINUX_IP1="${4:-}"
LINUX_IP2="${5:-}"
WIN_IP1="${6:-}"
SITE_URL="${7:-}"
CFG="/opt/monitoring/prometheus/prometheus.yml"

{
echo ""
echo "  # ════════════════════════════════"
echo "  # КЛИЕНТ: ${CLIENT_NAME} (${TIER})"
echo "  # Добавлен: $(date '+%Y-%m-%d')"
echo "  # ════════════════════════════════"
} >> "$CFG"

if [[ -n "$LINUX_IP1" ]]; then
cat >> "$CFG" << EOF

  - job_name: 'client-${CLIENT_SLUG}-linux'
    scrape_interval: 30s
    scrape_timeout: 25s
    static_configs:
      - targets:
          - '${LINUX_IP1}:9100'
$([ -n "$LINUX_IP2" ] && echo "          - '${LINUX_IP2}:9100'")
        labels:
          client:      '${CLIENT_SLUG}'
          client_name: '${CLIENT_NAME}'
          tier:        '${TIER}'
          env:         'production'
    metric_relabel_configs:
      - source_labels: [__name__]
        regex:  'go_.*'
        action: drop
EOF
fi

if [[ -n "$WIN_IP1" ]]; then
cat >> "$CFG" << EOF

  - job_name: 'client-${CLIENT_SLUG}-windows'
    scrape_interval: 30s
    static_configs:
      - targets:
          - '${WIN_IP1}:9182'
        labels:
          client:      '${CLIENT_SLUG}'
          client_name: '${CLIENT_NAME}'
          tier:        '${TIER}'
          env:         'production'
EOF
fi

if [[ -n "$SITE_URL" ]]; then
cat >> "$CFG" << EOF

  - job_name: 'client-${CLIENT_SLUG}-http'
    metrics_path: /probe
    params: { module: [http_2xx] }
    static_configs:
      - targets:
          - '${SITE_URL}'
        labels:
          client: '${CLIENT_SLUG}'
          tier:   '${TIER}'
    relabel_configs:
      - source_labels: [__address__]
        target_label:  __param_target
      - source_labels: [__param_target]
        target_label:  instance
      - target_label:  __address__
        replacement:   'localhost:9115'
EOF
fi

curl -s -X POST http://localhost:9090/-/reload && echo "Prometheus reloaded"
SCRIPT
sudo chmod +x /usr/local/bin/add_client.sh
'@
$bash | ssh -i $Env:MSP_SSH_KEY ubuntu@$Env:MSP_VM_IP bash -s
```

### 6.3. Использование

```powershell
Add-MspClient -ClientSlug example -ClientName "ООО Пример" `
              -LinuxIp1 10.9.0.10 -WindowsIp1 10.9.0.20 `
              -SiteUrl https://example.ru -CreateBucket
```

---

## 7. ЕЖЕНЕДЕЛЬНЫЙ ОТЧЁТ

### 7.1. Bash-скрипт на VM (через cron)

```powershell
$bash = @'
sudo tee /usr/local/bin/weekly_report.sh >/dev/null << 'SCRIPT'
#!/bin/bash
# weekly_report.sh — генерация еженедельного отчёта. Запускается cron.
PROMETHEUS="http://localhost:9090"
REPORT_DATE=$(date '+%d.%m.%Y')

echo "═══════════════════════════════════════════════"
echo "  MSP WEEKLY REPORT — ${REPORT_DATE}"
echo "═══════════════════════════════════════════════"

echo ""
echo "ДОСТУПНОСТЬ СЕРВЕРОВ"
curl -s "${PROMETHEUS}/api/v1/query?query=up" | \
    python3 -c "
import sys, json
d = json.load(sys.stdin)
for r in d['data']['result']:
    status = 'UP  ' if r['value'][1]=='1' else 'DOWN'
    client = r['metric'].get('client_name', r['metric'].get('client', '?'))
    inst   = r['metric'].get('instance','?')
    print(f'  {status:6} {client:30} {inst}')
"

echo ""
echo "СТАТУС БЭКАПОВ"
curl -s "${PROMETHEUS}/api/v1/query?query=restic_backup_last_status" | \
    python3 -c "
import sys, json
d = json.load(sys.stdin)
for r in d['data']['result']:
    status = 'OK  ' if r['value'][1]=='1' else 'FAIL'
    host   = r['metric'].get('host','?')
    print(f'  {status} {host}')
"

echo ""
echo "ИСПОЛЬЗОВАНИЕ ДИСКОВ (>70%)"
curl -s "${PROMETHEUS}/api/v1/query?query=(1-node_filesystem_avail_bytes{fstype!~\"tmpfs|overlay\"}/node_filesystem_size_bytes)*100>70" | \
    python3 -c "
import sys, json
d = json.load(sys.stdin)
if not d['data']['result']:
    print('  Все диски в норме')
for r in d['data']['result']:
    pct  = float(r['value'][1])
    inst = r['metric'].get('instance','?')
    mp   = r['metric'].get('mountpoint','?')
    clt  = r['metric'].get('client_name','?')
    print(f'  {pct:5.1f}%  {clt} / {inst}:{mp}')
"
SCRIPT
sudo chmod +x /usr/local/bin/weekly_report.sh
echo "0 8 * * 1 root /usr/local/bin/weekly_report.sh" | sudo tee /etc/cron.d/msp-weekly-report
'@
$bash | ssh -i $Env:MSP_SSH_KEY ubuntu@$Env:MSP_VM_IP bash -s
```

### 7.2. Ручной вызов с Win10

```powershell
ssh -i $Env:MSP_SSH_KEY ubuntu@$Env:MSP_VM_IP "sudo /usr/local/bin/weekly_report.sh" `
    | Tee-Object "$env:USERPROFILE\msp-reports\report-$(Get-Date -Format yyyy-MM-dd).txt"
```

---

## 8. ОБСЛУЖИВАНИЕ СТЕКА

### 8.1. Обновление образов

```powershell
$bash = @'
cd /opt/monitoring
docker compose pull prometheus
docker compose up -d prometheus
docker compose logs --tail=20 prometheus
'@
$bash | ssh -i $Env:MSP_SSH_KEY ubuntu@$Env:MSP_VM_IP bash -s
```

### 8.2. Снапшот VM перед изменениями

```powershell
$diskId = (yc compute instance get $Env:MSP_VM_NAME --folder-id $Env:MSP_FOLDER_ID --format json | ConvertFrom-Json).boot_disk.disk_id

yc compute snapshot create `
    --name "msp-$(Get-Date -Format yyyyMMdd-HHmm)" `
    --source-disk-id $diskId `
    --folder-id $Env:MSP_FOLDER_ID `
    --async
Write-Host "Снапшот создаётся в фоне"
```

### 8.3. Мониторинг самого стека

```powershell
msp-bash 'docker compose -f /opt/monitoring/docker-compose.yml ps'
msp-bash 'docker stats --no-stream'
msp-bash 'docker system df -v'
msp-bash 'curl -s http://localhost:9090/api/v1/status/tsdb | python3 -m json.tool | head -40'
```

### 8.4. Полное удаление VM

```powershell
yc compute instance delete --name $Env:MSP_VM_NAME --folder-id $Env:MSP_FOLDER_ID
```

---

## Что меняется в Silver/Gold

- Silver добавляет Loki/Promtail (`profile: silver`), еженедельный отчёт по
  Sentinel-логам и пайплайн централизованных конфигов (Puppet/Ansible).
  См. `technical/2_Silver/EXECUTOR/SOP_executor_silver.md`.
- Gold добавляет Wazuh Manager, KSC, osTicket. См.
  `technical/3_Gold/EXECUTOR/SOP_executor_gold.md`.

Все эти SOPs используют ту же Win10-обёртку (yc CLI + PowerShell + SSH heredoc).
