#!/usr/bin/env bash
# ═══════════════════════════════════════════════════════════════════
# НАЗНАЧЕНИЕ (для junior): Закрывает SSH снаружи: пускает порт 22 только из подсети AmneziaWG 10.9.0.0/24.
# КОГДА ЗАПУСКАТЬ:         ТОЛЬКО после того как туннель поднят и SSH через 10.9.0.1 проверен.
# КАК ЗАПУСКАТЬ:           Запускать ЧЕРЕЗ ТУННЕЛЬ: sudo bash cloudru-ssh-lockdown-ufw.sh
# ПРОВЕРКА УСПЕХА:         Test-NetConnection <IP> -Port 22 -> False; ssh ubuntu@10.9.0.1 -> работает.
# ОТКАТ:                   ufw allow 22/tcp (вернуть доступ снаружи).
# ═══════════════════════════════════════════════════════════════════
# Закрывает SSH снаружи: ufw пускает 22 только из подсети AmneziaWG 10.9.0.0/24.
set -uo pipefail
echo "=== ufw ДО ==="
ufw status | grep -E '22|10\.9\.0' || true

echo "=== удаляю правило 22/tcp для всех ==="
ufw --force delete allow 22/tcp 2>&1 || echo "(правила не было)"

echo "=== гарантирую доступ из 10.9.0.0/24 ==="
ufw allow from 10.9.0.0/24 to any port 22 proto tcp comment 'SSH via AmneziaWG only' 2>&1 || true

echo "=== ufw ПОСЛЕ ==="
ufw status verbose | sed -n '1,25p'

echo "=== ss: слушает ли 22 (сервис не трогаем, доступ режет ufw/SG) ==="
ss -tlnp 2>/dev/null | grep ':22 ' || sudo ss -tlnp | grep ':22 '
echo DONE
