#!/usr/bin/env bash
# Установка AmneziaWG на новую ВМ Cloud.ru (аналог шага cloud-init).
set -uo pipefail
export DEBIAN_FRONTEND=noninteractive
echo "=== 1. software-properties-common ==="
apt-get install -y software-properties-common >/dev/null 2>&1 || echo "warn spc"

echo "=== 2. PPA ppa:amnezia/ppa ==="
add-apt-repository -y ppa:amnezia/ppa 2>&1 | tail -3 || echo "PPA FAILED"
apt-get update -y >/dev/null 2>&1 || echo "apt update warn"

echo "=== 3. пакеты amneziawg ==="
apt-get install -y amneziawg-dkms amneziawg-tools qrencode 2>&1 | tail -6 || echo "INSTALL FAILED"

echo "=== 4. проверка ==="
command -v awg && awg --version || echo "awg NOT FOUND"
lsmod | grep -i amnezia || echo "(модуль не загружен — проверим dkms)"
dkms status 2>/dev/null | head -5

echo "=== 5. ip_forward ==="
echo 'net.ipv4.ip_forward=1' > /etc/sysctl.d/99-awg.conf
sysctl -w net.ipv4.ip_forward=1
echo AWG_INSTALL_DONE
