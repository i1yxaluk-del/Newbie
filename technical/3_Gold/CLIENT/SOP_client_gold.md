# SOP — Gold · Сторона КЛИЕНТА
# Версия 3.0 | PowerShell-first (Windows 10 admin workstation)
# ═══════════════════════════════════════════════════════════════════
#
# Gold клиент = Silver клиент + Wazuh Agent + Kaspersky Endpoint Security (KES).
# На клиенте — только лёгкие агенты. Тяжёлые сервисы (Wazuh Manager,
# Indexer, Dashboard, KSC) — у Исполнителя (см. SOP_executor_gold.md).
#
# Все операции — с Win10-станции администратора:
#   • Linux-серверы клиента → SSH (`ssh root@srv`, here-strings)
#   • Windows-серверы клиента → Invoke-Command (WinRM) / GPO
# ═══════════════════════════════════════════════════════════════════

## СОДЕРЖАНИЕ

0. Предпосылки
1. Wazuh Agent — Linux
2. Wazuh Agent — Windows (с FIM для 1С)
3. Kaspersky Endpoint Security — развёртывание через GPO
4. KES — мониторинг через windows_exporter
5. Верификация Gold Client
6. Troubleshooting

---

## 0. ПРЕДПОСЫЛКИ

- На Win10-станции — те же требования, что и в `SOP_client_bronze.md` §0.
- На клиенте Bronze + Silver уже установлены (`node_exporter`,
  `windows_exporter`, restic, WireGuard, Promtail, Puppet Agent).
- В сессии PowerShell подгружен `$client`:
  ```powershell
  $client.Gold = @{
      WazuhManager   = '10.9.0.3'
      WazuhVersion   = '4.7.5'
      KesMsiSysvol   = '\\domain.local\SYSVOL\domain.local\msp-tools\kes_setup.msi'
      KesOuPath      = 'OU=Servers,DC=domain,DC=local'
  }
  ```

---

## 1. WAZUH AGENT — LINUX

### 1.1. Что делает агент

- Собирает логи (`/var/log/auth.log`, `/var/log/syslog`, nginx, postgres).
- FIM — `/etc`, `/var/www`, `/bin`, `/sbin` и т.д.
- Сканер уязвимостей (CVE).
- Шлёт в Wazuh Manager (порт `1514/TCP` через VPN).
- Ресурсы — ~50–100 МБ RAM.

### 1.2. Установка через Ansible (рекомендуется)

```powershell
ssh msp-automation @"
cd /opt/ansible
ansible-playbook playbooks/deploy_gold.yml \
    -i inventory/clients/$($client.Slug)/hosts \
    --tags wazuh_agent \
    -e client_slug=$($client.Slug) \
    -e client_name='$($client.Name)' \
    -e wazuh_manager=$($client.Gold.WazuhManager) -v
"@
```

### 1.3. Ручная установка (если Ansible недоступен)

```powershell
$srv     = 'srv-app-01'
$manager = $client.Gold.WazuhManager
$ver     = $client.Gold.WazuhVersion

$bash = @"
set -euo pipefail
WAZUH_MANAGER='$manager'
WAZUH_VERSION='$ver'

# 1. GPG-ключ
curl -fsSL https://packages.wazuh.com/key/GPG-KEY-WAZUH | \
    sudo gpg --no-default-keyring --keyring gnupg-ring:/usr/share/keyrings/wazuh.gpg --import
sudo chmod 644 /usr/share/keyrings/wazuh.gpg

# 2. Репозиторий
echo 'deb [signed-by=/usr/share/keyrings/wazuh.gpg] https://packages.wazuh.com/4.x/apt/ stable main' | \
    sudo tee /etc/apt/sources.list.d/wazuh.list

# 3. Установка
sudo apt-get update -q
sudo apt-get install -y wazuh-agent

# 4. Адрес Manager
sudo sed -i "s|<address>MANAGER_IP</address>|<address>\${WAZUH_MANAGER}</address>|g" \
    /var/ossec/etc/ossec.conf

# 5. FIM + rootcheck + CVE scanner
sudo tee /var/ossec/etc/shared/agent.conf >/dev/null << 'EOF'
<agent_config>
  <syscheck>
    <disabled>no</disabled>
    <frequency>43200</frequency>
    <directories check_all="yes">/etc</directories>
    <directories check_all="yes">/var/ossec/etc</directories>
    <directories check_all="yes" report_changes="yes">/var/www</directories>
    <directories check_all="yes">/bin,/sbin,/usr/bin,/usr/sbin</directories>
    <ignore>/etc/mtab</ignore>
    <ignore>/etc/hosts.deny</ignore>
    <ignore>/etc/mail/statistics</ignore>
    <ignore>/etc/random-seed</ignore>
    <ignore type="sregex">.log\$|.swp\$|.tmp\$</ignore>
  </syscheck>
  <rootcheck>
    <disabled>no</disabled>
    <check_files>yes</check_files>
    <check_trojans>yes</check_trojans>
  </rootcheck>
  <wodle name="vulnerability-detector">
    <disabled>no</disabled>
    <interval>1d</interval>
    <run_on_start>yes</run_on_start>
  </wodle>
</agent_config>
EOF

# 6. UFW — разрешить исходящие к Manager
sudo ufw allow out to \${WAZUH_MANAGER} port 1514 proto tcp comment 'Wazuh Agent'   || true
sudo ufw allow out to \${WAZUH_MANAGER} port 1515 proto tcp comment 'Wazuh Enrol'   || true

# 7. Старт + статус
sudo systemctl daemon-reload
sudo systemctl enable --now wazuh-agent
sleep 5
sudo /var/ossec/bin/wazuh-control status
"@
$bash | ssh root@$srv bash -s

# Проверить регистрацию агента на Manager
ssh msp-wazuh "docker exec wazuh-manager /var/ossec/bin/agent_control -l | head"
```

