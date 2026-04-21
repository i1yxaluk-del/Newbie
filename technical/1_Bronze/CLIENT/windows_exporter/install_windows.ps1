# ═══════════════════════════════════════════════════════════════════
# install_windows.ps1 — Установка windows_exporter
# Тариф: Bronze+ | ОС: Windows Server 2012R2+, Windows 10/11
# Запуск: от имени Administrator
# ═══════════════════════════════════════════════════════════════════
#Requires -RunAsAdministrator

param(
    [string]$Version       = "0.25.1",
    [string]$ListenPort    = "9182",
    [string]$VpnSubnet     = "10.9.0.0/24",
    [string]$TextfileDir   = "C:\Program Files\windows_exporter\textfile_collector",
    [string]$ScriptsDir    = "C:\msp-scripts"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Write-Ok   { param($m) Write-Host "  ✓ $m" -ForegroundColor Green }
function Write-Warn { param($m) Write-Host "  ! $m" -ForegroundColor Yellow }
function Write-Err  { param($m) Write-Host "  ✗ $m" -ForegroundColor Red; exit 1 }

Write-Host ""
Write-Host "══════════════════════════════════════════" -ForegroundColor Cyan
Write-Host "  windows_exporter installer v$Version"
Write-Host "  Port: $ListenPort | VPN: $VpnSubnet"
Write-Host "══════════════════════════════════════════" -ForegroundColor Cyan
Write-Host ""

# ── Скачать MSI ───────────────────────────────────────────────────
$MsiUrl  = "https://github.com/prometheus-community/windows_exporter/releases/download/v${Version}/windows_exporter-${Version}-amd64.msi"
$MsiPath = "$env:TEMP\windows_exporter-${Version}.msi"

Write-Host "Скачиваю windows_exporter v${Version}..."
try {
    [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
    Invoke-WebRequest -Uri $MsiUrl -OutFile $MsiPath -UseBasicParsing
    Write-Ok "MSI скачан: $MsiPath"
} catch {
    Write-Err "Не удалось скачать: $_"
}

# ── Collectors ────────────────────────────────────────────────────
# Обоснование каждого:
# cpu           — загрузка процессора
# memory        — использование RAM
# logical_disk  — свободное место на дисках (КРИТИЧНО — диск 1С)
# service       — статус Windows-служб (1С, SQL, AD, DNS)
# process       — метрики процессов (rphost, sqlservr, lsass)
# system        — uptime, число сессий
# net           — сетевые интерфейсы и пропускная способность
# os            — версия ОС, последняя загрузка
# textfile      — кастомные метрики (1С, бэкап)
$Collectors = "cpu,memory,logical_disk,service,process,system,net,os,textfile"
$ExtraFlags = "--collector.textfile.directory=`"$TextfileDir`""

# ── Установка ─────────────────────────────────────────────────────
Write-Host "Устанавливаю..."
$msiArgs = @(
    "/i", $MsiPath,
    "/quiet", "/norestart",
    "ENABLED_COLLECTORS=$Collectors",
    "LISTEN_PORT=$ListenPort",
    "EXTRA_FLAGS=$ExtraFlags"
)

$proc = Start-Process -FilePath "msiexec.exe" -ArgumentList $msiArgs -Wait -PassThru -NoNewWindow
if ($proc.ExitCode -ne 0) {
    Write-Err "MSI завершился с кодом $($proc.ExitCode)"
}
Write-Ok "windows_exporter установлен"

# ── Textfile директория ───────────────────────────────────────────
New-Item -ItemType Directory -Force -Path $TextfileDir | Out-Null
Write-Ok "Textfile директория: $TextfileDir"

# ── Scripts директория ───────────────────────────────────────────
New-Item -ItemType Directory -Force -Path $ScriptsDir | Out-Null

# ── Скрипт мониторинга 1С ────────────────────────────────────────
$MonitorScript = @"
# monitor_1c.ps1 — Метрики 1С:Предприятие для Prometheus textfile
# Запускается каждые 5 минут через Task Scheduler

`$MetricsDir  = "$TextfileDir"
`$OutFile     = "`$MetricsDir\1c_sessions.prom"
`$Hostname    = `$env:COMPUTERNAME

# Собрать метрики rphost
`$rphostProcs = Get-Process -Name "rphost" -ErrorAction SilentlyContinue
`$rphostCount = (`$rphostProcs | Measure-Object).Count
`$rphostMemMB = if (`$rphostCount -gt 0) {
    [math]::Round((`$rphostProcs | Measure-Object WorkingSet64 -Sum).Sum / 1MB, 1)
} else { 0 }

# Статус лицензионного сервера
`$hasplm = Get-Process -Name "hasplms" -ErrorAction SilentlyContinue
`$hasp   = if (`$hasplm) { 1 } else { 0 }

# Статус агента 1С
`$agent1c = Get-Service -Name "1C:*" -ErrorAction SilentlyContinue | Where-Object Status -eq Running
`$agentOk = if (`$agent1c) { 1 } else { 0 }

@"
# HELP onec_rphost_count Active 1C rphost processes
# TYPE onec_rphost_count gauge
onec_rphost_count{host="`$Hostname"} `$rphostCount
# HELP onec_rphost_memory_mb RAM used by rphost (MB)
# TYPE onec_rphost_memory_mb gauge
onec_rphost_memory_mb{host="`$Hostname"} `$rphostMemMB
# HELP onec_hasp_running 1=license server running
# TYPE onec_hasp_running gauge
onec_hasp_running{host="`$Hostname"} `$hasp
# HELP onec_agent_running 1=1C server agent running
# TYPE onec_agent_running gauge
onec_agent_running{host="`$Hostname"} `$agentOk
"@ | Set-Content `$OutFile -Encoding UTF8
"@
$MonitorScript | Set-Content "$ScriptsDir\monitor_1c.ps1" -Encoding UTF8

# Зарегистрировать Task Scheduler для monitor_1c.ps1
$action  = New-ScheduledTaskAction -Execute "powershell.exe" `
    -Argument "-NonInteractive -ExecutionPolicy Bypass -File `"$ScriptsDir\monitor_1c.ps1`""
$trigger = New-ScheduledTaskTrigger -Once -At (Get-Date) -RepetitionInterval (New-TimeSpan -Minutes 5)
$settings= New-ScheduledTaskSettingsSet -MultipleInstances Ignore -ExecutionTimeLimit (New-TimeSpan -Minutes 2)
Register-ScheduledTask -TaskName "MSP-Monitor-1C" -Action $action -Trigger $trigger `
    -Settings $settings -User "SYSTEM" -RunLevel Highest -Force | Out-Null
Write-Ok "Task Scheduler: MSP-Monitor-1C (каждые 5 мин)"

# ── Firewall ──────────────────────────────────────────────────────
Remove-NetFirewallRule -DisplayName "MSP windows_exporter" -ErrorAction SilentlyContinue
New-NetFirewallRule `
    -DisplayName "MSP windows_exporter" `
    -Direction Inbound `
    -Protocol TCP `
    -LocalPort $ListenPort `
    -RemoteAddress $VpnSubnet `
    -Action Allow `
    -Profile Any `
    -Enabled True | Out-Null
Write-Ok "Firewall: порт $ListenPort открыт для $VpnSubnet"

# ── Убедиться что служба запущена ────────────────────────────────
Start-Sleep -Seconds 3
try {
    $svc = Get-Service -Name "windows_exporter"
    if ($svc.Status -ne "Running") {
        Start-Service windows_exporter
    }
    Set-Service windows_exporter -StartupType Automatic
    Write-Ok "Служба windows_exporter: Running"
} catch {
    Write-Warn "Служба: $_"
}

# ── Проверка ──────────────────────────────────────────────────────
try {
    $resp = Invoke-WebRequest -Uri "http://localhost:${ListenPort}/metrics" -UseBasicParsing -TimeoutSec 10
    $lineCount = ($resp.Content -split "`n").Count
    Write-Ok "Метрики доступны: $lineCount строк (http://localhost:${ListenPort}/metrics)"
} catch {
    Write-Warn "Метрики недоступны локально: $_"
}

# ── Удалить MSI ───────────────────────────────────────────────────
Remove-Item $MsiPath -Force -ErrorAction SilentlyContinue

Write-Host ""
Write-Host "══════════════════════════════════════════" -ForegroundColor Green
Write-Host "  ✓ Установка завершена!"
Write-Host "  Метрики: http://localhost:${ListenPort}/metrics"
Write-Host ""
Write-Host "  Следующий шаг:"
Write-Host "  Сообщите Исполнителю VPN-IP сервера"
Write-Host "══════════════════════════════════════════" -ForegroundColor Green
