#!/bin/sh
# Точка входа контейнера Prosody.
#
# Зачем так: Prosody ОТКАЗЫВАЕТСЯ запускаться под root (встроенная защита,
# в логе «Danger, Will Robinson! Prosody doesn't need to be run as root»,
# выход с кодом 1 → контейнер уходит в рестарт). Поэтому:
#   1) под root готовим каталоги и права;
#   2) затем СБРАСЫВАЕМ права на пользователя prosody (setpriv);
#   3) запускаем Prosody в переднем плане (-F), чтобы Docker видел процесс.
set -e

mkdir -p /var/lib/prosody /var/log/prosody /var/run/prosody /var/lib/prosody/http_upload
chown -R prosody:prosody /var/lib/prosody /var/log/prosody /var/run/prosody

if [ -d /etc/prosody/certs ]; then
    chmod 755 /etc/prosody/certs
    chmod 644 /etc/prosody/certs/*.crt 2>/dev/null || true
    chmod 640 /etc/prosody/certs/*.key 2>/dev/null || true
    chown -R prosody:prosody /etc/prosody/certs 2>/dev/null || true
fi

exec setpriv --reuid=prosody --regid=prosody --init-groups \
     prosody -F --config /etc/prosody/prosody.cfg.lua
