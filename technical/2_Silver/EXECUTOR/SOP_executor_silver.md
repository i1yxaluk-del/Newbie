# SOP — Silver · Сторона ИСПОЛНИТЕЛЯ
# Версия 2.0 | Апрель 2026
# ═══════════════════════════════════════════════════════════════════
#
# Silver добавляет к Bronze:
#   - Automation VM (отдельная или на той же машине при <8 клиентах)
#   - Loki (централизованное логирование)
#   - Puppet Server (desired state control)
#   - Ansible Control Node (автоматизация)
#   - расширенная отчётность
#
# ═══════════════════════════════════════════════════════════════════

## СОДЕРЖАНИЕ

1. Архитектура Исполнителя (Silver)
2. Automation VM — развёртывание
3. Loki — централизованные логи
4. Puppet Server — desired state
5. Ansible Control Node
6. Playbooks — deploy_bronze + deploy_silver
7. Обслуживание Silver

---

## 1. АРХИТЕКТУРА SILVER (ИСПОЛНИТЕЛЬ)

```
YANDEX CLOUD
┌──────────────────────────────────────────────────────────────────┐
│ Monitoring VM (4 vCPU 100%, 8 GB, 50 GB SSD)                    │
│ ├── Prometheus :9090                                              │
│ ├── Alertmanager :9093                                           │
│ ├── Grafana :3000 (только через VPN)                             │
│ ├── Loki :3100 ← NEW                                             │
│ ├── node-exporter                                                │
│ └── cAdvisor                                                     │
│                                                                  │
│ Automation VM (2 vCPU 100%, 4 GB, 40 GB SSD) ← NEW             │
│ ├── Puppet Server :8140                                          │
│ ├── Ansible Control Node                                         │
│ └── Git репозиторий конфигураций                                 │
│                                                                  │
│ Bastion VM (2 vCPU 5%, 2 GB, 20 GB SSD) — как в Bronze          │
│ └── WireGuard :51820                                             │
│                                                                  │
│ Object Storage (S3)                                              │
│ └── backup-CLIENT_NAME/ (restic репозитории)                    │
└──────────────────────────────────────────────────────────────────┘
```

**Стоимость Silver инфраструктуры Исполнителя:**
```
Monitoring VM (4 vCPU/8GB/50GB SSD):  ~3 800 ₽/мес
Automation VM (2 vCPU/4GB/40GB SSD):  ~1 900 ₽/мес
Bastion VM    (2 vCPU 5%/2GB/20GB):   ~600 ₽/мес
Object Storage (~200 ГБ):              ~200 ₽/мес
────────────────────────────────────────────────────
Итого:                                 ~6 500 ₽/мес
```

---

## 2. AUTOMATION VM — РАЗВЁРТЫВАНИЕ

```bash
# Создать Automation VM
yc compute instance create \
  --name msp-automation \
  --zone ru-central1-a \
  --network-interface subnet-name=default-vpc,nat-ip-version=none \
  --create-boot-disk \
    image-family=ubuntu-2204-lts,\
    size=40,\
    type=network-ssd \
  --cores 2 \
  --core-fraction 100 \
  --memory 4 \
  --ssh-key ~/.ssh/id_ed25519.pub \
  --preemptible  # Убрать для production!

# Получить внутренний IP (нет публичного — только через Bastion)
AUTO_IP=$(yc compute instance get msp-automation --format json | jq -r '.network_interfaces[0].primary_v4_address.address')
echo "Automation VM internal IP: $AUTO_IP"

# Подключиться через Bastion (через VPN)
ssh ubuntu@$AUTO_IP

# ── Базовая настройка ─────────────────────────────────────────────
sudo apt update && sudo apt upgrade -y
sudo apt install -y git curl wget python3 python3-pip ansible jq

# ── Java для Puppet Server ────────────────────────────────────────
sudo apt install -y default-jre-headless  # OpenJDK
java -version
```

---

## 3. LOKI — ЦЕНТРАЛИЗОВАННЫЕ ЛОГИ

### 3.1 Добавить Loki в docker-compose.yml (Monitoring VM)

