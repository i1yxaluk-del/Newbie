# SOP — Silver · Сторона КЛИЕНТА
# Версия 2.0 | Апрель 2026
# ═══════════════════════════════════════════════════════════════════
#
# Silver включает ВСЁ из Bronze ПЛЮС:
#   - Promtail (сбор логов → Loki)
#   - Puppet Agent (desired state control)
#   - Управление AD/DNS/GPO через согласованный контур
#
# ═══════════════════════════════════════════════════════════════════

## СОДЕРЖАНИЕ

1. Архитектура (добавления к Bronze)
2. Promtail — установка и конфигурация
3. Puppet Agent — установка и регистрация
4. AD/DNS/GPO — управление через Ansible
5. Верификация Silver
6. Troubleshooting

---

## 1. АРХИТЕКТУРА SILVER (КЛИЕНТ)

```
СЕРВЕРЫ ЗАКАЗЧИКА                    YANDEX CLOUD (Исполнитель)
┌───────────────────────────────┐    ┌──────────────────────────────────┐
│ Linux-серверы                  │    │ Monitoring VM                    │
│ ├── node_exporter   :9100 ✓   │◀──▶│ ├── Prometheus :9090             │
│ ├── restic backup        ✓    │    │ ├── Grafana    :3000             │
│ ├── WireGuard client     ✓    │    │ ├── Alertmanager :9093           │
│ ├── promtail ───────────────→ │──→ │ └── Loki       :3100 ← NEW      │
│ └── puppet_agent ──────────→  │◀──▶│                                  │
│                               │    │ Automation VM                    │
│ Windows-серверы               │    │ ├── Puppet Server :8140 ← NEW    │
│ ├── windows_exporter  :9182 ✓ │◀──▶│ └── Ansible Control Node ← NEW  │
│ ├── restic backup         ✓   │    └──────────────────────────────────┘
│ ├── WireGuard client      ✓   │
│ └── puppet_agent          ✓   │
└───────────────────────────────┘

Потоки данных Silver:
  Логи:    Клиент → [promtail] → [Loki] → Grafana Explore
  Config:  Puppet Server → [puppet_agent] → применяет desired state
  AD/GPO:  Ansible → [WinRM] → Windows DC
```

---

## 2. PROMTAIL — СБОР ЛОГОВ (Linux)

### 2.1 Что такое Promtail и зачем

```
Promtail = агент сбора логов для Grafana Loki.
Работает на клиентском сервере, читает лог-файлы и
отправляет их в Loki Исполнителя через VPN-туннель.

После настройки в Grafana можно искать:
  {client="company1"} |= "error"          — все ошибки клиента
  {host="web-01"} |= "nginx"              — логи nginx конкретного сервера
  {job="auth"} |= "Failed password"       — брутфорс попытки
```

### 2.2 Автоматическая установка (Ansible)

```bash
# На Ansible Control Node (Automation VM):
ansible-playbook -i inventory/clients/CLIENT/hosts \
  playbooks/deploy_silver.yml \
  --tags promtail \
  -e "client_slug=CLIENT_SLUG client_name='ООО Название'" \
  -v
```

### 2.3 Ручная установка Linux

