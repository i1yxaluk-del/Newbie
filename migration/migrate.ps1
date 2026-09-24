<#
.SYNOPSIS
  Загружает только разрешённые migration-артефакты и запускает restore.
.DESCRIPTION
  Не отключает проверку SSH host key и не переносит старые .env/cloud keys.
#>
[CmdletBinding()]
param(
  [Parameter(Mandatory=$true)][string]$NewVmIp,
  [string]$SshKeyPath = "$env:USERPROFILE\.ssh\id_ed25519_yc_new"
)
$ErrorActionPreference = "Stop"
$MigrationDir = $PSScriptRoot
$SshExe = "C:\Windows\System32\OpenSSH\ssh.exe"
$ScpExe = "C:\Windows\System32\OpenSSH\scp.exe"
$SshOpts = @("-o", "StrictHostKeyChecking=accept-new", "-i", $SshKeyPath)
$Allowed = @("mongodump.archive.gz", "vaultwarden-data.tar.gz", "max-session.tar.gz", "restore-on-vm.sh")

if (-not (Test-Path (Join-Path $MigrationDir "mongodump.archive.gz"))) { throw "Нет mongodump.archive.gz" }
if (-not (Test-Path (Join-Path $MigrationDir "restore-on-vm.sh"))) { throw "Нет restore-on-vm.sh" }

& $SshExe @SshOpts "ubuntu@$NewVmIp" "mkdir -p /tmp/migration"
if ($LASTEXITCODE -ne 0) { throw "SSH не доступен или host key не подтверждён" }
foreach ($Name in $Allowed) {
  $Path = Join-Path $MigrationDir $Name
  if (Test-Path $Path) {
    Write-Host "Загрузка $Name"
    & $ScpExe @SshOpts $Path "ubuntu@${NewVmIp}:/tmp/migration/"
    if ($LASTEXITCODE -ne 0) { throw "Не удалось загрузить $Name" }
  }
}
& $SshExe @SshOpts "ubuntu@$NewVmIp" "chmod +x /tmp/migration/restore-on-vm.sh && sudo /tmp/migration/restore-on-vm.sh"
if ($LASTEXITCODE -ne 0) { throw "Restore завершился с ошибкой" }
Write-Host "Restore завершён. Выполните gate из migration/README.md перед DNS switch." -ForegroundColor Green
