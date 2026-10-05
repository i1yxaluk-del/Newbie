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
for d in /opt/jams-src /opt/jams /opt/msp /opt/jami-services /home /var/log /tmp; do
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
echo "=== 4. убираю node_modules фронтенда JAMS (восстанавливается npm ci) ==="
if [ -d /opt/jams-src/jams-react-client/node_modules ]; then
  du -sh /opt/jams-src/jams-react-client/node_modules
  rm -rf /opt/jams-src/jams-react-client/node_modules
  echo "  удалено"
fi
[ -d /opt/jams-src/jams-react-client.broken-v9/node_modules ] && rm -rf /opt/jams-src/jams-react-client.broken-v9/node_modules
echo "  /opt/jams-src теперь: $(du -sh /opt/jams-src 2>/dev/null | cut -f1)"

echo
echo "=== 5. старые бэкапы jar/config (оставляю по одному свежему) ==="
ls -1t /opt/jams/jams-server.jar.bak* 2>/dev/null | tail -n +2 | while read -r f; do rm -f "$f"; echo "  удалён $f"; done
ls -1t /opt/jams/config.json.bak.* 2>/dev/null | tail -n +2 | while read -r f; do rm -f "$f"; echo "  удалён $f"; done

echo
echo "=== 6. диск ПОСЛЕ ==="
df -h / | tail -1

echo
echo "=== 7. coturn: где он живёт ==="
systemctl is-active coturn 2>/dev/null || echo "  coturn.service не активен"
systemctl list-units --all --type=service 2>/dev/null | grep -iE "turn|amnezia|awg" | head -5
ss -lntup 2>/dev/null | grep -E ":3478|:5349" | head -4
ls -la /etc/turnserver.conf 2>/dev/null | head -2
echo DONE
