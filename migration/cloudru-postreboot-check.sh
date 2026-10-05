#!/usr/bin/env bash
set -uo pipefail
echo "=== uptime (подтверждение перезагрузки) ==="
uptime
echo
echo "=== память и swap ==="
free -m
echo "  swap-файлы: $(swapon --show 2>/dev/null | wc -l)"
echo
echo "=== systemd-службы ==="
for s in caddy docker awg-quick@awg0 msp-policy-route jams coturn dhtnode jamiserver; do
  printf "  %-20s %s\n" "$s" "$(systemctl is-active "$s" 2>/dev/null)"
done
echo
echo "=== docker-контейнеры ==="
sudo docker ps --format '{{.Names}}: {{.Status}}' 2>/dev/null | sort
echo
echo "=== порты ==="
ss -ltnp 2>/dev/null | grep -E ':(80|443|8081|8888|8889|8890|8891|8892)\b' | awk '{print "  "$4}' | sort -u
echo
echo "=== локальные эндпоинты ==="
for u in "http://127.0.0.1:8081/api/info" "http://127.0.0.1:8888/" "http://127.0.0.1:8890/" "http://127.0.0.1:8891/"; do
  printf "  %-40s %s\n" "$u" "$(curl -s -o /dev/null -w '%{http_code}' -m 6 "$u" 2>/dev/null)"
done
echo
echo "=== состояние сборки фронта (осталось после ребута) ==="
ls -la /opt/jams-src/jams-react-client/build/static/js/main.*.js 2>/dev/null || echo "  build отсутствует"
echo "  лог последней сборки:"
tail -6 /tmp/fe2.log 2>/dev/null || echo "   (нет)"
echo "  версии MUI в node_modules:"
for p in @mui/material @mui/styles @mui/private-theming ajv ajv-keywords; do
  echo "    $p = $(python3 -c "import json;print(json.load(open('/opt/jams-src/jams-react-client/node_modules/$p/package.json'))['version'])" 2>/dev/null || echo '—')"
done
echo DONE
