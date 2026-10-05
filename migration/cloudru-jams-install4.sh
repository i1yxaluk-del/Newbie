#!/usr/bin/env bash
# Полный мастер JAMS: свой CA (openssl) -> install/ca -> install/auth -> install/settings
set -uo pipefail
ENV=/opt/jami-services/.env
JUSER=$(grep '^JAMS_ADMIN_USER=' "$ENV" | cut -d= -f2-)
JPASS=$(grep '^JAMS_ADMIN_PASSWORD=' "$ENV" | cut -d= -f2-)
BASE=http://127.0.0.1:8081
CT='Content-Type: application/json'

echo "=== 0. сброс состояния ==="
systemctl stop jams; sleep 3
cd /opt/jams
rm -rf app images jams tomcat.8080 derby.log oauth.key oauth.pub config.json keystore.jks CA.pem jams.crl 2>/dev/null
systemctl start jams
for i in $(seq 1 12); do
  sleep 6
  R=$(curl -s -m 5 "$BASE/api/info" 2>/dev/null)
  case "$R" in *'"installed":"false"'*) echo "  готов на попытке $i"; break;; esac
done

echo "=== 1. генерация CA (10 лет, CA:TRUE) ==="
openssl genrsa -out /tmp/ca.key 4096 2>/dev/null
openssl req -x509 -new -nodes -key /tmp/ca.key -sha256 -days 3650 \
  -subj "/C=RU/ST=Moscow/O=MSPShield/OU=Jami/CN=MSPShield JAMS CA" \
  -addext "basicConstraints=critical,CA:TRUE" \
  -addext "keyUsage=critical,keyCertSign,cRLSign" \
  -out /tmp/ca.crt 2>/dev/null
openssl pkcs8 -topk8 -nocrypt -in /tmp/ca.key -out /tmp/ca.pk8 2>/dev/null
openssl x509 -in /tmp/ca.crt -noout -subject -dates -ext basicConstraints

echo "=== 2. JSON для install/ca ==="
python3 - <<'PY' >/tmp/ca.json
import json
crt = open('/tmp/ca.crt').read()
key = open('/tmp/ca.pk8').read()
print(json.dumps({
    "fields": {"commonName": "MSPShield JAMS CA", "country": "RU", "state": "Moscow",
               "organization": "MSPShield", "organizationUnit": "Jami",
               "lifetime": 315360000000},
    "certificate": crt, "privateKey": key}))
PY
echo "  размер JSON: $(wc -c </tmp/ca.json) байт"

echo "=== 3. install/start -> token ==="
TOKEN=$(curl -s -m 25 -X PUT "$BASE/api/install/start" -H "$CT" \
  -d "{\"username\":\"$JUSER\",\"password\":\"$JPASS\"}" \
  | python3 -c 'import json,sys
try: print(json.load(sys.stdin).get("access_token",""))
except Exception: print("")')
echo "  token length: ${#TOKEN}"
[ -z "$TOKEN" ] && { echo "ТОКЕН НЕ ПОЛУЧЕН"; exit 2; }
AUTH="Authorization: Bearer $TOKEN"

echo "=== 4. install/ca ==="
curl -s -m 120 -X POST "$BASE/api/install/ca" -H "$CT" -H "$AUTH" --data-binary @/tmp/ca.json -w '\n  HTTP %{http_code}\n' | head -c 300; echo
echo "=== 5. install/auth ==="
curl -s -m 60 -X POST "$BASE/api/install/auth" -H "$CT" -H "$AUTH" -d '{"type":"LOCAL"}' -w '\n  HTTP %{http_code}\n' | head -c 300; echo
echo "=== 6. install/settings ==="
curl -s -m 60 -X POST "$BASE/api/install/settings" -H "$CT" -H "$AUTH" \
  -d '{"serverDomain":"https://m.msp-claude.online","reverseProxy":true,"crlLifetime":3600000,"deviceLifetime":31536000000,"userLifetime":31536000000}' \
  -w '\n  HTTP %{http_code}\n' | head -c 300; echo
echo "=== 7. info ==="
curl -s -m 15 "$BASE/api/info"; echo
echo "=== 8. артефакты CA (в бэкап!) ==="
ls -la /opt/jams/ | grep -E "CA.pem|keystore|crl|config.json"
echo "=== 9. лог ==="
journalctl -u jams -n 8 --no-pager 2>&1 | tail -8 | cut -c1-200
echo DONE
