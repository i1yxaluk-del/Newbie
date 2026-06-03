# Week 4 · Backup & Recovery (restic + DR)

## Цель

Уметь установить restic на новый tenant, настроить расписание, провести
smoke DR, объяснить клиенту RTO/RPO, интегрировать бэкап-метрики в
мониторинг.

---

## 1. Restic на VM: полная установка с нуля

### 1.1. Установка бинарника

```bash
# На VM
curl -LO https://github.com/restic/restic/releases/download/v0.16.4/restic_0.16.4_linux_amd64.bz2
bzip2 -d restic_0.16.4_linux_amd64.bz2
sudo mv restic_0.16.4_linux_amd64 /usr/local/bin/restic
sudo chmod +x /usr/local/bin/restic
restic version  # → restic 0.16.4
```

### 1.2. S3-репозиторий (Yandex Object Storage)

```bash
# Создаём bucket в YC Console: Object Storage → Create bucket
# Имя: <client-slug>-backups-prod, класс: STANDARD

# Секреты
sudo tee /etc/restic/env.sh > /dev/null << 'EOF'
export AWS_ACCESS_KEY_ID=<YC IAM access key>
export AWS_SECRET_ACCESS_KEY=<YC IAM secret>
export RESTIC_REPOSITORY=s3:https://storage.yandexcloud.net/<bucket-name>
export RESTIC_PASSWORD=<32+ символьный пароль шифрования>
EOF
sudo chmod 600 /etc/restic/env.sh
sudo chown root:root /etc/restic/env.sh
```

### 1.3. Инициализация репозитория

```bash
source /etc/restic/env.sh
restic init
# → created restic repository
```

### 1.4. Скрипт бэкапа

```bash
sudo mkdir -p /opt/restic-scripts /var/log/restic /var/lib/node_exporter/textfile_collector

sudo tee /opt/restic-scripts/backup.sh > /dev/null << 'SCRIPT'
#!/bin/bash
set -euo pipefail
LOG="/var/log/restic-backup.log"
METRICS_DIR="/var/lib/node_exporter/textfile_collector"
METRICS_FILE="${METRICS_DIR}/restic_backup.prom"
HOSTNAME="node-01"
REPO="<client-slug>-prod"
TIMESTAMP=$(date +%s)
STATUS=0
BYTES=0

source /etc/restic/env.sh

write_metrics() {
    local status=$1 timestamp=$2 bytes=$3
    mkdir -p "$METRICS_DIR"
    local tmp="${METRICS_FILE}.tmp"
    cat > "$tmp" << EOF
restic_backup_success{host="${HOSTNAME}",repo="${REPO}"} ${status}
restic_backup_timestamp_seconds{host="${HOSTNAME}",repo="${REPO}"} ${timestamp}
restic_backup_size_bytes{host="${HOSTNAME}",repo="${REPO}"} ${bytes}
EOF
    mv "$tmp" "$METRICS_FILE"
}

write_metrics 2 "$TIMESTAMP" 0

BACKUP_PATHS=("/etc" "/home" "/root" "/opt" "/var/www" "/var/lib/docker/volumes" "/var/lib/caddy")

EXISTING_PATHS=()
for p in "${BACKUP_PATHS[@]}"; do
    [[ -d "$p" ]] && EXISTING_PATHS+=("$p")
done

if restic backup "${EXISTING_PATHS[@]}" --tag auto --tag "$HOSTNAME" --compression auto --json 2>&1 | tee -a "$LOG"; then
    STATUS=1
    BYTES=$(grep -E '^\{"message_type":"summary"' "$LOG" | tail -1 | grep -oE '"total_bytes_processed":[0-9]+' | cut -d: -f2 || echo "0")
else
    STATUS=0; BYTES=0
fi

restic forget --tag "$HOSTNAME" --keep-daily 7 --keep-weekly 4 --keep-monthly 6 --keep-yearly 1 --prune --compact 2>&1 | tee -a "$LOG" || true

if [[ $(date +%u) -eq 7 ]]; then
    restic check 2>&1 | tee -a "$LOG" || true
fi

write_metrics "$STATUS" "$TIMESTAMP" "$BYTES"
exit $(( 1 - STATUS ))
SCRIPT

sudo chmod +x /opt/restic-scripts/backup.sh
```

### 1.5. Systemd timer (ежедневно 02:00)

```bash
sudo tee /etc/systemd/system/restic-backup.service > /dev/null << 'EOF'
[Unit]
Description=MSP Restic Backup
After=network-online.target

[Service]
Type=oneshot
EnvironmentFile=/etc/restic/env.sh
ExecStart=/opt/restic-scripts/backup.sh
Nice=19
IOSchedulingClass=best-effort
TimeoutStartSec=7200
SyslogIdentifier=restic-backup
EOF

sudo tee /etc/systemd/system/restic-backup.timer > /dev/null << 'EOF'
[Unit]
Description=MSP Restic Backup Timer

[Timer]
OnCalendar=*-*-* 02:00:00
RandomizedDelaySec=5min
Persistent=true

[Install]
WantedBy=timers.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable --now restic-backup.timer

# Проверяем
systemctl list-timers | grep restic
```

