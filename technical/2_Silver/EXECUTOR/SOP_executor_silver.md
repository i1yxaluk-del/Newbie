# SOP — Silver · Сторона ИСПОЛНИТЕЛЯ
# Версия 3.0 | PowerShell-first (Windows 10 admin workstation)
# ═══════════════════════════════════════════════════════════════════
#
# Silver добавляет к Bronze:
#   - Automation VM (Puppet Server + Ansible control node)
#   - Loki (централизованное логирование)
#   - расширенная отчётность
#
# Все команды cloud-CLI и SSH-вызовы выполняются с Win10-станции
# администратора (PowerShell 5.1+). Серверная часть остаётся Linux.
#
# Перед чтением убедитесь что прошли `SOP_executor_bronze.md` —
# здесь используются те же переменные окружения ($Env:MSP_*),
# вспомогательные функции (`msp-bash`, `Add-MspClient`,
# `New-MspBackupBucket`), репозиторий `~/.msp-secrets/`.
# ═══════════════════════════════════════════════════════════════════

## СОДЕРЖАНИЕ

0. Что добавляет Silver к Bronze
1. Архитектура Silver
2. Automation VM — развёртывание из PowerShell
3. Loki — централизованные логи
4. Puppet Server (на Automation VM)
5. Ansible Control Node
6. Управление конфигурациями в Git
7. Обслуживание Silver

---

## 0. ЧТО ДОБАВЛЯЕТ SILVER

| Компонент          | Где                          | Зачем                                        |
|--------------------|------------------------------|-----------------------------------------------|
| Loki + Promtail    | Monitoring VM (контейнер)    | Централизованные логи всех клиентов          |
| Puppet Server      | Automation VM (новая)        | Desired state — гарантирует базовый конфиг   |
| Ansible Control    | Automation VM (тот же хост)  | Идемпотентные плейбуки для deploy/rollback   |
| Git (IaC)          | Automation VM                | Версионирование всех конфигов                |
| Расширенный отчёт  | Monitoring VM (тот же cron)  | Включает Loki, Puppet drift, Ansible runs    |

Все сервисы внутри VPN `10.9.0.0/24`. Внешние порты не открываем.

---

## 1. АРХИТЕКТУРА SILVER

```
WINDOWS 10 АДМИН-СТАНЦИЯ                    YANDEX CLOUD
┌─────────────────────────┐                 ┌──────────────────────────────────────────────────────────────────┐
│  PowerShell             │  yc CLI / SSH   │ Monitoring VM (4 vCPU 100%, 8 GB, 50 GB SSD)                    │
│   yc CLI                │ ───────────────▶│ ├── Prometheus :9090                                              │
│   OpenSSH client        │                 │ ├── Alertmanager :9093                                           │
│   Invoke-Command        │                 │ ├── Grafana :3000 (только через VPN)                             │
└─────────────────────────┘                 │ ├── Loki :3100  ← NEW                                            │
                                            │ ├── node-exporter / cAdvisor                                     │
                                            │                                                                  │
                                            │ Automation VM (2 vCPU 100%, 4 GB, 40 GB SSD)  ← NEW             │
                                            │ ├── Puppet Server :8140                                          │
                                            │ ├── Ansible Control Node                                         │
                                            │ └── Git репозиторий /opt/ansible                                 │
                                            │                                                                  │
                                            │ Bastion VM (2 vCPU 50%, 2 GB, 20 GB SSD) — как в Bronze         │
                                            │ └── WireGuard :51820                                             │
                                            │                                                                  │
                                            │ Object Storage (S3)                                              │
                                            │ └── backup-CLIENT_NAME/  (restic репозитории)                    │
                                            └──────────────────────────────────────────────────────────────────┘
```