```bash
#!/bin/bash
# install_promtail.sh — устанавливает Promtail на Linux-сервер
# Запуск: sudo bash install_promtail.sh

set -euo pipefail

PROMTAIL_VERSION="${PROMTAIL_VERSION:-3.0.0}"
LOKI_URL="${LOKI_URL:-http://10.9.0.1:3100}"  # IP Bastion через VPN
CLIENT_SLUG="${CLIENT_SLUG:-unknown}"
CLIENT_NAME="${CLIENT_NAME:-Unknown Client}"
HOSTNAME_SHORT=$(hostname -s)

# ── Скачать promtail ──────────────────────────────────────────────
ARCH="linux-amd64"
URL="https://github.com/grafana/loki/releases/download/v${PROMTAIL_VERSION}/promtail-${ARCH}.zip"
TMP=$(mktemp -d)

echo "Скачиваю promtail v${PROMTAIL_VERSION}..."
curl -sSL "$URL" -o "${TMP}/promtail.zip"
unzip -q "${TMP}/promtail.zip" -d "${TMP}/"
install -m 0755 "${TMP}/promtail-${ARCH}" /usr/local/bin/promtail
rm -rf "${TMP}"

# ── Конфигурация ──────────────────────────────────────────────────
mkdir -p /etc/promtail
cat > /etc/promtail/config.yml << EOF
server:
  http_listen_port: 9080
  grpc_listen_port: 0
  log_level: warn

positions:
  filename: /var/lib/promtail/positions.yaml

clients:
  - url: ${LOKI_URL}/loki/api/v1/push
    tenant_id: ${CLIENT_SLUG}
    backoff_config:
      min_period: 500ms
      max_period: 5m
      max_retries: 10

scrape_configs:

  # ── Системные логи ─────────────────────────────────────────────
  - job_name: system
    static_configs:
      - targets: [localhost]
        labels:
          job: varlog
          host: "${HOSTNAME_SHORT}"
          client: "${CLIENT_SLUG}"
          client_name: "${CLIENT_NAME}"
    pipeline_stages:
      - multiline:
          firstline: '^\d{4}-\d{2}-\d{2}'
          max_wait_time: 3s
    static_configs:
      - targets: [localhost]
        labels:
          job: varlog
          __path__: /var/log/syslog

  # ── Логи аутентификации (SSH, sudo) ───────────────────────────
  - job_name: auth
    static_configs:
      - targets: [localhost]
        labels:
          job: auth
          host: "${HOSTNAME_SHORT}"
          client: "${CLIENT_SLUG}"
          __path__: /var/log/auth.log

  # ── Логи Nginx (если установлен) ─────────────────────────────
  - job_name: nginx
    static_configs:
      - targets: [localhost]
        labels:
          job: nginx
          host: "${HOSTNAME_SHORT}"
          client: "${CLIENT_SLUG}"
          __path__: /var/log/nginx/*.log
    pipeline_stages:
      - match:
          selector: '{job="nginx"}'
          stages:
            - regex:
                expression: '^(?P<remote_addr>\S+) - (?P<remote_user>\S+) \[(?P<time_local>[^\]]+)\] "(?P<method>\S+) (?P<request>[^"]+)" (?P<status>\d+) (?P<body_bytes_sent>\d+)'
            - labels:
                status:
                method:
            - metrics:
                nginx_requests_total:
                  type: Counter
                  description: "Total number of nginx requests"
                  source: status

  # ── Логи PostgreSQL (если установлен) ─────────────────────────
  - job_name: postgresql
    static_configs:
      - targets: [localhost]
        labels:
          job: postgresql
          host: "${HOSTNAME_SHORT}"
          client: "${CLIENT_SLUG}"
          __path__: /var/log/postgresql/*.log
EOF

# ── Создать директорию для positions ─────────────────────────────
mkdir -p /var/lib/promtail
chown nobody:nogroup /var/lib/promtail 2>/dev/null || true

# ── Systemd unit ──────────────────────────────────────────────────
cat > /etc/systemd/system/promtail.service << 'EOF'
[Unit]
Description=Promtail Log Shipper
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
ExecStart=/usr/local/bin/promtail -config.file=/etc/promtail/config.yml
Restart=on-failure
RestartSec=5s
StandardOutput=journal
StandardError=journal
SyslogIdentifier=promtail

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable --now promtail

echo "✓ Promtail установлен и запущен"
echo "  Проверка: curl -s http://localhost:9080/ready"
echo "  Логи: journalctl -u promtail -f"
```

---

## 3. PUPPET AGENT — DESIRED STATE (Linux/Windows)

### 3.1 Концепция Puppet в MSP

```
БЕЗ PUPPET:                    С PUPPET:
Сервер настроен → OK           Puppet Agent проверяет каждые 30 мин
Кто-то изменил → drift         Если изменили → вернёт к эталону
Обнаружим случайно             Автоматически фиксирует отклонения

Что контролирует Puppet:
  ✓ /etc/ssh/sshd_config      — SSH настройки (не допустить небезопасных)
  ✓ sysctl параметры          — сетевая безопасность ядра
  ✓ fail2ban конфигурация     — защита от брутфорса
  ✓ systemd services          — агенты мониторинга не должны быть отключены
  ✓ /etc/resolv.conf          — DNS настройки (Yandex DNS для РФ)
  ✓ /etc/ntp.conf             — синхронизация времени
```

### 3.2 Установка Puppet Agent (Linux)

