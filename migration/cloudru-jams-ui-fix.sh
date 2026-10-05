#!/usr/bin/env bash
# Фикс UI JAMS: @mui/styles@6 тянул свою копию @mui/private-theming@6 ->
# ThemeProvider и makeStyles оказывались в разных React-контекстах.
# Принудительно оставляем одну копию theming (9.3.0) и пересобираем.
set -uo pipefail
export JAVA_HOME=/opt/jdk26
export PATH=/opt/jdk26/bin:/opt/maven/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
export NODE_OPTIONS=--openssl-legacy-provider
FE=/opt/jams-src/jams-react-client
SRC=/opt/jams-src

echo "=== 1. overrides в package.json ==="
python3 - <<'PY'
import json
p = "/opt/jams-src/jams-react-client/package.json"
d = json.load(open(p))
ov = d.setdefault("overrides", {})
ov["@mui/styles"] = {"@mui/private-theming": "9.3.0"}
ov["@mui/private-theming"] = "9.3.0"
json.dump(d, open(p, "w"), indent=2)
print(json.dumps(ov, indent=2))
PY

echo "=== 2. npm install (применяем override) ==="
cd "$FE"
npm install --legacy-peer-deps 2>&1 | tail -6
echo "--- копии @mui/private-theming ---"
find node_modules -maxdepth 4 -type d -path "*@mui/private-theming" 2>/dev/null | while read -r p; do
  v=$(python3 -c "import json;print(json.load(open('$p/package.json'))['version'])" 2>/dev/null)
  echo "  $p -> $v"
done

echo "=== 3. сборка фронта ==="
npm run build 2>&1 | tail -10
WEB="$SRC/jams-server/src/main/resources/webapp"
mkdir -p "$WEB"
if [ -d build ]; then cp -r build/* "$WEB"/; fi
ls "$WEB" 2>/dev/null | head -6

echo "=== 4. maven package ==="
cd "$SRC"
/opt/maven/bin/mvn -q package -DskipTests 2>&1 | tail -6
ls -la "$SRC/jams/jams-server.jar" 2>/dev/null

echo "=== 5. деплой (состояние JAMS не трогаем) ==="
systemctl stop jams; sleep 3
cp "$SRC/jams/jams-server.jar" /opt/jams/jams-server.jar
cp "$SRC/jams/jams-launcher.jar" /opt/jams/jams-launcher.jar
chown -R jams:jams /opt/jams
rm -rf /opt/jams/tomcat.8080
systemctl start jams
sleep 45
echo -n "jams: "; systemctl is-active jams
curl -s -m 8 http://127.0.0.1:8081/api/info; echo
echo REBUILD_DONE
