#!/usr/bin/env bash
# Инвентаризация секретов на ВМ: только ИМЕНА переменных, без значений.
echo "=== файлы секретов на ВМ ==="
for f in /home/ubuntu/msp-deploy-secrets.txt /root/.postmaster-pass /etc/restic/env.sh; do
  if sudo test -f "$f"; then echo "--- $f ---"; sudo grep -oE '^[A-Za-z_][A-Za-z0-9_]*' "$f" 2>/dev/null | sort -u | head -30; fi
done
echo
echo "=== /opt/msp/Newbie: env-файлы ==="
sudo find /opt/msp/Newbie -maxdepth 3 \( -name "*.env" -o -name ".env" -o -name "*.env.bak" -o -name "env.sh" \) 2>/dev/null | head -20
echo
echo "=== имена переменных в каждом env-файле ==="
for f in $(sudo find /opt/msp/Newbie -maxdepth 3 \( -name "*.env" -o -name ".env" -o -name "*.env.bak" \) 2>/dev/null | head -10); do
  echo "--- $f ---"
  sudo grep -oE '^[A-Za-z_][A-Za-z0-9_]*=' "$f" 2>/dev/null | tr -d '=' | sort -u | tr '\n' ' '
  echo
done
echo
echo "=== контейнеры: сервисы ==="
sudo docker ps --format '{{.Names}}' | sort
echo DONE
