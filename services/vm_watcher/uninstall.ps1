<#
Назначение: удалить задачи VM Watcher и остановить только связанные PowerShell-процессы.
Где запускать: та же Windows-станция, где выполнялся install.ps1.
Побочные эффекты: автоматический запуск VM и tray прекращаются.
Проверка: Get-ScheduledTask MSPVMWatcher возвращает not found.
Откат: повторно запустить install.ps1.
#>
param()
$TaskName = "MSPVMWatcher"
$TrayTaskName = "MSPVMWatcherTray"
foreach ($pattern in @("watcher.ps1", "tray.ps1")) {
    Get-Process -Name powershell -ErrorAction SilentlyContinue | Where-Object {
        $command = (Get-CimInstance Win32_Process -Filter "ProcessId=$($_.Id)" -ErrorAction SilentlyContinue).CommandLine
        $command -match [regex]::Escape($pattern)
    } | Stop-Process -Force -ErrorAction SilentlyContinue
}
Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false -ErrorAction SilentlyContinue
Unregister-ScheduledTask -TaskName $TrayTaskName -Confirm:$false -ErrorAction SilentlyContinue
Write-Host "Удалены задачи $TaskName и $TrayTaskName"
