<#
Назначение: загрузить только разрешённые backup-артефакты и запустить restore.
Где запускать: операторская Windows-станция после подготовки новой VM.
Побочные эффекты: загружает архивы в /tmp/migration и запускает restore от root.
Проверка: restore exit=0, затем gates из migration/README.md.
Откат: восстановить snapshot новой VM; старая VM до acceptance не удаляется.
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
# accept-new допустим только для первого подключения. При изменении известного ключа SSH остановится.
$SshOpts = @("-o", "StrictHostKeyChecking=accept-new", "-i", $SshKeyPath)
$Allowed = @(
  "mongodump.archive.gz",
  "vaultwarden-data.tar.gz",
  "stalwart-etc.tar.gz",
  "stalwart-data.tar.gz",
  "max-session.tar.gz",
  "restore-on-vm.sh"
)
foreach ($required in @("mongodump.archive.gz", "restore-on-vm.sh")) {
  if (-not (Test-Path (Join-Path $MigrationDir $required))) { throw "Нет обязательного $required" }
}
& $SshExe @SshOpts "ubuntu@$NewVmIp" "mkdir -p /tmp/migration"
if ($LASTEXITCODE -ne 0) { throw "SSH недоступен или host key не подтверждён" }
foreach ($name in $Allowed) {
  $path = Join-Path $MigrationDir $name
  if (Test-Path $path) {
    Write-Host "Загрузка $name"
    & $ScpExe @SshOpts $path "ubuntu@${NewVmIp}:/tmp/migration/"
    if ($LASTEXITCODE -ne 0) { throw "Не удалось загрузить $name" }
  }
}
& $SshExe @SshOpts "ubuntu@$NewVmIp" "chmod +x /tmp/migration/restore-on-vm.sh && sudo /tmp/migration/restore-on-vm.sh"
if ($LASTEXITCODE -ne 0) { throw "Restore завершился с ошибкой" }
Write-Host "Restore завершён. Выполните acceptance gates до DNS switch." -ForegroundColor Green
