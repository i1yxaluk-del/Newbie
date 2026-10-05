#!/usr/bin/env bash
# Правильный подход: НЕ удалять package-lock.json (в нём рабочая комбинация
# транзитивных зависимостей). Меняем только диапазоны MUI в package.json
# и даём npm обновить залоченное минимально.
set -uo pipefail
export JAVA_HOME=/opt/jdk26
export PATH=/opt/jdk26/bin:/opt/maven/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
export NODE_OPTIONS="--openssl-legacy-provider --max-old-space-size=3072"
SRC=/opt/jams-src
FE=$SRC/jams-react-client

echo "=== 1. восстанавливаю package-lock.json из git ==="
cd "$SRC"
git checkout -- jams-react-client/package-lock.json 2>&1 && echo "  lock восстановлен"
git status --short jams-react-client/package.json jams-react-client/package-lock.json

echo "=== 2. что в package.json сейчас ==="
python3 -c "
import json; d=json.load(open('$FE/package.json'))
print('  @mui/material      =', d['dependencies'].get('@mui/material'))
print('  @mui/icons-material=', d['dependencies'].get('@mui/icons-material'))
print('  @mui/styles        =', d.get('devDependencies',{}).get('@mui/styles'))
print('  overrides          =', d.get('overrides'))
"

echo "=== 3. npm install (минимальное обновление по lock) ==="
cd "$FE"
rm -rf node_modules
npm install --legacy-peer-deps 2>&1 | tail -6
echo "--- версии ---"
for p in @mui/material @mui/icons-material @mui/styles @mui/system @mui/private-theming @mui/utils ajv ajv-keywords; do
  echo "  $p = $(python3 -c "import json;print(json.load(open('node_modules/$p/package.json'))['version'])" 2>/dev/null || echo '—')"
done
find node_modules -maxdepth 4 -type d -path "*@mui/private-theming" 2>/dev/null | sed 's/^/    theming: /'

echo "=== 4. сборка фронта ==="
rm -rf build
npx react-scripts build > /tmp/fe2.log 2>&1
echo "exit: $?"
grep -nE "Error|Cannot find|Compiled|Failed to compile" /tmp/fe2.log | head -10
ls -la build/static/js/main.*.js 2>/dev/null || { echo "НЕ СОБРАЛОСЬ — хвост лога:"; tail -15 /tmp/fe2.log; exit 4; }

echo "=== 5. копирую в webapp + maven ==="
WEB="$SRC/jams-server/src/main/resources/webapp"
rm -rf "$WEB"; mkdir -p "$WEB"
cp -r build/* "$WEB"/
ls "$WEB" | head -5
cd "$SRC"
/opt/maven/bin/mvn -q package -DskipTests 2>&1 | tail -5
ls -la "$SRC/jams/jams-server.jar"

echo "=== 6. деплой ==="
systemctl stop jams; sleep 3
cp "$SRC/jams/jams-server.jar" /opt/jams/jams-server.jar
cp "$SRC/jams/jams-launcher.jar" /opt/jams/jams-launcher.jar
chown -R jams:jams /opt/jams
rm -rf /opt/jams/tomcat.8080
systemctl start jams
sleep 45
echo -n "jams: "; systemctl is-active jams
curl -s -m 8 http://127.0.0.1:8081/api/info; echo
echo -n "  бандл: "; curl -s -m 10 http://127.0.0.1:8081/ | grep -oE 'static/js/main\.[a-z0-9]+\.js' | head -1
echo MUI_V6_OK
