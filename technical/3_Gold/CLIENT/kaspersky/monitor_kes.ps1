# ═══════════════════════════════════════════════════════════════════
# monitor_kes.ps1 — Мониторинг KES через windows_exporter textfile
# Тариф: Gold
# Размещение: C:\msp-scripts\monitor_kes.ps1
# Запуск: Task Scheduler каждые 5 минут
#
# ЧТО ДЕЛАЕТ СКРИПТ:
#   1. Проверяет статус службы Kaspersky (AVP*)
#   2. Читает дату обновления баз из реестра
#   3. Пишет .prom файл в textfile_collector
#   4. windows_exporter подхватывает и отдаёт Prometheus
#
# АЛЕРТЫ (у Исполнителя):
#   kaspersky_service_running == 0  → CRITICAL (KES не работает)
#   kaspersky_database_age_hours > 48 → WARNING (базы устарели)
# ═══════════════════════════════════════════════════════════════════

$MetricsDir = "C:\Program Files\windows_exporter\textfile_collector"
$OutFile    = "$MetricsDir\kaspersky.prom"
$Hostname   = $env:COMPUTERNAME

# ── Убедиться что директория существует ─────────────────────────────
if (-not (Test-Path $MetricsDir)) {
    New-Item -ItemType Directory -Force -Path $MetricsDir | Out-Null
}

# ── Статус службы KES ──────────────────────────────────────────────
# Имя службы KES обычно начинается с "AVP" (Kaspersky Anti-Virus Product)
$kesSvc = Get-Service -Name "AVP*" -ErrorAction SilentlyContinue | Select-Object -First 1
$kesRunning = if ($kesSvc -and $kesSvc.Status -eq "Running") { 1 } else { 0 }

# ── Дата последнего обновления баз ──────────────────────────────────
# Kaspersky хранит время обновления в реестре
$kesRegPath = "HKLM:\SOFTWARE\KasperskyLab\*\*\Statistics\*"
$lastUpdate = try {
    $reg = Get-ItemProperty $kesRegPath -ErrorAction Stop
    $ts = $reg.LastSuccessfulUpdate
    if ($ts) {
        # Конвертировать FILETIME (Windows) в Unix timestamp
        [DateTimeOffset]::FromFileTime($ts).ToUnixTimeSeconds()
    } else { 0 }
} catch { 0 }

# Возраст баз в часах
# Если >48 часов — значит базы устарели, нужен alert!
$dbAgeHours = if ($lastUpdate -gt 0) {
    [math]::Round(([DateTimeOffset]::UtcNow.ToUnixTimeSeconds() - $lastUpdate) / 3600, 1)
} else { -1 }

# ── Записать .prom файл ─────────────────────────────────────────────
# Формат Prometheus exposition format:
#   # HELP — описание метрики
#   # TYPE — тип (gauge = текущее значение)
#   metric_name{label="value"} число

@"
# HELP kaspersky_service_running 1=running 0=stopped
# TYPE kaspersky_service_running gauge
kaspersky_service_running{host="$Hostname"} $kesRunning
# HELP kaspersky_database_age_hours Age of antivirus databases in hours
# TYPE kaspersky_database_age_hours gauge
kaspersky_database_age_hours{host="$Hostname"} $dbAgeHours
# HELP kaspersky_last_update_timestamp Unix timestamp of last database update
# TYPE kaspersky_last_update_timestamp gauge
kaspersky_last_update_timestamp{host="$Hostname"} $lastUpdate
"@ | Set-Content $OutFile -Encoding UTF8
