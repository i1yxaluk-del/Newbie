#!/usr/bin/env bash
# Сборка фронта JAMS (MUI v6) с учётом swap + пакет + деплой.
set -uo pipefail
export JAVA_HOME=/opt/jdk26
export PATH=/opt/jdk26/bin:/opt/maven/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
export NODE_OPTIONS="--openssl-legacy-provider --max-old-space-size=3072"
SRC=/opt/jams-src
FE=$SRC/jams-react-client

echo "=== память перед сборкой ==="
free -m

echo "=== сборка фронта (лог /tmp/fe3.log) ==="
cd "$FE"
rm -rf build
npx react-scripts build > /tmp/fe3.log 2>&1
RC=$?
echo "build exit: $RC"
if [ $RC -ne 0 ]; then
  echo "--- ошибки ---"
  grep -nE "Error|Cannot find|Failed to compile|heap" /tmp/fe3.log | head -10
  echo "--- хвост ---"
  tail -20 /tmp/fe3.log
  exit 4
fi
grep -E "Compiled|File sizes|main\." /tmp/fe3.log | head -8
ls -la build/static/js/main.*.js

echo "=== копирую в webapp ==="
WEB="$SRC/jams-server/src/main/resources/webapp"
rm -rf "$WEB"; mkdir -p "$WEB"
cp -r build/* "$WEB"/
ls "$WEB" | head -5

echo "=== maven package ==="
cd "$SRC"
/opt/maven/bin/mvn -q package -DskipTests 2>&1 | tail -4
ls -la "$SRC/jams/jams-server.jar"

echo "=== деплой ==="
systemctl stop jams; sleep 3
cp "$SRC/jams/jams-server.jar" /opt/jams/jams-server.jar
cp "$SRC/jams/jams-launcher.jar" /opt/jams/jams-launcher.jar 2>/dev/null || true
chown -R jams:jams /opt/jams
rm -rf /opt/jams/tomcat.8080
systemctl start jams
sleep 45
echo -n "jams: "; systemctl is-active jams
echo -n "  /api/info: "; curl -s -m 8 http://127.0.0.1:8081/api/info; echo
echo -n "  бандл: "; curl -s -m 10 http://127.0.0.1:8081/ | grep -oE 'static/js/main\.[a-z0-9]+\.js' | head -1
echo BUILD_DEPLOY_DONE
