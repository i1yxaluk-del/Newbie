#!/usr/bin/env bash
# Диагностика после deploy/переноса. Скрипт только читает состояние.
set -u

echo "=== APPLICATION ==="
curl -fsS http://127.0.0.1:8001/api/health || echo "FAIL: backend health"

echo "=== MONITORING ==="
curl -fsS http://127.0.0.1:9090/-/healthy || echo "FAIL: Prometheus"
curl -fsS http://127.0.0.1:9093/-/healthy || echo "FAIL: Alertmanager"
curl -fsS http://127.0.0.1:9095/health || echo "FAIL: MAX webhook"

echo "=== MAX SESSION (SMS не отправляется) ==="
docker exec msp-max-alerter python -m max_alerter.auth || echo "WARN: нужна ручная авторизация"

echo "=== PROMETHEUS TARGETS ==="
curl -fsS http://127.0.0.1:9090/api/v1/targets | python3 -c '
import json, sys
for target in json.load(sys.stdin)["data"]["activeTargets"]:
    print(f"{target["labels"].get("job", "?"):25s} {target["health"]:8s} {target.get("lastError", "")[:80]}")
' || echo "FAIL: targets API"

echo "=== RESTIC ==="
systemctl is-active restic-backup.timer || true
cat /var/lib/node_exporter/textfile_collector/restic_backup.prom 2>/dev/null || echo "WARN: restic metrics отсутствуют"