---

## 2. WAZUH AGENT — WINDOWS (FIM для 1С)

```powershell
$srv     = 'WIN-AD01'
$cred    = Get-Credential -UserName "$srv\Administrator"
$manager = $client.Gold.WazuhManager
$ver     = $client.Gold.WazuhVersion

Invoke-Command -ComputerName $srv -Credential $cred -ScriptBlock {
    param($WazuhManager, $WazuhVersion)

    $url = "https://packages.wazuh.com/4.x/windows/wazuh-agent-${WazuhVersion}-1.msi"
    $msi = "$env:TEMP\wazuh-agent.msi"
    [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
    Invoke-WebRequest -Uri $url -OutFile $msi -UseBasicParsing

    Start-Process msiexec.exe -ArgumentList @(
        '/i', $msi, '/quiet', '/norestart',
        "WAZUH_MANAGER=$WazuhManager",
        "WAZUH_AGENT_NAME=$env:COMPUTERNAME"
    ) -Wait

    # FIM для 1С и Windows-критичных директорий
    $osSec = 'C:\Program Files (x86)\ossec-agent\ossec.conf'
    if (Test-Path $osSec) {
        $extra = @"
  <syscheck>
    <directories check_all="yes">C:\Program Files\1cv8</directories>
    <directories check_all="yes">C:\Program Files (x86)\1cv8</directories>
    <directories check_all="yes" report_changes="no">C:\Users\*\AppData\Roaming\1C</directories>
    <directories check_all="yes">C:\Windows\System32\drivers\etc</directories>
    <ignore type="sregex">.log`$</ignore>
    <ignore type="sregex">.tmp`$</ignore>
  </syscheck>
"@
        Add-Content -Path $osSec -Value $extra
    }

    Start-Service OssecSvc -ErrorAction SilentlyContinue
    Set-Service   OssecSvc -StartupType Automatic
    Remove-Item $msi -Force
    Get-Service OssecSvc | Select-Object Name, Status, StartType
} -ArgumentList $manager, $ver
```

---

## 3. KASPERSKY ENDPOINT SECURITY — РАЗВЁРТЫВАНИЕ

### 3.1. Через GPO (рекомендуется)

```
Логика:
  1. У Исполнителя в KSC создан installer-пакет KES (.msi).
  2. .msi кладётся в SYSVOL на DC.
  3. GPO Software Installation раздаёт MSI на нужные OU.
  4. KES сам подключается к KSC за политикой и лицензией.

Почему не ручной скрипт:
  - GPO — стандарт в AD-среде.
  - Автоматически применяется к новым ПК в OU.
  - Централизованный контроль политик через KSC.
```

С Win10 — через Invoke-Command на Domain Controller:

