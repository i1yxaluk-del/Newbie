#!/usr/bin/env bash
set -uo pipefail
export DEBIAN_FRONTEND=noninteractive

echo "=== 0. останавливаю рестарт-цикл jamiserver ==="
systemctl stop jamiserver 2>/dev/null || true
systemctl disable jamiserver 2>/dev/null || true
echo "  остановлен"

echo "=== 1. ищу рабочий URL GPG-ключа Jami ==="
KEY_OK=0
for u in \
  "https://dl.jami.net/jami.gpg" \
  "https://dl.jami.net/public.key" \
  "https://dl.jami.net/stable/ubuntu_22.04/Release.key" \
  "https://keyserver.ubuntu.com/pks/lookup?op=get&search=0x64CD5FA175348F84" \
  "https://keys.openpgp.org/vks/v1/by-fingerprint/64CD5FA175348F84" ; do
  code=$(curl -s -o /tmp/k.raw -w '%{http_code}' -m 20 "$u" 2>/dev/null)
  size=$(wc -c </tmp/k.raw 2>/dev/null || echo 0)
  echo "  $u -> HTTP $code, $size байт"
  if [ "$code" = "200" ] && [ "$size" -gt 200 ]; then
    if gpg --dearmor < /tmp/k.raw > /usr/share/keyrings/jami.gpg 2>/dev/null && [ -s /usr/share/keyrings/jami.gpg ]; then
      KEY_OK=1; echo "  КЛЮЧ УСТАНОВЛЕН из $u"; break
    fi
  fi
done
[ "$KEY_OK" = "0" ] && echo "  рабочий ключ не найден"

echo "=== 2. apt update + установка ==="
if [ "$KEY_OK" = "1" ]; then
  apt-get update -o Dir::Etc::sourcelist="sources.list.d/jami.list" -o Dir::Etc::sourceparts="-" -o APT::Get::List-Cleanup="0" 2>&1 | tail -3
  apt-get install -y jami-daemon 2>&1 | tail -5
  echo -n "  jamid: "; ls -la /usr/libexec/jamid 2>/dev/null || command -v jamid || echo "НЕ НАЙДЕН"
fi

echo "=== 3. создаю blueprint (policy) и группу MSPShield в JAMS ==="
ENV=/opt/jami-services/.env
JUSER=$(grep '^JAMS_ADMIN_USER=' "$ENV" | cut -d= -f2-)
JPASS=$(grep '^JAMS_ADMIN_PASSWORD=' "$ENV" | cut -d= -f2-)
TURNPASS=$(cat /root/.turn-pass 2>/dev/null | cut -d= -f2-)
BASE=http://127.0.0.1:8081
CT='Content-Type: application/json'

TOKEN=$(curl -s -m 20 -X POST "$BASE/api/login" -H "$CT" -d "{\"username\":\"$JUSER\",\"password\":\"$JPASS\"}" \
  | python3 -c 'import json,sys
try: print(json.load(sys.stdin).get("access_token",""))
except Exception: print("")')
AUTH="Authorization: Bearer $TOKEN"
echo "  token: ${#TOKEN}"

cat >/tmp/policy.json <<EOF
{
  "turnEnabled": true,
  "turnServer": "turn.msp-claude.online",
  "turnServerUserName": "jami",
  "turnServerPassword": "${TURNPASS}",
  "proxyEnabled": true,
  "proxyServer": "dht.msp-claude.online",
  "videoEnabled": true,
  "accountDiscovery": true,
  "peerDiscovery": true,
  "rendezVous": true,
  "upnpEnabled": false,
  "publicInCalls": false,
  "accountPublish": true,
  "allowLookup": true,
  "autoAnswer": false
}
EOF
echo "  policy JSON: $(wc -c </tmp/policy.json) байт"
echo -n "  POST /api/admin/policy?name=MSPShield -> "
curl -s -m 20 -X POST "$BASE/api/admin/policy?name=MSPShield" -H "$CT" -H "$AUTH" --data-binary @/tmp/policy.json -w 'HTTP %{http_code}\n' | head -c 200
echo -n "  POST /api/admin/group -> "
curl -s -m 20 -X POST "$BASE/api/admin/group" -H "$CT" -H "$AUTH" \
  -d '{"name":"MSPShield","blueprintName":"MSPShield"}' -w ' HTTP %{http_code}\n' | head -c 250
echo "  --- проверка ---"
echo -n "  policies: "; curl -s -m 10 "$BASE/api/admin/policy/MSPShield" -H "$AUTH" | head -c 200; echo
echo -n "  groups:   "; curl -s -m 10 "$BASE/api/admin/groups" -H "$AUTH" | head -c 200; echo
echo DONE
