# SOP — Gold · Сторона КЛИЕНТА
# Версия 3.0 | Апрель 2026
# ═══════════════════════════════════════════════════════════════════
#
# Gold клиент = Silver клиент + Wazuh Agent + Kaspersky Endpoint Security
#
# ПРИНЦИП: на клиенте — агенты, всё тяжёлое у Исполнителя.
#
# Для кого: Junior-инженер, выполняющий установку на серверах клиента
# ═══════════════════════════════════════════════════════════════════

## СОДЕРЖАНИЕ

1. Wazuh Agent — Linux
2. Wazuh Agent — Windows (с FIM для 1С)
3. Kaspersky Endpoint Security — развёртывание через GPO
4. KES — мониторинг через windows_exporter
5. Верификация Gold Client
6. Troubleshooting

---

## 1. WAZUH AGENT — LINUX

### 1.1 Что такое Wazuh и зачем он клиенту

```
Wazuh Agent — ЛЁГКИЙ агент (аналог node_exporter по нагрузке):
  ✓ Собирает системные логи (auth, syslog, nginx, postgres)
  ✓ Мониторит изменения файлов (FIM — File Integrity Monitoring)
  ✓ Сканирует уязвимости (CVE database)
  ✓ Отправляет ВСЕ данные → Wazuh Manager (у Исполнителя через VPN)

ВАЖНО для Junior:
  - Wazuh — слой ОБНАРУЖЕНИЯ, не предотвращения
  - Wazuh НЕ заменяет антивирус, firewall, hardening
  - Порт агента: 1514/TCP к Manager, не открывает ничего наружу
  - Ресурсы: ~50–100 MB RAM на агент
```

### 1.2 Автоматическая установка (Ansible)

```bash
# На Automation VM Исполнителя:
ansible-playbook -i inventory/clients/CLIENT/hosts \
  playbooks/deploy_gold.yml \
  --tags wazuh_agent \
  -e "client_slug=CLIENT_SLUG client_name='ООО Название'" \
  -v
```

### 1.3 Ручная установка

```bash
# Запустить скрипт: sudo bash install_wazuh_agent_linux.sh
# Или вручную по шагам ниже:

WAZUH_MANAGER="${WAZUH_MANAGER:-10.9.0.3}"  # IP Wazuh Manager ЧЕРЕЗ VPN
WAZUH_VERSION="4.7.5"

# ── Шаг 1: Добавить GPG-ключ репозитория Wazuh ─────────────────────
# GPG-ключ нужен чтобы apt проверял что пакеты действительно от Wazuh
curl -s https://packages.wazuh.com/key/GPG-KEY-WAZUH | \
    gpg --no-default-keyring --keyring gnupg-ring:/usr/share/keyrings/wazuh.gpg --import
chmod 644 /usr/share/keyrings/wazuh.gpg

# ── Шаг 2: Добавить репозиторий ─────────────────────────────────────
echo "deb [signed-by=/usr/share/keyrings/wazuh.gpg] https://packages.wazuh.com/4.x/apt/ stable main" \
    > /etc/apt/sources.list.d/wazuh.list

# ── Шаг 3: Установить агент ─────────────────────────────────────────
apt-get update -q
apt-get install -y wazuh-agent

# ── Шаг 4: Настроить адрес Manager ──────────────────────────────────
# ossec.conf — главный конфиг Wazuh Agent
sed -i "s|<address>MANAGER_IP</address>|<address>${WAZUH_MANAGER}</address>|g" \
    /var/ossec/etc/ossec.conf

# ── Шаг 5: Настройка FIM (мониторинг важных файлов) ────────────────
# FIM = File Integrity Monitoring — отслеживает изменения в файлах
# Если кто-то изменил /etc/passwd или /etc/ssh/sshd_config — мы узнаем
cat > /var/ossec/etc/shared/agent.conf << 'EOF'
<agent_config>
  <syscheck>
    <disabled>no</disabled>
    <frequency>43200</frequency>  <!-- Проверка каждые 12 часов -->
    <!-- Критичные системные конфиги -->
    <directories check_all="yes">/etc</directories>
    <directories check_all="yes">/var/ossec/etc</directories>
    <!-- Веб-файлы (если есть веб-сервер) -->
    <directories check_all="yes" report_changes="yes">/var/www</directories>
    <!-- Системные бинарники (защита от rootkit) -->
    <directories check_all="yes">/bin,/sbin,/usr/bin,/usr/sbin</directories>
    <!-- Исключения: файлы которые часто меняются нормально -->
    <ignore>/etc/mtab</ignore>
    <ignore>/etc/hosts.deny</ignore>
    <ignore>/etc/mail/statistics</ignore>
    <ignore>/etc/random-seed</ignore>
    <ignore type="sregex">.log$|.swp$|.tmp$</ignore>
  </syscheck>

  <rootcheck>
    <disabled>no</disabled>
    <check_files>yes</check_files>
    <check_trojans>yes</check_trojans>
  </rootcheck>

  <!-- Сканер уязвимостей — проверяет установленные пакеты на CVE -->
  <wodle name="vulnerability-detector">
    <disabled>no</disabled>
    <interval>1d</interval>  <!-- Раз в день -->
    <run_on_start>yes</run_on_start>
  </wodle>
</agent_config>
EOF

# ── Шаг 6: Настроить UFW (если используется) ───────────────────────
# Агент ИСХОДЯЩИЙ — не нужно открывать порты входящие
# Но если нужно разрешить исходящие к Manager:
ufw allow out to 10.9.0.3 port 1514 proto tcp comment "Wazuh Agent"
ufw allow out to 10.9.0.3 port 1515 proto tcp comment "Wazuh Enrollment"

# ── Шаг 7: Запустить ───────────────────────────────────────────────
systemctl daemon-reload
systemctl enable --now wazuh-agent

sleep 5
/var/ossec/bin/wazuh-control status

# ── Шаг 8: Проверка ─────────────────────────────────────────────────
# Локально: агент должен работать
systemctl is-active wazuh-agent && echo "OK: Wazuh Agent работает"

# Удалённо: попросить Исполнителя проверить регистрацию:
# ssh wazuh-vm 'docker exec wazuh-manager /var/ossec/bin/agent_control -l'
# Должен быть статус "Active" для нашего агента
```

