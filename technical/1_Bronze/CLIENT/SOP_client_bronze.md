# SOP — Bronze · Сторона КЛИЕНТА
# Версия 3.0 | PowerShell-first (управление с Windows 10 ноутбука админа)
# ═══════════════════════════════════════════════════════════════════
#
# Документ описывает ВСЁ, что устанавливается и настраивается
# на серверах ЗАКАЗЧИКА в рамках тарифа Bronze.
#
# Принцип:
#   - На стороне клиента — только лёгкие агенты.
#   - Тяжёлое (Prometheus, Grafana, S3) — у Исполнителя в Yandex Cloud.
#   - Всё разворачивается АДМИНИСТРАТОРОМ С НОУТБУКА (Windows 10),
#     который удалённо подключается к серверам клиента:
#       • SSH (OpenSSH client из Windows) — для Linux-серверов
#       • PowerShell Remoting / WinRM или RDP — для Windows-серверов
#
# Блоки в документе:
#   • ```powershell``` — выполняется на Win10-станции администратора.
#   • ```bash```       — выполняется на Linux-сервере клиента (открывается
#                        через SSH из PowerShell, либо передаётся как
#                        here-string `... | ssh user@host bash -s`).
#   • ```powershell (на Windows-сервере)``` — выполняется на Windows-сервере
#                        клиента (через Invoke-Command/RDP).
# ═══════════════════════════════════════════════════════════════════

## СОДЕРЖАНИЕ

0. Рабочая станция администратора (Windows 10)
1. Обзор архитектуры
2. Предварительные требования
3. AmneziaWG VPN-подключение (UDP/443, обфускация против РКН-DPI)
4. node_exporter (Linux)
5. windows_exporter (Windows)
6. restic Backup (Linux + Windows)
7. Верификация и чеклист
8. Устранение проблем

---

## 0. РАБОЧАЯ СТАНЦИЯ АДМИНИСТРАТОРА

Те же требования, что и в `SOP_executor_bronze.md` §0 (PowerShell 5.1+,
OpenSSH client, `yc` CLI, профиль с UTF-8). Дополнительно для управления
Windows-серверами клиента:

```powershell
# WinRM (PowerShell Remoting) — для Windows-серверов клиента.
# На стороне сервера должно быть выполнено `Enable-PSRemoting -Force`.
# Со стороны Win10-админа (один раз):
Set-Item WSMan:\localhost\Client\TrustedHosts -Value "*.client.example.local,10.0.*" -Force
Restart-Service WinRM
```

Удалённое исполнение PowerShell-блоков из этого SOP на Windows-серверах
клиента:
```powershell
$cred = Get-Credential                                    # admin@CLIENT-SRV
Invoke-Command -ComputerName CLIENT-SRV -Credential $cred `
    -ScriptBlock { ... содержимое блока 'powershell (на Windows-сервере)' ... }
```

Удалённое исполнение bash-блоков на Linux-серверах клиента:
```powershell
$bash = @'
...содержимое блока ```bash```...
'@
$bash | ssh -i $env:USERPROFILE\.ssh\id_ed25519_client root@CLIENT-LINUX bash -s
```

---

## 1. АРХИТЕКТУРА (BRONZE — КЛИЕНТ)

```
WINDOWS 10 АДМИН-СТАНЦИЯ          СЕРВЕРЫ ЗАКАЗЧИКА           YANDEX CLOUD (Исполнитель)
┌─────────────────────────┐       ┌─────────────────────────┐  ┌──────────────────────────────┐
│  PowerShell 5.1 / 7     │ ───▶  │ Linux-серверы            │  │ Monitoring VM                │
│   ssh + scp             │       │ ├── node_exporter :9100  │◀▶│ ├── Prometheus :9090         │
│   Invoke-Command (WinRM)│       │ ├── restic (backup)      │  │ ├── Grafana :3000            │
│   RDP                   │       │ └── AmneziaWG client     │VPN│ ├── Alertmanager :9093     │
│   yc CLI                │ ───▶  │                          │  │ └── Bastion :443/udp        │
└─────────────────────────┘       │ Windows-серверы          │  │                              │
                                  │ ├── windows_exporter :9182│  │ Object Storage (S3)          │
                                  │ ├── restic (backup)      │  │ └── restic бэкапы клиента    │
                                  │ └── WireGuard client     │  └──────────────────────────────┘
                                  └─────────────────────────┘
