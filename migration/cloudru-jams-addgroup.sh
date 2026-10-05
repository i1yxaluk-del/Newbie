#!/usr/bin/env bash
set -uo pipefail
ENV=/opt/jami-services/.env
JUSER=$(grep '^JAMS_ADMIN_USER=' "$ENV" | cut -d= -f2-)
JPASS=$(grep '^JAMS_ADMIN_PASSWORD=' "$ENV" | cut -d= -f2-)
B=http://127.0.0.1:8081
CT='Content-Type: application/json'
GID=614358b6-5e3c-44d9-afe7-e2dbdc04c2c4

echo "=== 1. что ждёт UserGroupServlet.doPost ==="
F=/opt/jams-src/jams-server/src/main/java/net/jami/jams/server/servlets/api/admin/group/UserGroupServlet.java
sed -n '/protected void doPost/,/^    }/p' "$F" 2>/dev/null | head -30

TOKEN=$(curl -s -m 20 -X POST "$B/api/login" -H "$CT" -d "{\"username\":\"$JUSER\",\"password\":\"$JPASS\"}" \
  | python3 -c 'import json,sys
try: print(json.load(sys.stdin).get("access_token",""))
except Exception: print("")')
AUTH="Authorization: Bearer $TOKEN"

echo
echo "=== 2. добавляю $JUSER в группу MSPShield ==="
for body in "{\"username\":\"$JUSER\"}" "{\"users\":[\"$JUSER\"]}" "{\"user\":\"$JUSER\"}"; do
  R=$(curl -s -m 15 -X POST "$B/api/admin/group/members/$GID" -H "$CT" -H "$AUTH" -d "$body" -w ' [%{http_code}]')
  echo "  body=$body -> $(echo "$R" | head -c 200)"
done

echo
echo "=== 3. состав группы после ==="
curl -s -m 12 "$B/api/admin/group/members/$GID" -H "$AUTH" | head -c 400; echo

echo
echo "=== 4. видит ли пользователь политику ==="
curl -s -m 12 "$B/api/auth/policyData" -H "$AUTH" | head -c 600; echo

echo
echo "=== 5. напоминание про dhtProxyListUrl (может требоваться мобильным клиентам) ==="
grep -rn "dhtProxyListUrl" /opt/jams-src/jams-common/src/main/java --include=*.java 2>/dev/null | head -3
echo DONE
