#!/usr/bin/env bash
set -uo pipefail
echo "=== 1. токены из /opt/jami-services/.env ==="
sudo grep -E "^(INVITE_ADMIN_TOKEN|NAMES_ADMIN_TOKEN|JAMS_ADMIN_USER)=" /opt/jami-services/.env
echo
echo "=== 2. контейнеры jami-services ==="
cd /opt/jami-services && sudo docker compose ps 2>&1 | head -8
echo
echo "=== 3. доступность эндпоинтов invite ==="
for u in "http://127.0.0.1:8890/health" "http://127.0.0.1:8890/login" "http://127.0.0.1:8890/admin" "http://127.0.0.1:8890/"; do
  printf "  %-45s %s\n" "$u" "$(curl -s -o /dev/null -w '%{http_code}' -m 8 "$u")"
done
echo
echo "=== 4. админка с токеном (200 = токен верный) ==="
TOK=$(sudo grep '^INVITE_ADMIN_TOKEN=' /opt/jami-services/.env | cut -d= -f2-)
echo "  /admin?token=<верный> -> $(curl -s -o /dev/null -w '%{http_code}' -m 8 "http://127.0.0.1:8890/admin?token=$TOK")"
echo "  /admin?token=wrong     -> $(curl -s -o /dev/null -w '%{http_code}' -m 8 "http://127.0.0.1:8890/admin?token=wrong")"
echo
echo "=== 5. список приглашений (БД после миграции — новая) ==="
ls -la /opt/jami-services/invite-data/ 2>/dev/null | head -5
sudo python3 - <<'PY'
import sqlite3, glob, os
for db in glob.glob("/opt/jami-services/invite-data/*.db") + glob.glob("/opt/jami-services/invite-data/*.sqlite*"):
    try:
        c = sqlite3.connect(db)
        tabs = [r[0] for r in c.execute("select name from sqlite_master where type='table'")]
        print("  БД:", os.path.basename(db), "таблицы:", tabs)
        for t in tabs:
            n = c.execute(f"select count(*) from {t}").fetchone()[0]
            print(f"    {t}: {n}")
    except Exception as e:
        print("  err", db, e)
PY
echo
echo "=== 6. пробное приглашение через CLI ==="
if [ -x /opt/jami-services/bin/jami-invite-create ]; then
  sudo /opt/jami-services/bin/jami-invite-create "Проверка миграции" 0000000000000000000000000000000000000000 72 "test" 2>&1 | tail -5
else
  echo "  скрипт bin/jami-invite-create отсутствует"
fi
echo
echo "=== 7. Jami ID у админ-учётки JAMS (для профиля приглашающего) ==="
ENV=/opt/jami-services/.env
JUSER=$(grep '^JAMS_ADMIN_USER=' "$ENV" | cut -d= -f2-)
JPASS=$(grep '^JAMS_ADMIN_PASSWORD=' "$ENV" | cut -d= -f2-)
TOKEN=$(curl -s -m 20 -X POST http://127.0.0.1:8081/api/login -H 'Content-Type: application/json' \
  -d "{\"username\":\"$JUSER\",\"password\":\"$JPASS\"}" | python3 -c 'import json,sys
try: print(json.load(sys.stdin).get("access_token",""))
except Exception: print("")')
echo "  GET /api/admin/user?username=$JUSER -> $(curl -s -o /dev/null -w '%{http_code}' -m 10 "http://127.0.0.1:8081/api/admin/user?username=$JUSER" -H "Authorization: Bearer $TOKEN")"
echo "  GET /api/admin/users -> $(curl -s -o /dev/null -w '%{http_code}' -m 10 "http://127.0.0.1:8081/api/admin/users" -H "Authorization: Bearer $TOKEN")"
echo "  пользователи: $(curl -s -m 10 "http://127.0.0.1:8081/api/admin/users" -H "Authorization: Bearer $TOKEN" | head -c 300)"
echo DONE
