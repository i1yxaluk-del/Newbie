# SOP — Silver · Сторона КЛИЕНТА
# Версия 3.0 | PowerShell-first (Windows 10 admin workstation)
# ═══════════════════════════════════════════════════════════════════
#
# Silver на стороне клиента = Bronze ПЛЮС:
#   - Promtail (сбор логов → Loki Исполнителя)
#   - Puppet Agent (desired state)
#   - Управление AD/DNS/GPO через согласованный контур
#
# Развёртывание — с Win10-станции администратора (PowerShell 5.1+).
# На серверах клиента остаются Linux (через SSH) и Windows
# (через PowerShell Remoting / WinRM).
# ═══════════════════════════════════════════════════════════════════

## СОДЕРЖАНИЕ

0. Предпосылки
1. Архитектура (добавления к Bronze)
2. Promtail — установка и конфигурация
3. Puppet Agent — установка и регистрация
4. AD/DNS/GPO — управление
5. Верификация Silver
6. Troubleshooting

---

## 0. ПРЕДПОСЫЛКИ

- На Win10-станции — те же требования, что и в `SOP_client_bronze.md` §0.
- На серверах клиента Bronze уже установлен (`node_exporter`, restic, WireGuard).
- Сводный объект `$client` (см. Bronze §2) уже подгружен в сессию PowerShell.
- Известны:
  - `$client.Silver.LokiUrl`        — обычно `http://10.9.0.1:3100`
  - `$client.Silver.PuppetServer`   — обычно `puppet-server.internal`
  - `$client.Slug`, `$client.Name`  — для labels Loki

---

## 1. АРХИТЕКТУРА SILVER (КЛИЕНТ)

```
WINDOWS 10 АДМИН        СЕРВЕРЫ ЗАКАЗЧИКА                   YANDEX CLOUD (Исполнитель)
┌──────────────┐        ┌──────────────────────────────┐    ┌──────────────────────────────────┐
│ PowerShell   │        │ Linux                          │    │ Monitoring VM                    │
│  ssh + scp   │ ─SSH─▶ │ ├── node_exporter   :9100 ✓    │◀──▶│ ├── Prometheus :9090             │
│  Invoke-Cmd  │ ─WinRM▶│ ├── restic backup       ✓      │    │ ├── Grafana    :3000             │
│  yc CLI      │        │ ├── WireGuard          ✓       │    │ ├── Alertmanager :9093           │
└──────────────┘        │ ├── promtail ─────────────────┼────│ └── Loki :3100  ← NEW (Silver)  │
                        │ └── puppet_agent ─────────────┼────│                                  │
                        │                                │    │ Automation VM                    │
                        │ Windows                        │    │ ├── Puppet Server :8140 ← NEW    │
                        │ ├── windows_exporter :9182 ✓   │    │ └── Ansible Control       ← NEW │
                        │ ├── restic backup        ✓     │    └──────────────────────────────────┘
                        │ ├── WireGuard           ✓      │
                        │ └── puppet_agent        ✓      │
                        └──────────────────────────────┘
```

---

## 2. PROMTAIL (Linux)

### 2.1. Через Ansible с Automation VM (рекомендуется)

```powershell
ssh msp-automation @"
cd /opt/ansible
ansible-playbook playbooks/deploy_silver.yml \
    -i inventory/clients/$($client.Slug)/hosts \
    --tags promtail \
    -e client_slug=$($client.Slug) \
    -e client_name='$($client.Name)' -v
"@
```

### 2.2. Ручная установка (если Ansible недоступен)

