# ═══════════════════════════════════════════════════════════════════
# kes_deploy_gpo.ps1 — Установка KES через Group Policy
# Тариф: Gold
# Запуск: PowerShell от Domain Admin на Domain Controller
#
# ЧТО ДЕЛАЕТ СКРИПТ:
#   1. Создаёт GPO "MSP-KES-Deploy"
#   2. Привязывает GPO к OU с серверами
#   3. Инструкция по добавлению .msi через GPMC
#
# ПРЕДВАРИТЕЛЬНЫЕ ТРЕБОВАНИЯ:
#   1. KSC (Kaspersky Security Center) развёрнут у Исполнителя
#      → см. SOP_executor_gold.md §5
#   2. Пакет KES скачан из KSC и скопирован в SYSVOL
#   3. Лицензия активирована на KSC
#
# КАК РАБОТАЕТ GPO-ДЕПЛОЙ:
#   GPO → Software Installation → указываем .msi →
#   Windows при gpupdate устанавливает KES автоматически →
#   KES подключается к KSC по сети и получает политики
# ═══════════════════════════════════════════════════════════════════

$ErrorActionPreference = "Stop"

# ── Пути к инсталлятору ─────────────────────────────────────────────
# Файлы должны быть в SYSVOL — сетевая папка доступная всем ПК в домене
$KesMsiPath = "\\domain.local\SYSVOL\domain.local\msp-tools\kes_setup.msi"
$DomainPath = (Get-ADDomain).DistinguishedName

Write-Host "════════════════════════════════════════════"
Write-Host " MSP-KES-Deploy — GPO для Kaspersky"
Write-Host "════════════════════════════════════════════"

# ── Проверить что MSI доступен ─────────────────────────────────────
if (-not (Test-Path $KesMsiPath)) {
    Write-Host "⚠ MSI не найден: $KesMsiPath"
    Write-Host "Скачайте KES из KSC и скопируйте в SYSVOL:"
    Write-Host "  1. KSC → Tasks → Install application → Download package"
    Write-Host "  2. Скопировать .msi в \\domain.local\SYSVOL\domain.local\msp-tools\"
    Write-Host "  3. Запустить этот скрипт ещё раз"
    exit 1
}

# ── Создать GPO ─────────────────────────────────────────────────────
$Gpo = New-GPO -Name "MSP-KES-Deploy"
Write-Host "  ✓ GPO MSP-KES-Deploy создан"

# ── Привязать к OU ──────────────────────────────────────────────────
# Заменить "OU=Servers" на реальный путь OU!
$TargetOU = "OU=Servers,$DomainPath"
New-GPLink -Name "MSP-KES-Deploy" -Target $TargetOU
Write-Host "  ✓ GPO привязан к: $TargetOU"

# ── Инструкция по Software Installation ─────────────────────────────
# Это нужно сделать ВРУЧНУЮ через GPMC — PowerShell не умеет
# добавлять Software Installation программно
Write-Host ""
Write-Host "⚠ ВРУЧНУЮ через GPMC (Group Policy Management Console):"
Write-Host "  1. Правый клик на MSP-KES-Deploy → Edit"
Write-Host "  2. Computer Configuration → Software Settings → Software Installation"
Write-Host "  3. Правый клик → New → Package"
Write-Host "  4. Указать путь: $KesMsiPath"
Write-Host "  5. Выбрать 'Assigned' (установить автоматически)"
Write-Host "  6. OK"
Write-Host ""
Write-Host "Применить на клиентах: gpupdate /force"
Write-Host "════════════════════════════════════════════"
