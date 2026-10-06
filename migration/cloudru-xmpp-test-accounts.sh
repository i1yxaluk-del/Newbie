#!/usr/bin/env bash
# Создание второго тестового XMPP-аккаунта и проверка состояния сервера.
set -uo pipefail
echo "=== 1. создаю test2 ==="
sudo docker exec -u prosody msp-prosody prosodyctl register test2 x.msp-claude.online 'TestPass456' 2>&1 | tail -2

echo
echo "=== 2. список учёток ==="
sudo docker exec -u prosody msp-prosody sh -c 'ls /var/lib/prosody/x.msp-claude.online/accounts/ 2>/dev/null' | sed 's/\.dat$//' | sed 's/^/  /'

echo
echo "=== 3. ошибки загрузки модулей (должно быть 0) ==="
sudo docker logs msp-prosody 2>&1 | grep -c "Unable to load" | sed 's/^/  /'

echo
echo "=== 4. какие модули реально активны ==="
sudo docker logs msp-prosody 2>&1 | grep -oE "Moderating|Activated service '[a-z_]+'" | sort -u | head -10 | sed 's/^/  /'
sudo docker exec -u prosody msp-prosody sh -c 'grep -oE "mod_[a-z_]+" /var/log/prosody/prosody.log 2>/dev/null | sort -u | head -20' | sed 's/^/  /'

echo
echo "=== 5. ресурсы ==="
sudo docker stats --no-stream --format '{{.Name}}: {{.MemUsage}} (CPU {{.CPUPerc}})' msp-prosody
free -m | head -2 | sed 's/^/  /'
df -h / | tail -1 | sed 's/^/  /'

echo
echo "=== 6. доступность ==="
echo -n "  XMPP 5222 снаружи: "
timeout 8 bash -c "cat < /dev/null > /dev/tcp/45.132.176.143/5222" 2>/dev/null && echo да || echo НЕТ
echo -n "  https://x.msp-claude.online/ -> "
curl -s -o /dev/null -w '%{http_code}\n' -m 10 https://x.msp-claude.online/
echo -n "  STARTTLS-проверка: "
timeout 10 openssl s_client -connect 127.0.0.1:5222 -starttls xmpp -servername x.msp-claude.online </dev/null 2>/dev/null \
  | grep -E "subject=|Verify return code" | head -2 | tr '\n' ' ' | sed 's/^/  /'
echo
echo XMPP_READY
