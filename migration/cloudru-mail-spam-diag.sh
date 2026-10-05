#!/usr/bin/env bash
set -uo pipefail
echo "=== 0. убираю тестового пользователя ==="
ENV=/opt/jami-services/.env
JUSER=$(grep '^JAMS_ADMIN_USER=' "$ENV" | cut -d= -f2-)
JPASS=$(grep '^JAMS_ADMIN_PASSWORD=' "$ENV" | cut -d= -f2-)
TOKEN=$(curl -s -m 20 -X POST http://127.0.0.1:8081/api/login -H 'Content-Type: application/json' \
  -d "{\"username\":\"$JUSER\",\"password\":\"$JPASS\"}" | python3 -c 'import json,sys
try: print(json.load(sys.stdin).get("access_token",""))
except Exception: print("")')
TESTU=$(curl -s -m 15 http://127.0.0.1:8081/api/admin/users -H "Authorization: Bearer $TOKEN" | python3 -c '
import json,sys
try:
    d=json.load(sys.stdin)
    us=[u.get("username") for u in (d if isinstance(d,list) else d.get("users",[]))]
    print([u for u in us if u and u.startswith("test")][0] if [u for u in us if u and u.startswith("test")] else "")
except Exception: print("")')
echo "  тестовый пользователь: ${TESTU:-нет}"
if [ -n "$TESTU" ]; then
  curl -s -o /dev/null -w "  revoke -> HTTP %{http_code}\n" -m 20 -X POST "http://127.0.0.1:8081/api/admin/user/revoke?username=$TESTU" -H "Authorization: Bearer $TOKEN"
fi
echo
echo "=== 1. hostname ВМ (его Stalwart может использовать как HELO) ==="
hostname; hostname -f 2>/dev/null || true
echo "  в /etc/hosts: $(grep -E '127\.0\.1\.1|msp-cloud' /etc/hosts | head -3 | tr '\n' '|')"
echo
echo "=== 2. что Stalwart считает своим именем (конфиг домена) ==="
curl -s -u "admin:$(sudo grep '^STALWART_ADMIN_PASSWORD=' /opt/msp/Newbie/deploy/yandex/.env | cut -d= -f2-)" \
  -H 'Content-Type: application/json' \
  -d '{"using":["urn:ietf:params:jmap:core","urn:stalwart:jmap"],"methodCalls":[["x:Domain/get",{},"0"]]}' \
  http://127.0.0.1:8080/jmap/ 2>/dev/null | python3 -c '
import json,sys
try:
    d=json.load(sys.stdin)["methodResponses"][0][1]["list"][0]
    for k,v in d.items():
        if any(s in k.lower() for s in ("host","helo","name","domain","banner","report","dns")):
            print(f"  {k} = {str(v)[:120]}")
except Exception as e: print("  err", e)
'
echo
echo "=== 3. PTR нашего IP (что видят приёмники) ==="
dig +short -x 45.132.176.143 2>/dev/null || nslookup 45.132.176.143 2>/dev/null | tail -3
echo "  FORWARD: mail.msp-claude.online -> $(dig +short mail.msp-claude.online 2>/dev/null | head -1)"
echo
echo "=== 4. проверка по чёрным спискам (RBL) ==="
REV=$(echo 45.132.176.143 | awk -F. '{print $4"."$3"."$2"."$1}')
for bl in zen.spamhaus.org bl.spamcop.net b.barracudacentral.org dnsbl.sorbs.net; do
  R=$(dig +short "$REV.$bl" 2>/dev/null | head -1)
  echo "  $bl -> ${R:-чисто (не в списке)}"
done
echo
echo "=== 5. последняя исходящая доставка (HELO/коды) ==="
sudo docker exec msp-stalwart-1 sh -c 'tail -n 400 /var/lib/stalwart/logs/* 2>/dev/null' | grep -iE "ehlo|helo|delivered|dsn|rejected|spam" | tail -10 | cut -c1-190
echo DONE
