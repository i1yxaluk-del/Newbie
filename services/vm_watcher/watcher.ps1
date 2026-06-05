param(
    [string]$Target = "93.77.184.219",
    [int]$IntervalSeconds = 300,
    [int]$FailThreshold = 5,
    [string]$VmId = "fhmab2qg10esn09j0na2",
    [string]$YcConfigDir = "C:\ProgramData\yandex-cloud"
)

$ScriptDir = $PSScriptRoot
$LogPath = Join-Path $ScriptDir "vm-watcher.log"

function Write-Log {
    param([string]$Msg)
    $ts = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    $line = "[$ts] $Msg"
    Add-Content -Path $LogPath -Value $line -Encoding UTF8
}

function Test-VmPing {
    param([string]$T)
    $null = ping -n 1 -w 3000 $T 2>&1
    return ($LASTEXITCODE -eq 0)
}

function Get-VmStatus {
    param([string]$Id)
    $env:YC_CLI_INITIALIZATION_SILENCE = "true"
    $env:YC_CONFIG_DIR = $YcConfigDir
    $raw = & yc compute instance get $Id --format json 2>&1 | Where-Object {
        $_ -notmatch "WARNING:"
    } | Out-String
    try {
        $obj = $raw | ConvertFrom-Json
        return $obj.status
    } catch {
        Write-Log "YC CLI error: $($_.Exception.Message)"
        return "unknown"
    }
}

function Start-VmInstance {
    param([string]$Id)
    $env:YC_CLI_INITIALIZATION_SILENCE = "true"
    $env:YC_CONFIG_DIR = $YcConfigDir
    try {
        & yc compute instance start $Id --async 2>&1 | Out-Null
        Write-Log "VM START command sent for $Id"
        return $true
    } catch {
        Write-Log "VM START failed: $($_.Exception.Message)"
        return $false
    }
}

function Send-TgAlert {
    param([string]$Text)
    $token = "8950653616:AAGn3UrlAxD3sWP5hmnKpB6EvT2kiCxof_I"
    $chatId = "-1004230593984"
    try {
        $body = @{ chat_id = $chatId; text = $Text; parse_mode = "HTML" } | ConvertTo-Json -Compress
        Invoke-RestMethod -Uri "https://api.telegram.org/bot$token/sendMessage" -Method Post -Body $body -ContentType "application/json" | Out-Null
        Write-Log "Telegram alert sent"
    } catch {
        Write-Log "Telegram send failed: $($_.Exception.Message)"
    }
}

Write-Log "=== VM Watcher started ==="
Write-Log "Target=$Target Interval=${IntervalSeconds}s Threshold=$FailThreshold VM=$VmId"

$consecutiveFails = 0
$alerted = $false
$retryInterval = 30

while ($true) {
    $ok = Test-VmPing -T $Target

    if ($ok) {
        if ($consecutiveFails -gt 0) {
            Write-Log "PING OK (recovered after $consecutiveFails fails)"
            Send-TgAlert -Text "VM restored - ping $Target OK (was $consecutiveFails fails)"
        } else {
            Write-Log "PING OK"
        }
        $consecutiveFails = 0
        $alerted = $false
        Start-Sleep -Seconds $IntervalSeconds
    } else {
        $consecutiveFails++
        Write-Log "PING FAIL ($consecutiveFails/$FailThreshold)"

        if ($consecutiveFails -ge $FailThreshold -and -not $alerted) {
            Write-Log "Threshold reached - checking VM via YC CLI"
            $status = Get-VmStatus -Id $VmId
            Write-Log "VM status: $status"

            if ($status -eq "stopped") {
                Write-Log "VM STOPPED - sending start command"
                $started = Start-VmInstance -Id $VmId
                if ($started) {
                    Send-TgAlert -Text "VM msp-cloud-vm was STOPPED - start command sent (yc compute instance start)"
                }
            } elseif ($status -eq "running") {
                Write-Log "VM RUNNING but unreachable - network issue"
                Send-TgAlert -Text "VM msp-cloud-vm RUNNING but ping $Target fails ($consecutiveFails fails) - possible network/VPN issue"
            } else {
                Write-Log "VM status unknown: $status"
                Send-TgAlert -Text "VM status: $status - ping $Target fails ($consecutiveFails fails)"
            }
            $alerted = $true
            Start-Sleep -Seconds $IntervalSeconds
        } else {
            Start-Sleep -Seconds $retryInterval
        }
    }
}
