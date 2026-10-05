#!/usr/bin/env bash
# Установка jami-daemon (always-online узел) + служба jamiserver.
set -uo pipefail
export DEBIAN_FRONTEND=noninteractive

echo "=== 1. репозиторий Jami ==="
apt-get install -y gnupg curl >/dev/null 2>&1 || true
if ! curl -fsSL https://dl.jami.net/stable/ubuntu_22.04/jami.gpg -o /usr/share/keyrings/jami.gpg; then
  echo "  тяну ключ с keyserver"
  gpg --keyserver keyserver.ubuntu.com --recv-keys 64CD5FA175348F84 2>&1 | tail -2
  gpg --export 64CD5FA175348F84 > /usr/share/keyrings/jami.gpg
fi
ls -la /usr/share/keyrings/jami.gpg 2>/dev/null
echo "deb [signed-by=/usr/share/keyrings/jami.gpg] https://dl.jami.net/stable/ubuntu_22.04/ jami main" >/etc/apt/sources.list.d/jami.list
cat /etc/apt/sources.list.d/jami.list

echo "=== 2. apt update (только этот репозиторий) ==="
apt-get update -o Dir::Etc::sourcelist="sources.list.d/jami.list" -o Dir::Etc::sourceparts="-" -o APT::Get::List-Cleanup="0" 2>&1 | tail -4

echo "=== 3. установка jami-daemon ==="
apt-get install -y jami-daemon 2>&1 | tail -6
echo "--- бинарники ---"
ls -la /usr/libexec/jamid 2>/dev/null || command -v jamid || echo "jamid не найден"
command -v dbus-launch || apt-get install -y dbus-x11 >/dev/null 2>&1
command -v dbus-launch && echo "dbus-launch OK"

echo "=== 4. пользователь и служба jamiserver ==="
id jamiserver >/dev/null 2>&1 || useradd -r -m -d /home/jamiserver -s /bin/bash jamiserver
mkdir -p /home/jamiserver/.local/share/jami && chown -R jamiserver:jamiserver /home/jamiserver

cat >/etc/systemd/system/jamiserver.service <<'EOS'
[Unit]
Description=Jami always-online daemon (jamiserver)
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=jamiserver
Group=jamiserver
WorkingDirectory=/home/jamiserver
# dbus-launch обязателен: демон Jami публикует API в сессионной шине D-Bus
ExecStart=/bin/bash -c 'exec dbus-launch --sh-syntax --exit-with-session /usr/libexec/jamid -p -d'
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOS
systemctl daemon-reload
systemctl enable --now jamiserver
sleep 15
echo -n "jamiserver: "; systemctl is-active jamiserver
echo "--- лог ---"
journalctl -u jamiserver -n 12 --no-pager 2>&1 | tail -12
echo "--- процессы ---"
pgrep -af jamid | head -3
echo JAMI_DAEMON_DONE