```

**IP-схема VPN (10.9.0.0/24):**
- 10.9.0.1 — Bastion / Monitoring VM Исполнителя
- 10.9.0.10–19 — Клиент 1
- 10.9.0.20–29 — Клиент 2
- и т.д.

---

## 2. ПРЕДВАРИТЕЛЬНЫЕ ТРЕБОВАНИЯ

### От Заказчика:
- [ ] SSH-доступ к Linux-серверам (ключ или пароль)
- [ ] RDP/WinRM-доступ к Windows-серверам (для PowerShell Remoting)
- [ ] Права администратора/sudo
- [ ] Разрешён исходящий **UDP/443** с серверов наружу (AmneziaWG)
- [ ] Интернет-доступ с серверов (загрузка агентов)

### От Исполнителя (заранее, в одной таблице):
- [ ] VPN-IP для каждого сервера клиента (`10.9.0.X`)
- [ ] Публичный ключ Bastion AmneziaWG
- [ ] 9 параметров обфускации (`Jc, Jmin, Jmax, S1, S2, H1..H4`) — выдаёт Исполнитель, ДОЛЖНЫ совпадать с сервером
- [ ] Public IP Bastion
- [ ] S3-bucket + ключи доступа для бэкапов
- [ ] restic-пароль (`openssl rand -hex 32`, сохранить в KeePass / 1Password)

Шаблон сводной таблицы (заполняется до выезда/доступа к клиенту):

```powershell
$client = @{
    Slug           = 'company1'
    Name           = 'ООО Компания'
    BastionPubKey  = '<base64 32 байта>'
    BastionIp      = '<yc-public-ip>'
    Servers = @(
        @{ Host = 'srv-app-01';  OS = 'linux';   VpnIp = '10.9.0.10' }
        @{ Host = 'srv-db-01';   OS = 'linux';   VpnIp = '10.9.0.11' }
        @{ Host = 'WIN-AD01';    OS = 'windows'; VpnIp = '10.9.0.12' }
    )
    S3 = @{
        AccessKeyId     = '...'
        SecretAccessKey = '...'
        Bucket          = 'backup-company1'
        ResticPassword  = '<openssl rand -hex 32>'
    }
}
$client | ConvertTo-Json -Depth 5 | Set-Content "$env:USERPROFILE\.msp-secrets\client-company1.json"
```

---

## 3. AMNEZIAWG VPN — ПОДКЛЮЧЕНИЕ КЛИЕНТА

> AmneziaWG — российский форк WireGuard с обфускацией handshake
> против РКН-DPI. Команды идентичны WG (`awg show` = `wg show`,
> `awg-quick` = `wg-quick`); интерфейс именуется `awg0-msp` (вместо
> `wg0-msp`), конфиг лежит в `/etc/amnezia/amneziawg/` (вместо
> `/etc/wireguard/`). На Windows GUI «AmneziaVPN» вместо «WireGuard».

### 3.1. Linux-сервер клиента — установка из PowerShell

```powershell
$srv      = 'srv-app-01'                              # hostname или IP клиента
$VpnIp    = '10.9.0.10'                               # назначен Исполнителем
$Bastion  = $client.BastionIp                         # см. §2
$BastPub  = $client.BastionPubKey

# Bash-блок выполняется на сервере клиента через SSH
$bash = @"
set -euo pipefail

# 1) Установка пакетов из AmneziaWG PPA
sudo apt update
sudo apt install -y software-properties-common
sudo add-apt-repository -y ppa:amnezia/ppa
sudo apt update && sudo apt install -y amneziawg-dkms amneziawg-tools

# 2) Генерация ключевой пары
sudo mkdir -p /etc/amnezia/amneziawg && sudo chmod 700 /etc/amnezia/amneziawg
cd /etc/amnezia/amneziawg
sudo awg genkey | sudo tee client_private.key | sudo awg pubkey | sudo tee client_public.key >/dev/null
sudo chmod 600 client_private.key

