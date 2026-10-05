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

echo
echo "=== 2. dhtnode: параметры и прокси ==="
dhtnode -h 2>&1 | head -25 || dhtnode --help 2>&1 | head -25
echo "--- перезапуск ---"
systemctl restart dhtnode
sleep 10
echo -n "dhtnode: "; systemctl is-active dhtnode
echo "--- порты ---"
ss -lunp 2>/dev/null | grep ':4222' | head -2
ss -ltnp 2>/dev/null | grep ':8888' | head -2 || echo "  8888 (REST proxy) не слушается"
echo "--- REST ---"
curl -s -m 8 http://127.0.0.1:8888/ | head -c 300; echo
echo "--- лог dhtnode ---"
journalctl -u dhtnode -n 10 --no-pager 2>&1 | tail -10
echo DONE
