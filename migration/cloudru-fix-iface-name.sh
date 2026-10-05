#!/usr/bin/env bash
# Имя direct-IP интерфейса НЕ стабильно между перезагрузками (enp8s0 -> enp4s0),
# поэтому определяем его по публичному IP, а не хардкодим.
set -uo pipefail
PUB_IP=45.132.176.143

echo "=== 1. скрипт определения интерфейса ==="
cat >/usr/local/bin/msp-policy-route.sh <<'EOS'
#!/usr/bin/env bash
# Приоритетный default-маршрут через интерфейс, на котором лежит публичный IP.
# Имя интерфейса может меняться после перезагрузки (enp8s0/enp4s0/...), поэтому
# ищем по адресу, а не по имени.
set -euo pipefail
PUB_IP="${PUB_IP:-45.132.176.143}"
IFACE=""
for _ in $(seq 1 60); do
  IFACE=$(ip -4 -o addr show | awk -v ip="$PUB_IP" 'index($4, ip"/")==1 {print $2; exit}')
  [ -n "$IFACE" ] && break
  sleep 2
done
if [ -z "$IFACE" ]; then echo "интерфейс с $PUB_IP не найден"; exit 1; fi
GW=$(ip route | awk -v i="$IFACE" '$1=="default" && $5==i {print $3; exit}')
if [ -z "$GW" ]; then echo "шлюз для $IFACE не найден"; exit 1; fi
ip route replace default via "$GW" dev "$IFACE" metric 50
echo "default via $GW dev $IFACE metric 50"
EOS
chmod 755 /usr/local/bin/msp-policy-route.sh

echo "=== 2. unit ==="
cat >/etc/systemd/system/msp-policy-route.service <<'EOS'
[Unit]
Description=MSPShield: приоритетный default через интерфейс с публичным IP (Cloud.ru)
After=network-online.target
Wants=network-online.target

[Service]
Type=oneshot
RemainAfterExit=yes
ExecStart=/usr/local/bin/msp-policy-route.sh
Restart=on-failure
RestartSec=10

[Install]
WantedBy=multi-user.target
EOS
systemctl daemon-reload
systemctl reset-failed msp-policy-route 2>/dev/null || true
systemctl enable msp-policy-route >/dev/null 2>&1
systemctl restart msp-policy-route
sleep 4
echo -n "  статус: "; systemctl is-active msp-policy-route
echo "  вывод скрипта: $(/usr/local/bin/msp-policy-route.sh 2>&1)"
echo "  default-маршруты:"; ip route | grep '^default' | sed 's/^/    /'
echo "  ip route get 8.8.8.8 -> $(ip route get 8.8.8.8 | head -1)"

echo
echo "=== 3. AWG: PostUp тоже ссылается на имя интерфейса — чиню ==="
grep -nE "PostUp|PostDown" /etc/amnezia/amneziawg/awg0.conf | head -4
python3 - <<'PY'
import re, subprocess
p = "/etc/amnezia/amneziawg/awg0.conf"
s = open(p).read()
new_up = "PostUp   = /usr/local/bin/msp-awg-nat.sh add"
new_down = "PostDown = /usr/local/bin/msp-awg-nat.sh del"
lines = []
for line in s.splitlines():
    if line.startswith("PostUp"):
        lines.append(new_up)
    elif line.startswith("PostDown"):
        lines.append(new_down)
    else:
        lines.append(line)
open(p, "w").write("\n".join(lines) + "\n")
print("  PostUp/PostDown заменены на скрипт")
PY
cat >/usr/local/bin/msp-awg-nat.sh <<'EOS'
#!/usr/bin/env bash
# NAT для клиентов AmneziaWG. Интерфейс выхода определяем по публичному IP.
set -euo pipefail
ACTION="${1:-add}"
PUB_IP="${PUB_IP:-45.132.176.143}"
IFACE=$(ip -4 -o addr show | awk -v ip="$PUB_IP" 'index($4, ip"/")==1 {print $2; exit}')
[ -z "$IFACE" ] && exit 0
if [ "$ACTION" = "add" ]; then
  iptables -C FORWARD -i awg0 -j ACCEPT 2>/dev/null || iptables -A FORWARD -i awg0 -j ACCEPT
  iptables -C FORWARD -o awg0 -j ACCEPT 2>/dev/null || iptables -A FORWARD -o awg0 -j ACCEPT
  iptables -t nat -C POSTROUTING -o "$IFACE" -j MASQUERADE 2>/dev/null || iptables -t nat -A POSTROUTING -o "$IFACE" -j MASQUERADE
else
  iptables -D FORWARD -i awg0 -j ACCEPT 2>/dev/null || true
  iptables -D FORWARD -o awg0 -j ACCEPT 2>/dev/null || true
  for i in $(ip -o link show | awk -F': ' '{print $2}' | grep -E '^enp'); do
    iptables -t nat -D POSTROUTING -o "$i" -j MASQUERADE 2>/dev/null || true
  done
fi
EOS
chmod 755 /usr/local/bin/msp-awg-nat.sh
sed -n '/PostUp/,/PostDown/p' /etc/amnezia/amneziawg/awg0.conf
systemctl restart awg-quick@awg0
sleep 5
echo -n "  awg-quick@awg0: "; systemctl is-active awg-quick@awg0
awg show 2>/dev/null | head -3
echo "  NAT-правило: $(iptables -t nat -S POSTROUTING 2>/dev/null | grep MASQUERADE | head -2)"
echo DONE
