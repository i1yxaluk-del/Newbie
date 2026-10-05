#!/usr/bin/env bash
# ═══════════════════════════════════════════════════════════════════
# НАЗНАЧЕНИЕ (для junior): Настраивает restic-бэкапы и метрики для Grafana (дашборд MSPShield - Backups).
# КОГДА ЗАПУСКАТЬ:         На ВМ от root после деплоя приложения.
# КАК ЗАПУСКАТЬ:           sudo bash cloudru-backup-setup.sh
# ПРОВЕРКА УСПЕХА:         restic snapshots -> есть снапшот; в Prometheus restic_backup_success = 1.
# ОТКАТ:                   Удалить cron-запись и /etc/restic/env.sh; репозиторий останется в /var/backups/restic.
# ═══════════════════════════════════════════════════════════════════
# Настройка бэкапов: restic + метрики в textfile (их забирает node-exporter -> Prometheus -> Grafana).
# ВНИМАНИЕ: репозиторий ПОКА ЛОКАЛЬНЫЙ (/var/backups/restic), т.к. статических S3-ключей нет.
# Для off-site достаточно поменять RESTIC_REPOSITORY в /etc/restic/env.sh на s3:https://s3.cloud.ru/<bucket>.
set -uo pipefail

echo "=== 1. скрипты бэкапа -> /opt/restic-scripts ==="
mkdir -p /opt/restic-scripts
cp /opt/msp/Newbie/migration/restic-backup.sh /opt/restic-scripts/restic-backup.sh
chmod 755 /opt/restic-scripts/restic-backup.sh
ls -la /opt/restic-scripts/

echo
echo "=== 2. файл исключений ==="
if [ ! -f /opt/restic-scripts/excludes.txt ]; then
  cat >/opt/restic-scripts/excludes.txt <<'EOF'
# Что НЕ попадает в бэкап (мусор и то, что восстанавливается из репозитория).
/opt/msp-backups
/opt/jams-src
/opt/*.tar.gz
/opt/*.log
**/node_modules
**/.cache
**/__pycache__
**/tmp
**/*.log
/var/lib/docker/overlay2
/var/log
/root/.cache
/root/.npm
/root/.gnupg
/home/*/.cache
/home/*/.npm
/home/*/.local/share/Trash
EOF
  echo "  создан excludes.txt"
fi
wc -l /opt/restic-scripts/excludes.txt

echo
echo "=== 3. /etc/restic/env.sh (репозиторий + пароль шифрования) ==="
mkdir -p /etc/restic /var/backups/restic /opt/msp-backups /var/log
if [ ! -f /etc/restic/env.sh ]; then
  RP=$(head -c 40 /dev/urandom | base64 | tr -d '/+=' | head -c 32)
  cat >/etc/restic/env.sh <<EOF
# Репозиторий restic для MSPShield.
# СЕЙЧАС ЛОКАЛЬНЫЙ: S3-статических ключей Object Storage нет.
# Как перейти на off-site: создать бакет и статические ключи в консоли cloud.ru,
# затем заменить строку ниже на:
#   export RESTIC_REPOSITORY="s3:https://s3.cloud.ru/<bucket>"
#   export AWS_ACCESS_KEY_ID="<static-key-id>"
#   export AWS_SECRET_ACCESS_KEY="<static-secret>"
export RESTIC_REPOSITORY="/var/backups/restic"
export RESTIC_PASSWORD="$RP"
EOF
  chmod 600 /etc/restic/env.sh
  echo "  создан (пароль 32 симв., root:600)"
else
  echo "  уже существует"
fi
# shellcheck disable=SC1091
. /etc/restic/env.sh
echo "  RESTIC_REPOSITORY=$RESTIC_REPOSITORY"

echo
echo "=== 4. инициализация репозитория ==="
if restic snapshots >/dev/null 2>&1; then
  echo "  репозиторий уже инициализирован"
else
  restic init 2>&1 | tail -3
fi
restic snapshots 2>&1 | tail -3

echo
echo "=== 5. ПЕРВЫЙ БЭКАП (может занять несколько минут) ==="
/opt/restic-scripts/restic-backup.sh > /tmp/first-backup.log 2>&1
echo "  exit: $?"
tail -12 /tmp/first-backup.log

echo
echo "=== 6. метрика для Prometheus ==="
cat /var/lib/node_exporter/textfile_collector/restic_backup.prom 2>/dev/null || echo "  метрики нет"
echo
echo "=== 7. snapshots ==="
restic snapshots 2>&1 | tail -5

echo
echo "=== 8. cron (ежедневно в 03:00) ==="
( crontab -l 2>/dev/null | grep -v restic-backup; echo "0 3 * * * /opt/restic-scripts/restic-backup.sh >> /var/log/restic-backup.log 2>&1" ) | crontab -
crontab -l | grep restic
echo BACKUP_SETUP_DONE