---

## 2. WAZUH AGENT — WINDOWS

### 2.1 Установка

```powershell
# Запустить: install_wazuh_agent_windows.ps1
# Или вручную:

param(
    [string]$WazuhManager = "10.9.0.3",  # IP Manager ЧЕРЕЗ VPN
    [string]$WazuhVersion = "4.7.5"
)

$MsiUrl  = "https://packages.wazuh.com/4.x/windows/wazuh-agent-${WazuhVersion}-1.msi"
$MsiPath = "$env:TEMP\wazuh-agent.msi"

# Скачать MSI
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
Invoke-WebRequest -Uri $MsiUrl -OutFile $MsiPath -UseBasicParsing

$AgentName = $env:COMPUTERNAME

# Установить (тихая установка)
Start-Process msiexec.exe -ArgumentList @(
    "/i", $MsiPath,
    "/quiet",
    "/norestart",
    "WAZUH_MANAGER=$WazuhManager",
    "WAZUH_AGENT_NAME=$AgentName"
) -Wait

# ── Настроить FIM для 1С и Windows ─────────────────────────────────
# FIM = File Integrity Monitoring — отслеживает критичные изменения
$OsSecConf = "C:\Program Files (x86)\ossec-agent\ossec.conf"
if (Test-Path $OsSecConf) {
    # Добавить мониторинг 1С директорий
    $extraConf = @"
  <syscheck>
    <!-- 1С Enterprise — критичные директории -->
    <directories check_all="yes">C:\Program Files\1cv8</directories>
    <directories check_all="yes">C:\Program Files (x86)\1cv8</directories>
    <!-- Базы данных 1С (без report_changes — слишком много данных) -->
    <directories check_all="yes" report_changes="no">C:\Users\*\AppData\Roaming\1C</directories>
    <!-- Windows hosts файл (часто модифицируется вредоносами) -->
    <directories check_all="yes">C:\Windows\System32\drivers\etc</directories>
    <!-- Исключения: лог-файлы и tmp — меняются постоянно, не алертить -->
    <ignore type="sregex">.log$</ignore>
    <ignore type="sregex">.tmp$</ignore>
  </syscheck>
"@
    Add-Content -Path $OsSecConf -Value $extraConf
    Write-Host "FIM конфигурация для 1С добавлена"
}

# Запустить службу
Start-Service OssecSvc -ErrorAction SilentlyContinue
Set-Service OssecSvc -StartupType Automatic

Get-Service OssecSvc | Select-Object Name, Status, StartType

Remove-Item $MsiPath -Force
Write-Host "Wazuh Agent установлен"
```

---

## 3. KASPERSKY ENDPOINT SECURITY — DEPLOY

### 3.1 Способ установки: GPO (рекомендуется)