**Стоимость Silver-инфраструктуры:**
```
Monitoring VM (4 vCPU/8GB/50GB SSD):    ~3 800 ₽/мес
Automation VM (2 vCPU/4GB/40GB SSD):    ~1 900 ₽/мес
Bastion VM    (2 vCPU 50%/2GB/20GB):      ~750 ₽/мес   # урок L5: core-fraction <50% недоступен для 2 vCPU
Object Storage (~200 ГБ):                  ~200 ₽/мес
─────────────────────────────────────────────────────
Итого:                                    ~6 650 ₽/мес
```

---

## 2. AUTOMATION VM — РАЗВЁРТЫВАНИЕ ИЗ POWERSHELL

### 2.1. Создать VM

> **Урок L7 (PS 5.1 + yc):** все вызовы `yc` ниже идут через helper
> `Invoke-Yc` (определён в Bronze SOP §0.3). Он оборачивает вызов в
> `cmd /c "yc ... 2>&1"`, сливая stderr в stdout — иначе PS 5.1 ломается
> даже на успешных командах. Скопируйте `Invoke-Yc` в свой `$PROFILE`.

```powershell
$Env:MSP_AUTO_NAME = 'msp-automation'

Invoke-Yc compute instance create `
    --name $Env:MSP_AUTO_NAME `
    --folder-id $Env:MSP_FOLDER_ID `
    --zone $Env:MSP_ZONE `
    --network-interface "subnet-name=default,nat-ip-version=none" `
    --create-boot-disk "image-family=ubuntu-2204-lts,size=40GB,type=network-ssd" `
    --cores 2 `
    --core-fraction 100 `
    --memory 4GB `
    --ssh-key "$Env:MSP_SSH_KEY.pub"
# Для теста добавьте --preemptible. Для production Silver не использовать
# (Silver подразумевает SLA + HA, preemptible режется YC раз в 24ч).
# ⚠️ УРОК L5: если VM preemptible — обязательно резервируйте static IP
# (+190₽/мес). Без static IP IP меняется при рестарте → DNS устаревает.
# core-fraction <50% недоступен для 2 vCPU (API вернёт ошибку).
# См. Bronze SOP §2.2 и deploy/yandex/README.md §10.0.3.

$vmJson = (Invoke-Yc compute instance get $Env:MSP_AUTO_NAME --format json) -join "`n"
$vm = $vmJson | ConvertFrom-Json
$Env:MSP_AUTO_IP = $vm.network_interfaces[0].primary_v4_address.address
Write-Host "Automation VM internal IP: $Env:MSP_AUTO_IP"
```

> Automation VM не имеет публичного IP. Доступ — через Bastion (Monitoring VM) по VPN.

### 2.2. Подключение через Bastion (`ProxyJump`)

Добавьте в `$env:USERPROFILE\.ssh\config`:
```text
Host msp-bastion
  HostName    <MSP_VM_IP>
  User        ubuntu
  IdentityFile ~/.ssh/id_ed25519_yc
  # ⚠️ УРОК ИЗ ДЕПЛОЯ: preemptible VM меняет host keys при рестарте
  StrictHostKeyChecking no
  UserKnownHostsFile NUL

Host msp-automation
  HostName    <MSP_AUTO_IP>
  User        ubuntu
  IdentityFile ~/.ssh/id_ed25519_yc
  ProxyJump   msp-bastion
```

Затем:
```powershell
ssh msp-automation
```

### 2.3. Базовая настройка VM (через ProxyJump)

```powershell
$bash = @'
set -euo pipefail
sudo apt update && sudo apt upgrade -y
sudo apt install -y git curl wget python3 python3-pip ansible jq

# Java для Puppet Server
sudo apt install -y default-jre-headless
java -version
'@
$bash | ssh msp-automation bash -s
```

Helper для повторного запуска bash на Automation VM:
```powershell
function msp-auto-bash {
    param([Parameter(Mandatory)][string]$Script)
    $Script | ssh msp-automation bash -s
}
```

---

## 3. LOKI — ЦЕНТРАЛИЗОВАННЫЕ ЛОГИ (на Monitoring VM)

### 3.1. Развернуть Loki через docker compose

```powershell
$bash = @'
set -euo pipefail
cd /opt/monitoring
mkdir -p loki

