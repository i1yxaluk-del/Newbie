#!/usr/bin/env bash
set -uo pipefail
echo "=== параметры jamid ==="
/usr/libexec/jamid --help 2>&1 | head -20
echo
echo "=== запуск службы ==="
systemctl enable jamiserver >/dev/null 2>&1
systemctl restart jamiserver
sleep 25
echo -n "jamiserver: "; systemctl is-active jamiserver
echo "--- процессы ---"
pgrep -af jamid | head -3
echo "--- лог ---"
journalctl -u jamiserver -n 18 --no-pager 2>&1 | tail -18 | cut -c1-190
echo "--- D-Bus сессия ---"
sudo -u jamiserver bash -lc 'ls -la /home/jamiserver/.local/share/jami 2>/dev/null | head -8'
echo "--- порты демона ---"
ss -ltnp 2>/dev/null | grep jamid || echo "  (нет TCP-портов)"
echo DONE