PRIV=\$(sudo cat /etc/amnezia/amneziawg/client_private.key)
PUB=\$(sudo cat /etc/amnezia/amneziawg/client_public.key)

# 3) Конфиг туннеля.
#    Параметры Jc/Jmin/Jmax/S1/S2/H1..H4 ниже — выдаёт Исполнитель;
#    они ОБЯЗАНЫ совпадать с теми, что у bastion, иначе handshake не пройдёт.
sudo tee /etc/amnezia/amneziawg/awg0-msp.conf >/dev/null << EOF
[Interface]
PrivateKey = \$PRIV
Address    = $VpnIp/32
DNS        = 77.88.8.8, 77.88.8.1

Jc   = 4
Jmin = 50
Jmax = 1000
S1   = 86
S2   = 574
H1   = 1779539752
H2   = 1138729192
H3   = 2050378563
H4   = 8345423

[Peer]
PublicKey           = $BastPub
Endpoint            = ${Bastion}:443
AllowedIPs          = 10.9.0.0/24
PersistentKeepalive = 25
EOF
sudo chmod 600 /etc/amnezia/amneziawg/awg0-msp.conf

# 4) Старт + автозапуск
sudo systemctl enable --now awg-quick@awg0-msp

# 5) Вывести client public key — нужно Исполнителю, чтобы добавить peer на Bastion
echo "CLIENT_PUBKEY=\$PUB"
sudo awg show awg0-msp
"@

$out = $bash | ssh root@$srv bash -s
$out
# Извлечь CLIENT_PUBKEY и передать Исполнителю:
$clientPubKey = ($out | Select-String '^CLIENT_PUBKEY=(.+)').Matches.Groups[1].Value
Add-MspVpnPeer -ClientSlug $client.Slug -VpnIp $VpnIp -ClientPubKey $clientPubKey
```

> `Add-MspVpnPeer` определена в `SOP_executor_bronze.md` §4.3.

Проверка из PowerShell:
```powershell
ssh root@$srv 'sudo awg show awg0-msp ; ping -c 3 10.9.0.1'
```

### 3.2. Windows-сервер клиента — установка из PowerShell Remoting

```powershell
$srv      = 'WIN-AD01'
$cred     = Get-Credential -UserName "$srv\Administrator" -Message "RDP/WinRM creds"
$VpnIp    = '10.9.0.12'
$Bastion  = $client.BastionIp
$BastPub  = $client.BastionPubKey

Invoke-Command -ComputerName $srv -Credential $cred -ScriptBlock {
    param($VpnIp, $Bastion, $BastPub)

    # 1) Установить AmneziaVPN (Windows-клиент с поддержкой AmneziaWG-обфускации).
    #    Прямые релизы: https://github.com/amnezia-vpn/amnezia-client/releases
    #    Импорт awg0-msp.conf в AmneziaVPN GUI после установки.
    #    Ниже — fallback на обычный WireGuard-клиент без обфускации
    #    (работает только если у клиента НЕТ РКН-DPI).
    if (-not (Get-Command wg.exe -ErrorAction SilentlyContinue)) {
        winget install --id WireGuard.WireGuard --silent --accept-package-agreements --accept-source-agreements
    }

    # 2) Сгенерировать ключи через wg.exe (входит в установку WireGuard)
    $wgDir = "$env:ProgramData\WireGuard"
    New-Item -ItemType Directory -Force -Path $wgDir | Out-Null
    $priv = & "C:\Program Files\WireGuard\wg.exe" genkey
    $pub  = $priv | & "C:\Program Files\WireGuard\wg.exe" pubkey

    # 3) Записать конфиг
    $conf = @"
[Interface]
PrivateKey = $priv
Address    = $VpnIp/32
DNS        = 77.88.8.8, 77.88.8.1

[Peer]
PublicKey           = $BastPub
Endpoint            = ${Bastion}:443
AllowedIPs          = 10.9.0.0/24
PersistentKeepalive = 25
"@
    $confPath = "$wgDir\wg0-msp.conf"
    Set-Content -Path $confPath -Value $conf -Encoding ASCII

    # 4) Установить туннель как Windows-сервис
    & "C:\Program Files\WireGuard\wireguard.exe" /installtunnelservice $confPath

    [pscustomobject]@{ ClientPubKey = $pub.Trim() }
} -ArgumentList $VpnIp, $Bastion, $BastPub | ForEach-Object {
    Add-MspVpnPeer -ClientSlug $client.Slug -VpnIp $VpnIp -ClientPubKey $_.ClientPubKey
}
```

Проверка:
```powershell
Invoke-Command -ComputerName $srv -Credential $cred -ScriptBlock { ping -n 3 10.9.0.1 }
```

---

## 4. NODE_EXPORTER — LINUX

PowerShell-обёртка над bash-инсталлятором (запуск с Win10):

```powershell
$srv = 'srv-app-01'
$bash = @'
set -euo pipefail
NODE_EXPORTER_VERSION="1.7.0"