```powershell
$srv         = 'srv-app-01'
$slug        = $client.Slug
$cname       = $client.Name
$promtailVer = '3.0.0'
$lokiUrl     = $client.Silver.LokiUrl

$bash = @"
set -euo pipefail
PROMTAIL_VERSION='$promtailVer'
LOKI_URL='$lokiUrl'
CLIENT_SLUG='$slug'
CLIENT_NAME='$cname'
HOST=\$(hostname -s)

# Скачать promtail
ARCH=linux-amd64
curl -sSL "https://github.com/grafana/loki/releases/download/v\${PROMTAIL_VERSION}/promtail-\${ARCH}.zip" -o /tmp/promtail.zip
unzip -q /tmp/promtail.zip -d /tmp/
sudo install -m 0755 "/tmp/promtail-\${ARCH}" /usr/local/bin/promtail
rm -rf /tmp/promtail*

# Конфиг
sudo mkdir -p /etc/promtail /var/lib/promtail
sudo tee /etc/promtail/config.yml >/dev/null << EOF
server:
  http_listen_port: 9080
  grpc_listen_port: 0
  log_level: warn

positions:
  filename: /var/lib/promtail/positions.yaml

clients:
  - url: \${LOKI_URL}/loki/api/v1/push
    tenant_id: \${CLIENT_SLUG}
    backoff_config:
      min_period: 500ms
      max_period: 5m
      max_retries: 10

scrape_configs:
  - job_name: varlog
    static_configs:
      - targets: [localhost]
        labels:
          job: varlog
          host: \${HOST}
          client: \${CLIENT_SLUG}
          client_name: '\${CLIENT_NAME}'
          __path__: /var/log/syslog

  - job_name: auth
    static_configs:
      - targets: [localhost]
        labels:
          job: auth
          host: \${HOST}
          client: \${CLIENT_SLUG}
          __path__: /var/log/auth.log

  - job_name: nginx
    static_configs:
      - targets: [localhost]
        labels:
          job: nginx
          host: \${HOST}
          client: \${CLIENT_SLUG}
          __path__: /var/log/nginx/*.log

  - job_name: postgresql
    static_configs:
      - targets: [localhost]
        labels:
          job: postgresql
          host: \${HOST}
          client: \${CLIENT_SLUG}
          __path__: /var/log/postgresql/*.log
EOF

sudo chown -R nobody:nogroup /var/lib/promtail 2>/dev/null || true

# Systemd
sudo tee /etc/systemd/system/promtail.service >/dev/null << 'EOF'
[Unit]
Description=Promtail Log Shipper
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
ExecStart=/usr/local/bin/promtail -config.file=/etc/promtail/config.yml
Restart=on-failure
RestartSec=5s
SyslogIdentifier=promtail

[Install]
WantedBy=multi-user.target
EOF

sudo ufw allow from 10.9.0.0/24 to any port 9080 proto tcp comment 'promtail HTTP' || true

sudo systemctl daemon-reload
sudo systemctl enable --now promtail
sudo systemctl --no-pager status promtail | head -10
curl -fsS http://localhost:9080/ready
"@
$bash | ssh root@$srv bash -s
```

---

## 3. PUPPET AGENT (Linux + Windows)

### 3.1. Концепция

| Без Puppet                          | С Puppet                                  |
|-------------------------------------|--------------------------------------------|
| Настроили → надеемся, что не сломают | Каждые 30 мин проверяется desired state    |
| Drift замечаем случайно              | Drift фиксируется, при необходимости откатывается |

Что фиксируется на клиенте:
- `/etc/ssh/sshd_config` — небезопасные опции возвращаются к baseline.
- `sysctl` — сетевая безопасность ядра.
- `fail2ban` — конфиг и сервис.
- systemd-юниты `node_exporter`, `restic-backup.timer`, `promtail`.
- `/etc/resolv.conf`, `/etc/ntp.conf`.

### 3.2. Linux — установка через PowerShell + SSH

```powershell
$srv     = 'srv-app-01'
$pserver = $client.Silver.PuppetServer
$cname   = "$srv.$($client.Slug).internal"

$bash = @"
set -euo pipefail
PUPPET_SERVER='$pserver'
CERTNAME='$cname'

CODENAME=\$(lsb_release -cs)
wget -qO /tmp/puppet8-release.deb "https://apt.puppetlabs.com/puppet8-release-\${CODENAME}.deb"
sudo dpkg -i /tmp/puppet8-release.deb
sudo apt-get update -q
sudo apt-get install -y puppet-agent

sudo tee /etc/puppetlabs/puppet/puppet.conf >/dev/null << EOF
[main]
certname = \${CERTNAME}
server   = \${PUPPET_SERVER}

[agent]
runinterval       = 1800
report            = true
splay             = true
splaylimit        = 300
usecacheonfailure = true
EOF

# Первый запуск — запрос сертификата (ОК если падает: ждёт подписи)
/opt/puppetlabs/bin/puppet agent --test --waitforcert 60 || true

echo "Подпишите на Automation VM:"
echo "  ssh msp-automation 'sudo puppetserver ca sign --certname \${CERTNAME}'"
"@
$bash | ssh root@$srv bash -s

# Подписать сертификат с Win10 одной командой:
ssh msp-automation "sudo puppetserver ca sign --certname $cname"
ssh root@$srv "/opt/puppetlabs/bin/puppet agent --test --verbose | tail -20"
```

