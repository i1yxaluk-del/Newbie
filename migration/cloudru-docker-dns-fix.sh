#!/usr/bin/env bash
# ═══════════════════════════════════════════════════════════════════
# НАЗНАЧЕНИЕ (для junior): Чинит DNS внутри Docker-контейнеров (8.8.8.8 из cloud.ru не отвечает).
# КОГДА ЗАПУСКАТЬ:         На чистой ВМ ДО первой сборки контейнеров.
# КАК ЗАПУСКАТЬ:           sudo bash cloudru-docker-dns-fix.sh
# ПРОВЕРКА УСПЕХА:         docker run --rm python:3.12-slim getent hosts pypi.org -> имя резолвится.
# ОТКАТ:                   Убрать ключ dns из /etc/docker/daemon.json и перезапустить docker.
# ═══════════════════════════════════════════════════════════════════
# Docker раздаёт контейнерам 8.8.8.8, который из cloud.ru не отвечает -> ставим рабочие резолверы.
set -uo pipefail
cp /etc/docker/daemon.json /etc/docker/daemon.json.bak.$(date +%s) 2>/dev/null || true

python3 - <<'PY'
import json, os
p = '/etc/docker/daemon.json'
d = json.load(open(p)) if os.path.exists(p) and os.path.getsize(p) > 0 else {}
d['dns'] = ['1.1.1.1', '8.8.4.4']
json.dump(d, open(p, 'w'), indent=2)
print("daemon.json:", open(p).read())
PY

echo "=== рестарт docker ==="
systemctl restart docker
sleep 20
systemctl is-active docker
echo "=== ждём возврата контейнеров (30 с) ==="
sleep 30
sudo docker ps --format '{{.Names}}: {{.Status}}' | sort | head -20

echo
echo "=== проверка DNS в контейнере ==="
sudo docker run --rm python:3.12-slim sh -c 'grep nameserver /etc/resolv.conf; getent hosts pypi.org && echo DNS_OK || echo DNS_FAIL' 2>&1 | head -8

echo
echo "=== проверка pip ==="
timeout 120 sudo docker run --rm python:3.12-slim pip install --no-cache-dir --disable-pip-version-check -q "fastapi>=0.115" 2>&1 | tail -4
echo "pip exit: $?"
echo DONE