# Пользователь
sudo useradd --system --no-create-home --shell /sbin/nologin node_exporter 2>/dev/null || true

# Бинарь
cd /tmp
wget -q "https://github.com/prometheus/node_exporter/releases/download/v${NODE_EXPORTER_VERSION}/node_exporter-${NODE_EXPORTER_VERSION}.linux-amd64.tar.gz"
tar xzf node_exporter-${NODE_EXPORTER_VERSION}.linux-amd64.tar.gz
sudo install -m 0755 node_exporter-${NODE_EXPORTER_VERSION}.linux-amd64/node_exporter /usr/local/bin/
rm -rf /tmp/node_exporter-*

# Каталог textfile_collector
sudo mkdir -p /var/lib/node_exporter/textfile_collector
sudo chown node_exporter:node_exporter /var/lib/node_exporter/textfile_collector

# Systemd unit
sudo tee /etc/systemd/system/node_exporter.service >/dev/null << 'EOF'
[Unit]
Description=Prometheus Node Exporter
After=network.target

[Service]
Type=simple
User=node_exporter
Group=node_exporter
ExecStart=/usr/local/bin/node_exporter \
    --web.listen-address=:9100 \
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

# Firewall: порт 9100 — только из VPN
sudo ufw allow from 10.9.0.0/24 to any port 9100 proto tcp comment "node_exporter from MSP VPN" || true

sudo systemctl daemon-reload
sudo systemctl enable --now node_exporter
systemctl --no-pager status node_exporter | head -10
curl -s http://localhost:9100/metrics | head -2
'@
$bash | ssh root@$srv bash -s
```

---

## 5. WINDOWS_EXPORTER

PowerShell Remoting на Windows-сервер клиента:

```powershell
$srv  = 'WIN-AD01'
$cred = Get-Credential -UserName "$srv\Administrator"

