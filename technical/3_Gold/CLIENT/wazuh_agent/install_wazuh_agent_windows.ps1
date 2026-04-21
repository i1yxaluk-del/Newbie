# ═══════════════════════════════════════════════════════════════════
# install_wazuh_agent_windows.ps1 — Установка Wazuh Agent (Windows)
# Тариф: Gold | ОС: Windows Server 2012R2+, Windows 10/11
# Запуск: от имени Administrator (PowerShell)
# ═══════════════════════════════════════════════════════════════════
#Requires -RunAsAdministrator

param(
    [string]$WazuhManager  = "10.9.0.3",
    [string]$WazuhVersion  = "4.7.5",
    [string]$AgentName     = $env:COMPUTERNAME,
    [string]$AgentGroup    = "default"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12

function Write-Ok   { param($m) Write-Host "  [OK] $m" -ForegroundColor Green }
function Write-Warn { param($m) Write-Host "  [!]  $m" -ForegroundColor Yellow }
function Write-Info { param($m) Write-Host "  [->] $m" -ForegroundColor Cyan }
function Write-Err  { param($m) Write-Host "  [X]  $m" -ForegroundColor Red; exit 1 }

Write-Host ""
Write-Host "══════════════════════════════════════════" -ForegroundColor Cyan
Write-Host "  Wazuh Agent v$WazuhVersion — Windows Install"
Write-Host "  Manager: $WazuhManager"
Write-Host "  Agent:   $AgentName"
Write-Host "══════════════════════════════════════════" -ForegroundColor Cyan
Write-Host ""

# ── Скачать MSI ───────────────────────────────────────────────────
$MsiUrl  = "https://packages.wazuh.com/4.x/windows/wazuh-agent-${WazuhVersion}-1.msi"
$MsiPath = "$env:TEMP\wazuh-agent-${WazuhVersion}.msi"

Write-Info "Скачиваю Wazuh Agent MSI..."
try {
    Invoke-WebRequest -Uri $MsiUrl -OutFile $MsiPath -UseBasicParsing
    Write-Ok "MSI скачан: $MsiPath"
} catch {
    Write-Err "Не удалось скачать: $_"
}

# ── Установить ────────────────────────────────────────────────────
Write-Info "Устанавливаю..."
$msiArgs = @(
    "/i", $MsiPath,
    "/quiet",
    "/norestart",
    "WAZUH_MANAGER=$WazuhManager",
    "WAZUH_MANAGER_PORT=1514",
    "WAZUH_AGENT_NAME=$AgentName",
    "WAZUH_AGENT_GROUP=$AgentGroup",
    "WAZUH_REGISTRATION_SERVER=$WazuhManager",
    "WAZUH_REGISTRATION_PORT=1515"
)

$proc = Start-Process msiexec.exe -ArgumentList $msiArgs -Wait -PassThru -NoNewWindow
if ($proc.ExitCode -ne 0) {
    Write-Err "MSI завершился с кодом $($proc.ExitCode)"
}
Write-Ok "Wazuh Agent установлен"

# ── Добавить FIM правила для 1С ──────────────────────────────────
$OssecConf = "C:\Program Files (x86)\ossec-agent\ossec.conf"
if (Test-Path $OssecConf) {
    Write-Info "Настраиваю FIM для Windows..."

    # Добавить дополнительные директории для мониторинга
    $syscheck = @"

  <!-- MSPShield FIM: Windows-специфика -->
  <syscheck>
    <disabled>no</disabled>
    <frequency>43200</frequency>

    <!-- Критичные системные директории -->
    <directories check_all="yes" report_changes="yes">%WINDIR%\System32\drivers\etc</directories>
    <directories check_all="yes">%PROGRAMFILES%</directories>
    <directories check_all="yes">%PROGRAMFILES(X86)%</directories>

    <!-- 1С Enterprise (если установлен) -->
    <directories check_all="yes" report_changes="yes">C:\Program Files\1cv8</directories>
    <directories check_all="yes" report_changes="yes">C:\Program Files (x86)\1cv8</directories>

    <!-- Исключения -->
    <ignore type="sregex">.log$</ignore>
    <ignore type="sregex">.tmp$</ignore>
    <ignore type="sregex">pagefile.sys</ignore>
    <ignore type="sregex">hiberfil.sys</ignore>
  </syscheck>
"@

    # Проверить и добавить если ещё нет MSPShield блока
    $confContent = Get-Content $OssecConf -Raw
    if ($confContent -notlike "*MSPShield FIM*") {
        # Вставить перед закрывающим </ossec_config>
        $confContent = $confContent -replace '</ossec_config>', "$syscheck`n</ossec_config>"
        Set-Content $OssecConf -Value $confContent -Encoding UTF8
        Write-Ok "FIM конфигурация добавлена"
    } else {
        Write-Warn "FIM конфигурация уже существует"
    }
}

# ── Firewall: разрешить исходящие порты Wazuh ────────────────────
Write-Info "Настраиваю Firewall..."

# Wazuh Manager → порты
$fwRules = @(
    @{ Name="Wazuh-Manager-1514-TCP"; Port=1514; Proto="TCP" },
    @{ Name="Wazuh-Manager-1514-UDP"; Port=1514; Proto="UDP" },
    @{ Name="Wazuh-Manager-1515-TCP"; Port=1515; Proto="TCP" }
)

foreach ($rule in $fwRules) {
    Remove-NetFirewallRule -DisplayName $rule.Name -ErrorAction SilentlyContinue
    New-NetFirewallRule `
        -DisplayName $rule.Name `
        -Direction Outbound `
        -Protocol $rule.Proto `
        -RemotePort $rule.Port `
        -RemoteAddress $WazuhManager `
        -Action Allow `
        -Enabled True | Out-Null
}
Write-Ok "Firewall: порты 1514, 1515 → $WazuhManager разрешены"

# ── Скрипт мониторинга Kaspersky (textfile_collector) ─────────────
$TextfileDir = "C:\Program Files\windows_exporter\textfile_collector"
if (Test-Path $TextfileDir) {
    Write-Info "Создаю скрипт мониторинга Kaspersky..."

    $monitorScript = @'
# monitor_kaspersky.ps1 — метрики KES для Prometheus
$MetricsDir = "C:\Program Files\windows_exporter\textfile_collector"
$OutFile    = "$MetricsDir\kaspersky.prom"
$Host       = $env:COMPUTERNAME

# Статус службы Kaspersky
$svc = Get-Service -Name "AVP*" -ErrorAction SilentlyContinue | Select-Object -First 1
$running = if ($svc -and $svc.Status -eq "Running") { 1 } else { 0 }

# Возраст баз (из реестра)
$regPaths = @(
    "HKLM:\SOFTWARE\KasperskyLab\*\*\Statistics\Protection",
    "HKLM:\SOFTWARE\WOW6432Node\KasperskyLab\*\*\Statistics\Protection"
)
$lastUpdate = 0
foreach ($path in $regPaths) {
    $resolved = Resolve-Path $path -ErrorAction SilentlyContinue
    if ($resolved) {
        $reg = Get-ItemProperty $resolved.Path -ErrorAction SilentlyContinue
        if ($reg.LastSuccessfulUpdate) {
            $lastUpdate = [DateTimeOffset]::FromFileTime($reg.LastSuccessfulUpdate).ToUnixTimeSeconds()
            break
        }
    }
}

$now = [DateTimeOffset]::UtcNow.ToUnixTimeSeconds()
$ageHours = if ($lastUpdate -gt 0) {
    [math]::Round(($now - $lastUpdate) / 3600, 1)
} else { -1 }

# Wazuh Agent статус
$wazuhSvc = Get-Service -Name "OssecSvc" -ErrorAction SilentlyContinue
$wazuhRunning = if ($wazuhSvc -and $wazuhSvc.Status -eq "Running") { 1 } else { 0 }

@"
# HELP kaspersky_service_running 1=running 0=stopped -1=not_installed
# TYPE kaspersky_service_running gauge
kaspersky_service_running{host="$Host"} $running
# HELP kaspersky_database_age_hours Age of AV databases in hours
# TYPE kaspersky_database_age_hours gauge
kaspersky_database_age_hours{host="$Host"} $ageHours
# HELP kaspersky_last_update_timestamp Unix timestamp of last DB update
# TYPE kaspersky_last_update_timestamp gauge
kaspersky_last_update_timestamp{host="$Host"} $lastUpdate
# HELP wazuh_agent_running 1=running 0=stopped
# TYPE wazuh_agent_running gauge
wazuh_agent_running{host="$Host"} $wazuhRunning
"@ | Set-Content $OutFile -Encoding UTF8
'@
    $monitorScript | Set-Content "C:\msp-scripts\monitor_kaspersky.ps1" -Encoding UTF8
    Write-Ok "Скрипт мониторинга Kaspersky создан"

    # Task Scheduler: каждые 5 минут
    $action  = New-ScheduledTaskAction -Execute "powershell.exe" `
        -Argument '-NonInteractive -ExecutionPolicy Bypass -File "C:\msp-scripts\monitor_kaspersky.ps1"'
    $trigger = New-ScheduledTaskTrigger -Once -At (Get-Date) `
        -RepetitionInterval (New-TimeSpan -Minutes 5)
    $settings = New-ScheduledTaskSettingsSet -MultipleInstances Ignore `
        -ExecutionTimeLimit (New-TimeSpan -Minutes 2)
    Register-ScheduledTask -TaskName "MSP-Monitor-Kaspersky" `
        -Action $action -Trigger $trigger -Settings $settings `
        -User "SYSTEM" -RunLevel Highest -Force | Out-Null
    Write-Ok "Task Scheduler: MSP-Monitor-Kaspersky (каждые 5 мин)"
}

# ── Запустить службу ──────────────────────────────────────────────
Write-Info "Запускаю Wazuh Agent..."
Start-Sleep -Seconds 5
try {
    Start-Service "OssecSvc" -ErrorAction SilentlyContinue
    Set-Service "OssecSvc" -StartupType Automatic
    $svc = Get-Service "OssecSvc"
    Write-Ok "Служба OssecSvc: $($svc.Status)"
} catch {
    Write-Warn "Служба: $_"
}

# ── Cleanup ───────────────────────────────────────────────────────
Remove-Item $MsiPath -Force -ErrorAction SilentlyContinue

Write-Host ""
Write-Host "══════════════════════════════════════════" -ForegroundColor Green
Write-Host "  ✅ Wazuh Agent установлен!"
Write-Host ""
Write-Host "  Проверить на Manager (ssh executor-vm):"
Write-Host "  docker exec wazuh-manager /var/ossec/bin/agent_control -l"
Write-Host ""
Write-Host "  Логи агента:"
Write-Host "  Get-Content 'C:\Program Files (x86)\ossec-agent\ossec.log' -Tail 20"
Write-Host "══════════════════════════════════════════" -ForegroundColor Green
