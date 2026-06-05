param()

$TaskName = "MSPVMWatcher"
$ScriptDir = $PSScriptRoot
$WatcherScript = Join-Path $ScriptDir "watcher.ps1"
$TrayScript = Join-Path $ScriptDir "tray.ps1"

$existing = Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
if ($existing) {
    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false
}

$action = New-ScheduledTaskAction -Execute "powershell.exe" `
    -Argument "-NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File `"$WatcherScript`""

$trigger = New-ScheduledTaskTrigger -AtStartup

$principal = New-ScheduledTaskPrincipal -UserId $env:USERNAME -LogonType S4U -RunLevel Highest

$settings = New-ScheduledTaskSettingsSet `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -StartWhenAvailable `
    -RestartCount 3 `
    -RestartInterval (New-TimeSpan -Minutes 1) `
    -ExecutionTimeLimit (New-TimeSpan -Days 0)

Register-ScheduledTask -TaskName $TaskName `
    -Action $action `
    -Trigger $trigger `
    -Principal $principal `
    -Settings $settings `
    -Description "MSPShield VM Watcher: monitors Yandex Cloud VM via ping, auto-starts if stopped" | Out-Null

$trayTaskName = "MSPVMWatcherTray"
$existingTray = Get-ScheduledTask -TaskName $trayTaskName -ErrorAction SilentlyContinue
if ($existingTray) {
    Unregister-ScheduledTask -TaskName $trayTaskName -Confirm:$false
}

$trayAction = New-ScheduledTaskAction -Execute "powershell.exe" `
    -Argument "-NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File `"$TrayScript`""

$trayTrigger = @(
    (New-ScheduledTaskTrigger -AtLogOn)
)

$trayPrincipal = New-ScheduledTaskPrincipal -UserId $env:USERNAME -LogonType Interactive -RunLevel Highest

$traySettings = New-ScheduledTaskSettingsSet `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -StartWhenAvailable `
    -ExecutionTimeLimit (New-TimeSpan -Days 0)

Register-ScheduledTask -TaskName $trayTaskName `
    -Action $trayAction `
    -Trigger $trayTrigger `
    -Principal $trayPrincipal `
    -Settings $traySettings `
    -Description "MSPShield VM Watcher tray icon" | Out-Null

Write-Host "Installed:"
Write-Host "  $TaskName (watcher, runs as $env:USERNAME at startup)"
Write-Host "  $trayTaskName (tray icon, runs at logon)"
Write-Host ""
Write-Host "Starting watcher and tray..."
Start-ScheduledTask -TaskName $TaskName
Start-ScheduledTask -TaskName $trayTaskName
