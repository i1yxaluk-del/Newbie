<#
Назначение: проверить production VM по TCP/443 и запустить остановленную VM через YC CLI.
Где запускать: операторская Windows-станция, не production VM.
Вход: JSON config; Telegram token/chat ID — User environment variables.
Побочные эффекты: может запустить указанную VM после нескольких ошибок.
Откат: остановить задачу MSPVMWatcher; скрипт никогда не останавливает VM.
#>
param([string]$ConfigPath = "$env:USERPROFILE\.config\mspshield\vm-watcher.json")
$ErrorActionPreference = "Stop"
if (-not (Test-Path $ConfigPath)) { throw "Нет config: $ConfigPath" }
$config = Get-Content $ConfigPath -Raw -Encoding UTF8 | ConvertFrom-Json
foreach ($field in @("target", "vmId")) { if (-not $config.$field) { throw "В config отсутствует $field" } }
$Target = [string]$config.target
$VmId = [string]$config.vmId
$Port = if ($config.port) { [int]$config.port } else { 443 }
$IntervalSeconds = if ($config.intervalSeconds) { [int]$config.intervalSeconds } else { 300 }
$FailThreshold = if ($config.failThreshold) { [int]$config.failThreshold } else { 5 }
$YcExe = if ($config.ycExe) { [string]$config.ycExe } else { "yc.exe" }
$LogPath = Join-Path $PSScriptRoot "vm-watcher.log"

function Write-Log([string]$Message) { Add-Content $LogPath "[$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')] $Message" -Encoding UTF8 }
function Test-Tcp443 {
    try { $client = [Net.Sockets.TcpClient]::new(); $task = $client.ConnectAsync($Target, $Port); if (-not $task.Wait(3000)) { return $false }; $client.Dispose(); return $true } catch { return $false }
}
function Invoke-Yc([string[]]$Arguments) {
    # Современный yc читает профиль из %USERPROFILE%\.config\yandex-cloud; YC_CONFIG_DIR не задаём.
    $output = & $YcExe @Arguments --format json 2>&1 | Out-String
    if ($LASTEXITCODE -ne 0) { throw "yc exit=$LASTEXITCODE: $output" }
    return $output
}
function Get-VmStatus { try { return ((Invoke-Yc @("compute","instance","get",$VmId)) | ConvertFrom-Json).status } catch { Write-Log $_; return "unknown" } }
function Start-Vm { try { & $YcExe compute instance start $VmId --async | Out-Null; return ($LASTEXITCODE -eq 0) } catch { Write-Log $_; return $false } }
function Send-Alert([string]$Text) {
    $token, $chat = $env:TELEGRAM_BOT_TOKEN, $env:TELEGRAM_CHAT_ID
    if (-not $token -or -not $chat) { Write-Log "Telegram не настроен"; return }
    try { Invoke-RestMethod -Uri ("https://api.telegram.org/bot" + $token + "/sendMessage") -Method Post -ContentType "application/json" -Body (@{chat_id=$chat;text=$Text} | ConvertTo-Json -Compress) | Out-Null } catch { Write-Log "Telegram error: $_" }
}

Write-Log "Watcher started: target=$Target port=$Port vm=$VmId"
$fails = 0; $alerted = $false
while ($true) {
    if (Test-Tcp443) {
        if ($fails -gt 0) { Send-Alert "MSP VM снова доступна по TCP/$Port после $fails ошибок" }
        $fails = 0; $alerted = $false; Start-Sleep $IntervalSeconds; continue
    }
    $fails++; Write-Log "TCP/$Port FAIL $fails/$FailThreshold"
    if ($fails -ge $FailThreshold -and -not $alerted) {
        $status = Get-VmStatus; Write-Log "YC status=$status"
        if ($status -eq "STOPPED" -or $status -eq "stopped") {
            if (Start-Vm) { Send-Alert "MSP VM была остановлена; команда запуска отправлена" }
        } elseif ($status -eq "RUNNING" -or $status -eq "running") {
            Send-Alert "MSP VM RUNNING, но TCP/$Port недоступен: проверьте Caddy/SG/маршрут"
        } else { Send-Alert "Статус MSP VM не определён; TCP/$Port недоступен" }
        $alerted = $true
    }
    Start-Sleep 30
}
