#!/usr/bin/env bash
set -uo pipefail
TOK=$(grep '^INVITE_ADMIN_TOKEN=' /opt/jami-services/.env | cut -d= -f2-)
echo "=== 1. создаю приглашение через CLI (как это делает админ) ==="
/opt/jami-services/bin/jami-invite-create "Проверка миграции" "" 72 "тест после миграции" 2>&1 | head -c 500
echo
echo
echo "=== 2. список приглашений (админ-API с токеном) ==="
curl -s -m 10 -H "X-Admin-Token: $TOK" http://127.0.0.1:8890/admin/invites | head -c 600
echo
echo
echo "=== 3. БД ==="
python3 - <<'PY'
import sqlite3
c = sqlite3.connect("/opt/jami-services/invite-data/invites.db")
for t in ("invites", "members", "settings"):
    try:
        print(f"  {t}: {c.execute(f'select count(*) from {t}').fetchone()[0]}")
    except Exception as e:
        print("  err", t, e)
for r in c.execute("select token, inviter_name, note, used, datetime(created_at,'unixepoch') from invites limit 3"):
    print("  ", r)
PY
echo
echo "=== 4. страница приглашения доступна? ==="
T=$(python3 -c "
import sqlite3
c=sqlite3.connect('/opt/jami-services/invite-data/invites.db')
r=c.execute('select token from invites order by rowid desc limit 1').fetchone()
print(r[0] if r else '')")
if [ -n "$T" ]; then
  for p in "/i/$T" "/i/$T/qr.png" "/c/0000000000000000000000000000000000000000"; do
    printf "  %-70s %s\n" "$p" "$(curl -s -o /dev/null -w '%{http_code}' -m 8 "http://127.0.0.1:8890$p")"
  done
  echo "  ссылка: https://invite.msp-claude.online/i/$T"
fi
echo
echo "=== 5. убираю тестовое приглашение ==="
if [ -n "$T" ]; then
  curl -s -o /dev/null -w "  delete -> HTTP %{http_code}\n" -m 10 -X DELETE -H "X-Admin-Token: $TOK" "http://127.0.0.1:8890/admin/invites/$T"
fi
python3 -c "
import sqlite3
c=sqlite3.connect('/opt/jami-services/invite-data/invites.db')
print('  осталось приглашений:', c.execute('select count(*) from invites').fetchone()[0])"
echo DONE
