#!/usr/bin/env bash
set -uo pipefail
echo "=== 1. диагностика маршрутизации ==="
echo "--- msp-policy-route ---"
systemctl status msp-policy-route --no-pager 2>&1 | head -12
echo "--- unit ---"
cat /etc/systemd/system/msp-policy-route.service 2>/dev/null
echo "--- маршруты ---"
ip route
echo "--- ip route get 8.8.8.8 ---"
ip route get 8.8.8.8

echo
echo "=== 2. чиню msp-policy-route (ждём интерфейс и шлюз) ==="
cat >/etc/systemd/system/msp-policy-route.service <<'EOS'
[Unit]
Description=MSPShield: приоритетный default-маршрут через direct-IP интерфейс
# Интерфейс enp8s0 и шлюз появляются не мгновенно — ждём сеть и повторяем.
After=network-online.target
Wants=network-online.target
StartLimitIntervalSec=0

[Service]
Type=oneshot
RemainAfterExit=yes
ExecStartPre=/bin/bash -c 'for i in $(seq 1 60); do ip -4 addr show dev enp8s0 2>/dev/null | grep -q "inet " && exit 0; sleep 2; done; exit 1'
ExecStart=/bin/bash -c 'GW=$(ip route | awk "/^default/ && /enp8s0/ {print \$3; exit}"); [ -z "$GW" ] && GW=$(ip -4 addr show dev enp8s0 | awk "/inet /{split(\$2,a,\"/\"); split(a[1],b,\".\"); print b[1]\".\"b[2]\".\"b[3]\".1\"; exit}"); ip route replace default via "$GW" dev enp8s0 metric 50'
Restart=on-failure
RestartSec=10

[Install]
WantedBy=multi-user.target
EOS
systemctl daemon-reload
systemctl reset-failed msp-policy-route 2>/dev/null || true
systemctl enable msp-policy-route >/dev/null 2>&1
systemctl start msp-policy-route
sleep 3
echo -n "  статус: "; systemctl is-active msp-policy-route
echo "  маршрут сейчас:"
ip route | grep '^default'
echo "  ip route get 8.8.8.8:"
ip route get 8.8.8.8 | head -1

echo
echo "=== 3. добавляю swap 4G (без него webpack-сборка задыхается) ==="
if swapon --show 2>/dev/null | grep -q .; then
  echo "  swap уже есть:"; swapon --show
else
  if fallocate -l 4G /swapfile 2>/dev/null || dd if=/dev/zero of=/swapfile bs=1M count=4096 status=none; then
    chmod 600 /swapfile
    mkswap /swapfile >/dev/null
    swapon /swapfile
    grep -q '^/swapfile' /etc/fstab || echo '/swapfile none swap sw 0 0' >>/etc/fstab
    echo 'vm.swappiness=10' >/etc/sysctl.d/99-swap.conf
    sysctl -w vm.swappiness=10 >/dev/null
    echo "  swap создан"
  else
    echo "  НЕ УДАЛОСЬ создать swap"
  fi
fi
echo "--- память после ---"
free -m
echo DONE