cat > loki/loki-config.yml << 'EOF'
auth_enabled: false

server:
  http_listen_port: 3100
  grpc_listen_port: 9096
  log_level: warn

common:
  instance_addr: 127.0.0.1
  path_prefix: /loki
  storage:
    filesystem:
      chunks_directory: /loki/chunks
      rules_directory:  /loki/rules
  replication_factor: 1
  ring:
    kvstore: { store: inmemory }

query_range:
  results_cache:
    cache:
      embedded_cache: { enabled: true, max_size_mb: 128 }

schema_config:
  configs:
    - from: 2024-01-01
      store: tsdb
      object_store: filesystem
      schema: v13
      index: { prefix: index_, period: 24h }

storage_config:
  filesystem: { directory: /loki/storage }

limits_config:
  retention_period: 720h
  max_query_length:  721h
  max_query_parallelism: 32
  ingestion_rate_mb: 64
  ingestion_burst_size_mb: 128
  per_stream_rate_limit: 64MB
  per_stream_rate_limit_burst: 128MB
  allow_structured_metadata: true

compactor:
  working_directory: /loki/compactor
  compaction_interval: 10m
  retention_enabled: true
  retention_delete_delay: 2h
  retention_delete_worker_count: 150

ruler:
  alertmanager_url: http://alertmanager:9093
EOF

docker compose --profile silver up -d loki
sleep 5
curl -fsS http://localhost:3100/ready && echo "Loki OK"

# Datasource Grafana
cat > grafana/provisioning/datasources/loki.yml << 'EOF'
apiVersion: 1
datasources:
  - name: Loki
    type: loki
    access: proxy
    url:  http://loki:3100
    isDefault: false
    editable: false
    jsonData:
      maxLines: 1000
      timeout: 60
EOF
docker compose restart grafana
'@
$bash | ssh -i $Env:MSP_SSH_KEY ubuntu@$Env:MSP_VM_IP bash -s
```

### 3.2. Шпаргалка LogQL

```logql
# Все ошибки клиента за 24ч
{client="company1"} |= "error" | logfmt

# Брутфорс SSH
{job="auth", client="company1"} |= "Failed password" | regexp `from (?P<ip>\S+) port`

# Nginx 5xx у клиента
{job="nginx", client="company1", status=~"5.."} | logfmt

# Объём входящих логов по клиентам
sum by (client) (rate({client=~".+"}[5m]))

# PostgreSQL ошибки
{job="postgresql", client="company1"} |= "ERROR" | logfmt
```

---

## 4. PUPPET SERVER

Все блоки `bash` выполняются на Automation VM через `msp-auto-bash`.

### 4.1. Установка пакетов

```powershell
msp-auto-bash @'
set -euo pipefail
CODENAME=$(lsb_release -cs)
wget -qO /tmp/puppet8-release.deb "https://apt.puppetlabs.com/puppet8-release-${CODENAME}.deb"
sudo dpkg -i /tmp/puppet8-release.deb
sudo apt update -q
sudo apt install -y puppetserver

# JVM 2GB для Silver (<20 клиентов)
sudo sed -i 's/JAVA_ARGS=.*/JAVA_ARGS="-Xms2g -Xmx2g"/' /etc/default/puppetserver

sudo tee /etc/puppetlabs/puppet/puppet.conf >/dev/null << EOF
[main]
certname    = puppet-server.internal
server      = puppet-server.internal
environment = production

[master]
dns_alt_names = puppet-server,puppet-server.internal,10.9.0.2

[agent]
server      = puppet-server.internal
runinterval = 1800
EOF

echo "10.9.0.2 puppet-server.internal puppet-server" | sudo tee -a /etc/hosts
sudo ufw allow from 10.9.0.0/24 to any port 8140 proto tcp comment "Puppet clients" || true

