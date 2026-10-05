<#
Назначение: проверить production VM по TCP/443 и сообщить о недоступности в Telegram.
Где запускать: операторская Windows-станция, не production VM.
Вход: JSON config; ключи Cloud.ru и Telegram — User environment variables.
Побочные эффекты: только чтение (GET статуса ВМ через Cloud.ru API). VM не запускает и не останавливает.
Откат: остановить задачу MSPVMWatcher.
#>
param([string]$ConfigPath = "$env:USERPROFILE\.config\mspshield\vm-watcher.json")
$ErrorActionPreference = "Stop"
if (-not (Test-Path $ConfigPath)) { throw "Нет config: $ConfigPath" }
$config = Get-Content $ConfigPath -Raw -Encoding UTF8 | ConvertFrom-Json
foreach ($field in @("target")) { if (-not $config.$field) { throw "В config отсутствует $field" } }
$Target = [string]$config.target
$Port = if ($config.port) { [int]$config.port } else { 443 }
$IntervalSeconds = if ($config.intervalSeconds) { [int]$config.intervalSeconds } else { 300 }
$FailThreshold = if ($config.failThreshold) { [int]$config.failThreshold } else { 5 }
# Cloud.ru Evolution (необязательно: без projectId/vmId watcher работает как чистый TCP-монитор).
$ProjectId = [string]$config.projectId
$VmId = [string]$config.vmId
$LogPath = Join-Path $PSScriptRoot "vm-watcher.log"

function Write-Log([string]$Message) { Add-Content $LogPath "[$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')] $Message" -Encoding UTF8 }
function Test-Tcp443 {
    try { $client = [Net.Sockets.TcpClient]::new(); $task = $client.ConnectAsync($Target, $Port); if (-not $task.Wait(3000)) { return $false }; $client.Dispose(); return $true } catch { return $false }
}

# Cloud.ru Evolution: OAuth-ключ -> access_token (TTL ~1 час), затем статус ВМ.
function Get-CloudRuToken {
    if (-not $env:CLOUDRU_KEY_ID -or -not $env:CLOUDRU_KEY_SECRET) { return $null }
    $body = @{ keyId = $env:CLOUDRU_KEY_ID; secret = $env:CLOUDRU_KEY_SECRET } | ConvertTo-Json -Compress
    $resp = Invoke-RestMethod -Method Post -Uri "https://iam.api.cloud.ru/api/v1/auth/token" -ContentType "application/json" -Body $body
    return $resp.access_token
}
function Get-VmStatus {
    if (-not $ProjectId -or -not $VmId) { return "unknown" }
    try {
        $token = Get-CloudRuToken
        if (-not $token) { Write-Log "CLOUDRU_KEY_ID/CLOUDRU_KEY_SECRET не заданы"; return "unknown" }
        $vm = Invoke-RestMethod -Uri "https://compute.api.cloud.ru/api/v1/vms/$VmId`?project_id=$ProjectId" -Headers @{ Authorization = "Bearer $token" } -TimeoutSec 20
        return [string]$vm.state
    } catch { Write-Log "Cloud.ru status error: $_"; return "unknown" }
}
function Send-Alert([string]$Text) {
    $token, $chat = $env:TELEGRAM_BOT_TOKEN, $env:TELEGRAM_CHAT_ID
    if (-not $token -or -not $chat) { Write-Log "Telegram не настроен"; return }
    try { Invoke-RestMethod -Uri ("https://api.telegram.org/bot" + $token + "/sendMessage") -Method Post -ContentType "application/json" -Body (@{chat_id=$chat;text=$Text} | ConvertTo-Json -Compress) | Out-Null } catch { Write-Log "Telegram error: $_" }
}

Write-Log "Watcher started: target=$Target port=$Port vm=$VmId project=$ProjectId"
$fails = 0; $alerted = $false
while ($true) {
    if (Test-Tcp443) {
        if ($fails -gt 0) { Send-Alert "MSP VM снова доступна по TCP/$Port после $fails ошибок" }
        $fails = 0; $alerted = $false; Start-Sleep $IntervalSeconds; continue
    }
    $fails++; Write-Log "TCP/$Port FAIL $fails/$FailThreshold"
    if ($fails -ge $FailThreshold -and -not $alerted) {
        $state = Get-VmStatus; Write-Log "Cloud.ru VM state=$state"
        if ($state -eq "running") {
            Send-Alert "MSP VM RUNNING, но TCP/$Port недоступен: проверьте Caddy/SG/маршрут (SSH только через AmneziaWG, 10.9.0.1)"
        } elseif ($state -eq "stopped" -or $state -eq "stopping") {
            Send-Alert "MSP VM ОСТАНОВЛЕНА ($state). Запустите её в консоли Cloud.ru (API старта ВМ в Evolution не публикует)."
        } else {
            Send-Alert "Статус MSP VM не определён ($state); TCP/$Port недоступен"
        }
        $alerted = $true
    }
    Start-Sleep 30
}
