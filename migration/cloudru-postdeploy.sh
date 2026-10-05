#!/usr/bin/env bash
# Post-deploy: webroot из frontend/build + боевой Caddyfile с MSP_DOMAIN.
set -uo pipefail
REPO=/opt/msp/Newbie
DEPLOY=$REPO/deploy/yandex
DOMAIN="${MSP_DOMAIN:-msp-claude.online}"

echo "=== webroot ==="
sudo mkdir -p /var/www/landing
if [ -d "$REPO/frontend/build" ]; then
  sudo rm -rf /var/www/landing/*
  sudo cp -r "$REPO/frontend/build/." /var/www/landing/
  sudo chown -R caddy:caddy /var/www/landing
  if [ -s /var/www/landing/index.html ]; then
    echo "webroot OK ($(du -sh /var/www/landing | cut -f1))"
  else
    echo "ERROR: /var/www/landing/index.html пуст"
  fi
else
  echo "WARN: $REPO/frontend/build отсутствует — фронт не собран"
fi

echo "=== Caddyfile ==="
sudo install -m 0644 "$DEPLOY/Caddyfile" /etc/caddy/Caddyfile
sudo sed -i "s/{\$MSP_DOMAIN}/$DOMAIN/g" /etc/caddy/Caddyfile
if grep -q '{\$MSP_DOMAIN}' /etc/caddy/Caddyfile; then
  echo "ERROR: в Caddyfile остался плейсхолдер"; exit 1
fi
sudo mkdir -p /etc/systemd/system/caddy.service.d
sudo tee /etc/systemd/system/caddy.service.d/override.conf >/dev/null <<EOF
[Service]
Environment="MSP_DOMAIN=$DOMAIN"
EOF
sudo systemctl daemon-reload
if sudo caddy validate --config /etc/caddy/Caddyfile --adapter caddyfile 2>&1 | tail -3; then
  echo "CADDY_CONFIG_OK"
else
  echo "ERROR: Caddyfile невалиден"; exit 1
fi
echo "WEBROOT_CADDY_DONE"
