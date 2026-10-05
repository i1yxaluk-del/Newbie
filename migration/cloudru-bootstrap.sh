#!/usr/bin/env bash
# Bootstrap MSPShield VM на Cloud.ru Evolution (аналог deploy/yandex/cloud-init.yaml,
# но применяется ПОСЛЕ создания ВМ — через SSH, т.к. ВМ создана из чистого образа).
# Idempotent: можно запускать повторно.
set -uo pipefail
export DEBIAN_FRONTEND=noninteractive
log() { echo "[bootstrap $(date -u +%H:%M:%S)] $*"; }

log "=== 1. APT: форсируем IPv4 + базовые пакеты ==="
echo 'Acquire::ForceIPv4 "true";' > /etc/apt/apt.conf.d/99force-ipv4
apt-get update -y
apt-get install -y ca-certificates curl gnupg git jq ufw python3-pip python3-venv openssl unzip lsb-release

log "=== 2. Docker (официальный репозиторий) ==="
install -m 0755 -d /etc/apt/keyrings
if [ ! -f /etc/apt/keyrings/docker.asc ]; then
  curl -4fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc || log "WARN docker gpg"
  chmod a+r /etc/apt/keyrings/docker.asc
fi
echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/ubuntu jammy stable" \
  > /etc/apt/sources.list.d/docker.list

log "=== 3. Caddy (официальный репозиторий) ==="
if [ ! -f /usr/share/keyrings/caddy-stable-archive-keyring.gpg ]; then
  curl -4fsSL https://dl.cloudsmith.io/public/caddy/stable/gpg.key | gpg --dearmor -o /usr/share/keyrings/caddy-stable-archive-keyring.gpg || log "WARN caddy gpg"
fi
curl -4fsSL https://dl.cloudsmith.io/public/caddy/stable/debian.deb.txt > /etc/apt/sources.list.d/caddy-stable.list || log "WARN caddy list"

log "=== 4. NodeSource Node 20 ==="
if [ ! -f /etc/apt/keyrings/nodesource.gpg ]; then
  curl -4fsSL https://deb.nodesource.com/gpgkey/nodesource-repo.gpg.key | gpg --dearmor -o /etc/apt/keyrings/nodesource.gpg || log "WARN nodesource gpg"
fi
echo "deb [signed-by=/etc/apt/keyrings/nodesource.gpg] https://deb.nodesource.com/node_20.x nodistro main" \
  > /etc/apt/sources.list.d/nodesource.list

log "=== 5. apt update + установка ==="
apt-get update -y
apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin || log "ERROR docker install"
apt-get install -y caddy || log "ERROR caddy install"
apt-get install -y nodejs || log "ERROR nodejs install"
apt-get install -y restic || log "WARN restic install"

log "=== 6. Docker storage-driver overlay2 (нужно для cAdvisor) ==="
echo '{"storage-driver": "overlay2"}' > /etc/docker/daemon.json

log "=== 7. yarn через corepack ==="
corepack enable 2>/dev/null || true
corepack prepare yarn@stable --activate 2>/dev/null || true

log "=== 8. docker group ==="
usermod -aG docker ubuntu 2>/dev/null || true

log "=== 9. ufw ==="
ufw default deny incoming || true
ufw default allow outgoing || true
for r in "22/tcp" "80/tcp" "443/tcp" "443/udp" "465/tcp" "587/tcp" "143/tcp" "993/tcp" "4190/tcp" \
         "3478/tcp" "3478/udp" "5349/tcp" "5349/udp" "4222/tcp" "4222/udp"; do
  ufw allow "$r" || true
done
ufw allow 49160:49250/udp || true
ufw --force enable || true

log "=== 10. Каталог приложения ==="
mkdir -p /opt/msp
chown -R ubuntu:ubuntu /opt/msp

log "=== 11. Сервисы ==="
systemctl daemon-reload || true
systemctl enable --now docker || log "ERROR docker enable"
systemctl enable --now caddy || log "WARN caddy enable"

log "=== 12. Валидация ==="
miss=""
for b in docker caddy node curl git jq unzip python3; do
  command -v "$b" >/dev/null 2>&1 || miss="$miss $b"
done
if [ -n "$miss" ]; then
  log "BASE-VALIDATION FAILED: missing:$miss"
else
  log "BASE-VALIDATION OK: node=$(node -v) docker=$(docker --version)"
fi
docker compose version 2>/dev/null || log "WARN docker compose plugin missing"
echo "BOOTSTRAP_DONE"
