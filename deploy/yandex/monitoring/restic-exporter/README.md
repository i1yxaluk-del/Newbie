# restic → Prometheus Exporter

Скрипты-обёртки для экспорта метрик restic-бэкапов в Prometheus через **node-exporter textfile collector**. Дашборд в Grafana — `MSPShield — Backups`.

## 📦 Что внутри

| Файл | Назначение |
|---|---|
| `restic-metrics.sh` | Пишет `.prom` файлы в textfile-директорию node-exporter |
| `run-backup.sh` | Обёртка для `restic backup` — запускает + эмитит метрики |
| `run-verify.sh` | Обёртка для `restic check` (создай по аналогии) |
| `run-restore-test.sh` | DR drill — восстанавливает случайный snapshot во временный каталог |

---

## 🚀 Установка на ВМ

### 1. node-exporter с textfile collector

```bash
# В docker-compose.yml добавить:
node-exporter:
image: prom/node-exporter:v1.8.1
command:
  - '--path.rootfs=/host'
  - '--collector.textfile.directory=/var/lib/node_exporter/textfile'
volumes:
  - /:/host:ro,rslave
  - /var/lib/node_exporter/textfile:/var/lib/node_exporter/textfile:ro
pid: host
network_mode: host
```

### 2. Скопировать скрипты

```bash
sudo mkdir -p /opt/backups /var/lib/node_exporter/textfile /var/log/restic
sudo cp restic-metrics.sh run-backup.sh /opt/backups/
sudo chmod +x /opt/backups/*.sh
```

### 3. Секреты в `/etc/backup.env`

```bash
sudo tee /etc/backup.env > /dev/null <<'EOF'
export RESTIC_REPOSITORY="s3:s3.yandexcloud.net/msp-backups"
export RESTIC_PASSWORD="<32-символьный пароль шифрования>"
export AWS_ACCESS_KEY_ID="<Yandex IAM access key>"
export AWS_SECRET_ACCESS_KEY="<Yandex IAM secret>"
EOF
sudo chmod 600 /etc/backup.env
sudo chown root:root /etc/backup.env
```

### 4. Cron для каждого хоста

```bash
# /etc/cron.d/restic-backup
SHELL=/bin/bash
PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin

# Ежедневный backup в 03:00
0 3 * * * root /opt/backups/run-backup.sh web-01 main /etc /var/www

# Verify раз в неделю (вс 04:00)
0 4 * * 0 root /opt/backups/run-verify.sh web-01 main

# Restore-test раз в месяц (1-е число, 05:00)
0 5 1 * * root /opt/backups/run-restore-test.sh web-01 main
```

---

## 📊 Метрики

После каждого запуска в `/var/lib/node_exporter/textfile/` появляются файлы `restic_<cmd>_<host>.prom`. node-exporter экспортирует их на `:9100/metrics`:

```
restic_backup_success{host="web-01",repo="main"} 1
restic_backup_timestamp_seconds{host="web-01",repo="main"} 1717405200
restic_backup_size_bytes{host="web-01",repo="main"} 1288490188
restic_verify_success{host="web-01",repo="main"} 1
restic_restore_test_success{host="web-01",repo="main"} 1
restic_restore_test_timestamp_seconds{host="web-01",repo="main"} 1717405200
```

---

## 🔔 Алёрты

См. `../prometheus/rules/backups.yml` — 6 правил:

| Alert | Severity | Trigger |
|---|---|---|
| `BackupFailed` | critical | `restic_backup_success == 0` |
| `BackupMissed24h` | critical | Бэкап не запускался > 26ч |
| `VerifyStale` | warning | Verify > 7 дней |
| `RestoreTestStale` | warning | DR drill > 30 дней |
| `RestoreTestFailed` | critical | Restore-test упал |
| `BackupSizeDropped` | warning | Размер < 50% от 7-дневного среднего |

---

## 🩹 Runbooks

### <a id="backup-failed"></a> BackupFailed

1. Залогиниться на хост: `ssh ubuntu@<host>`
2. Посмотреть лог: `tail -100 /var/log/restic/<host>-<repo>.log`
3. Типовые причины:
 - **Auth** — IAM-ключи протухли → обновить `/etc/backup.env`
 - **Network** — нет связи с S3 Yandex → `curl -I https://s3.yandexcloud.net`
 - **Disk** — закончилось место в `/tmp` (restic использует для упаковки)
 - **Lock** — предыдущий запуск завис → `restic unlock`
4. Перезапустить вручную: `/opt/backups/run-backup.sh <host> <repo> <paths>`
5. Если успешно — метрика обновится, алёрт закроется автоматически

### BackupMissed24h

1. Проверить cron: `systemctl status cron && grep restic /etc/cron.d/restic-backup`
2. Проверить логи cron: `journalctl -u cron --since "26 hours ago" | grep restic`
3. Запустить вручную чтобы убедиться что скрипт работает

### RestoreTestFailed

**КРИТИЧНО.** Это значит что бэкап есть, но восстановление не работает = бэкапа де-факто нет.

1. Запустить restore-test вручную: `/opt/backups/run-restore-test.sh <host> <repo>`
2. Если падает — debug:
 - `restic snapshots` — снапшоты вообще видны?
 - `restic restore <snapshot-id> --target /tmp/restore-test --dry-run`
3. Если падает на конкретном snapshot — он битый. Запустить `restic check --read-data` и проверить целостность всего репозитория.

---

## 🎯 Dashboard

Grafana → MSPShield → **MSPShield — Backups** (uid `mspshield-backups`)

Виджет повторяет ровно тот, что на сайте `msp-claude.online`:

- **Stat (верх):** `<успех>/<всего> ✓ · <verify-pending>` за 7 дней
- **Stat (верх справа):** `AES-256 · ОБЛАЧНОЕ ХРАНИЛИЩЕ`
- **Heatmap (центр):** хост × день, зелёный = ok, амбер = fail
- **Table (справа):** размер последнего бэкапа на хост
- **Stat (низ):** `Последний restore-test: <X> назад · <host>`

Палитра — единая со всем MSPShield: forest `#1b4d3e` (ok), amber `#b45309` (warning), red `#b91c1c` (critical).
