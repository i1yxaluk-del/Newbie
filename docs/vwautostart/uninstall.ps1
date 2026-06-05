param()

$TaskName = "MSPVMWatcher"
$TrayTaskName = "MSPVMWatcherTray"

$trayProc = Get-Process -Name powershell -ErrorAction SilentlyContinue | Where-Object {
    $cmd = (Get-CimInstance Win32_Process -Filter "ProcessId=$($_.Id)" -ErrorAction SilentlyContinue).CommandLine
    $cmd -match "tray.ps1"
}
$trayProc | Stop-Process -Force -ErrorAction SilentlyContinue

$watcherProc = Get-Process -Name powershell -ErrorAction SilentlyContinue | Where-Object {
    $cmd = (Get-CimInstance Win32_Process -Filter "ProcessId=$($_.Id)" -ErrorAction SilentlyContinue).CommandLine
    $cmd -match "watcher.ps1"
}
$watcherProc | Stop-Process -Force -ErrorAction SilentlyContinue

Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false -ErrorAction SilentlyContinue
Unregister-ScheduledTask -TaskName $TrayTaskName -Confirm:$false -ErrorAction SilentlyContinue

Write-Host "Removed $TaskName and $TrayTaskName"