Invoke-Command -ComputerName $srv -Credential $cred -ScriptBlock {
    $Version = "0.25.1"
    $MsiUrl  = "https://github.com/prometheus-community/windows_exporter/releases/download/v${Version}/windows_exporter-${Version}-amd64.msi"
    $MsiPath = "$env:TEMP\windows_exporter.msi"

    Invoke-WebRequest -Uri $MsiUrl -OutFile $MsiPath -UseBasicParsing

    Start-Process msiexec.exe -ArgumentList @(
        "/i", $MsiPath,
        "/quiet", "/norestart",
        'ENABLED_COLLECTORS="cpu,memory,logical_disk,service,process,system,net,os,textfile"',
        'LISTEN_PORT=9182',
        'EXTRA_FLAGS="--collector.textfile.directory=C:\Program Files\windows_exporter\textfile_collector"'
    ) -Wait -NoNewWindow

    New-Item -ItemType Directory -Force -Path "C:\Program Files\windows_exporter\textfile_collector" | Out-Null

    # Firewall: 9182 — только из VPN-подсети
    Remove-NetFirewallRule -DisplayName "windows_exporter MSP" -ErrorAction SilentlyContinue
    New-NetFirewallRule `
        -DisplayName "windows_exporter MSP" `
        -Direction Inbound -Protocol TCP -LocalPort 9182 `
        -RemoteAddress "10.9.0.0/24" -Action Allow -Profile Any

    Start-Service windows_exporter -ErrorAction SilentlyContinue
    Set-Service   windows_exporter -StartupType Automatic

    Remove-Item $MsiPath -Force
    Get-Service windows_exporter | Format-Table Name, Status, StartType
    (Invoke-WebRequest -Uri "http://localhost:9182/metrics" -UseBasicParsing).StatusCode
}
```

### 5.1. Textfile collector для 1С

```powershell
Invoke-Command -ComputerName $srv -Credential $cred -ScriptBlock {
    $ScriptDir  = "C:\msp-scripts"
    $MetricsDir = "C:\Program Files\windows_exporter\textfile_collector"
    New-Item -ItemType Directory -Force -Path $ScriptDir, $MetricsDir | Out-Null

    $monitor = @'
$MetricsDir = "C:\Program Files\windows_exporter\textfile_collector"
$OutFile    = "$MetricsDir\1c_sessions.prom"

$rphost = Get-Process -Name rphost -ErrorAction SilentlyContinue
$count  = ($rphost | Measure-Object).Count
$memMb  = if ($rphost) { [math]::Round(($rphost | Measure-Object WorkingSet64 -Sum).Sum / 1MB, 1) } else { 0 }

@"
# HELP onec_rphost_count Number of active 1C rphost processes
# TYPE onec_rphost_count gauge
onec_rphost_count{host="$env:COMPUTERNAME"} $count
# HELP onec_rphost_memory_mb Total RAM used by 1C rphost (MB)
# TYPE onec_rphost_memory_mb gauge
onec_rphost_memory_mb{host="$env:COMPUTERNAME"} $memMb
"@ | Set-Content -Path $OutFile -Encoding UTF8
'@
    Set-Content -Path "$ScriptDir\monitor_1c.ps1" -Value $monitor -Encoding UTF8

    $action  = New-ScheduledTaskAction -Execute 'powershell.exe' `
        -Argument '-NonInteractive -ExecutionPolicy Bypass -File "C:\msp-scripts\monitor_1c.ps1"'
    $trigger = New-ScheduledTaskTrigger -Once (Get-Date) `
        -RepetitionInterval (New-TimeSpan -Minutes 5) -RepetitionDuration ([TimeSpan]::MaxValue)
    Register-ScheduledTask -TaskName 'MSP-1C-Monitor' -Action $action -Trigger $trigger `
        -User 'SYSTEM' -RunLevel Highest -Force | Out-Null
}
```

---

## 6. RESTIC BACKUP

### 6.1. Подготовка (Исполнитель, до выхода на клиента)

1. `New-MspBackupBucket -ClientSlug company1` (см. executor SOP §2.3).
2. Сгенерировать пароль репозитория:
   ```powershell
   $resticPwd = -join ((1..32) | ForEach-Object { '{0:x}' -f (Get-Random -Maximum 16) })
   $client.S3.ResticPassword = $resticPwd
   ```
3. Положить ключи и пароль в `$env:USERPROFILE\.msp-secrets\client-<slug>.json` —
   передаём оттуда в установщики ниже.

### 6.2. Linux-сервер — установка из PowerShell

```powershell
$srv  = 'srv-app-01'
$s3   = $client.S3
$bash = @"
set -euo pipefail
RESTIC_VERSION="0.16.4"

# Установка restic
curl -sL "https://github.com/restic/restic/releases/download/v\${RESTIC_VERSION}/restic_\${RESTIC_VERSION}_linux_amd64.bz2" \
    | bunzip2 | sudo tee /usr/local/bin/restic >/dev/null
sudo chmod +x /usr/local/bin/restic
restic version

sudo mkdir -p /opt/restic-scripts /etc/restic

# Переменные окружения (значения подставлены из \$client)
sudo tee /etc/restic/env.sh >/dev/null << 'EOF'
export AWS_ACCESS_KEY_ID="$($s3.AccessKeyId)"
export AWS_SECRET_ACCESS_KEY="$($s3.SecretAccessKey)"
export RESTIC_REPOSITORY="s3:https://storage.yandexcloud.net/$($s3.Bucket)"
export RESTIC_PASSWORD="$($s3.ResticPassword)"
EOF
sudo chmod 600 /etc/restic/env.sh

