<#
Назначение: установить VM Watcher как две задачи Windows Task Scheduler.
Где запускать: операторская Windows-станция от администратора.
Проверка: Get-ScheduledTask MSPVMWatcher; Get-Content .\vm-watcher.log -Tail 20.
Откат: .\uninstall.ps1.
#>
param()
$ErrorActionPreference = "Stop"
$TaskName = "MSPVMWatcher"
$TrayTaskName = "MSPVMWatcherTray"
$ScriptDir = $PSScriptRoot
$WatcherScript = Join-Path $ScriptDir "watcher.ps1"
$TrayScript = Join-Path $ScriptDir "tray.ps1"
$ConfigPath = Join-Path $env:USERPROFILE ".config\mspshield\vm-watcher.json"

if (-not (Test-Path $ConfigPath)) { throw "Создайте $ConfigPath по образцу config.example.json" }
foreach ($name in @($TaskName, $TrayTaskName)) {
    if (Get-ScheduledTask -TaskName $name -ErrorAction SilentlyContinue) {
        Unregister-ScheduledTask -TaskName $name -Confirm:$false
    }
}
# Токены не встраиваются в action: watcher читает User environment во время запуска.
$action = New-ScheduledTaskAction -Execute "powershell.exe" -Argument "-NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File `"$WatcherScript`" -ConfigPath `"$ConfigPath`""
$principal = New-ScheduledTaskPrincipal -UserId $env:USERNAME -LogonType S4U -RunLevel Highest
$settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable -RestartCount 3 -RestartInterval (New-TimeSpan -Minutes 1) -ExecutionTimeLimit (New-TimeSpan -Days 0)
Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger (New-ScheduledTaskTrigger -AtStartup) -Principal $principal -Settings $settings -Description "MSPShield: проверка VM по TCP/443 и запуск через YC CLI" | Out-Null
$trayAction = New-ScheduledTaskAction -Execute "powershell.exe" -Argument "-NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File `"$TrayScript`""
$trayPrincipal = New-ScheduledTaskPrincipal -UserId $env:USERNAME -LogonType Interactive -RunLevel Highest
Register-ScheduledTask -TaskName $TrayTaskName -Action $trayAction -Trigger (New-ScheduledTaskTrigger -AtLogOn) -Principal $trayPrincipal -Settings $settings -Description "MSPShield VM Watcher tray" | Out-Null
Start-ScheduledTask $TaskName
Start-ScheduledTask $TrayTaskName
Write-Host "Установлено. Конфиг: $ConfigPath"
