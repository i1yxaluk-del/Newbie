#!/usr/bin/env bash
set -uo pipefail
ENV=/opt/jami-services/.env
JUSER=$(grep '^JAMS_ADMIN_USER=' "$ENV" | cut -d= -f2-)
JPASS=$(grep '^JAMS_ADMIN_PASSWORD=' "$ENV" | cut -d= -f2-)
B=http://127.0.0.1:8081
CT='Content-Type: application/json'

echo "=== 1. что ждёт /api/admin/directory/entry (doPost) ==="
F=$(grep -rl '@WebServlet("/api/admin/directory/entry")' /opt/jams-src --include=*.java 2>/dev/null | head -1)
echo "  файл: $F"
[ -n "$F" ] && sed -n '/protected void doPost/,/^    }/p' "$F" | head -35

TOKEN=$(curl -s -m 20 -X POST "$B/api/login" -H "$CT" -d "{\"username\":\"$JUSER\",\"password\":\"$JPASS\"}" \
  | python3 -c 'import json,sys
try: print(json.load(sys.stdin).get("access_token",""))
except Exception: print("")')
AUTH="Authorization: Bearer $TOKEN"

echo
echo "=== 2. создаю профили существующим пользователям ==="
add_profile() {
  local u="$1" fn="$2" ln="$3"
  local code
  code=$(curl -s -o /tmp/pr.json -w '%{http_code}' -m 15 -X POST "$B/api/admin/directory/entry" \
    -H "$CT" -H "$AUTH" -d "{\"username\":\"$u\",\"firstName\":\"$fn\",\"lastName\":\"$ln\",\"email\":\"\"}")
  echo "  $u -> HTTP $code $(head -c 140 /tmp/pr.json)"
}
add_profile "run" "Сухарь" ""
add_profile "ilya" "ilya" ""
add_profile "mspadmin" "Администратор" "MSPShield"

echo
echo "=== 3. читается ли профиль теперь ==="
for u in run ilya mspadmin; do
  R=$(curl -s -m 10 "$B/api/auth/userprofile/$u" -H "$AUTH")
  echo "  $u -> $(echo "$R" | head -c 160)"
done

echo
echo "=== 4. пробую device-registration (что делал клиент) ==="
# Эмулируем то, что делает клиент при входе: регистрация устройства.
for u in run ilya; do
  P=$(python3 -c "
import sqlite3
c=sqlite3.connect('/opt/jami-services/invite-data/invites.db'); c.row_factory=sqlite3.Row
for r in c.execute('select jams_password from members where jams_username=? order by rowid desc limit 1',('$u',)):
    print(r['jams_password'])
" 2>/dev/null)
  [ -z "$P" ] && { echo "  $u: пароль не найден"; continue; }
  T=$(curl -s -m 15 -X POST "$B/api/login" -H "$CT" -d "{\"username\":\"$u\",\"password\":\"$P\"}" \
    | python3 -c 'import json,sys
try: print(json.load(sys.stdin).get("access_token",""))
except Exception: print("")')
  echo "  $u: логин -> ${#T} симв. токена"
done
echo DONE
