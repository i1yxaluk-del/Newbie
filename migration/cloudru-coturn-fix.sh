#!/usr/bin/env bash
set -uo pipefail
echo "=== 1. coturn: убираю взаимоисключающие no-*-relay ==="
sed -i '/^no-udp-relay$/d; /^no-tcp-relay$/d' /etc/turnserver.conf
cat >>/etc/turnserver.conf <<'EOF'
no-multicast-peers
stale-nonce
EOF
grep -vE '^\s*#|^\s*$' /etc/turnserver.conf > /tmp/turnserver.filtered; cp /tmp/turnserver.filtered /etc/turnserver.conf
systemctl reset-failed coturn 2>/dev/null || true
systemctl restart coturn
sleep 4
echo -n "coturn: "; systemctl is-active coturn
ss -lunp 2>/dev/null | grep -E ':3478|:5349' | head -4
ss -ltnp 2>/dev/null | grep -E ':3478|:5349' | head -4
echo "--- лог (последнее) ---"
journalctl -u coturn -n 6 --no-pager 2>&1 | tail -6

echo DONE
