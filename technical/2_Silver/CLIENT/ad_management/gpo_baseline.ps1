# ═══════════════════════════════════════════════════════════════════
# gpo_baseline.ps1 — Создание базовых GPO политик безопасности
# Тариф: Silver+
# Запуск: PowerShell от Domain Admin на Domain Controller
#
# ЧТО ДЕЛАЕТ СКРИПТ:
#   1. Парольная политика (длина 12, сложность, срок 90 дней)
#   2. Политика блокировки аккаунта (5 попыток, блокировка 30 мин)
#   3. GPO "MSP-Security-Baseline" — аудит событий
#   4. GPO "MSP-ScreenLock" — блокировка экрана 15 мин
#
# ПРЕДВАРИТЕЛЬНЫЕ ТРЕБОВАНИЯ:
#   - Запускать на Domain Controller
#   - Права Domain Admin
#   - Модуль ActiveDirectory (установлен по умолчанию на DC)
# ═══════════════════════════════════════════════════════════════════

$ErrorActionPreference = "Stop"

Write-Host "════════════════════════════════════════════"
Write-Host " MSP GPO Baseline — Создание политик"
Write-Host "════════════════════════════════════════════"

# ── 1. Парольная политика ───────────────────────────────────────────
# Применяется через Default Domain Policy (FGPP)
# MinPasswordLength 12 — минимум 12 символов (рекомендация ФСТЭК)
# MaxPasswordAge 90    — менять каждые 90 дней
# MinPasswordAge 1     — нельзя менять чаще раза в день
# PasswordHistory 12  — помнить 12 предыдущих паролей
# ComplexityEnabled    — требовать: верхний+нижний регистр, цифру, спецсимвол

$DomainPath = (Get-ADDomain).DistinguishedName

Write-Host ""
Write-Host "── 1. Парольная политика ──"
Set-ADDefaultDomainPasswordPolicy -Identity $env:USERDOMAIN `
    -MinPasswordLength 12 `
    -MaxPasswordAge (New-TimeSpan -Days 90) `
    -MinPasswordAge (New-TimeSpan -Days 1) `
    -PasswordHistoryCount 12 `
    -ComplexityEnabled $true `
    -ReversibleEncryptionEnabled $false   # НИКОГДА не включать обратимое шифрование!

Write-Host "  ✓ Минимальная длина: 12"
Write-Host "  ✓ Срок действия: 90 дней"
Write-Host "  ✓ Сложность: включена"
Write-Host "  ✓ Обратимое шифрование: ОТКЛЮЧЕНО"

# ── 2. Политика блокировки аккаунта ────────────────────────────────
# LockoutThreshold 5   — блокировка после 5 неудачных попыток
# LockoutDuration 30   — блокировка на 30 минут
# LockoutObservation 30 — окно наблюдения 30 минут

Write-Host ""
Write-Host "── 2. Политика блокировки ──"
Set-ADDefaultDomainPasswordPolicy -Identity $env:USERDOMAIN `
    -LockoutDuration (New-TimeSpan -Minutes 30) `
    -LockoutObservationWindow (New-TimeSpan -Minutes 30) `
    -LockoutThreshold 5

Write-Host "  ✓ Порог: 5 неудачных попыток"
Write-Host "  ✓ Блокировка: 30 минут"

# ── 3. GPO: Аудит событий ──────────────────────────────────────────
# Зачем: аудит входов, изменений политик, доступа к объектам
# Используется Wazuh/Loki для анализа инцидентов

Write-Host ""
Write-Host "── 3. GPO: MSP-Security-Baseline ──"

$gpo = New-GPO -Name "MSP-Security-Baseline"

# Привязать к домену (применяется ко всем)
New-GPLink -Name "MSP-Security-Baseline" -Target $DomainPath -Enforced Yes

Write-Host "  ✓ GPO создан и привязан к домену"
Write-Host "  ⚠ Настроить параметры аудита через GPMC вручную:"
Write-Host "    Computer Config → Policies → Windows Settings → Security Settings → Advanced Audit Policy"
Write-Host "    - Audit Logon: Success + Failure"
Write-Host "    - Audit Account Logon: Success + Failure"
Write-Host "    - Audit Object Access: Failure"
Write-Host "    - Audit Policy Change: Success + Failure"
Write-Host "    - Audit Account Management: Success + Failure"

# ── 4. GPO: Блокировка экрана ──────────────────────────────────────
# Блокировка через 15 минут бездействия
# Защита от несанкционированного доступа к оставленному компьютеру

Write-Host ""
Write-Host "── 4. GPO: MSP-ScreenLock ──"

$LockGpo = New-GPO -Name "MSP-ScreenLock"

# Настроить блокировку экрана (через реестр)
Set-GPRegistryValue -Name "MSP-ScreenLock" `
    -Key "HKLM\SOFTWARE\Policies\Microsoft\Windows\Personalization" `
    -ValueName "NoLockScreen" `
    -Type DWord `
    -Value 0    # 0 = не отключать экран блокировки

# Таймаут блокировки экрана (секунды)
Set-GPRegistryValue -Name "MSP-ScreenLock" `
    -Key "HKLM\SOFTWARE\Microsoft\Windows\CurrentVersion\Policies\System" `
    -ValueName "InactivityTimeoutSecs" `
    -Type DWord `
    -Value 900  # 900 секунд = 15 минут

New-GPLink -Name "MSP-ScreenLock" -Target $DomainPath

Write-Host "  ✓ GPO создан и привязан"
Write-Host "  ✓ Блокировка экрана: 15 минут"

# ── Итог ────────────────────────────────────────────────────────────
Write-Host ""
Write-Host "════════════════════════════════════════════"
Write-Host " Все GPO созданы!"
Write-Host " Применить на клиентах: gpupdate /force"
Write-Host "════════════════════════════════════════════"