sudo systemctl enable --now puppetserver
sleep 10
sudo systemctl --no-pager status puppetserver | head -10
curl -sk https://localhost:8140/status/v1/simple && echo "Puppet Server OK"
'@
```

### 4.2. Структура Puppet-модулей

```powershell
msp-auto-bash @'
set -euo pipefail
sudo mkdir -p /etc/puppetlabs/code/environments/production/{modules,manifests,hiera}
sudo chown -R ubuntu:ubuntu /etc/puppetlabs/code/

mkdir -p /etc/puppetlabs/code/environments/production/modules/base_linux/manifests
mkdir -p /etc/puppetlabs/code/environments/production/modules/hardening/manifests
mkdir -p /etc/puppetlabs/code/environments/production/modules/monitoring_agents/manifests
'@
```

### 4.3. Модули `base_linux`, `hardening`, `monitoring_agents`

> Полные манифесты лежат в репозитории
> `i1yxaluk-del/Newbie:technical/2_Silver/EXECUTOR/puppet-modules/`. Залейте их
> на Automation VM через `scp`:

```powershell
cd $env:USERPROFILE\Newbie\technical\2_Silver\EXECUTOR
scp -r .\puppet-modules\* ubuntu@msp-automation:/etc/puppetlabs/code/environments/production/modules/
```

Краткое описание:

- **`base_linux`** — taimezone Europe/Moscow, chrony, ufw, fail2ban,
  отключение root-SSH/password auth, MOTD «под управлением MSP».
- **`hardening`** — sysctl (rp_filter, kptr_restrict и т.д.), fail2ban.
- **`monitoring_agents`** — гарантирует, что `node_exporter`,
  `restic-backup.timer` и `promtail` (Silver+) запущены.

### 4.4. `site.pp`

```powershell
msp-auto-bash @'
cat > /etc/puppetlabs/code/environments/production/manifests/site.pp << 'EOF'
# site.pp — точка входа Puppet
node default {
  include base_linux
  include hardening
  include monitoring_agents
}
EOF

puppet parser validate /etc/puppetlabs/code/environments/production/manifests/site.pp
puppet parser validate /etc/puppetlabs/code/environments/production/modules/base_linux/manifests/init.pp
echo "Puppet OK"
'@
```

---

## 5. ANSIBLE CONTROL NODE

### 5.1. Структура каталога

```powershell
msp-auto-bash @'
set -euo pipefail
mkdir -p /opt/ansible/{roles,playbooks,inventory/group_vars,files}
cd /opt/ansible

cat > ansible.cfg << 'EOF'
[defaults]
inventory       = ./inventory
roles_path      = ./roles
retry_files_enabled = false
forks           = 10
timeout         = 30
host_key_checking = false
stdout_callback = yaml
stderr_callback = yaml
log_path        = /var/log/ansible.log

[ssh_connection]
pipelining      = true
control_path    = /tmp/ansible-ssh-%%h-%%p-%%r
EOF