# Исключения
sudo tee /opt/restic-scripts/excludes.txt >/dev/null << 'EOF'
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
sudo tee /opt/restic-scripts/backup.sh >/dev/null << 'SCRIPT'
#!/bin/bash
set -euo pipefail
LOG=/var/log/restic-backup.log
METRICS_DIR=/var/lib/node_exporter/textfile_collector
METRICS_FILE=\${METRICS_DIR}/restic_backup.prom
TS=\$(date +%s)
HOST=\$(hostname -f)

log() { echo "[\$(date '+%F %T')] \$*" | tee -a \$LOG ; }
source /etc/restic/env.sh

log "=== START BACKUP ==="
if restic backup /etc /home /root /opt /srv /var/www \
       --exclude-file=/opt/restic-scripts/excludes.txt \
       --tag auto --tag \$(hostname) --verbose 2>&1 | tee -a \$LOG ; then
    STATUS=1 ; log "SUCCESS"
else
    STATUS=0 ; log "FAILED"
fi

restic forget --keep-daily 7 --keep-weekly 4 --keep-monthly 6 --keep-yearly 1 --prune 2>&1 | tee -a \$LOG

mkdir -p \$METRICS_DIR
cat > \$METRICS_FILE << EOF
# HELP restic_backup_last_status Status of last restic backup (1=success, 0=failure)
# TYPE restic_backup_last_status gauge
restic_backup_last_status{host="\$HOST"} \$STATUS
# HELP restic_backup_last_timestamp_seconds Unix timestamp of last backup attempt
# TYPE restic_backup_last_timestamp_seconds gauge
restic_backup_last_timestamp_seconds{host="\$HOST"} \$TS
EOF

log "=== END BACKUP (status=\$STATUS) ==="
SCRIPT
sudo chmod +x /opt/restic-scripts/backup.sh

# Systemd service + timer
sudo tee /etc/systemd/system/restic-backup.service >/dev/null << 'EOF'
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
SyslogIdentifier=restic-backup

[Install]
WantedBy=multi-user.target
EOF

sudo tee /etc/systemd/system/restic-backup.timer >/dev/null << 'EOF'
[Unit]
Description=Restic Backup Timer
Requires=restic-backup.service

[Timer]
OnCalendar=*-*-* 02:00:00
RandomizedDelaySec=300
Persistent=true

[Install]
WantedBy=timers.target
EOF

# Инициализация репозитория (ОДИН РАЗ для клиента)
source /etc/restic/env.sh
restic init || echo "Repository already exists"

sudo systemctl daemon-reload
sudo systemctl enable --now restic-backup.timer
sudo systemctl start restic-backup.service
restic snapshots
"@
$bash | ssh root@$srv bash -s
```

### 6.3. Windows-сервер — установка из PowerShell Remoting

```powershell
$srv  = 'WIN-AD01'
$cred = Get-Credential -UserName "$srv\Administrator"
$s3   = $client.S3

