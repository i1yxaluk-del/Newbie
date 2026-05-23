# SOP — Gold · Сторона ИСПОЛНИТЕЛЯ
# Версия 3.0 | PowerShell-first (Windows 10 admin workstation)
# ═══════════════════════════════════════════════════════════════════
#
# Gold Исполнитель = Silver + Wazuh VM + KSC + osTicket.
#
# Все cloud-операции и оркестрация выполняются с Win10-станции
# (PowerShell 5.1+). Серверная часть остаётся Ubuntu 22.04 LTS.
# Предполагается, что Bronze + Silver уже развёрнуты и доступны
# `$Env:MSP_*`-переменные, `msp-bastion`/`msp-automation` SSH-конфиги.
# ═══════════════════════════════════════════════════════════════════

## СОДЕРЖАНИЕ

1. Архитектура Gold (Исполнитель)
2. Wazuh VM — создание из PowerShell
3. Wazuh Docker Compose — развёртывание
4. Wazuh Manager — конфигурация + Telegram / MAX
5. KSC — Kaspersky Security Center
6. osTicket — тикет-система
7. Gold alert rules
8. Верификация Gold Executor
9. Troubleshooting

---

## 1. АРХИТЕКТУРА GOLD (ИСПОЛНИТЕЛЬ)

```
WINDOWS 10 АДМИН-СТАНЦИЯ                YANDEX CLOUD
┌────────────────────┐                  ┌──────────────────────────────────────────────────────────────────┐
│ PowerShell         │  yc CLI / SSH    │ Monitoring VM (4 vCPU, 8 GB) — Silver                            │
│  yc CLI            │ ────────────────▶│ ├── Prometheus / Alertmanager / Grafana / Loki                   │
│  OpenSSH client    │                  │                                                                  │
│  Invoke-Command    │                  │ Automation VM (2 vCPU, 4 GB) — Silver                            │
└────────────────────┘                  │ ├── Puppet Server / Ansible Control / Git                        │
                                        │                                                                  │
                                        │ Bastion VM — Bronze                                              │
                                        │ └── WireGuard :51820                                             │
                                        │                                                                  │
                                        │ Wazuh VM (8 vCPU, 16 GB, 100 GB SSD)   ← NEW (Gold)             │
                                        │ ├── Wazuh Manager :1514/1515                                     │
                                        │ ├── Wazuh Indexer (OpenSearch) :9200                             │
                                        │ ├── Wazuh Dashboard :443 (только VPN)                            │
                                        │ ├── osTicket :8080 (только VPN, на Bastion)                      │
                                        │ └── KSC metrics exporter :9101                                   │
                                        │                                                                  │
                                        │ Object Storage (S3) — backup-CLIENT/...                          │
                                        └──────────────────────────────────────────────────────────────────┘
```

**Стоимость Gold-инфраструктуры:**
```
Monitoring VM:    ~3 800 ₽/мес
Automation VM:    ~1 900 ₽/мес
Bastion VM:         ~750 ₽/мес   # урок L5: 2 vCPU × 50% (минимум)
Wazuh VM:         ~8 500 ₽/мес
Object Storage:     ~300 ₽/мес
─────────────────────────────────────
Итого:           ~14 950 ₽/мес (окупается при 15+ клиентах)
```

---

## 2. WAZUH VM — СОЗДАНИЕ ИЗ POWERSHELL

### 2.1. Требования

```
ЖЁСТКИЕ требования:
  CPU:  8 vCPU 100% (для >20 агентов)
  RAM:  16 GB
  Disk: 100 GB network-ssd
  OS:   Ubuntu 22.04 LTS
  Net:  без публичного IP (всё через Bastion + VPN)

КРИТИЧНО для OpenSearch (Wazuh Indexer):
  vm.max_map_count = 262144   ← иначе Indexer не запустится
  fs.file-max      = 65536
```

### 2.2. Создать VM

> **Урок L7 (PS 5.1 + yc):** `yc` вызывается через helper `Invoke-Yc`
> (определён в Bronze SOP §0.3) — PS 5.1 превращает stderr в ErrorRecord
> и ломает скрипт даже на успешных командах. Скопируйте `Invoke-Yc`
> в свой `$PROFILE`.

