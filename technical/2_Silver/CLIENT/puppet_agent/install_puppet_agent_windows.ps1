# ═══════════════════════════════════════════════════════════════════
# install_puppet_agent_windows.ps1 — Установка Puppet Agent на Windows
# Тариф: Silver+
# Запуск: PowerShell от Administrator
#
# ЧТО ДЕЛАЕТ СКРИПТ:
#   1. Скачивает MSI-установщик Puppet Agent
#   2. Устанавливает с параметрами сервера
#   3. Запускает первый run — запрос сертификата
#
# ПОСЛЕ УСТАНОВКИ:
#   Исполнитель подписывает сертификат:
#   puppetserver ca sign --certname <COMPUTERNAME>.clients.internal
# ═══════════════════════════════════════════════════════════════════
param(
    [string]$PuppetServer  = "puppet-server.internal",
    [string]$PuppetVersion = "8.5.0"
)

$ErrorActionPreference = "Stop"

# ── Скачать MSI ─────────────────────────────────────────────────────
$AgentUrl = "https://downloads.puppetlabs.com/windows/puppet8/puppet-agent-${PuppetVersion}-x64.msi"
$MsiPath  = "$env:TEMP\puppet-agent.msi"

Write-Host "Скачиваю Puppet Agent v${PuppetVersion}..."
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
Invoke-WebRequest -Uri $AgentUrl -OutFile $MsiPath -UseBasicParsing

# ── Имя сертификата ────────────────────────────────────────────────
# Формат: COMPUTERNAME.clients.internal — чтобы Puppet Server
# мог группировать клиентов по домену
$Certname = $env:COMPUTERNAME.ToLower() + ".clients.internal"

# ── Установка (тихая) ──────────────────────────────────────────────
# PUPPET_MASTER_SERVER — адрес Puppet Server
# PUPPET_AGENT_CERTNAME — уникальное имя сертификата
Write-Host "Устанавливаю Puppet Agent..."
Start-Process msiexec.exe -ArgumentList @(
    "/i", $MsiPath,
    "/quiet",
    "/norestart",
    "PUPPET_MASTER_SERVER=$PuppetServer",
    "PUPPET_AGENT_CERTNAME=$Certname"
) -Wait

# ── Добавить в PATH ────────────────────────────────────────────────
$puppetBin = "C:\Program Files\Puppet Labs\Puppet\bin"
if ($env:Path -notlike "*$puppetBin*") {
    $env:Path += ";$puppetBin"
}

# ── Первый запуск — запрос сертификата ─────────────────────────────
Write-Host ""
Write-Host "Запрашиваю сертификат ($Certname)..."
& puppet agent --test --waitforcert 60 2>&1 | Select-Object -First 20

Write-Host ""
Write-Host "Puppet Agent установлен."
Write-Host ""
Write-Host "НА PUPPET SERVER подписать сертификат:"
Write-Host "  puppetserver ca sign --certname $Certname"
Write-Host ""
Write-Host "Проверить после подписания:"
Write-Host "  puppet agent --test --verbose"

# ── Удалить MSI ─────────────────────────────────────────────────────
Remove-Item $MsiPath -Force -ErrorAction SilentlyContinue