### 3.3. Windows — установка через Invoke-Command

```powershell
$srv     = 'WIN-AD01'
$cred    = Get-Credential -UserName "$srv\Administrator"
$pserver = $client.Silver.PuppetServer
$pver    = '8.5.0'

Invoke-Command -ComputerName $srv -Credential $cred -ScriptBlock {
    param($PuppetServer, $PuppetVersion)
    $url = "https://downloads.puppetlabs.com/windows/puppet8/puppet-agent-${PuppetVersion}-x64.msi"
    $msi = "$env:TEMP\puppet-agent.msi"
    Invoke-WebRequest -Uri $url -OutFile $msi -UseBasicParsing

    $cert = $env:COMPUTERNAME.ToLower() + ".clients.internal"
    Start-Process msiexec.exe -ArgumentList @(
        '/i', $msi, '/quiet', '/norestart',
        "PUPPET_MASTER_SERVER=$PuppetServer",
        "PUPPET_AGENT_CERTNAME=$cert"
    ) -Wait

    & 'C:\Program Files\Puppet Labs\Puppet\bin\puppet.bat' agent --test --waitforcert 60 2>&1 |
        Select-Object -First 25
    Remove-Item $msi -Force
    Write-Output "Cert request submitted for $cert"
} -ArgumentList $pserver, $pver

# Подписать с Win10
$cert = "$($srv.ToLower()).clients.internal"
ssh msp-automation "sudo puppetserver ca sign --certname $cert"
```

---

## 4. AD/DNS/GPO

### 4.1. Что входит в Silver

В тариф **входит**:
- мониторинг репликации AD и статуса DC;
- стандартные операции с пользователями и группами;
- типовые GPO (парольная политика, экран блокировки, аудит);
- мониторинг DNS;
- управление WSUS/Windows Update через GPO.

В тариф **не входит** (отдельное соглашение):
- проектирование новой структуры AD/леса;
- миграции доменов/лесов;
- Exchange Hybrid / Azure AD Connect;
- более 3 нестандартных GPO в месяц.

### 4.2. Типовые GPO — выполняется на Domain Controller через WinRM

