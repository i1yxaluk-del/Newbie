#!/usr/bin/env bash
set -uo pipefail
B=http://127.0.0.1:8081
echo "=== 1. какой бандл отдаётся и грузится ==="
IDX=$(curl -s -m 10 "$B/")
JS=$(echo "$IDX" | grep -oE 'static/js/main\.[a-z0-9]+\.js' | head -1)
echo "  бандл: $JS"
echo -n "  HTTP бандла: "; curl -s -o /tmp/b2.js -w '%{http_code}' -m 25 "$B/$JS"; echo
echo "  размер: $(wc -c </tmp/b2.js) байт"
echo
echo "=== 2. собирался ли бандл с ОДНОЙ копией темы ==="
echo "  (косвенно: в дереве одна копия @mui/private-theming)"
find /opt/jams-src/jams-react-client/node_modules -maxdepth 4 -type d -path "*@mui/private-theming" | sed 's/^/    /'
echo "  версии:"
for p in @mui/material @mui/styles @mui/private-theming; do
  echo "    $p = $(python3 -c "import json;print(json.load(open('/opt/jams-src/jams-react-client/node_modules/$p/package.json'))['version'])" 2>/dev/null)"
done
echo
echo "=== 3. коды ответов ==="
for u in "/" "/signin" "/signup" "/api/info"; do
  printf "  %-14s -> %s\n" "$u" "$(curl -s -o /dev/null -w '%{http_code}' -m 10 "$B$u")"
done
echo
echo "=== 4. наружу через Caddy ==="
for h in "/" "/signin" "/signup" "/api/info"; do
  printf "  m.msp-claude.online%-10s -> %s\n" "$h" "$(curl -s -o /dev/null -w '%{http_code}' -m 12 --resolve m.msp-claude.online:443:127.0.0.1 "https://m.msp-claude.online$h")"
done
echo
echo "=== 5. логин ==="
ENV=/opt/jami-services/.env
JUSER=$(grep '^JAMS_ADMIN_USER=' "$ENV" | cut -d= -f2-)
JPASS=$(grep '^JAMS_ADMIN_PASSWORD=' "$ENV" | cut -d= -f2-)
curl -s -o /dev/null -w '  POST /api/login -> %{http_code}\n' -m 15 -X POST "$B/api/login" \
  -H 'Content-Type: application/json' -d "{\"username\":\"$JUSER\",\"password\":\"$JPASS\"}"
echo
echo "=== 6. ошибки в логе JAMS после деплоя ==="
journalctl -u jams --since "3 min ago" --no-pager 2>/dev/null | grep -iE "error|exception" | tail -5 || echo "  ошибок нет"
echo DONE