```bash
# На Monitoring VM:
cd /opt/monitoring

# Добавить Loki конфигурацию
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
    kvstore:
      store: inmemory

query_range:
  results_cache:
    cache:
      embedded_cache:
        enabled: true
        max_size_mb: 128

schema_config:
  configs:
    - from: 2024-01-01
      store: tsdb
      object_store: filesystem
      schema: v13
      index:
        prefix: index_
        period: 24h

storage_config:
  filesystem:
    directory: /loki/storage

limits_config:
  # Хранение логов по умолчанию
  retention_period: 720h       # 30 дней
  max_query_length: 721h
  max_query_parallelism: 32
  ingestion_rate_mb: 64
  ingestion_burst_size_mb: 128
  per_stream_rate_limit: 64MB
  per_stream_rate_limit_burst: 128MB
  # Разрешить запросы старше retention
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

# Запустить с Silver профилем (включает Loki)
docker compose --profile silver up -d loki

# Проверить
sleep 5
curl -s http://localhost:3100/ready && echo "Loki OK"

# Добавить Loki datasource в Grafana (автоматически через provisioning)
cat > grafana/provisioning/datasources/loki.yml << 'EOF'
apiVersion: 1
datasources:
  - name: Loki
    type: loki
    access: proxy
    url: http://loki:3100
    isDefault: false
    editable: false
    jsonData:
      maxLines: 1000
      timeout: 60
EOF

# Перезапустить Grafana для применения datasource
docker compose restart grafana
```

### 3.2 Полезные LogQL запросы (шпаргалка)

```logql
# Все ошибки клиента за 24ч
{client="company1"} |= "error" | logfmt

# Брутфорс SSH — неудачные попытки входа
{job="auth", client="company1"} |= "Failed password" | regexp `from (?P<ip>\S+) port`

# Ошибки Nginx у конкретного клиента
{job="nginx", client="company1", status=~"5.."} | logfmt

# Объём входящих логов по клиентам
sum by (client) (rate({client=~".+"}[5m]))

# Поиск определённого IP во всех логах клиента
{client="company1"} |= "1.2.3.4"

# Ошибки PostgreSQL
{job="postgresql", client="company1"} |= "ERROR" | logfmt | line_format "{{.log}}"
```

---

## 4. PUPPET SERVER

### 4.1 Установка на Automation VM

```bash
# На Automation VM:

# ── Добавить репозиторий ──────────────────────────────────────────
CODENAME=$(lsb_release -cs)
wget -qO /tmp/puppet8-release.deb \
    "https://apt.puppetlabs.com/puppet8-release-${CODENAME}.deb"
sudo dpkg -i /tmp/puppet8-release.deb
sudo apt update -q
sudo apt install -y puppetserver

# ── Настроить JVM память ──────────────────────────────────────────
# Silver: 2GB JVM достаточно для <20 клиентов
sudo sed -i 's/JAVA_ARGS=.*/JAVA_ARGS="-Xms2g -Xmx2g"/' /etc/default/puppetserver

# ── Конфигурация Puppet Server ────────────────────────────────────
sudo tee /etc/puppetlabs/puppet/puppet.conf << EOF
[main]
certname   = puppet-server.internal
server     = puppet-server.internal
environment = production

[master]
# Алиасы (клиенты подключаются по имени puppet-server.internal)
dns_alt_names = puppet-server,puppet-server.internal,10.9.0.2

[agent]
server      = puppet-server.internal
runinterval = 1800
EOF

# ── Добавить запись в /etc/hosts для DNS-резолвинга ───────────────
echo "10.9.0.2 puppet-server.internal puppet-server" | sudo tee -a /etc/hosts

# ── Настроить UFW ─────────────────────────────────────────────────
sudo ufw allow from 10.9.0.0/24 to any port 8140 proto tcp comment "Puppet clients"

# ── Запустить ─────────────────────────────────────────────────────
sudo systemctl enable --now puppetserver
sleep 10  # Дать время на инициализацию JVM

sudo systemctl status puppetserver
curl -sk https://localhost:8140/status/v1/simple && echo "Puppet Server OK"
```

### 4.2 Модули Puppet для MSP

