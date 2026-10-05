#!/usr/bin/env bash
set -uo pipefail
echo "=== есть ли dbus-run-session ==="
command -v dbus-run-session || apt-get install -y dbus >/dev/null 2>&1
command -v dbus-run-session && echo OK

echo "=== новый unit через dbus-run-session ==="
systemctl stop jamiserver 2>/dev/null || true
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
Environment=HOME=/home/jamiserver
# dbus-run-session создаёт сессионную шину: без неё jamid завершается
# ("Manager accessed before initialization"). -p = оставаться живым.
ExecStart=/usr/bin/dbus-run-session -- /usr/libexec/jamid -p
Restart=on-failure
RestartSec=15

[Install]
WantedBy=multi-user.target
EOS
systemctl daemon-reload
systemctl restart jamiserver
sleep 30
echo -n "jamiserver: "; systemctl is-active jamiserver
echo "--- процессы ---"
pgrep -af "jamid" | head -4
echo "--- лог (последнее) ---"
journalctl -u jamiserver -n 14 --no-pager 2>&1 | tail -14 | cut -c1-180
echo "--- D-Bus адрес процесса ---"
PID=$(pgrep -f '/usr/libexec/jamid' | head -1)
if [ -n "$PID" ]; then
  echo "  pid=$PID"
  tr '\0' '\n' < /proc/$PID/environ 2>/dev/null | grep -i dbus | head -3
fi
echo DONE