```
КАК РАБОТАЕТ KES DEPLOYMENT:
1. Исполнитель настраивает KSC (Kaspersky Security Center) → см. SOP_executor_gold.md §5
2. Из KSC скачивается инсталляционный пакет KES (.msi)
3. Пакет кладётся в SYSVOL на Domain Controller
4. Через GPO (Group Policy) пакет устанавливается на все ПК/серверы
5. KES автоматически подключается к KSC для получения политик

ПОЧЕМУ НЕ РУЧНОЙ СКРИПТ:
- GPO — стандартный способ развёртывания в AD-среде
- Автоматически применяется к новым ПК в OU
- Централизованный контроль обновлений и политик
```

### 3.2 GPO-деплой (скрипт для Domain Controller)

```powershell
# kes_deploy_gpo.ps1 — Создание GPO для установки KES
# Запускать на Domain Controller от Domain Admin
#
# ПРЕДВАРИТЕЛЬНЫЕ ТРЕБОВАНИЯ:
# 1. KSC развёрнут у Исполнителя → SOP_executor_gold.md §5
# 2. Пакет KES скачан из KSC и скопирован в SYSVOL
# 3. Лицензия активирована на KSC

$KesMsiPath = "\\domain.local\SYSVOL\domain.local\msp-tools\kes_setup.msi"

# Создать GPO для установки KES
$Gpo = New-GPO -Name "MSP-KES-Deploy"

# Привязать к OU с серверами (заменить на реальный путь OU)
New-GPLink -Name "MSP-KES-Deploy" -Target "OU=Servers,DC=domain,DC=local"

Write-Host "GPO MSP-KES-Deploy создан и привязан"
Write-Host "ВАЖНО: добавить .msi через GPMC → Software Installation вручную"
Write-Host "Путь MSI: $KesMsiPath"
Write-Host "KES установится при следующем gpupdate /force"
```

### 3.3 Ручная установка (если нет AD)

```powershell
# Только если нет домена — иначе использовать GPO!
# Скачать KES с сайта Kaspersky или из KSC

$KesInstaller = "\\fileserver\share\kes_setup.exe"
$KesIni = "\\fileserver\share\kes.ini"  # Файл ответов для тихой установки

Start-Process -FilePath $KesInstaller -ArgumentList "/s /i $KesIni" -Wait -NoNewWindow
Write-Host "KES установлен. Проверить: Get-Service 'AVP*'"
```

---

## 4. KES — МОНИТОРИНГ ЧЕРЕЗ WINDOWS_EXPORTER

### 4.1 Скрипт monitor_kes.ps1

```powershell
# monitor_kes.ps1 — Генерация метрик KES для Prometheus
# Размещение: C:\msp-scripts\monitor_kes.ps1
# Запуск: через Task Scheduler каждые 5 минут
# Результат: файл C:\Program Files\windows_exporter\textfile_collector\kaspersky.prom
#
# КАК РАБОТАЕТ:
# windows_exporter читает .prom файлы из textfile_collector
# и отдаёт их как метрики Prometheus
# Исполнитель видит статус антивируса в Grafana

$MetricsDir = "C:\Program Files\windows_exporter\textfile_collector"
$OutFile    = "$MetricsDir\kaspersky.prom"
$Hostname   = $env:COMPUTERNAME

# ── Статус службы KES ───────────────────────────────────────────────
# Имя службы KES обычно начинается с "AVP"
$kesSvc = Get-Service -Name "AVP*" -ErrorAction SilentlyContinue | Select-Object -First 1
$kesRunning = if ($kesSvc -and $kesSvc.Status -eq "Running") { 1 } else { 0 }

# ── Дата последнего обновления баз ─────────────────────────────────
# Читаем из реестра Kaspersky
$kesRegPath = "HKLM:\SOFTWARE\KasperskyLab\*\*\Statistics\*"
$lastUpdate = try {
    $reg = Get-ItemProperty $kesRegPath -ErrorAction Stop
    $ts = $reg.LastSuccessfulUpdate
    if ($ts) { [DateTimeOffset]::FromFileTime($ts).ToUnixTimeSeconds() } else { 0 }
} catch { 0 }

# Возраст баз в часах (если >48 — алерт!)
$dbAgeHours = if ($lastUpdate -gt 0) {
    [math]::Round(([DateTimeOffset]::UtcNow.ToUnixTimeSeconds() - $lastUpdate) / 3600, 1)
} else { -1 }

# ── Записать метрики ───────────────────────────────────────────────
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
```