```powershell
$dc   = 'WIN-DC01'
$cred = Get-Credential -UserName 'CORP\msp-admin' -Message 'Domain Admin for GPO'

Invoke-Command -ComputerName $dc -Credential $cred -ScriptBlock {
    Import-Module ActiveDirectory, GroupPolicy

    $DomainPath = (Get-ADDomain).DistinguishedName
    $Domain     = $env:USERDOMAIN

    # ── Парольная политика ───────────────────────────────────────
    Set-ADDefaultDomainPasswordPolicy -Identity $Domain `
        -MinPasswordLength 12 `
        -MaxPasswordAge (New-TimeSpan -Days 90) `
        -MinPasswordAge (New-TimeSpan -Days 1) `
        -PasswordHistoryCount 12 `
        -ComplexityEnabled $true `
        -ReversibleEncryptionEnabled $false

    # ── Lockout ─────────────────────────────────────────────────
    Set-ADDefaultDomainPasswordPolicy -Identity $Domain `
        -LockoutDuration            (New-TimeSpan -Minutes 30) `
        -LockoutObservationWindow   (New-TimeSpan -Minutes 30) `
        -LockoutThreshold           5

    # ── GPO: Security Baseline ─────────────────────────────────
    if (-not (Get-GPO -Name 'MSP-Security-Baseline' -ErrorAction SilentlyContinue)) {
        $gpo = New-GPO -Name 'MSP-Security-Baseline'
        New-GPLink -Name 'MSP-Security-Baseline' -Target $DomainPath -Enforced Yes
    }

    # ── GPO: Screen Lock ───────────────────────────────────────
    if (-not (Get-GPO -Name 'MSP-ScreenLock' -ErrorAction SilentlyContinue)) {
        $lock = New-GPO -Name 'MSP-ScreenLock'
        Set-GPRegistryValue -Name 'MSP-ScreenLock' `
            -Key 'HKLM\SOFTWARE\Policies\Microsoft\Windows\Personalization' `
            -ValueName 'NoLockScreen' -Type DWord -Value 0
        New-GPLink -Name 'MSP-ScreenLock' -Target $DomainPath
    }
    Write-Output "GPO baseline applied for $Domain"
}
```

---

## 5. ВЕРИФИКАЦИЯ SILVER

PowerShell-обёртка, использующая `Test-MspBronzeClient` из Bronze SOP плюс Silver-проверки:

```powershell
function Test-MspSilverClient {
    param([Parameter(Mandatory)]$Client)

    Test-MspBronzeClient -Client $Client | Out-Null

    foreach ($s in $Client.Servers) {
        Write-Host "`n=== Silver checks · $($s.Host) ($($s.OS)) ===" -ForegroundColor Cyan

        if ($s.OS -eq 'linux') {
            $check = @'
echo -n "promtail active ........ "
systemctl is-active --quiet promtail && echo OK || echo FAIL

echo -n "promtail HTTP /ready ... "
curl -fsS --max-time 5 http://localhost:9080/ready | grep -q ready && echo OK || echo FAIL

echo -n "puppet agent active .... "
systemctl is-active --quiet puppet && echo OK || echo FAIL

echo -n "puppet last run <40 min: "
last=$(stat -c %Y /opt/puppetlabs/puppet/cache/state/last_run_summary.yaml 2>/dev/null || echo 0)
elapsed=$(( $(date +%s) - last ))
[ "$elapsed" -lt 2400 ] && echo "OK (${elapsed}s)" || echo "STALE (${elapsed}s)"
'@
            $check | ssh root@$($s.Host) bash -s
        }
        else {
            $cred = Get-Credential -UserName "$($s.Host)\Administrator" -Message "WinRM creds"
            Invoke-Command -ComputerName $s.Host -Credential $cred -ScriptBlock {
                @{
                    'Puppet service' = (Get-Service puppet -ErrorAction SilentlyContinue).Status
                    'Puppet last run'= (Get-Item 'C:\ProgramData\PuppetLabs\puppet\cache\state\last_run_summary.yaml' -ErrorAction SilentlyContinue).LastWriteTime
                }
            } | Format-Table -AutoSize
        }
    }
}

Test-MspSilverClient -Client $client
```

---

## 6. TROUBLESHOOTING

| Проблема                          | Диагностика (с Win10)                                             | Решение                                                                                |
|-----------------------------------|--------------------------------------------------------------------|-----------------------------------------------------------------------------------------|
| Promtail не шлёт логи             | `ssh root@srv 'journalctl -u promtail -n 50'`                      | Проверить VPN; `ssh root@srv 'curl -fsS http://10.9.0.1:3100/ready'`                   |
| `positions.yaml` застрял          | `ssh root@srv 'cat /var/lib/promtail/positions.yaml'`              | `ssh root@srv 'sudo rm /var/lib/promtail/positions.yaml; sudo systemctl restart promtail'` |
| Puppet не применяет каталог       | `ssh root@srv 'sudo puppet agent --test --verbose 2>&1 \| tail -30'` | Проверить сертификат: `ssh msp-automation 'sudo puppetserver ca list --all'`          |
| Puppet сертификат устарел         | `ssh root@srv 'sudo puppet ssl show'`                              | `ssh root@srv 'sudo puppet ssl clean'`, затем заново запросить                          |
| Puppet Agent (Windows) не работает | `Invoke-Command -ComputerName $srv ... { Get-Service puppet }`     | `Invoke-Command ... { & 'C:\Program Files\Puppet Labs\Puppet\bin\puppet.bat' agent --test }` |
| GPO не применяется                | `Invoke-Command ... { gpresult /h C:\gpr.html ; Get-Content C:\gpr.html }` | `gpupdate /force` на DC и клиенте; проверить link и Enforced флаг                 |