```bash
# Создать структуру модулей
sudo mkdir -p /etc/puppetlabs/code/environments/production/{modules,manifests,hiera}
sudo chown -R ubuntu:ubuntu /etc/puppetlabs/code/

# ── Модуль: base_linux ────────────────────────────────────────────
mkdir -p /etc/puppetlabs/code/environments/production/modules/base_linux/manifests

cat > /etc/puppetlabs/code/environments/production/modules/base_linux/manifests/init.pp << 'EOF'
# Класс base_linux — применяется ко ВСЕМ Linux-серверам
# Обеспечивает базовые настройки, которые не должны отклоняться
class base_linux (
  String  $timezone           = 'Europe/Moscow',
  Array   $ntp_servers        = ['0.ru.pool.ntp.org', '1.ru.pool.ntp.org'],
  Boolean $disable_root_ssh   = true,
  Boolean $disable_password_auth = true,
) {

  # Часовой пояс
  exec { 'set_timezone':
    command => "/bin/timedatectl set-timezone ${timezone}",
    onlyif  => "/bin/test \"$(timedatectl show --property=Timezone --value)\" != \"${timezone}\"",
  }

  # Базовые пакеты (должны быть установлены)
  package { ['chrony', 'curl', 'fail2ban', 'htop', 'jq', 'ufw']:
    ensure => present,
  }

  # Chrony (NTP) должен работать
  service { 'chrony':
    ensure  => running,
    enable  => true,
    require => Package['chrony'],
  }

  # SSH hardening — не допускать root-входа
  if $disable_root_ssh {
    file_line { 'ssh_no_root':
      path   => '/etc/ssh/sshd_config',
      line   => 'PermitRootLogin no',
      match  => '^#?PermitRootLogin',
      notify => Service['sshd'],
    }
  }

  if $disable_password_auth {
    file_line { 'ssh_no_password':
      path   => '/etc/ssh/sshd_config',
      line   => 'PasswordAuthentication no',
      match  => '^#?PasswordAuthentication',
      notify => Service['sshd'],
    }
  }

  service { 'sshd':
    ensure => running,
    enable => true,
  }

  # MOTD — информация об обслуживании
  file { '/etc/motd':
    ensure  => file,
    content => "
╔════════════════════════════════════════╗
║  Сервер под управлением MSPShield      ║
║  Все изменения конфигурации            ║
║  отслеживаются системой мониторинга.   ║
╚════════════════════════════════════════╝

",
  }
}
EOF

# ── Модуль: hardening ─────────────────────────────────────────────
mkdir -p /etc/puppetlabs/code/environments/production/modules/hardening/manifests

cat > /etc/puppetlabs/code/environments/production/modules/hardening/manifests/init.pp << 'EOF'
class hardening {

  # Sysctl: сетевая безопасность
  $sysctl_params = {
    'net.ipv4.conf.all.accept_redirects'    => 0,
    'net.ipv4.conf.all.send_redirects'      => 0,
    'net.ipv4.conf.all.rp_filter'           => 1,
    'net.ipv4.conf.all.accept_source_route' => 0,
    'net.ipv4.conf.all.log_martians'        => 1,
    'kernel.randomize_va_space'             => 2,
    'kernel.dmesg_restrict'                 => 1,
    'kernel.kptr_restrict'                  => 2,
    'fs.suid_dumpable'                      => 0,
  }

  $sysctl_params.each |String $param, Integer $value| {
    exec { "sysctl_${param}":
      command => "/sbin/sysctl -w ${param}=${value}",
      onlyif  => "/bin/bash -c 'test \"$(/sbin/sysctl -n ${param})\" != \"${value}\"'",
    }
  }

  # fail2ban должен быть запущен
  service { 'fail2ban':
    ensure  => running,
    enable  => true,
    require => Package['fail2ban'],
  }
}
EOF

# ── Модуль: monitoring_agents ─────────────────────────────────────
mkdir -p /etc/puppetlabs/code/environments/production/modules/monitoring_agents/manifests

cat > /etc/puppetlabs/code/environments/production/modules/monitoring_agents/manifests/init.pp << 'EOF'
# КЛЮЧЕВОЙ МОДУЛЬ: агенты мониторинга не должны быть отключены
class monitoring_agents {

  # node_exporter должен быть запущен
  service { 'node_exporter':
    ensure => running,
    enable => true,
  }

  # Бэкап таймер должен быть включён
  service { 'restic-backup.timer':
    ensure => running,
    enable => true,
  }

  # promtail (если Silver+)
  if lookup('tier', undef, undef, 'bronze') != 'bronze' {
    service { 'promtail':
      ensure => running,
      enable => true,
    }
  }
}
EOF

# ── site.pp — главный манифест ────────────────────────────────────
cat > /etc/puppetlabs/code/environments/production/manifests/site.pp << 'EOF'
# site.pp — точка входа Puppet
# Определяет какие классы применяются к каким узлам

# Все Linux-узлы получают базовую конфигурацию
node default {
  include base_linux
  include hardening
  include monitoring_agents
}

# Специфичные серверы (по certname или facts)
# node /^web-/ {
#   include base_linux
#   include hardening
#   include monitoring_agents
#   # Специфика для веб-серверов
# }
EOF

# Проверить синтаксис
puppet parser validate /etc/puppetlabs/code/environments/production/manifests/site.pp
puppet parser validate /etc/puppetlabs/code/environments/production/modules/base_linux/manifests/init.pp

echo "✓ Puppet конфигурация готова"
```

