#!/usr/bin/env bash
# Назначение: восстановить Mongo, Vaultwarden, Stalwart и MAX на подготовленной новой VM.
# Где запускать: новая VM от root после deploy preflight.
# Важно: старые .env/cloud credentials не восстанавливаются.
# Откат: snapshot новой VM, созданный до запуска.
#
# Раскладка артефактов (урок миграции 28.09):
#   скрипт сам ищет файлы во всех типовых раскладках кита бэкапа —
#   плоско в MIGRATION_DIR, в MIGRATION_DIR/volumes, в opt/msp-backups/current{/volumes}.
#   Если из root-only каталогов копируете вручную — только через
#   sudo sh -c 'cp .../*.tar.gz /tmp/migration/'  (glob раскрывается ДО sudo!).
# Ожидаемые файлы: mongodump.archive.gz, vaultwarden-data.tar.gz,
#   stalwart-etc.tar.gz, stalwart-data.tar.gz, max-session.tar.gz.
set -Eeuo pipefail

MIGRATION_DIR="${MIGRATION_DIR:-/tmp/migration}"
REPO_DIR="${REPO_DIR:-/opt/msp/Newbie}"
DEPLOY_DIR="$REPO_DIR/deploy/yandex"
MONITORING_DIR="$DEPLOY_DIR/monitoring"
log() { echo "[$(date -Iseconds)] $*" | tee -a /var/log/msp-migration.log; }

# Поиск артефакта по всем вероятным раскладкам кита бэкапа.
find_artifact() {
  local name="$1" candidate
  for candidate in \
    "$MIGRATION_DIR/$name" \
    "$MIGRATION_DIR/volumes/$name" \
    "$MIGRATION_DIR/opt/msp-backups/current/$name" \
    "$MIGRATION_DIR/opt/msp-backups/current/volumes/$name" \
    "/opt/msp-backups/current/$name" \
    "/opt/msp-backups/current/volumes/$name" \
    ; do
    if [[ -s "$candidate" ]]; then echo "$candidate"; return 0; fi
  done
  return 1
}

RESTORED=()
MISSING=()

MONGO_ARCHIVE="$(find_artifact mongodump.archive.gz || true)"
[[ -n "$MONGO_ARCHIVE" ]] || { log "ERROR: не найден mongodump.archive.gz (искал в $MIGRATION_DIR и opt/msp-backups/current)"; exit 1; }
log "mongodump: $MONGO_ARCHIVE"

[[ -s "$DEPLOY_DIR/.env" && -s "$MONITORING_DIR/.env" ]] || { log "ERROR: сначала создайте новые .env"; exit 1; }

(cd "$MONITORING_DIR" && docker compose down) || true
(cd "$DEPLOY_DIR" && docker compose --profile mail down) || true
cd "$DEPLOY_DIR"
docker compose up -d mongo
MONGO_ID="$(docker compose ps -q mongo)"
for _ in $(seq 1 30); do docker exec "$MONGO_ID" mongosh --quiet --eval "db.adminCommand('ping').ok" 2>/dev/null | grep -q 1 && break; sleep 3; done
docker exec "$MONGO_ID" mongosh --quiet --eval "db.adminCommand('ping').ok" | grep -q 1
docker exec -i "$MONGO_ID" mongorestore --archive --gzip --drop < "$MONGO_ARCHIVE"
RESTORED+=("mongo")

restore_volume() {
  local archive_name="$1" volume="$2" path file_count
  if ! path="$(find_artifact "$archive_name")"; then
    log "WARN: $archive_name НЕ найден — том $volume не будет восстановлен (проверьте раскладку, см. шапку скрипта)"
    MISSING+=("$archive_name")
    return 0
  fi
  log "restore: $path -> volume $volume"
  docker volume create "$volume" >/dev/null
  docker run --rm -v "$volume:/target" -v "$(dirname "$path"):/backup:ro" alpine:3.20 \
    sh -c "rm -rf /target/* && tar xzf /backup/$(basename "$path") -C /target"
  # Проверка, что том не пуст — урок 28.09: молчаливые пустые тома → bootstrap.
  file_count="$(docker run --rm -v "$volume:/target" alpine:3.20 sh -c 'find /target -mindepth 1 | wc -l')"
  if [[ "${file_count:-0}" -eq 0 ]]; then
    log "ERROR: том $volume пуст после восстановления ($archive_name) — прерываю"
    exit 1
  fi
  log "  ok: $volume ($file_count файлов)"
  RESTORED+=("$volume")
}
restore_volume vaultwarden-data.tar.gz msp_vaultwarden-data
restore_volume stalwart-etc.tar.gz msp_stalwart-etc
restore_volume stalwart-data.tar.gz msp_stalwart-data

MAX_ARCHIVE="$(find_artifact max-session.tar.gz || true)"
if [[ -n "$MAX_ARCHIVE" ]]; then
  rm -rf "$MONITORING_DIR/max-session"
  tar xzf "$MAX_ARCHIVE" -C "$MONITORING_DIR"
  chmod 700 "$MONITORING_DIR/max-session"
  chmod 600 "$MONITORING_DIR/max-session/max.db" 2>/dev/null || true
  RESTORED+=("max-session")
else
  log "WARN: max-session.tar.gz не найден — MAX-сессия не восстановлена"
  MISSING+=("max-session.tar.gz")
fi

(cd "$DEPLOY_DIR" && docker compose up -d)
# Stalwart запускается только если mail profile используется осознанно.
if find_artifact stalwart-etc.tar.gz >/dev/null 2>&1; then
  (cd "$DEPLOY_DIR" && docker compose --profile mail up -d stalwart)
  sleep 10
  # Урок 28.09: пустые тома → Stalwart стартует в bootstrap-режиме и молча теряет почту.
  if docker logs msp-stalwart-1 2>&1 | grep -q "bootstrap mode"; then
    log "ERROR: Stalwart в bootstrap-режиме — тома stalwart-etc/stalwart-data не восстановились. См. MIGRATION_RUNBOOK §9.4"
    exit 1
  fi
  RESTORED+=("stalwart")
fi
(cd "$MONITORING_DIR" && chmod +x alertmanager/entrypoint.sh && docker compose up -d --build)

curl -fsS --retry 30 --retry-delay 3 http://127.0.0.1:8001/api/health >/dev/null
curl -fsS http://127.0.0.1:9093/-/healthy >/dev/null
curl -fsS http://127.0.0.1:9095/health >/dev/null
if ! docker exec msp-max-alerter python -m max_alerter.auth; then
  log "WARN: MAX session требует ручной авторизации: docker exec -it msp-max-alerter python -m max_alerter.auth --authorize"
fi

log "ИТОГ: восстановлено: ${RESTORED[*]:-нет}"
if [[ ${#MISSING[@]} -gt 0 ]]; then log "ИТОГ: пропущено (проверьте!): ${MISSING[*]}"; fi
log "Restore завершён. До DNS switch обязательны тест P1, restore evidence и новый restic snapshot. См. MIGRATION_RUNBOOK §9.8."