```powershell
$dc   = 'WIN-DC01'
$cred = Get-Credential -UserName 'CORP\msp-admin'
$msi  = $client.Gold.KesMsiSysvol
$ou   = $client.Gold.KesOuPath

Invoke-Command -ComputerName $dc -Credential $cred -ScriptBlock {
    param($KesMsi, $TargetOU)
    Import-Module ActiveDirectory, GroupPolicy

    if (-not (Get-GPO -Name 'MSP-KES-Deploy' -ErrorAction SilentlyContinue)) {
        $gpo = New-GPO -Name 'MSP-KES-Deploy'
        New-GPLink -Name 'MSP-KES-Deploy' -Target $TargetOU
    }

    Write-Output "GPO 'MSP-KES-Deploy' создан и привязан к $TargetOU"
    Write-Output "Добавьте MSI ($KesMsi) через GPMC -> Software Installation"
    Write-Output "KES установится при следующем 'gpupdate /force' на клиентах"
} -ArgumentList $msi, $ou
```

### 3.2. Ручная установка (если домена нет)

```powershell
$srv  = 'STANDALONE-SRV'
$cred = Get-Credential -UserName "$srv\Administrator"
$kes  = '\\fileserver\share\kes_setup.exe'
$ini  = '\\fileserver\share\kes.ini'

Invoke-Command -ComputerName $srv -Credential $cred -ScriptBlock {
    param($KesExe, $KesIni)
    Start-Process -FilePath $KesExe -ArgumentList "/s /i $KesIni" -Wait -NoNewWindow
    Get-Service 'AVP*' | Select-Object Name, Status, StartType
} -ArgumentList $kes, $ini
```

---

## 4. KES — МОНИТОРИНГ ЧЕРЕЗ WINDOWS_EXPORTER

`monitor_kes.ps1` пишет `kaspersky.prom` в `textfile_collector` Windows-сервера —
`windows_exporter` подхватывает файл и отдаёт метрики Prometheus.

```powershell
$srv  = 'WIN-AD01'
$cred = Get-Credential -UserName "$srv\Administrator"

Invoke-Command -ComputerName $srv -Credential $cred -ScriptBlock {
    $ScriptDir = 'C:\msp-scripts'
    New-Item -ItemType Directory -Force -Path $ScriptDir | Out-Null

    $script = @'
$MetricsDir = "C:\Program Files\windows_exporter\textfile_collector"
$OutFile    = "$MetricsDir\kaspersky.prom"
$Hostname   = $env:COMPUTERNAME

# Статус службы
$kes        = Get-Service -Name 'AVP*' -ErrorAction SilentlyContinue | Select-Object -First 1
$kesRunning = if ($kes -and $kes.Status -eq 'Running') { 1 } else { 0 }

# Дата последнего обновления баз
$lastUpdate = try {
    $reg = Get-ItemProperty 'HKLM:\SOFTWARE\KasperskyLab\*\*\Statistics\*' -ErrorAction Stop
    $ts  = $reg.LastSuccessfulUpdate
    if ($ts) { [DateTimeOffset]::FromFileTime($ts).ToUnixTimeSeconds() } else { 0 }
} catch { 0 }

$dbAgeHours = if ($lastUpdate -gt 0) {
    [math]::Round(([DateTimeOffset]::UtcNow.ToUnixTimeSeconds() - $lastUpdate) / 3600, 1)
} else { -1 }

if (-not (Test-Path $MetricsDir)) { New-Item -ItemType Directory -Force -Path $MetricsDir | Out-Null }

@"
# HELP kaspersky_service_running 1=running 0=stopped
# TYPE kaspersky_service_running gauge
kaspersky_service_running{host="$Hostname"} $kesRunning
# HELP kaspersky_database_age_hours Age of antivirus databases in hours
# TYPE kaspersky_database_age_hours gauge
kaspersky_database_age_hours{host="$Hostname"} $dbAgeHours
# HELP kaspersky_last_update_timestamp Unix timestamp of last DB update
# TYPE kaspersky_last_update_timestamp gauge
kaspersky_last_update_timestamp{host="$Hostname"} $lastUpdate
"@ | Set-Content $OutFile -Encoding UTF8
'@
    Set-Content -Path "$ScriptDir\monitor_kes.ps1" -Value $script -Encoding UTF8

    $action  = New-ScheduledTaskAction -Execute 'powershell.exe' `
        -Argument '-NonInteractive -ExecutionPolicy Bypass -File "C:\msp-scripts\monitor_kes.ps1"'
    $trigger = New-ScheduledTaskTrigger -Once -At (Get-Date) `
        -RepetitionInterval (New-TimeSpan -Minutes 5)
    $settings= New-ScheduledTaskSettingsSet -ExecutionTimeLimit (New-TimeSpan -Minutes 2)

    Register-ScheduledTask -TaskName 'MSP-KES-Monitor' `
        -Action $action -Trigger $trigger -Settings $settings `
        -User 'SYSTEM' -RunLevel Highest -Force | Out-Null
}
```