```powershell
$Env:MSP_WAZUH_NAME = 'msp-wazuh'

Invoke-Yc compute instance create `
    --name $Env:MSP_WAZUH_NAME `
    --folder-id $Env:MSP_FOLDER_ID `
    --zone $Env:MSP_ZONE `
    --network-interface "subnet-name=default,nat-ip-version=none" `
    --create-boot-disk "image-family=ubuntu-2204-lts,size=100GB,type=network-ssd" `
    --cores 8 --core-fraction 100 --memory 16GB `
    --ssh-key "$Env:MSP_SSH_KEY.pub"

$vmJson = (Invoke-Yc compute instance get $Env:MSP_WAZUH_NAME --format json) -join "`n"
$vm = $vmJson | ConvertFrom-Json
$Env:MSP_WAZUH_IP = $vm.network_interfaces[0].primary_v4_address.address
Write-Host "Wazuh VM internal IP: $Env:MSP_WAZUH_IP"
```

Добавить в `~/.ssh/config`:
```text
Host msp-wazuh
  HostName     <MSP_WAZUH_IP>
  User         ubuntu
  IdentityFile ~/.ssh/id_ed25519_yc
  ProxyJump    msp-bastion
```

### 2.3. Подключить VM к VPN (10.9.0.3)

```powershell
# На Wazuh VM пробросить туннель wg0-msp (тот же скрипт что для
# клиентских серверов из Bronze §3.1) — VPN_IP = 10.9.0.3.
$bash = @'
set -euo pipefail
sudo apt update && sudo apt install -y wireguard wireguard-tools
cd /etc/wireguard
sudo wg genkey | sudo tee client_private.key | sudo wg pubkey | sudo tee client_public.key >/dev/null
sudo chmod 600 client_private.key
echo "WAZUH_PUBKEY=$(sudo cat /etc/wireguard/client_public.key)"
'@
$out = $bash | ssh msp-wazuh bash -s
$wazuhPub = ($out | Select-String '^WAZUH_PUBKEY=(.+)').Matches.Groups[1].Value

# Добавить peer на Bastion (Add-MspVpnPeer определён в Bronze SOP §4.3)
Add-MspVpnPeer -ClientSlug 'internal-wazuh' -VpnIp '10.9.0.3' -ClientPubKey $wazuhPub

# Записать клиентский wg0-msp.conf
$bash2 = @"
set -euo pipefail
sudo tee /etc/wireguard/wg0-msp.conf >/dev/null << EOF
[Interface]
PrivateKey = \$(sudo cat /etc/wireguard/client_private.key)
Address    = 10.9.0.3/32
[Peer]
PublicKey           = $($Env:MSP_BASTION_PUBKEY)
Endpoint            = $($Env:MSP_VM_IP):51820
AllowedIPs          = 10.9.0.0/24
PersistentKeepalive = 25
EOF
sudo chmod 600 /etc/wireguard/wg0-msp.conf
sudo systemctl enable --now wg-quick@wg0-msp
ping -c 2 10.9.0.1
"@
$bash2 | ssh msp-wazuh bash -s
```

### 2.4. Параметры ядра + Docker

```powershell
$bash = @'
set -euo pipefail

# КРИТИЧНО для OpenSearch
echo "vm.max_map_count=262144" | sudo tee /etc/sysctl.d/99-wazuh.conf
echo "fs.file-max=65536"        | sudo tee -a /etc/sysctl.d/99-wazuh.conf
sudo sysctl --system
sysctl vm.max_map_count

sudo apt update
sudo apt install -y docker.io docker-compose-plugin curl git jq htop

# ⚠️ УРОК ИЗ ДЕПЛОЯ: Docker 29+ на Ubuntu 22.04 по умолчанию использует
# overlayfs driver (containerd snapshotter). cAdvisor и другие инструменты
# не могут читать layerdb/mounts/. Фикс: daemon.json с overlay2.
# См. Bronze SOP §3 и deploy/yandex/README.md §10.0.1.
sudo mkdir -p /etc/docker
echo '{"storage-driver": "overlay2"}' | sudo tee /etc/docker/daemon.json
sudo systemctl restart docker

sudo usermod -aG docker ubuntu
docker --version
docker info --format '{{.Driver}}'   # должно быть overlay2
'@
$bash | ssh msp-wazuh bash -s
```

---

## 3. WAZUH DOCKER COMPOSE

### 3.1. Залить compose / .env с Win10

> compose-файл лежит в репо: `technical/3_Gold/EXECUTOR/wazuh/docker-compose.yml`.

```powershell
ssh msp-wazuh 'sudo mkdir -p /opt/wazuh && sudo chown -R ubuntu:ubuntu /opt/wazuh'

