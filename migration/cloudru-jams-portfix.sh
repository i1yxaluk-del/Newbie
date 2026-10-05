#!/usr/bin/env bash
# JAMS на 8081: порт захардкожен в launcher/AppStarter.java -> правим и пересобираем.
set -uo pipefail
export JAVA_HOME=/opt/jdk26
export PATH=/opt/jdk26/bin:/opt/maven/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
SRC=/opt/jams-src
F="$SRC/jams-launcher/src/main/java/launcher/AppStarter.java"

echo "=== до правки ==="
grep -n 'jams-server.jar' "$F"

sed -i 's|ProcessBuilder("java", "-jar", "jams-server.jar", "8080")|ProcessBuilder("java", "-jar", "jams-server.jar", "8081")|' "$F"

echo "=== после правки ==="
grep -n 'jams-server.jar' "$F"

echo "=== пересборка ==="
cd "$SRC"
/opt/maven/bin/mvn -q package -DskipTests 2>&1 | tail -8
echo "--- артефакты ---"
ls -la "$SRC/jams-launcher/target/jams-launcher.jar" "$SRC/jams/jams-launcher.jar" 2>/dev/null
grep -c '8081' "$SRC/jams-launcher/src/main/java/launcher/AppStarter.java"

echo "=== подмена лаунчера в /opt/jams (состояние не трогаем) ==="
systemctl stop jams
sleep 3
cp "$SRC/jams/jams-launcher.jar" /opt/jams/jams-launcher.jar
chown jams:jams /opt/jams/jams-launcher.jar
rm -rf /opt/jams/tomcat.8080
systemctl reset-failed jams 2>/dev/null || true
systemctl start jams
echo "жду старт (45 с)…"
sleep 45
echo -n "jams: "; systemctl is-active jams
echo "--- порты ---"
ss -ltnp 2>/dev/null | grep -E ':(8080|8081)\b'
echo "--- /api/info ---"
echo -n "  :8081 -> "; curl -s -m 8 http://127.0.0.1:8081/api/info; echo
echo "--- лог ---"
journalctl -u jams -n 14 --no-pager 2>&1 | tail -14
echo DONE