### 1.6. Первый бэкап вручную

```bash
sudo systemctl start restic-backup
sudo journalctl -u restic-backup --since "5 min ago"

# Проверяем метрики
cat /var/lib/node_exporter/textfile_collector/restic_backup.prom
# restic_backup_success{...} 1  ← успех
```

---

## 2. Мониторинг бэкапов в Grafana

Метрики из §1.4 видны в Prometheus через node-exporter textfile collector.

**Dashboard "MSPShield — Backups"** (uid: `mspshield-backups`):

| Panel | Что показывает | PromQL |
|-------|---------------|--------|
| Статус | OK/FAIL/RUNNING | `restic_backup_success` |
| Размер | bytes | `restic_backup_size_bytes` |
| Возраст | секунды с последнего | `time() - restic_backup_timestamp_seconds` |
| 7 дней | история (state-timeline) | `restic_backup_success` range |
| Retention | текст | static `vector(1)` |

**Alert-правила** (`rules/backups.yml`):

| Alert | Severity | Триггер |
|-------|----------|---------|
| BackupFailed | P1 | `restic_backup_success == 0` |
| BackupMissed24h | P1 | `time() - timestamp > 93600` |
| BackupSizeDropped | P2 | `size < avg[7d] * 0.5` |
| BackupInProgress | P3 | `success == 2 for 30m` |

---

## 3. DR (Disaster Recovery) drill

### 3.1. Список снапшотов

```bash
source /etc/restic/env.sh
restic snapshots --latest 5
```

### 3.2. Восстановление одного файла

```bash
restic restore <snapshot-id> --target /tmp/restore-test --include /etc/caddy/Caddyfile
diff /etc/caddy/Caddyfile /tmp/restore-test/etc/caddy/Caddyfile
# → no differences = OK
rm -rf /tmp/restore-test
```

### 3.3. Полное восстановление на новой VM

```bash
# На новой VM:
# 1. Установить restic
# 2. Скопировать /etc/restic/env.sh
# 3. Восстановить всё:
source /etc/restic/env.sh
restic restore latest --target /tmp/full-restore

# 4. Копировать нужные данные на место:
sudo cp -a /tmp/full-restore/var/lib/docker/volumes/* /var/lib/docker/volumes/
sudo cp -a /tmp/full-restore/var/lib/caddy/* /var/lib/caddy/
sudo cp -a /tmp/full-restore/etc/caddy/Caddyfile /etc/caddy/
# ... и т.д.
```

### 3.4. Verify (целостность репозитория)

```bash
source /etc/restic/env.sh
restic check            # быстрая проверка метаданных
restic check --read-data  # полная (долго, читать все pack files)
```

---

## 4. Что бэкапим (чеклист)

| Путь | Что внутри | Критичность |
|------|-----------|-------------|
| `/etc` | Конфиги ОС, systemd, UFW | Высокая |
| `/home` | Пользовательские данные | Средняя |
| `/root` | Root home | Средняя |
| `/opt` | Приложения, скрипты | Высокая |
| `/var/www` | Лендинг/сайт | Средняя |
| `/var/lib/docker/volumes` | Все Docker volumes | **Критическая** |
| `/var/lib/caddy` | SSL-сертификаты | **Критическая** |

**Retention:** daily 7, weekly 4, monthly 6, yearly 1
**S3 bucket:** `<client-slug>-backups-prod`
**Verify:** каждую неделю (воскресенье)

---

## Задачи

- [ ] Развернуть restic на test-VM от нуля (§1)
- [ ] Сделать первый бэкап, проверить метрики в Prometheus
- [ ] Провести DR drill: восстановить один файл (§3.2)
- [ ] Настроить Grafana Backups dashboard
- [ ] Сессия с owner: 30 мин про restic internals (pack files,
      snapshots, prune)

## Production

- [ ] Пройти R-backup-failed: симулируй ошибку, исправь по runbook'у
- [ ] Подготовить monthly report для 1 Bronze-клиента

## Read

- [Restic docs: "Operations"](https://restic.readthedocs.io/en/latest/060_forget.html)
- `deploy/yandex/monitoring/restic-exporter/README.md` — наши скрипты
- `deploy/yandex/README.md` §15 — что бэкапится

## Check-in

1. Что такое `restic prune` и почему он дорогой?
2. RTO и RPO — формулируй для Bronze / Silver / Gold
3. Что делать если `restic check` показал `repository broken`?
4. Как restic-метрики попадают в Prometheus?
5. Что будет если забыть `/var/lib/caddy` в BACKUP_PATHS?

## DoD

- Самостоятельно провёл DR smoke-test
- Restic-метрики видны в Grafana
- Monthly report сдан
