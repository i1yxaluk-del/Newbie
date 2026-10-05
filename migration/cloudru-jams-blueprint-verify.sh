#!/usr/bin/env bash
set -uo pipefail
ENV=/opt/jami-services/.env
JUSER=$(grep '^JAMS_ADMIN_USER=' "$ENV" | cut -d= -f2-)
JPASS=$(grep '^JAMS_ADMIN_PASSWORD=' "$ENV" | cut -d= -f2-)
B=http://127.0.0.1:8081
CT='Content-Type: application/json'

TOKEN=$(curl -s -m 20 -X POST "$B/api/login" -H "$CT" -d "{\"username\":\"$JUSER\",\"password\":\"$JPASS\"}" \
  | python3 -c 'import json,sys
try: print(json.load(sys.stdin).get("access_token",""))
except Exception: print("")')
AUTH="Authorization: Bearer $TOKEN"
echo "token: ${#TOKEN}"

echo
echo "=== 1. blueprint (policy) MSPShield: что сохранено ==="
curl -s -m 15 "$B/api/admin/policy/MSPShield" -H "$AUTH" | python3 -c '
import json,sys
try:
    d=json.load(sys.stdin)
    print("  name:", d.get("name"))
    pd=json.loads(d.get("policyData","{}"))
    for k in ("turnEnabled","turnServer","turnServerUserName","turnServerPassword","proxyEnabled","proxyServer","dhtProxyListUrl","videoEnabled"):
        v=pd.get(k)
        if k=="turnServerPassword" and v: v="<задан>"
        print(f"  {k} = {v}")
except Exception as e: print("  err:", e)'

echo
echo "=== 2. группы и состав ==="
curl -s -m 15 "$B/api/admin/groups" -H "$AUTH" > /tmp/groups.json
cat /tmp/groups.json | head -c 500; echo
python3 - <<'PY'
import json
try:
    gs = json.load(open("/tmp/groups.json"))
    if isinstance(gs, dict): gs = gs.get("groups", [])
    for g in gs:
        print("  группа:", g.get("name"), "| blueprint:", g.get("blueprint"), "| id:", g.get("id"))
except Exception as e:
    print("  err", e)
PY

echo
echo "=== 3. состав группы MSPShield (members) ==="
GID=$(python3 -c "
import json
gs=json.load(open('/tmp/groups.json'))
if isinstance(gs, dict): gs=gs.get('groups',[])
print(next((g['id'] for g in gs if g.get('name')=='MSPShield'), ''))")
echo "  group id: ${GID:-не найдена}"
if [ -n "$GID" ]; then
  for ep in "/api/admin/group/$GID" "/api/admin/group/$GID/members" "/api/admin/group/members/$GID"; do
    R=$(curl -s -m 12 "$B$ep" -H "$AUTH")
    echo "  $ep -> $(echo "$R" | head -c 250)"
  done
fi

echo
echo "=== 4. все пользователи JAMS ==="
curl -s -m 15 "$B/api/admin/users" -H "$AUTH" | head -c 500; echo

echo
echo "=== 5. политика, которую видит сам пользователь (/api/auth/policyData) ==="
curl -s -m 12 "$B/api/auth/policyData" -H "$AUTH" | head -c 300; echo

echo
echo "=== 6. есть ли эндпоинт добавления в группу ==="
grep -rhoE '@WebServlet\("/api/admin/group[^"]*"\)' /opt/jams-src/jams-server/src/main/java --include=*.java 2>/dev/null | sort -u
echo "--- метод(ы) ---"
for f in $(grep -rl 'api/admin/group' /opt/jams-src/jams-server/src/main/java --include=*.java 2>/dev/null); do
  echo "  $(basename $f): $(grep -oE '@WebServlet\("[^"]+"\)' $f) -> do(Get|Post|Put|Delete)"
  grep -oE 'protected void do[A-Za-z]+' "$f" | sed 's/^/      /'
done
echo DONE
