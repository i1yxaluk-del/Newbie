#!/usr/bin/env bash
# coturn (TURN/STUN) — синхронизация сертификата из Caddy.
set -uo pipefail
export DEBIAN_FRONTEND=noninteractive
EXT_IP=45.132.176.143
DOMAIN=turn.msp-claude.online

echo "=== 1. пакеты ==="
apt-get install -y coturn >/dev/null 2>&1 || echo "warn apt"
command -v turnserver && turnserver --version 2>&1 | head -1

echo "=== 2. coturn: включение службы ==="
sed -i 's/^#*TURNSERVER_ENABLED=.*/TURNSERVER_ENABLED=1/' /etc/default/coturn
grep TURNSERVER_ENABLED /etc/default/coturn

echo "=== 3. пароль TURN-пользователя ==="
if sudo test -f /root/.turn-pass; then
  TURN_PASS=$(sudo cat /root/.turn-pass | cut -d= -f2-)
  echo "пароль уже есть"
else
  TURN_PASS=$(head -c 24 /dev/urandom | base64 | tr -d '/+=' | head -c 24)
  echo "TURN_PASSWORD=$TURN_PASS" | sudo tee /root/.turn-pass >/dev/null
  sudo chmod 600 /root/.turn-pass
  echo "пароль сгенерирован"
fi

echo "=== 4. /etc/turnserver.conf ==="
cat >/etc/turnserver.conf <<EOF
# MSPShield TURN (coturn)
listening-port=3478
tls-listening-port=5349
fingerprint
realm=${DOMAIN}
server-name=${DOMAIN}
external-ip=${EXT_IP}
min-port=49160
max-port=49199
cert=/etc/turn/turn.pem
pkey=/etc/turn/turn.pem
no-cli
no-tlsv1
no-tlsv1_1
no-udp-relay
no-tcp-relay
EOF
grep -E 'realm|external-ip|min-port|cert=' /etc/turnserver.conf

echo "=== 5. синхронизация сертификата из Caddy ==="
cat >/usr/local/bin/coturn-cert-sync.sh <<'EOS'
#!/usr/bin/env bash
# Копирует сертификат turn.<domain> из хранилища Caddy в coturn; рестарт только при изменении.
set -uo pipefail
SRC=$(ls -d /var/lib/caddy/.local/share/caddy/certificates/*/turn.msp-claude.online 2>/dev/null | head -1)
[ -z "$SRC" ] && { echo "cert not found"; exit 1; }
mkdir -p /etc/turn
cat "$SRC/turn.msp-claude.online.crt" "$SRC/turn.msp-claude.online.key" > /tmp/turn-full.pem
if ! cmp -s /tmp/turn-full.pem /etc/turn/turn.pem 2>/dev/null; then
  cp /tmp/turn-full.pem /etc/turn/turn.pem
  chmod 640 /etc/turn/turn.pem
  chgrp turnserver /etc/turn/turn.pem 2>/dev/null || true
  systemctl restart coturn
  echo "cert updated + coturn restarted"
else
  echo "cert unchanged"
fi
EOS
chmod 755 /usr/local/bin/coturn-cert-sync.sh
/usr/local/bin/coturn-cert-sync.sh

systemctl enable coturn >/dev/null 2>&1
systemctl restart coturn
sleep 3
systemctl is-active coturn
ss -lunp 2>/dev/null | grep -E ':3478|:5349' | head -4

echo "=== 6. cron для cert-sync ==="
( crontab -l 2>/dev/null | grep -v coturn-cert-sync; echo "30 4 * * * /usr/local/bin/coturn-cert-sync.sh >/dev/null 2>&1" ) | crontab -
crontab -l | tail -2

echo DONE
