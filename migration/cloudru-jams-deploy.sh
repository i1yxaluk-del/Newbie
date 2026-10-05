#!/usr/bin/env bash
# Развёртывание JAMS: дистрибутив -> /opt/jams, служба с JDK 26 в JAVA_HOME и PATH.
set -uo pipefail

echo "=== 1. где задаётся порт ==="
grep -rn -E "server\.port|server-port|8080" /opt/jams-src/jams-server/src/main/resources/ 2>/dev/null | head -6
cat /opt/jams-src/java.properties 2>/dev/null | head -10
echo "--- дефолт в исходниках ---"
grep -rn -E "8080" /opt/jams-src/jams-server/src/main/java 2>/dev/null | head -5

echo "=== 2. пользователь и раскладка ==="
id jams >/dev/null 2>&1 || useradd -r -m -d /var/lib/jams -s /usr/sbin/nologin jams
mkdir -p /opt/jams
cp -r /opt/jams-src/jams/. /opt/jams/
chown -R jams:jams /opt/jams
ls -la /opt/jams | head -8

echo "=== 3. systemd unit (JDK 26 обязателен и в PATH!) ==="
cat >/etc/systemd/system/jams.service <<'EOF'
[Unit]
Description=JAMS (Jami Account Management Server)
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=jams
Group=jams
WorkingDirectory=/opt/jams
# ВАЖНО: лаунчер запускает дочернюю java из PATH. Без JDK 26 в PATH
# будет UnsupportedClassVersionError (class file 70.0 vs runtime 55.0).
Environment=JAVA_HOME=/opt/jdk26
Environment=PATH=/opt/jdk26/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
ExecStart=/opt/jdk26/bin/java -jar /opt/jams/jams-launcher.jar
Restart=on-failure
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF
systemctl daemon-reload
systemctl enable jams >/dev/null 2>&1
systemctl restart jams
echo "жду старт (40 с)…"
sleep 40
echo -n "jams: "; systemctl is-active jams
echo "--- порты ---"
ss -ltnp 2>/dev/null | grep -E ':808[0-9]' || echo "  8080/8081 не слушаются"
echo "--- /api/info ---"
for p in 8080 8081; do
  echo -n "  :$p -> "; curl -s -m 6 "http://127.0.0.1:$p/api/info"; echo
done
echo "--- лог ---"
journalctl -u jams -n 22 --no-pager 2>&1 | tail -22
echo DONE