Invoke-Command -ComputerName $srv -Credential $cred -ArgumentList $s3 -ScriptBlock {
    param($s3)

    $ResticVersion = "0.16.4"
    $ResticDir     = "C:\Program Files\restic"
    $ScriptsDir    = "C:\msp-scripts"
    $LogDir        = "C:\ProgramData\msp-logs"

    New-Item -ItemType Directory -Force -Path $ResticDir, $ScriptsDir, $LogDir | Out-Null

    # Скачать и установить restic
    $url = "https://github.com/restic/restic/releases/download/v${ResticVersion}/restic_${ResticVersion}_windows_amd64.zip"
    $zip = "$env:TEMP\restic.zip"
    Invoke-WebRequest -Uri $url -OutFile $zip -UseBasicParsing
    Expand-Archive -Path $zip -DestinationPath $ResticDir -Force
    Remove-Item $zip

    $exeFile = Get-ChildItem "$ResticDir\restic*.exe" | Select-Object -First 1
    if ($exeFile.Name -ne 'restic.exe') {
        Rename-Item $exeFile.FullName "$ResticDir\restic.exe" -Force
    }

    # PATH
    $envPath = [System.Environment]::GetEnvironmentVariable('Path', 'Machine')
    if ($envPath -notlike "*$ResticDir*") {
        [System.Environment]::SetEnvironmentVariable('Path', "$envPath;$ResticDir", 'Machine')
    }

    # Файл с переменными (как .ps1 — будет dot-source-нут backup.ps1)
    $envFile = "$ScriptsDir\backup-env.ps1"
    @"
`$env:AWS_ACCESS_KEY_ID     = '$($s3.AccessKeyId)'
`$env:AWS_SECRET_ACCESS_KEY = '$($s3.SecretAccessKey)'
`$env:RESTIC_REPOSITORY     = 's3:https://storage.yandexcloud.net/$($s3.Bucket)'
`$env:RESTIC_PASSWORD       = '$($s3.ResticPassword)'
"@ | Set-Content -Path $envFile -Encoding UTF8

    # Скрипт backup.ps1
    $backup = @'
. "C:\msp-scripts\backup-env.ps1"

$LogFile     = "C:\ProgramData\msp-logs\restic-backup.log"
$MetricsDir  = "C:\Program Files\windows_exporter\textfile_collector"
$MetricsFile = "$MetricsDir\restic_backup.prom"
$Hostname    = $env:COMPUTERNAME
$Timestamp   = [DateTimeOffset]::UtcNow.ToUnixTimeSeconds()

function Log($msg) {
    $line = "[$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')] $msg"
    Add-Content $LogFile $line
    Write-Output $line
}

Log "=== START BACKUP ==="

$BackupPaths = @('C:\Users','C:\inetpub','C:\Backup')
$ExcludeArgs = @(
    '--exclude','*.tmp','--exclude','*.log','--exclude','pagefile.sys',
    '--exclude','hiberfil.sys','--exclude',"$env:WINDIR\Temp"
)
$ResticExe = 'C:\Program Files\restic\restic.exe'

$args = @('backup') + $BackupPaths + $ExcludeArgs + @('--tag','auto','--tag',$Hostname,'--verbose')
& $ResticExe @args 2>&1 | Tee-Object -FilePath $LogFile -Append

$Status = if ($LASTEXITCODE -eq 0) { 1 } else { 0 }
Log "Backup status=$Status"

& $ResticExe forget --keep-daily 7 --keep-weekly 4 --keep-monthly 6 --prune 2>&1 |
    Tee-Object -FilePath $LogFile -Append

if (-not (Test-Path $MetricsDir)) { New-Item -ItemType Directory -Force -Path $MetricsDir | Out-Null }

@"
# HELP restic_backup_last_status Status of last backup (1=success, 0=failure)
# TYPE restic_backup_last_status gauge
restic_backup_last_status{host="$Hostname"} $Status
# HELP restic_backup_last_timestamp_seconds Unix timestamp of last backup attempt
# TYPE restic_backup_last_timestamp_seconds gauge
restic_backup_last_timestamp_seconds{host="$Hostname"} $Timestamp
"@ | Set-Content $MetricsFile -Encoding UTF8

Log "=== END BACKUP (status=$Status) ==="
'@
    Set-Content -Path "$ScriptsDir\backup.ps1" -Value $backup -Encoding UTF8

    # Scheduled Task
    $action  = New-ScheduledTaskAction -Execute 'powershell.exe' `
        -Argument '-NonInteractive -ExecutionPolicy Bypass -File "C:\msp-scripts\backup.ps1"'
    $trigger = New-ScheduledTaskTrigger -Daily -At '02:00'
    $settings= New-ScheduledTaskSettingsSet -ExecutionTimeLimit (New-TimeSpan -Hours 4) -RunOnlyIfNetworkAvailable

    Register-ScheduledTask -TaskName 'MSP-ResticBackup' `
        -Action $action -Trigger $trigger -Settings $settings `
        -User 'SYSTEM' -RunLevel Highest -Force | Out-Null

    # Инициализация репо
    . $envFile
    & 'C:\Program Files\restic\restic.exe' init 2>$null
    Write-Output "Backup configured. First run: $(Get-Date -Format 'yyyy-MM-dd') 02:00"
}
```

---

## 7. ЧЕКЛИСТ ВЕРИФИКАЦИИ

PowerShell-обёртка, которая прогоняет проверки по всему `$client.Servers`:

```powershell
function Test-MspBronzeClient {
    param([Parameter(Mandatory)]$Client)

    foreach ($s in $Client.Servers) {
        Write-Host "`n=== $($s.Host) ($($s.OS)) ===" -ForegroundColor Cyan

        if ($s.OS -eq 'linux') {
            $checks = @'
echo -n "AmneziaWG handshake .... "
sudo awg show awg0-msp 2>/dev/null | grep -q "latest handshake" && echo OK || echo FAIL

echo -n "Bastion reachable ...... "
ping -c 2 -W 3 10.9.0.1 >/dev/null && echo OK || echo FAIL

echo -n "node_exporter active ... "
systemctl is-active --quiet node_exporter && echo OK || echo FAIL

echo -n "metrics from VPN ....... "
MY=$(ip addr show awg0-msp 2>/dev/null | awk '/inet /{print $2}' | cut -d/ -f1)
curl -s --max-time 5 "http://${MY}:9100/metrics" | head -1 | grep -q '^#' && echo OK || echo FAIL

echo -n "restic timer enabled ... "
systemctl is-enabled --quiet restic-backup.timer && echo OK || echo FAIL

echo -n "restic repository ...... "
source /etc/restic/env.sh 2>/dev/null
restic snapshots --quiet 2>/dev/null >/dev/null && echo OK || echo FAIL
'@
            $checks | ssh root@$($s.Host) bash -s
        }
        else {
            $cred = Get-Credential -UserName "$($s.Host)\Administrator" -Message "WinRM creds for $($s.Host)"
            Invoke-Command -ComputerName $s.Host -Credential $cred -ScriptBlock {
                @{
                    'WinExporter service' = (Get-Service windows_exporter -ErrorAction SilentlyContinue).Status
                    'Metrics HTTP 200'    = (Invoke-WebRequest -Uri http://localhost:9182/metrics -UseBasicParsing).StatusCode
                    'AmneziaWG service'   = (Get-Service 'WireGuardTunnel$wg0-msp' -ErrorAction SilentlyContinue).Status
                    'Backup task'         = (Get-ScheduledTask -TaskName MSP-ResticBackup -ErrorAction SilentlyContinue).State
                    'Bastion ping'        = (Test-Connection -ComputerName 10.9.0.1 -Count 2 -Quiet)
                }
            } | Format-Table -AutoSize
        }
    }
}

