#!/usr/bin/env bash
# ═══════════════════════════════════════════════════════════════════
# НАЗНАЧЕНИЕ (для junior): Собирает UI JAMS из согласованного стека MUI v5 (коммит ee62171~1).
# КОГДА ЗАПУСКАТЬ:         На ВМ от root, когда UI падает с 'theme.spacing is not a function'.
# КАК ЗАПУСКАТЬ:           sudo bash cloudru-jams-frontend-rollback.sh
# ПРОВЕРКА УСПЕХА:         Сборка exit 0; в node_modules РОВНО одна копия @mui/private-theming.
# ОТКАТ:                   git checkout ee62171 -- jams-react-client/ и пересобрать (вернуть сломанную версию).
# ═══════════════════════════════════════════════════════════════════
# ВЫВОД ПО АНАЛИЗУ: коммит JAMS ee621710 "update dependencies to latest" сломал UI
# (@mui/material -> v9 при @mui/styles v6; исходники завязаны на API v7+/v9).
# Он же — ПОСЛЕДНИЙ коммит в репозитории и трогал ТОЛЬКО jams-react-client/.
# => откатываем только фронтенд на ee62171~1 (согласованный стек v5), бэкенд не трогаем.
set -uo pipefail
export JAVA_HOME=/opt/jdk26
export PATH=/opt/jdk26/bin:/opt/maven/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
SRC=/opt/jams-src
FE=$SRC/jams-react-client

echo "=== 1. бэкап текущего фронта ==="
[ -d "$FE.broken-v9" ] || cp -r "$FE" "$FE.broken-v9" 2>/dev/null || true
echo "  бэкап: $FE.broken-v9"

echo "=== 2. откат jams-react-client на ee62171~1 ==="
cd "$SRC"
git checkout ee62171~1 -- jams-react-client/ 2>&1 && echo "  откат выполнен"
python3 -c "
import json
d=json.load(open('$FE/package.json'))
for k in ('dependencies','devDependencies'):
    for n,v in sorted(d.get(k,{}).items()):
        if 'mui' in n or n in ('react','react-dom'):
            print(f'  {n} = {v}')
"
git log -1 --format='  откат к: %h %ad %s' --date=short ee62171~1

echo "=== 3. чистая установка по родному lock-файлу ==="
cd "$FE"
rm -rf node_modules build
npm ci --legacy-peer-deps 2>&1 | tail -5
echo "--- версии после установки ---"
for p in @mui/material @mui/icons-material @mui/styles @mui/private-theming; do
  echo "  $p = $(python3 -c "import json;print(json.load(open('node_modules/$p/package.json'))['version'])" 2>/dev/null || echo '—')"
done
echo "  копий theming: $(find node_modules -maxdepth 4 -type d -path '*@mui/private-theming' | wc -l)"

echo "=== 4. сборка (React 17 + --openssl-legacy-provider) ==="
NODE_OPTIONS="--openssl-legacy-provider --max-old-space-size=3072" npx react-scripts build > /tmp/fe4.log 2>&1
RC=$?
echo "build exit: $RC"
if [ $RC -ne 0 ]; then
  grep -nE "error TS|Error|Cannot find|Failed to compile" /tmp/fe4.log | head -12
  tail -15 /tmp/fe4.log
  exit 4
fi
grep -E "Compiled|File sizes|main\." /tmp/fe4.log | head -6
ls -la build/static/js/main.*.js

echo "=== 5. копирую в webapp + maven ==="
WEB="$SRC/jams-server/src/main/resources/webapp"
rm -rf "$WEB"; mkdir -p "$WEB"
cp -r build/* "$WEB"/
ls "$WEB" | head -5
cd "$SRC"
/opt/maven/bin/mvn -q package -DskipTests 2>&1 | tail -4
ls -la "$SRC/jams/jams-server.jar"

echo "=== 6. деплой ==="
systemctl stop jams; sleep 3
cp "$SRC/jams/jams-server.jar" /opt/jams/jams-server.jar
chown -R jams:jams /opt/jams
rm -rf /opt/jams/tomcat.8080
systemctl start jams
sleep 45
echo -n "jams: "; systemctl is-active jams
echo -n "  /api/info: "; curl -s -m 8 http://127.0.0.1:8081/api/info; echo
echo -n "  бандл: "; curl -s -m 10 http://127.0.0.1:8081/ | grep -oE 'static/js/main\.[a-z0-9]+\.js' | head -1
echo ROLLBACK_BUILD_DONE