cd $env:USERPROFILE\Newbie\technical\3_Gold\EXECUTOR\wazuh
scp .\docker-compose.yml .\wazuh_manager_ossec.conf ubuntu@msp-wazuh:/opt/wazuh/

# .env с паролями — генерируем на Windows и заливаем
function New-RandomBase64 { -join ((1..32) | ForEach-Object { '{0:x}' -f (Get-Random -Maximum 16) }) }

$envFile = @"
WAZUH_INDEXER_PASSWORD=$(New-RandomBase64)
WAZUH_API_PASSWORD=$(New-RandomBase64)
WAZUH_DASHBOARD_PASSWORD=$(New-RandomBase64)
"@
$tmp = New-TemporaryFile
Set-Content $tmp.FullName $envFile -Encoding ASCII
scp $tmp.FullName ubuntu@msp-wazuh:/opt/wazuh/.env
Remove-Item $tmp.FullName

ssh msp-wazuh 'chmod 600 /opt/wazuh/.env'
```

> Сохраните `.env` отдельно в `$env:USERPROFILE\.msp-secrets\wazuh.env` — пароли потребуются для Dashboard.

### 3.2. Запуск

```powershell
ssh msp-wazuh @'
set -euo pipefail
cd /opt/wazuh
docker compose up -d
echo "Wait for Indexer init (~3 min)..."
sleep 180
docker compose ps
'@

