Add-Type -AssemblyName System.Windows.Forms

$ScriptDir = $PSScriptRoot
$TaskName = "MSPVMWatcher"
$WatcherScript = Join-Path $ScriptDir "watcher.ps1"
$LogPath = Join-Path $ScriptDir "vm-watcher.log"

function Get-TaskState {
    $t = Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
    if (-not $t) { return "notfound" }
    return $t.State.ToString().ToLower()
}

function Start-Watcher {
    Start-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
    Start-Sleep -Milliseconds 500
    Update-Tray
}

function Stop-Watcher {
    $proc = Get-Process -Name powershell -ErrorAction SilentlyContinue | Where-Object {
        $cmd = (Get-CimInstance Win32_Process -Filter "ProcessId=$($_.Id)" -ErrorAction SilentlyContinue).CommandLine
        $cmd -match "watcher.ps1"
    }
    $proc | Stop-Process -Force -ErrorAction SilentlyContinue
    Stop-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
    Start-Sleep -Milliseconds 500
    Update-Tray
}

function Set-Autostart {
    param([bool]$Enabled)
    $t = Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
    if (-not $t) { return }
    if ($Enabled) {
        Enable-ScheduledTask -TaskName $TaskName | Out-Null
    } else {
        Disable-ScheduledTask -TaskName $TaskName | Out-Null
    }
    Update-Tray
}

function Get-Autostart {
    $t = Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
    if (-not $t) { return $false }
    return ($t.Settings.Enabled -eq $true)
}

function Update-Tray {
    $state = Get-TaskState
    $isAutostart = Get-Autostart

    if ($state -eq "running") {
        $notifyIcon.Icon = [System.Drawing.SystemIcons]::Information
        $notifyIcon.Text = "MSP VM Watcher: RUNNING"
    } else {
        $notifyIcon.Icon = [System.Drawing.SystemIcons]::Warning
        $notifyIcon.Text = "MSP VM Watcher: STOPPED"
    }

    $menuStartStop.Text = if ($state -eq "running") { "Stop" } else { "Start" }
    $menuAutostart.Checked = $isAutostart
}

$notifyIcon = New-Object System.Windows.Forms.NotifyIcon
$notifyIcon.BalloonTipTitle = "MSP VM Watcher"
$notifyIcon.Visible = $true

$menuStartStop = New-Object System.Windows.Forms.ToolStripMenuItem
$menuStartStop.Text = "Start"

$menuAutostart = New-Object System.Windows.Forms.ToolStripMenuItem
$menuAutostart.Text = "Autostart with Windows"
$menuAutostart.CheckOnClick = $true

$menuExit = New-Object System.Windows.Forms.ToolStripMenuItem
$menuExit.Text = "Exit"

$contextMenu = New-Object System.Windows.Forms.ContextMenuStrip
$contextMenu.Items.AddRange(@($menuStartStop, $menuAutostart, (New-Object System.Windows.Forms.ToolStripSeparator), $menuExit))
$notifyIcon.ContextMenuStrip = $contextMenu

Update-Tray

$menuStartStop.Add_Click({
    $state = Get-TaskState
    if ($state -eq "running") {
        Stop-Watcher
    } else {
        Start-Watcher
    }
})

$menuAutostart.Add_Click({
    Set-Autostart -Enabled $menuAutostart.Checked
})

$menuExit.Add_Click({
    $notifyIcon.Visible = $false
    $notifyIcon.Dispose()
    [System.Windows.Forms.Application]::Exit()
})

$notifyIcon.Add_DoubleClick({
    $state = Get-TaskState
    if ($state -eq "running") {
        Stop-Watcher
    } else {
        Start-Watcher
    }
})

[System.Windows.Forms.Application]::Run()