### 4.2 Task Scheduler для monitor_kes.ps1

```powershell
# Добавить в Task Scheduler (выполнить один раз):
$Action  = New-ScheduledTaskAction -Execute "powershell.exe" `
    -Argument "-NonInteractive -ExecutionPolicy Bypass -File `"C:\msp-scripts\monitor_kes.ps1`""
$Trigger = New-ScheduledTaskTrigger -Once -At (Get-Date) -RepetitionInterval (New-TimeSpan -Minutes 5)
$Settings = New-ScheduledTaskSettingsSet -ExecutionTimeLimit (New-TimeSpan -Minutes 2) -DontStopOnIdleEnd

Register-ScheduledTask -TaskName "MSP-KES-Monitor" `
    -Action $Action -Trigger $Trigger -Settings $Settings `
    -User "SYSTEM" -RunLevel Highest -Force | Out-Null

Write-Host "Task MSP-KES-Monitor зарегистрирован (каждые 5 мин)"
```

---

## 5. ВЕРИФИКАЦИЯ GOLD CLIENT

```bash
#!/bin/bash
# Запускать на каждом Linux-сервере после установки Gold

echo "=== ВЕРИФИКАЦИЯ GOLD CLIENT ==="
echo "Сервер: $(hostname) | Дата: $(date)"

# ── Bronze + Silver проверки ────────────────────────────────────────
echo ""
echo "─── Bronze компоненты ───"
echo -n "  WireGuard VPN... "; sudo wg show wg0-msp &>/dev/null && echo "OK" || echo "FAIL"
echo -n "  node_exporter... "; systemctl is-active node_exporter &>/dev/null && echo "OK" || echo "FAIL"
echo -n "  Restic timer... "; systemctl is-active restic-backup.timer &>/dev/null && echo "OK" || echo "FAIL"

echo ""
echo "─── Silver компоненты ───"
echo -n "  Promtail... "; systemctl is-active promtail &>/dev/null && echo "OK" || echo "FAIL"
echo -n "  Puppet Agent... "; systemctl is-active puppet &>/dev/null && echo "OK" || echo "FAIL"

# ── Gold проверки ───────────────────────────────────────────────────
echo ""
echo "─── Gold компоненты ───"
echo -n "  Wazuh Agent... "; systemctl is-active wazuh-agent 2>/dev/null && echo "OK" || echo "FAIL"

echo -n "  Wazuh модули... "
/var/ossec/bin/wazuh-control status 2>/dev/null | grep -q "wazuh-modulesd running" && \
    echo "OK" || echo "WARN (проверить вручную)"

echo ""
echo "=== ВЕРИФИКАЦИЯ ЗАВЕРШЕНА ==="

# Windows-проверки (запустить отдельно в PowerShell):
# Get-Service "OssecSvc" | Select-Object Status       → Wazuh Agent
# Get-Service "AVP*" | Select-Object Name, Status     → Kaspersky
# type "C:\Program Files\windows_exporter\textfile_collector\kaspersky.prom"
```

---

## 6. TROUBLESHOOTING GOLD CLIENT

| Проблема | Диагностика | Решение |
|---|---|---|
| Wazuh Agent не подключается | `/var/ossec/bin/wazuh-control status` | Проверить VPN: `ping 10.9.0.3`; проверить адрес Manager в `ossec.conf`: `grep address /var/ossec/etc/ossec.conf` |
| FIM не показывает изменения | `/var/ossec/bin/wazuh-control status` | Проверить что syscheck не disabled: `grep -A5 syscheck /var/ossec/etc/shared/agent.conf` |
| KES не устанавливается через GPO | `gpresult /r /scope computer` | `gpupdate /force`, проверить путь MSI в SYSVOL, проверить что OU правильный |
| KES не работает после установки | `Get-Service "AVP*"` | Запустить: `Start-Service AVP*`; проверить лицензию в KSC |
| KES базы устарели | См. `kaspersky.prom` метрику `kaspersky_database_age_hours` | Обновить вручную через KSC или: `"C:\Program Files\Kaspersky Lab\KES\avp.com" UPDATE` |
| monitor_kes.ps1 не пишет метрики | Проверить Task Scheduler | `Get-ScheduledTask -TaskName "MSP-KES-Monitor"`; проверить путь к textfile_collector |
| Wazuh Agent — сертификат ошибка | `/var/ossec/bin/wazuh-control status` | `rm /var/ossec/etc/sslmanager.cert`, перезапустить агент: `systemctl restart wazuh-agent` |
