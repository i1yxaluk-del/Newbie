#!/usr/bin/env bash
# Cloud.ru Evolution: ВМ имеет 2 интерфейса — enp3s0 (внутренний, 10.0.0.6) и
# enp8s0 (direct-IP, 45.132.176.143). Оба получают default-маршрут с metric 100,
# из-за чего ответные пакеты (в т.ч. от docker-контейнеров) уходят через enp3s0
# с чужим source-IP → соединения рвутся.
#
# Решение: добавить в ОСНОВНУЮ таблицу default через enp8s0 с metric 50 (приоритетнее).
# Внутренние маршруты (docker-бриджи, 10.0.0.0/24) остаются в основной таблице,
# поэтому связь host<->контейнер не страдает.
set -uo pipefail

sudo tee /etc/systemd/system/msp-policy-route.service >/dev/null <<'EOF'
[Unit]
Description=MSP: prefer direct-IP interface as default route (Cloud.ru)
After=network-online.target
Wants=network-online.target

[Service]
Type=oneshot
RemainAfterExit=yes
ExecStart=/bin/bash -c 'ip route replace default via 45.132.176.1 dev enp8s0 metric 50'

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable msp-policy-route.service 2>&1 | tail -1
sudo systemctl restart msp-policy-route.service

echo "=== default routes ==="
ip route show default
echo "=== rules ==="
ip rule show
echo "=== local checks ==="
echo -n "backend: "; curl -sS -m 6 http://127.0.0.1:8001/api/health; echo
echo -n "grafana: "; curl -sS -m 6 -o /dev/null -w '%{http_code}\n' http://127.0.0.1:3000/login
echo -n "vault:   "; curl -sS -m 6 -o /dev/null -w '%{http_code}\n' http://127.0.0.1:8180/
echo "FIX_ROUTING_DONE"