---

## 5. ВЕРИФИКАЦИЯ GOLD CLIENT

```powershell
function Test-MspGoldClient {
    param([Parameter(Mandatory)]$Client)

    Test-MspSilverClient -Client $Client | Out-Null

    foreach ($s in $Client.Servers) {
        Write-Host "`n=== Gold checks · $($s.Host) ($($s.OS)) ===" -ForegroundColor Cyan

        if ($s.OS -eq 'linux') {
            $check = @'
echo -n "wazuh-agent active ..... "
systemctl is-active --quiet wazuh-agent && echo OK || echo FAIL

echo -n "wazuh-control status ... "
sudo /var/ossec/bin/wazuh-control status 2>/dev/null | grep -q "wazuh-modulesd running" && echo OK || echo WARN

echo -n "VPN -> Manager ........... "
ping -c 2 -W 3 10.9.0.3 >/dev/null && echo OK || echo FAIL
'@
            $check | ssh root@$($s.Host) bash -s
        }
        else {
            $cred = Get-Credential -UserName "$($s.Host)\Administrator" -Message "WinRM creds"
            Invoke-Command -ComputerName $s.Host -Credential $cred -ScriptBlock {
                @{
                    'OssecSvc'         = (Get-Service OssecSvc -ErrorAction SilentlyContinue).Status
                    'Kaspersky (AVP)'  = (Get-Service 'AVP*'    -ErrorAction SilentlyContinue | Select-Object -First 1).Status
                    'KES metrics file' = (Test-Path 'C:\Program Files\windows_exporter\textfile_collector\kaspersky.prom')
                    'Monitor task'     = (Get-ScheduledTask -TaskName 'MSP-KES-Monitor' -ErrorAction SilentlyContinue).State
                }
            } | Format-Table -AutoSize
        }
    }

    Write-Host "`n--- Wazuh Manager view ---" -ForegroundColor Cyan
    ssh msp-wazuh "docker exec wazuh-manager /var/ossec/bin/agent_control -l | head -20"
}

Test-MspGoldClient -Client $client
```

---

## 6. TROUBLESHOOTING

| Проблема                                | Диагностика с Win10                                                                              | Решение                                                                                          |
|-----------------------------------------|--------------------------------------------------------------------------------------------------|--------------------------------------------------------------------------------------------------|
| Wazuh Agent (Linux) не подключается     | `ssh root@srv 'sudo /var/ossec/bin/wazuh-control status'`                                        | `ssh root@srv 'ping -c2 10.9.0.3 && grep address /var/ossec/etc/ossec.conf'`                     |
| FIM не показывает изменения             | `ssh root@srv 'grep -A5 syscheck /var/ossec/etc/shared/agent.conf'`                              | Убедиться `<disabled>no</disabled>`; `ssh root@srv 'sudo systemctl restart wazuh-agent'`         |
| Wazuh Agent (Windows) не стартует       | `Invoke-Command ... { Get-Service OssecSvc \| fl }`                                              | `Invoke-Command ... { Start-Service OssecSvc; Get-EventLog -LogName Application -Source ossec }` |
| KES не устанавливается через GPO        | `Invoke-Command -ComputerName WIN-CLIENT ... { gpresult /r /scope computer }`                     | На клиенте `gpupdate /force`; проверить путь MSI в SYSVOL и таргет OU                            |
| KES установлен, но не запущен           | `Invoke-Command ... { Get-Service 'AVP*' }`                                                       | `Invoke-Command ... { Start-Service 'AVP*' }`; проверить лицензию в KSC                          |
| KES базы устарели                       | `ssh msp-bastion 'curl -s http://10.9.0.2:9101/metrics \| grep kaspersky_database_age_hours'`     | Обновить через KSC или: `Invoke-Command ... { & 'C:\Program Files\Kaspersky Lab\KES\avp.com' UPDATE }` |
| `monitor_kes.ps1` не пишет метрики      | `Invoke-Command ... { Get-ScheduledTask MSP-KES-Monitor \| Get-ScheduledTaskInfo }`               | Перепроверить путь к textfile_collector; проверить, что `windows_exporter` запущен               |