```bash
#!/bin/bash
# install_puppet_agent.sh
# Переменные: PUPPET_SERVER, CLIENT_CERTNAME

set -euo pipefail

PUPPET_SERVER="${PUPPET_SERVER:-puppet-server.internal}"
CLIENT_CERTNAME="${CLIENT_CERTNAME:-$(hostname -f)}"

echo "Устанавливаю Puppet Agent..."
echo "Puppet Server: $PUPPET_SERVER"
echo "Certname: $CLIENT_CERTNAME"

# ── Добавить репозиторий ──────────────────────────────────────────
CODENAME=$(lsb_release -cs 2>/dev/null || echo "jammy")
wget -qO /tmp/puppet8-release.deb \
    "https://apt.puppetlabs.com/puppet8-release-${CODENAME}.deb"
dpkg -i /tmp/puppet8-release.deb
apt-get update -q
rm /tmp/puppet8-release.deb

# ── Установка ─────────────────────────────────────────────────────
apt-get install -y puppet-agent

# ── Конфигурация ──────────────────────────────────────────────────
cat > /etc/puppetlabs/puppet/puppet.conf << EOF
[main]
certname = ${CLIENT_CERTNAME}
server   = ${PUPPET_SERVER}

[agent]
runinterval    = 1800    # 30 минут
report         = true
splay          = true    # Случайная задержка (не все клиенты сразу)
splaylimit     = 300     # До 5 минут случайной задержки
usecacheonfailure = true # Применять последний известный каталог при недоступности сервера
EOF

# ── Первый запуск (запрос сертификата) ───────────────────────────
echo ""
echo "Запрашиваю сертификат у Puppet Server..."
/opt/puppetlabs/bin/puppet agent --test --waitforcert 60 || true

echo ""
echo "✓ Puppet Agent установлен"
echo ""
echo "На Puppet Server выполнить:"
echo "  puppetserver ca sign --certname ${CLIENT_CERTNAME}"
echo ""
echo "Затем проверить: puppet agent --test --verbose"
```

### 3.3 Установка Puppet Agent (Windows)

```powershell
# install_puppet_agent.ps1
param(
    [string]$PuppetServer  = "puppet-server.internal",
    [string]$PuppetVersion = "8.5.0"
)

$AgentUrl = "https://downloads.puppetlabs.com/windows/puppet8/puppet-agent-${PuppetVersion}-x64.msi"
$MsiPath  = "$env:TEMP\puppet-agent.msi"

Write-Host "Скачиваю Puppet Agent v${PuppetVersion}..."
Invoke-WebRequest -Uri $AgentUrl -OutFile $MsiPath -UseBasicParsing

$Certname = $env:COMPUTERNAME.ToLower() + ".clients.internal"

Write-Host "Устанавливаю..."
Start-Process msiexec.exe -ArgumentList @(
    "/i", $MsiPath,
    "/quiet",
    "/norestart",
    "PUPPET_MASTER_SERVER=$PuppetServer",
    "PUPPET_AGENT_CERTNAME=$Certname"
) -Wait

# Добавить в PATH
$env:Path += ";C:\Program Files\Puppet Labs\Puppet\bin"

# Запросить сертификат
Write-Host "Запрашиваю сертификат..."
& puppet agent --test --waitforcert 60 2>&1 | Select-Object -First 20

Write-Host ""
Write-Host "На Puppet Server выполнить:"
Write-Host "  puppetserver ca sign --certname $Certname"

Remove-Item $MsiPath -Force
```

---

## 4. AD/DNS/GPO — УПРАВЛЕНИЕ

### 4.1 Что входит в Silver (границы)

```
ВХОДИТ:
✓ Мониторинг репликации AD
✓ Мониторинг статуса контроллеров домена
✓ Добавление/удаление пользователей (стандарт)
✓ Управление членством в группах безопасности
✓ Типовые GPO (парольная политика, экран блокировки, аудит)
✓ Мониторинг DNS (доступность, задержки)
✓ Контроль обновлений Windows через GPO/WSUS

НЕ ВХОДИТ (требует отдельного соглашения):
✗ Проектирование новой AD-структуры
✗ Миграция доменов или лесов
✗ Exchange/Hybrid AD настройки
✗ Azure AD Connect
✗ Более 3 нестандартных GPO в месяц
```

### 4.2 Типовые GPO (шаблоны для клиентов)

```powershell
# gpо_baseline.ps1 — Создание базовых политик безопасности
# Запускать от Domain Admin

# ── 1. Парольная политика ─────────────────────────────────────────
# Применяется через Fine-Grained Password Policy (FGPP)
# или через Default Domain Policy

$DomainPath = (Get-ADDomain).DistinguishedName

# Настроить Default Domain Policy (минимальные требования)
Set-ADDefaultDomainPasswordPolicy -Identity $env:USERDOMAIN `
    -MinPasswordLength 12 `
    -MaxPasswordAge (New-TimeSpan -Days 90) `
    -MinPasswordAge (New-TimeSpan -Days 1) `
    -PasswordHistoryCount 12 `
    -ComplexityEnabled $true `
    -ReversibleEncryptionEnabled $false

# ── 2. Политика блокировки аккаунта ──────────────────────────────
Set-ADDefaultDomainPasswordPolicy -Identity $env:USERDOMAIN `
    -LockoutDuration (New-TimeSpan -Minutes 30) `
    -LockoutObservationWindow (New-TimeSpan -Minutes 30) `
    -LockoutThreshold 5

