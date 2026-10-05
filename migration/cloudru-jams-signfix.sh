#!/usr/bin/env bash
# ═══════════════════════════════════════════════════════════════════
# НАЗНАЧЕНИЕ (для junior): Чинит 500 при создании пользователя JAMS (в caConfiguration не хватало signingAlgorithm).
# КОГДА ЗАПУСКАТЬ:         На ВМ от root, когда UserServlet отдаёт 500 при создании пользователя.
# КАК ЗАПУСКАТЬ:           sudo bash cloudru-jams-signfix.sh
# ПРОВЕРКА УСПЕХА:         POST /api/admin/user -> HTTP 201; в логе 'User certificate: Not valid after'.
# ОТКАТ:                   Восстановить /opt/jams/config.json из бэкапа рядом (config.json.bak.*).
# ═══════════════════════════════════════════════════════════════════
set -uo pipefail
echo "=== 1. JamsCA: что читает из конфига ==="
sed -n '70,115p' /opt/jams-src/jams-ca/src/main/java/net/jami/jams/ca/JamsCA.java 2>/dev/null | grep -vE "^\s*\*|^/\*|^import" | head -30

echo
echo "=== 2. бэкап config.json ==="
cp /opt/jams/config.json "/opt/jams/config.json.bak.$(date +%s)"
cat /opt/jams/config.json; echo

echo "=== 3. добавляю signingAlgorithm ==="
python3 - <<'PY'
import json
p = "/opt/jams/config.json"
d = json.load(open(p))
inner = json.loads(d["caConfiguration"])
print("  было:", inner)
if not inner.get("signingAlgorithm"):
    inner["signingAlgorithm"] = "SHA512WITHRSA"
d["caConfiguration"] = json.dumps(inner)
json.dump(d, open(p, "w"))
print("  стало:", json.loads(d["caConfiguration"]))
PY
chown jams:jams /opt/jams/config.json

echo
echo "=== 4. рестарт JAMS ==="
systemctl restart jams
sleep 40
echo -n "  jams: "; systemctl is-active jams
echo -n "  /api/info: "; curl -s -m 8 http://127.0.0.1:8081/api/info; echo

echo
echo "=== 5. пробую создать пользователя через API ==="
ENV=/opt/jami-services/.env
JUSER=$(grep '^JAMS_ADMIN_USER=' "$ENV" | cut -d= -f2-)
JPASS=$(grep '^JAMS_ADMIN_PASSWORD=' "$ENV" | cut -d= -f2-)
TOKEN=$(curl -s -m 20 -X POST http://127.0.0.1:8081/api/login -H 'Content-Type: application/json' \
  -d "{\"username\":\"$JUSER\",\"password\":\"$JPASS\"}" | python3 -c 'import json,sys
try: print(json.load(sys.stdin).get("access_token",""))
except Exception: print("")')
echo "  token: ${#TOKEN} симв"
TESTUSER="test$(date +%s)"
echo "  создаю пользователя: $TESTUSER"
curl -s -m 40 -X POST http://127.0.0.1:8081/api/admin/user \
  -H 'Content-Type: application/json' -H "Authorization: Bearer $TOKEN" \
  -d "{\"username\":\"$TESTUSER\",\"password\":\"TestPass123!\",\"displayName\":\"Test User\"}" \
  -w '\n  HTTP %{http_code}\n' | head -c 400
echo
echo "=== 6. ошибки в логе за 2 минуты ==="
journalctl -u jams --since "2 min ago" --no-pager 2>/dev/null | grep -iE "CertificateSigner|UserBuilder|NullPointer|CA stored|OCSP|error" | tail -8
echo DONE