# Использование:
Test-MspBronzeClient -Client $client
```

---

## 8. УСТРАНЕНИЕ ПРОБЛЕМ

| Проблема                          | Диагностика                                | Решение                                                                       |
|-----------------------------------|---------------------------------------------|-------------------------------------------------------------------------------|
| VPN — нет handshake (Linux)       | `ssh root@srv 'sudo awg show awg0-msp'`     | Проверить endpoint, параметры Jc/Jmin/Jmax/S1/S2/H1..H4 совпадают с bastion; перезапустить: `sudo systemctl restart awg-quick@awg0-msp` |
| VPN — нет handshake (Windows)     | `Invoke-Command ... Get-Service WireGuardTunnel*` | Открыть AmneziaVPN UI → Reconnect; проверить outbound UDP/443 |
| node_exporter не стартует         | `ssh root@srv 'journalctl -u node_exporter -n 50'` | Проверить права на `/var/lib/node_exporter/textfile_collector`         |
| Метрики недоступны из VPN         | `ssh root@srv 'sudo ufw status'`            | `ufw allow from 10.9.0.0/24 to any port 9100`                                 |
| Бэкап падает (Linux)              | `ssh root@srv 'journalctl -u restic-backup -n 100'` | Проверить ключи S3, свободное место, сеть к `storage.yandexcloud.net`  |
| Бэкап падает (Windows)            | `Get-Content C:\ProgramData\msp-logs\restic-backup.log` | Те же проверки + Scheduled Task → History                          |
| S3 недоступен                     | `curl -I https://storage.yandexcloud.net`   | Проверить интернет/DNS/ключи                                                  |
| Порт 9100/9182 занят              | `ss -tlnp \| grep :9100` / `netstat -ano \| findstr :9182` | Найти/убить конкурирующий процесс                                |