---

## 5. ANSIBLE CONTROL NODE

### 5.1 Структура Ansible

```bash
# На Automation VM:
mkdir -p /opt/ansible/{roles,playbooks,inventory/group_vars,files}
cd /opt/ansible

# Ansible конфигурация
cat > /opt/ansible/ansible.cfg << 'EOF'
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

# ── Коллекции для Windows ─────────────────────────────────────────
ansible-galaxy collection install ansible.windows community.general
pip3 install pywinrm requests-kerberos
```

### 5.2 Плейбук deploy_bronze.yml

```bash
cat > /opt/ansible/playbooks/deploy_bronze.yml << 'EOF'
---
# deploy_bronze.yml — Развёртывание агентов Bronze на серверы клиента
# Запуск: ansible-playbook playbooks/deploy_bronze.yml -i inventory/clients/CLIENT/hosts -v

- name: "Bronze Client Setup — Linux Servers"
  hosts: client_linux
  become: yes
  gather_facts: yes
  vars_files:
    - "{{ playbook_dir }}/../inventory/clients/{{ client_slug }}/vars.yml"

  pre_tasks:
    - name: Проверить доступность сервера
      ansible.builtin.ping:

    - name: Вывести информацию о сервере
      ansible.builtin.debug:
        msg: "{{ inventory_hostname }} | {{ ansible_distribution }} {{ ansible_distribution_version }} | {{ ansible_processor_vcpus }} vCPU | {{ (ansible_memtotal_mb / 1024) | round(1) }} GB RAM"

  tasks:
    - name: Обновить apt cache
      ansible.builtin.apt:
        update_cache: yes
        cache_valid_time: 3600

    - name: Установить базовые пакеты
      ansible.builtin.apt:
        name: [curl, wget, git, htop, jq, ufw, fail2ban]
        state: present

    - name: Установить node_exporter
      ansible.builtin.include_role:
        name: node_exporter
      tags: [node_exporter, monitoring]

    - name: Установить restic
      ansible.builtin.include_role:
        name: restic_backup
      tags: [restic, backup]

    - name: Настроить UFW
      community.general.ufw:
        rule: allow
        from_ip: "10.9.0.0/24"
        port: "{{ item }}"
        proto: tcp
      loop: [9100, 9080]
      tags: [firewall]

  post_tasks:
    - name: Верификация node_exporter
      ansible.builtin.uri:
        url: "http://localhost:9100/metrics"
        status_code: 200
      register: ne_check
      failed_when: ne_check.status != 200
      tags: [verify]

    - name: Показать результат
      ansible.builtin.debug:
        msg: "✅ {{ inventory_hostname }} — Bronze компоненты установлены"
      tags: [verify]

- name: "Bronze Client Setup — Windows Servers"
  hosts: client_windows
  gather_facts: yes
  vars_files:
    - "{{ playbook_dir }}/../inventory/clients/{{ client_slug }}/vars.yml"

  tasks:
    - name: Установить windows_exporter
      ansible.builtin.include_role:
        name: windows_exporter
      tags: [windows_exporter, monitoring]

    - name: Установить restic (Windows)
      ansible.builtin.include_role:
        name: restic_backup_windows
      tags: [restic, backup]

    - name: Верификация windows_exporter
      ansible.windows.win_uri:
        url: "http://localhost:9182/metrics"
        method: GET
        status_code: 200
      tags: [verify]
EOF
```

### 5.3 Плейбук deploy_silver.yml

