<#
.SYNOPSIS
    SSH tunnel to MSPShield monitoring (Grafana, Prometheus, Alertmanager)
.EXAMPLE
    .\tunnel-monitoring.ps1
    Opens tunnels and prints access URLs. Press Ctrl+C to close.
#>

$VmIp = "93.77.184.219"
$SshKey = "$env:USERPROFILE\.ssh\id_ed25519_yc"
$SshOpts = "-o StrictHostKeyChecking=no -o UserKnownHostsFile=NUL -o ServerAliveInterval=60 -o ServerAliveCountMax=3"

Write-Host ""
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "  MSPShield Monitoring SSH Tunnel" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "  Grafana:       http://localhost:3000" -ForegroundColor White
Write-Host "                 admin / <see Vaultwarden>" -ForegroundColor Gray
Write-Host "  Prometheus:    http://localhost:9090" -ForegroundColor White
Write-Host "  Alertmanager:  http://localhost:9093" -ForegroundColor White
Write-Host "  Blackbox:      http://localhost:9115" -ForegroundColor White
Write-Host "  Stalwart:      http://localhost:8080" -ForegroundColor White
Write-Host "                 admin / <see Vaultwarden>" -ForegroundColor Gray
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "  Press Ctrl+C to close tunnel." -ForegroundColor Yellow
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host ""

$SshExe = "C:\Windows\System32\OpenSSH\ssh.exe"
$command = "$SshExe $SshOpts -i `"$SshKey`" -L 3000:127.0.0.1:3000 -L 9090:127.0.0.1:9090 -L 9093:127.0.0.1:9093 -L 9115:127.0.0.1:9115 -L 8080:127.0.0.1:8080 ubuntu@${VmIp}"

Write-Host "Opening tunnel to $VmIp ..." -ForegroundColor Yellow
Invoke-Expression $command
