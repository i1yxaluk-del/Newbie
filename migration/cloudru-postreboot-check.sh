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
for s in caddy docker awg-quick@awg0 msp-policy-route coturn; do
  printf "  %-20s %s\n" "$s" "$(systemctl is-active "$s" 2>/dev/null)"
done
echo
echo "=== docker-контейнеры ==="
sudo docker ps --format '{{.Names}}: {{.Status}}' 2>/dev/null | sort
echo
echo "=== порты ==="
ss -ltnp 2>/dev/null | grep -E ':(80|443|5222|5280|8448|8891|8895|8896|8898|8899)\b' | awk '{print "  "$4}' | sort -u
echo
echo "=== локальные эндпоинты ==="
for u in "http://127.0.0.1:8891/" "http://127.0.0.1:8895/health" "http://127.0.0.1:8896/health" "http://127.0.0.1:8898/health"; do
  printf "  %-40s %s\n" "$u" "$(curl -s -o /dev/null -w '%{http_code}' -m 6 "$u" 2>/dev/null)"
done
echo
echo DONE