# Коллекции для Windows-таргетов
ansible-galaxy collection install ansible.windows community.general
pip3 install pywinrm requests-kerberos
'@
```

### 5.2. Плейбук `deploy_bronze.yml` и `deploy_silver.yml`

> Файлы лежат в репо
> `technical/2_Silver/EXECUTOR/ansible-playbooks/`. Залейте scp-ом:

```powershell
cd $env:USERPROFILE\Newbie\technical\2_Silver\EXECUTOR
scp -r .\ansible-playbooks\* ubuntu@msp-automation:/opt/ansible/playbooks/
```

### 5.3. Запуск плейбуков из PowerShell

```powershell
function Invoke-MspAnsiblePlaybook {
    param(
        [Parameter(Mandatory)][string]$ClientSlug,
        [ValidateSet('deploy_bronze','deploy_silver')][string]$Playbook,
        [string]$Tags
    )
    $tagArg = if ($Tags) { "--tags $Tags" } else { '' }
    ssh msp-automation `
        "cd /opt/ansible && ansible-playbook playbooks/$Playbook.yml " +
        "-i inventory/clients/$ClientSlug/hosts " +
        "-e client_slug=$ClientSlug $tagArg -v"
}

# Примеры:
Invoke-MspAnsiblePlaybook -ClientSlug company1 -Playbook deploy_bronze
Invoke-MspAnsiblePlaybook -ClientSlug company1 -Playbook deploy_silver -Tags promtail,puppet
```

---

## 6. УПРАВЛЕНИЕ КОНФИГУРАЦИЯМИ В GIT

```powershell
msp-auto-bash @'
set -euo pipefail
cd /opt/ansible
git init
git config user.email "msp@your-domain.ru"
git config user.name  "MSPShield Automation"

cat > .gitignore << 'EOF'
# Секреты никогда не в Git
*.key
*.pem
*-keys.json
*.secret
vault_password
inventory/clients/*/vars_secret.yml
inventory/clients/*/s3-keys.json

# Логи и временные файлы
*.log
*.retry
__pycache__/
*.pyc
.tmp/
EOF

git add .
git commit -m "Initial MSP IaC setup"
echo "Git repo initialized in /opt/ansible"
'@
```

Bootstrap remote (с Windows-станции, через GitHub PAT или deploy-key):

```powershell
$repo = 'git@github.com:i1yxaluk-del/msp-iac.git'
ssh msp-automation @"
cd /opt/ansible
git remote add origin $repo || git remote set-url origin $repo
git push -u origin main
"@
```

---

## 7. ОБСЛУЖИВАНИЕ SILVER

### 7.1. Puppet Server

```powershell
# Список зарегистрированных агентов и pending-сертификатов
ssh msp-automation 'sudo puppetserver ca list --all'

# Подписать все pending
ssh msp-automation 'sudo puppetserver ca sign --all'

# Отозвать сертификат (при удалении клиента)
ssh msp-automation 'sudo puppetserver ca revoke --certname client.domain'

# Лог Puppet Server
ssh msp-automation 'sudo journalctl -u puppetserver -f --no-pager'
```

### 7.2. Loki

```powershell
$ip = $Env:MSP_VM_IP
ssh -i $Env:MSP_SSH_KEY ubuntu@$ip 'curl -s http://localhost:3100/ready'
ssh -i $Env:MSP_SSH_KEY ubuntu@$ip 'curl -s http://localhost:3100/metrics | grep loki_ingester | head'

# Тестовый LogQL запрос
$query = '{client="company1"} |= "error"'
$encoded = [uri]::EscapeDataString($query)
$now = [int][double]::Parse((Get-Date -UFormat %s))
$start = $now - 3600
ssh -i $Env:MSP_SSH_KEY ubuntu@$ip "curl -s 'http://localhost:3100/loki/api/v1/query_range?query=$encoded&start=$start&end=$now' | python3 -m json.tool | head -40"
```

### 7.3. Ansible

```powershell
# Health-check всех клиентов
ssh msp-automation 'cd /opt/ansible && ansible all -m ping -i inventory/clients/company1/hosts'

# Сухой запуск playbook (check mode)
ssh msp-automation `
    'cd /opt/ansible && ansible-playbook playbooks/deploy_silver.yml -i inventory/clients/company1/hosts --check --diff -v'
```

### 7.4. Снапшоты обеих VM

```powershell
# Урок L7: yc через Invoke-Yc (см. Bronze SOP §0.3)
foreach ($name in @($Env:MSP_VM_NAME, $Env:MSP_AUTO_NAME)) {
    $instJson = (Invoke-Yc compute instance get $name --folder-id $Env:MSP_FOLDER_ID --format json) -join "`n"
    $diskId = ($instJson | ConvertFrom-Json).boot_disk.disk_id
    Invoke-Yc compute snapshot create `
        --name "$name-$(Get-Date -Format yyyyMMdd-HHmm)" `
        --source-disk-id $diskId `
        --folder-id $Env:MSP_FOLDER_ID `
        --async
}
```
