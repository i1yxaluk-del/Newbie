#!/usr/bin/env bash
# Освобождение места на диске перед развёртыванием Synapse/Prosody.
# ВАЖНО: нигде не используем --volumes — данные контейнеров не трогаем.
set -uo pipefail
echo "=== 1. диск ДО ==="
df -h / | tail -1

echo
echo "=== 2. что занимает ==="
du -sh /var/lib/docker/* 2>/dev/null | sort -hr | head -5
echo "  --- каталоги ---"
for d in /opt/msp /home /var/log /tmp; do
  [ -e "$d" ] && du -sh "$d" 2>/dev/null
done
echo "  --- docker df ---"
docker system df 2>/dev/null

echo
echo "=== 3. чистим build cache и неиспользуемые образы (БЕЗ volumes) ==="
docker builder prune -af 2>&1 | tail -2
docker image prune -af 2>&1 | tail -2
docker system df 2>/dev/null

echo
echo "=== 4. диск ПОСЛЕ ==="
df -h / | tail -1

echo
echo "=== 5. coturn: где он живёт ==="
systemctl is-active coturn 2>/dev/null || echo "  coturn.service не активен"
systemctl list-units --all --type=service 2>/dev/null | grep -iE "turn|amnezia|awg" | head -5
ss -lntup 2>/dev/null | grep -E ":3478|:5349" | head -4
ls -la /etc/turnserver.conf 2>/dev/null | head -2
echo DONE