Write-Host "✓ Парольная политика настроена"

# ── 3. GPO: Аудит событий ────────────────────────────────────────
# Через Group Policy Management Console (GPMC) или PowerShell:

# Создать GPO для аудита
$gpo = New-GPO -Name "MSP-Security-Baseline"

# Настроить аудит входов (для анализа в Loki/Wazuh)
$gpoGuid = $gpo.Id.Guid
$settings = @{
    "AuditLogon"           = "Success, Failure"
    "AuditAccountLogon"    = "Success, Failure"
    "AuditObjectAccess"    = "Failure"
    "AuditPrivilegeUse"    = "Failure"
    "AuditProcessTracking" = "Failure"
    "AuditPolicyChange"    = "Success, Failure"
    "AuditAccountManagement" = "Success, Failure"
}

# Привязать GPO к домену
New-GPLink -Name "MSP-Security-Baseline" -Target $DomainPath -Enforced Yes

Write-Host "✓ GPO MSP-Security-Baseline создан и привязан"

# ── 4. GPO: Экран блокировки ─────────────────────────────────────
$LockGpo = New-GPO -Name "MSP-ScreenLock"
# Блокировка через 15 минут бездействия
Set-GPRegistryValue -Name "MSP-ScreenLock" `
    -Key "HKLM\SOFTWARE\Policies\Microsoft\Windows\Personalization" `
    -ValueName "NoLockScreen" `
    -Type DWord `
    -Value 0

New-GPLink -Name "MSP-ScreenLock" -Target $DomainPath

Write-Host "✓ GPO MSP-ScreenLock создан"
```

---

## 5. ВЕРИФИКАЦИЯ SILVER CLIENT

```bash
#!/bin/bash
echo "=== ВЕРИФИКАЦИЯ SILVER CLIENT ==="
echo "Сервер: $(hostname) | Дата: $(date)"

# ── Bronze checks ─────────────────────────────────────────────────
echo ""
echo "─── Bronze компоненты ───"
echo -n "  WireGuard VPN... "
sudo wg show wg0-msp &>/dev/null && echo "✅ OK" || echo "❌ FAIL"

echo -n "  node_exporter... "
curl -s --max-time 5 http://localhost:9100/metrics | head -1 | grep -q "^#" && echo "✅ OK" || echo "❌ FAIL"

echo -n "  Restic timer... "
systemctl is-active restic-backup.timer &>/dev/null && echo "✅ OK" || echo "❌ FAIL"

# ── Silver checks ─────────────────────────────────────────────────
echo ""
echo "─── Silver компоненты ───"
echo -n "  Promtail service... "
systemctl is-active promtail &>/dev/null && echo "✅ OK" || echo "❌ FAIL"

echo -n "  Promtail → Loki... "
curl -s --max-time 5 http://localhost:9080/ready | grep -q "ready" && echo "✅ OK" || echo "❌ FAIL"

echo -n "  Puppet Agent service... "
systemctl is-active puppet &>/dev/null && echo "✅ OK" || echo "❌ FAIL"

echo -n "  Puppet last run (< 40 мин назад)... "
LAST_RUN=$(stat -c %Y /opt/puppetlabs/puppet/cache/state/last_run_summary.yaml 2>/dev/null || echo 0)
ELAPSED=$(( $(date +%s) - LAST_RUN ))
[ "$ELAPSED" -lt 2400 ] && echo "✅ OK (${ELAPSED}с назад)" || echo "⚠️ ДАВНО (${ELAPSED}с назад)"

echo ""
echo "=== ВЕРИФИКАЦИЯ ЗАВЕРШЕНА ==="
```

---

## 6. TROUBLESHOOTING SILVER

| Проблема | Диагностика | Решение |
|---|---|---|
| Promtail не отправляет логи | `journalctl -u promtail -n 50` | Проверить VPN (доступен 10.9.0.1:3100?), `curl -s http://10.9.0.1:3100/ready` |
| Positions застрял | `cat /var/lib/promtail/positions.yaml` | Удалить positions.yaml, перезапустить promtail |
| Puppet не применяет каталог | `puppet agent --test --verbose 2>&1 \| tail -30` | Проверить сертификат: `puppet ssl verify`, возможно нужно пересоздать |
| Puppet сертификат устарел | `puppet ssl show` | `puppet ssl clean`, перезапросить у сервера |
| GPO не применяются | `gpresult /r /scope computer` | `gpupdate /force`, проверить DNS, репликацию AD |