```bash
cat > /opt/ansible/playbooks/deploy_silver.yml << 'EOF'
---
# deploy_silver.yml — Дополнительные компоненты Silver
# Запуск: ansible-playbook playbooks/deploy_silver.yml -i inventory/clients/CLIENT/hosts -v

- name: "Silver Client Setup — Linux"
  hosts: client_linux
  become: yes
  gather_facts: yes
  vars_files:
    - "{{ playbook_dir }}/../inventory/clients/{{ client_slug }}/vars.yml"

  pre_tasks:
    - name: Проверить что Bronze уже установлен
      ansible.builtin.uri:
        url: "http://localhost:9100/metrics"
        status_code: 200
      register: bronze_check
      failed_when: bronze_check.status != 200

  tasks:
    - name: Установить Promtail
      ansible.builtin.include_role:
        name: promtail
      tags: [promtail, logging]

    - name: Установить Puppet Agent
      ansible.builtin.include_role:
        name: puppet_agent
      tags: [puppet]

    - name: Запросить сертификат Puppet
      ansible.builtin.command:
        cmd: /opt/puppetlabs/bin/puppet agent --test --waitforcert 60
      register: puppet_cert
      failed_when: false  # Ожидаем ошибку до подписания сертификата
      changed_when: puppet_cert.rc == 0
      tags: [puppet]

    - name: Сообщить о необходимости подписать сертификат
      ansible.builtin.debug:
        msg: |
          ⚠️ Подписать сертификат Puppet на Puppet Server:
          puppetserver ca sign --certname {{ inventory_hostname }}
      when: puppet_cert.rc != 0
      tags: [puppet]

  post_tasks:
    - name: Проверить Promtail
      ansible.builtin.uri:
        url: "http://localhost:9080/ready"
        status_code: 200
      tags: [verify]

    - name: Финальный статус Silver
      ansible.builtin.debug:
        msg: "✅ {{ inventory_hostname }} — Silver компоненты установлены"
      tags: [verify]

- name: "Подписать Puppet сертификаты (на Puppet Server)"
  hosts: localhost
  gather_facts: false

  tasks:
    - name: Список ожидающих сертификатов
      ansible.builtin.command: puppetserver ca list
      register: puppet_pending
      changed_when: false
      ignore_errors: true
      tags: [puppet]

    - name: Показать ожидающие сертификаты
      ansible.builtin.debug:
        var: puppet_pending.stdout_lines
      tags: [puppet]
EOF
```

---

## 6. УПРАВЛЕНИЕ КОНФИГУРАЦИЯМИ В GIT

```bash
# Инициализировать Git-репозиторий для IaC
cd /opt/ansible
git init
git config user.email "msp@your-domain.ru"
git config user.name "MSPShield Automation"

# Создать .gitignore
cat > .gitignore << 'EOF'
# Секреты никогда не в Git!
*.key
*.pem
*-keys.json
*.secret
vault_password
inventory/clients/*/vars_secret.yml
inventory/clients/*/s3-keys.json

# Логи
*.log
*.retry

# Python
__pycache__/
*.pyc

# Временные файлы
.tmp/
EOF

# Первый коммит
git add .
git commit -m "Initial MSP Infrastructure as Code setup"

echo "✓ Git репозиторий инициализирован в /opt/ansible"
echo "Следующий шаг: добавить remote для бэкапа кода"
echo "  git remote add origin git@github.com:YOUR_USER/msp-config.git"
```

---

## 7. ОБСЛУЖИВАНИЕ SILVER

### Мониторинг Puppet Server

```bash
# Список всех зарегистрированных агентов
puppetserver ca list --all

# Подписать все ожидающие сертификаты
puppetserver ca sign --all

# Отозвать сертификат (при удалении клиента)
puppetserver ca revoke --certname client.domain

# Статус JVM
curl -sk https://localhost:8140/status/v1/services | python3 -m json.tool

# Лог Puppet Server
journalctl -u puppetserver -f
```

### Мониторинг Loki

```bash
# Статус Loki
curl -s http://localhost:3100/ready
curl -s http://localhost:3100/metrics | grep loki_ingester

# Статистика хранилища
curl -s http://localhost:3100/loki/api/v1/series \
    -G -d 'start=1h' -d 'match[]={client=~".+"}' | python3 -m json.tool

# Тестовый запрос через API
curl -s "http://localhost:3100/loki/api/v1/query_range" \
    -G -d 'query={client="company1"}' \
    -d 'start=1h' \
    -d 'limit=10'
```
