#!/usr/bin/env bash
set -uo pipefail
echo "=== 1. контейнеры после рестарта Docker ==="
sudo docker ps --format '{{.Names}}: {{.Status}}' | sort
echo
echo "=== 2. если чего-то нет — поднимаю прод-стек ==="
MISSING=0
for c in msp-mongo-1 msp-backend-1 msp-vaultwarden-1 msp-grafana msp-prometheus; do
  sudo docker ps --format '{{.Names}}' | grep -qx "$c" || { echo "  НЕТ: $c"; MISSING=1; }
done
if [ "$MISSING" = "1" ]; then
  echo "поднимаю /opt/msp/Newbie/deploy/yandex …"
  cd /opt/msp/Newbie/deploy/yandex && sudo docker compose --profile mail up -d 2>&1 | tail -8
  sleep 20
  cd /opt/msp/Newbie/deploy/yandex/monitoring 2>/dev/null && sudo docker compose up -d 2>&1 | tail -5
  sleep 15
  sudo docker ps --format '{{.Names}}: {{.Status}}' | sort
fi
echo
echo "=== 3. пересборка jami-services ==="
cd /opt/jami-services
sudo docker compose up -d --build 2>&1 | tail -25
sleep 25
sudo docker compose ps
echo
echo "=== 4. проверка сервисов ==="
for p in 8889 8890 8891 8892; do
  echo -n "  :$p -> "; curl -s -o /dev/null -w '%{http_code}\n' -m 6 "http://127.0.0.1:$p/" 2>/dev/null || echo "нет"
done
echo "=== 5. наружу ==="
for h in names.msp-claude.online invite.msp-claude.online push.msp-claude.online; do
  echo -n "  $h -> HTTP "; curl -s -o /dev/null -w '%{http_code}\n' -m 10 --resolve "$h:443:127.0.0.1" "https://$h/" 2>/dev/null
done
echo DONE
