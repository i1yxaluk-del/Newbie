#!/usr/bin/env bash
# Диагностика: почему Conversations не подключается.
# Ключевая гипотеза: в security group облака НЕ открыт порт 5222.
set -uo pipefail

echo "=== 1. видел ли Prosody ХОТЬ ОДНО подключение извне ==="
sudo docker logs msp-prosody 2>&1 | grep -E "Client connected|Moderating|c2s" | tail -10 | sed 's/^/  /'
echo "  --- все c2s-подключения с IP ---"
sudo docker logs msp-prosody 2>&1 | grep -oE "c2s[a-f0-9]+\s+info\s+Client connected" | wc -l | sed 's/^/  всего подключений: /'

echo
echo "=== 2. слушает ли Prosody на всех интерфейсах ==="
ss -lntp 2>/dev/null | grep 5222 | sed 's/^/  /'
sudo docker exec msp-prosody sh -c 'ss -lnt 2>/dev/null || netstat -lnt 2>/dev/null' | grep 5222 | sed 's/^/  в контейнере: /'

echo
echo "=== 3. доступен ли 5222 ИЗ ИНТЕРНЕТА (через публичный сервис) ==="
echo -n "  nmap-сервис: "
curl -s -m 25 "https://api.hackertarget.com/nmap/?q=45.132.176.143" 2>/dev/null | grep -iE "5222|open" | head -5 | tr '\n' ' '
echo
echo "  --- открытые порты по мнению сервиса ---"
curl -s -m 25 "https://api.hackertarget.com/nmap/?q=45.132.176.143" 2>/dev/null | head -20 | sed 's/^/  /'

echo
echo "=== 4. firewall на ВМ ==="
sudo ufw status 2>/dev/null | head -12 | sed 's/^/  /' || echo "  ufw нет"

echo
echo "=== 5. локальная проверка (не показательна для SG) ==="
timeout 6 bash -c "cat < /dev/null > /dev/tcp/45.132.176.143/5222" 2>/dev/null && echo "  локально на публичный IP: ок" || echo "  локально: нет"
echo DONE
