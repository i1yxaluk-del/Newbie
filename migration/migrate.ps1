<#
.SYNOPSIS
    Миграция MSP Cloud на новую ВМ / новый аккаунт Yandex Cloud.
    Запускается ПОСЛЕ deploy.ps1 (который создаёт ВМ и ставит приложение).

.DESCRIPTION
    1. Загружает migration-данные на новую ВМ через SCP
    2. Запускает restore-on-vm.sh (восстановление БД, почты, паролей, бэкапов)
    3. Выводит инструкции по DNS

.PARAMETER NewVmIp
    Публичный IP новой ВМ (из вывода deploy.ps1 или .deploy-state.json)

.PARAMETER SkipDeploy
    Не запускать deploy.ps1 (если ВМ уже создана)

.EXAMPLE
    .\migrate.ps1 -NewVmIp 51.250.1.2
    .\migrate.ps1 -SkipDeploy -NewVmIp 51.250.1.2
#>

[CmdletBinding()]
param(
    [Parameter(Mandatory=$true)]
    [string]$NewVmIp,

    [switch]$SkipDeploy
)

$ErrorActionPreference = "Stop"
$MigrationDir = $PSScriptRoot
$DeployDir = Join-Path $MigrationDir "..\deploy\yandex"
$SshKeyPath = Join-Path $env:USERPROFILE ".ssh\id_ed25519_yc_new"
$SshExe = "C:\Windows\System32\OpenSSH\ssh.exe"
$ScpExe = "C:\Windows\System32\OpenSSH\scp.exe"
$SshOpts = "-o StrictHostKeyChecking=no -o UserKnownHostsFile=NUL"

function Write-Stage { param([string]$Text) Write-Host "`n═══ $Text ═══" -ForegroundColor Cyan }
function Write-Ok   { param([string]$Text) Write-Host "  ✓ $Text" -ForegroundColor Green }
function Write-Fail { param([string]$Text) Write-Host "  ✗ $Text" -ForegroundColor Red; exit 1 }

Write-Host @"

  +--------------------------------------------------------------+
  |   MSP Cloud — MIGRATION to new VM                            |
  +--------------------------------------------------------------+
  |   Target IP: $NewVmIp
  |   Data dir:  $MigrationDir
  +--------------------------------------------------------------+
"@ -ForegroundColor Cyan

# ═══ Проверка файлов миграции ═══
Write-Stage "Проверка migration-данных"
$requiredFiles = @(
    "mongodump.archive.gz",
    "stalwart-data.tar.gz",
    "vaultwarden-data.tar.gz",
    "caddy-data.tar.gz",
    "backend.env.bak",
    "deploy.env.bak",
    "restic-env.sh",
    "restic-backup.sh",
    "restore-on-vm.sh"
)
foreach ($f in $requiredFiles) {
    $path = Join-Path $MigrationDir $f
    if (-not (Test-Path $path)) { Write-Fail "Отсутствует: $f" }
}
Write-Ok "Все файлы на месте ($($requiredFiles.Count) файлов)"

# ═══ SSH connectivity ═══
Write-Stage "Проверка SSH до $NewVmIp"
$sshTest = cmd /c "$SshExe $SshOpts -o ConnectTimeout=10 -i `"$SshKeyPath`" ubuntu@$NewVmIp echo READY 2>nul"
if ($sshTest -notmatch "READY") { Write-Fail "SSH не отвечает. Проверьте IP и что ВМ запущена." }
Write-Ok "SSH доступен"

# ═══ Загрузка данных ═══
Write-Stage "Загрузка migration-данных на ВМ"
cmd /c "$SshExe $SshOpts -i `"$SshKeyPath`" ubuntu@$NewVmIp `"mkdir -p /tmp/migration`" 2>nul"

$filesToUpload = Get-ChildItem -Path $MigrationDir -File | Where-Object {
    $_.Name -ne "migrate.ps1" -and $_.Name -ne "README.md"
}
foreach ($file in $filesToUpload) {
    Write-Host "  ↑ $($file.Name) ($([math]::Round($file.Length/1KB))KB)" -ForegroundColor Gray
    cmd /c "$ScpExe $SshOpts -i `"$SshKeyPath`" `"$($file.FullName)`" ubuntu@${NewVmIp}:/tmp/migration/ 2>nul"
    if ($LASTEXITCODE -ne 0) { Write-Fail "SCP не сработал для $($file.Name)" }
}
Write-Ok "Загружено $($filesToUpload.Count) файлов"

# ═══ Запуск restore ═══
Write-Stage "Восстановление данных на ВМ (restore-on-vm.sh)"
Write-Host "  Это займёт 1-3 минуты..." -ForegroundColor Gray
$restoreCmd = "chmod +x /tmp/migration/restore-on-vm.sh && sudo bash /tmp/migration/restore-on-vm.sh 2>&1"
cmd /c "$SshExe $SshOpts -i `"$SshKeyPath`" ubuntu@$NewVmIp `"$restoreCmd`" 2>nul"
if ($LASTEXITCODE -ne 0) { Write-Fail "restore-on-vm.sh завершился с ошибкой" }
Write-Ok "Восстановление завершено"

# ═══ Финальная проверка ═══
Write-Stage "Финальная проверка"
$health = cmd /c "$SshExe $SshOpts -i `"$SshKeyPath`" ubuntu@$NewVmIp `"curl -sS http://127.0.0.1:8001/api/health`" 2>nul"
Write-Host "  /api/health → $health" -ForegroundColor White

$containers = cmd /c "$SshExe $SshOpts -i `"$SshKeyPath`" ubuntu@$NewVmIp `"docker ps --format '{{.Names}}' | wc -l`" 2>nul"
Write-Host "  Контейнеров: $containers" -ForegroundColor White

# ═══ DNS инструкции ═══
Write-Host @"

  +--------------------------------------------------------------+
  |   MIGRATION COMPLETE                                         |
  +--------------------------------------------------------------+

  Новый IP: $NewVmIp

  ОБНОВИТЕ DNS (reg.ru / Namecheap):
    A  @       → $NewVmIp
    A  www     → $NewVmIp
    A  mail    → $NewVmIp
    A  vault   → $NewVmIp
    A  mon     → $NewVmIp
    MX @       → mail.msp-claude.online (приоритет 10)
    TTL: 300

  После обновления DNS (5-30 мин):
    curl https://msp-claude.online/api/health
    → {"status":"ok"}

  Старую ВМ можно остановить/удалить после проверки.
  +--------------------------------------------------------------+
"@ -ForegroundColor Green
