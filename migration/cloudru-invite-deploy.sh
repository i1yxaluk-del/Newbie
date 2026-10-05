#!/usr/bin/env bash
# Обновляет app.py портала приглашений (добавлено создание профиля JAMS) и пересобирает контейнер.
set -uo pipefail
echo "=== 1. бэкап текущего app.py ==="
cp /opt/jami-services/invite/app.py "/opt/jami-services/invite/app.py.bak.$(date +%s)"
ls -la /opt/jami-services/invite/ | head -5

echo
echo "=== 2. ставлю новый app.py ==="
if [ ! -s /tmp/app_patched.py ]; then echo "  ОШИБКА: /tmp/app_patched.py не загружен"; exit 2; fi
cp /tmp/app_patched.py /opt/jami-services/invite/app.py
wc -l /opt/jami-services/invite/app.py
echo "  новые строки:"
grep -n "_jams_create_user_profile" /opt/jami-services/invite/app.py | head -5

echo
echo "=== 3. проверка синтаксиса ==="
python3 -m py_compile /opt/jami-services/invite/app.py && echo "  синтаксис OK"

echo
echo "=== 4. пересборка контейнера invite ==="
cd /opt/jami-services
sudo docker compose up -d --build invite 2>&1 | tail -8
sleep 15
sudo docker compose ps invite

echo
echo "=== 5. проверка после пересборки ==="
curl -s -o /dev/null -w '  /health -> %{http_code}\n' -m 10 http://127.0.0.1:8890/health
curl -s -o /dev/null -w '  /login  -> %{http_code}\n' -m 10 http://127.0.0.1:8890/login
echo -n "  создание через CLI -> "
/opt/jami-services/bin/jami-invite-create "Проверка профиля" "" 24 "test" 2>&1 | head -c 160
echo
TOK=$(grep '^INVITE_ADMIN_TOKEN=' /opt/jami-services/.env | cut -d= -f2-)
T=$(python3 -c "
import sqlite3
c=sqlite3.connect('/opt/jami-services/invite-data/invites.db')
r=c.execute('select token from invites order by rowid desc limit 1').fetchone()
print(r[0] if r else '')")
[ -n "$T" ] && curl -s -o /dev/null -w "  удаление теста -> HTTP %{http_code}\n" -X DELETE -H "X-Admin-Token: $TOK" "http://127.0.0.1:8890/admin/invites/$T"
echo DEPLOY_DONE