# Sanity check
$pwd = (Select-String -Path "$env:USERPROFILE\.msp-secrets\wazuh.env" `
        -Pattern '^WAZUH_INDEXER_PASSWORD=(.*)').Matches.Groups[1].Value
ssh msp-wazuh "curl -sk https://localhost:9200 -u admin:$pwd | head -10"

Write-Host "Wazuh Dashboard:  https://10.9.0.3:443"
Write-Host "  Login: admin / <WAZUH_INDEXER_PASSWORD>"
```

---

## 4. WAZUH MANAGER — КОНФИГУРАЦИЯ + TELEGRAM / MAX

### 4.1. ossec.conf — главный конфиг

```powershell
# Скопировать с Win10-станции, затем загрузить в контейнер
scp .\wazuh_manager_ossec.conf ubuntu@msp-wazuh:/opt/wazuh/wazuh_manager_ossec.conf
ssh msp-wazuh @'
docker cp /opt/wazuh/wazuh_manager_ossec.conf wazuh-manager:/var/ossec/etc/ossec.conf
docker restart wazuh-manager
'@
```

### 4.2. Интеграция Wazuh → Telegram / MAX

Два варианта (можно комбинировать):

- **Путь A — прямо из Wazuh** через `custom-telegram.py` (legacy, дублирует код только под Telegram).
- **Путь B — рекомендованный**: Wazuh → Alertmanager → backend `/api/alerts/alertmanager` → MAX + Telegram. Каналы управляются через `ALERT_CHANNELS=max,telegram` в `backend/.env`. См. [`docs/MAX_SETUP.md` §10](../../../docs/MAX_SETUP.md) и [`deploy/alertmanager/alertmanager.yml`](../../../deploy/alertmanager/alertmanager.yml).

#### Путь A — Telegram integration script

> Файл `custom-telegram.py` лежит в репо: `technical/3_Gold/EXECUTOR/wazuh/custom-telegram.py`.

```powershell
scp .\custom-telegram.py ubuntu@msp-wazuh:/opt/wazuh/custom-telegram.py
ssh msp-wazuh @'
docker cp /opt/wazuh/custom-telegram.py wazuh-manager:/var/ossec/integrations/custom-telegram
docker exec wazuh-manager chmod 750 /var/ossec/integrations/custom-telegram
docker exec wazuh-manager chown root:wazuh /var/ossec/integrations/custom-telegram
'@
```

Токены `TELEGRAM_BOT_TOKEN` / `TELEGRAM_CHAT_ID` пробрасываются через
`docker-compose.yml` секцию `environment` контейнера `wazuh.manager`.

#### Путь B — Alertmanager → MAX

1. В `wazuh_manager_ossec.conf` остаётся только integration на Alertmanager (`custom-am-webhook` или native), без `custom-telegram`.
2. В `alertmanager.yml` — receiver `webhook_configs` → `https://msp-claude.online/api/alerts/alertmanager` с Bearer-токеном `ALERTMANAGER_WEBHOOK_TOKEN`.
3. В `backend/.env`:
   ```env
   MAX_BOT_TOKEN=...
   MAX_ALERT_CHAT_ID=...
   ALERT_CHANNELS=max,telegram
   ```
4. Smoke-test с Win10:
   ```powershell
   ssh msp-bastion 'docker exec msp-alertmanager amtool alert add alertname=WazuhTest severity=critical'
   # → в MAX и Telegram прилетает: 🔴 P1 · WazuhTest · agent01
   ```

---

## 5. KSC — KASPERSKY SECURITY CENTER

### 5.1. Варианты развёртывания

- **A. KSC Cloud Console (SaaS от Kaspersky)** — быстрее всего, требует только лицензию.
- **B. Локальный KSC Server** — отдельная Windows VM в Yandex Cloud (требует Windows Server лицензию + AD).

Подробный гайд: `technical/3_Gold/EXECUTOR/ksc/ksc_setup_guide.md`.

### 5.2. KSC Metrics Exporter

Python-скрипт `ksc_exporter.py` тянет метрики из KSC REST API и
выставляет их на `:9101/metrics` как Prometheus exporter.

```powershell
# Залить exporter на Automation VM
scp ..\ksc\ksc_exporter.py ..\ksc\ksc-exporter.service `
    ubuntu@msp-automation:/tmp/

ssh msp-automation @'
sudo install -m 0755 /tmp/ksc_exporter.py /usr/local/bin/ksc_exporter.py
sudo install -m 0644 /tmp/ksc-exporter.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now ksc-exporter
curl -fsS http://localhost:9101/metrics | head -20
'@
```

В Prometheus (Monitoring VM) добавить job:
```yaml
- job_name: ksc
  static_configs:
    - targets: ['10.9.0.2:9101']
```

---

## 6. OSTICKET — ТИКЕТ-СИСТЕМА

> osTicket разворачиваем на Bastion (Monitoring) — не плодим лишних VM.

> compose-файл: `technical/3_Gold/EXECUTOR/osticket/docker-compose.yml`.

```powershell
ssh msp-bastion 'sudo mkdir -p /opt/osticket && sudo chown -R ubuntu:ubuntu /opt/osticket'

scp ..\osticket\docker-compose.yml ubuntu@msp-bastion:/opt/osticket/

$envContent = @"
DB_ROOT_PASS=$(New-RandomBase64)
DB_PASS=$(New-RandomBase64)
ADMIN_EMAIL=admin@$Env:MSP_DOMAIN
"@
$tmp = New-TemporaryFile
Set-Content $tmp.FullName $envContent -Encoding ASCII
scp $tmp.FullName ubuntu@msp-bastion:/opt/osticket/.env
Remove-Item $tmp.FullName

ssh msp-bastion @'
chmod 600 /opt/osticket/.env
cd /opt/osticket
docker compose up -d
echo "osTicket: http://10.9.0.1:8080"
'@
```

Завершить установку: открыть SSH-туннель и зайти браузером:
```powershell
ssh -L 8080:10.9.0.1:8080 msp-bastion
# В отдельной вкладке: http://localhost:8080
```

---

## 7. GOLD ALERT RULES

> Файл лежит в репо: `technical/3_Gold/EXECUTOR/prometheus/gold_alerts.yml`.

```powershell
scp ..\prometheus\gold_alerts.yml ubuntu@msp-bastion:/opt/monitoring/prometheus/rules/
ssh msp-bastion @'
cd /opt/monitoring
docker compose exec prometheus promtool check rules /etc/prometheus/rules/gold_alerts.yml
docker compose kill -s HUP prometheus
'@
```

Содержание (для справки):

```yaml
groups:
  - name: gold_security
    rules:
      - alert: WazuhAgentDown
        expr: wazuh_agent_status{status!="Active"} == 1
        for: 5m
        labels:   { severity: warning, category: security }
        annotations:
          summary: "Wazuh Agent неактивен: {{ $labels.agent_name }}"
          description: "Проверить на сервере: systemctl status wazuh-agent"

      - alert: KasperskyNotRunning
        expr: kaspersky_service_running == 0
        for: 10m
        labels:   { severity: critical, category: security }
        annotations:
          summary: "Kaspersky НЕ работает: {{ $labels.host }}"

      - alert: KasperskyDatabaseOld
        expr: kaspersky_database_age_hours > 48
        for: 1h
        labels:   { severity: warning, category: security }
        annotations:
          summary: "Базы Kaspersky устарели: {{ $value | printf \"%.0f\" }} ч"

  - name: gold_sla
    rules:
      - alert: SLAReactionTimeAtRisk
        expr: |
          (time() - alertmanager_alerts_firing_timestamp_seconds) > 2700
          and on() up{job="alertmanager"} == 1
        for: 0m
        labels:   { severity: critical, category: sla }
        annotations:
          summary: "SLA: алерт не закрыт > 45 минут (Gold P1 = 1 ч)"
```

---

## 8. ВЕРИФИКАЦИЯ GOLD EXECUTOR

```powershell
function Test-MspGoldExecutor {
    Write-Host "`n--- Bronze + Silver ---" -ForegroundColor Cyan
    ssh msp-bastion @'
        for c in msp-prometheus msp-loki msp-grafana msp-alertmanager; do
            status=$(docker inspect $c --format '{{.State.Running}}' 2>/dev/null)
            printf "%-20s %s\n" "$c" "$status"
        done
'@
    Write-Host "`n--- Gold: Wazuh ---" -ForegroundColor Cyan
    ssh msp-wazuh @'
        for c in wazuh-manager wazuh-indexer wazuh-dashboard; do
            status=$(docker inspect $c --format '{{.State.Running}}' 2>/dev/null)
            printf "%-20s %s\n" "$c" "$status"
        done
        echo "Wazuh agents:"
        docker exec wazuh-manager /var/ossec/bin/agent_control -l | head -20
'@
    Write-Host "`n--- Gold: osTicket ---" -ForegroundColor Cyan
    ssh msp-bastion "docker inspect osticket-app --format '{{.State.Running}}'"

    Write-Host "`n--- Gold alerts loaded ---" -ForegroundColor Cyan
    ssh msp-bastion "curl -s localhost:9090/api/v1/rules | python3 -c 'import json,sys;d=json.load(sys.stdin);print([g[\"name\"] for g in d[\"data\"][\"groups\"] if \"gold\" in g[\"name\"]])'"
}

Test-MspGoldExecutor
```

---

## 9. TROUBLESHOOTING GOLD EXECUTOR

| Проблема                                | Диагностика с Win10                                                                                  | Решение                                                                                  |
|-----------------------------------------|------------------------------------------------------------------------------------------------------|-------------------------------------------------------------------------------------------|
| Wazuh Indexer не стартует               | `ssh msp-wazuh 'docker logs wazuh-indexer 2>&1 \| tail -50'`                                          | Проверить `sysctl vm.max_map_count` = 262144 и RAM ≥ 8 GB                                |
| Wazuh Manager не принимает агентов      | `ssh msp-wazuh 'docker exec wazuh-manager /var/ossec/bin/agent_control -l'`                          | Порты 1514/1515 доступны из VPN? `ssh msp-wazuh 'docker restart wazuh-manager'`           |
| Dashboard недоступен                    | `Test-NetConnection 10.9.0.3 -Port 443`                                                              | Проверить, что VPN IP 10.9.0.3 настроен на Wazuh VM и `wg0-msp` поднят                  |
| Telegram интеграция не работает         | `ssh msp-wazuh 'docker logs wazuh-manager 2>&1 \| grep -i telegram'`                                  | Проверить `TELEGRAM_BOT_TOKEN` / `TELEGRAM_CHAT_ID` в `/opt/wazuh/.env`                  |
| osTicket ошибка БД                      | `ssh msp-bastion 'docker logs osticket-db 2>&1 \| tail -30'`                                          | `ssh msp-bastion 'docker restart osticket-db'`, дождаться healthcheck                    |
| KSC exporter не отдаёт метрики          | `ssh msp-automation 'curl -fsS http://localhost:9101/metrics \| head'`                                | `ssh msp-automation 'sudo journalctl -u ksc-exporter -n 50'`; проверить токен KSC API     |
| Gold alerts не загружены в Prometheus   | `ssh msp-bastion 'curl -s localhost:9090/api/v1/rules \| python3 -m json.tool \| grep gold'`          | `scp gold_alerts.yml ...` и `kill -HUP $(pidof prometheus)` (или `docker kill -s HUP`)    |
