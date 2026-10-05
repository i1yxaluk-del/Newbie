#!/usr/bin/env bash
# Импорт актуального сертификата Caddy (mail.msp-claude.online) в Stalwart.
set -uo pipefail
PW=$(sudo grep '^STALWART_ADMIN_PASSWORD=' /opt/msp/Newbie/deploy/yandex/.env | cut -d= -f2-)
CD=/var/lib/caddy/.local/share/caddy/certificates/acme-v02.api.letsencrypt.org-directory/mail.msp-claude.online
sudo cp "$CD/mail.msp-claude.online.crt" /tmp/mail.crt
sudo cp "$CD/mail.msp-claude.online.key" /tmp/mail.key
sudo chmod 644 /tmp/mail.crt /tmp/mail.key
echo "=== cert dates (Caddy) ==="
openssl x509 -in /tmp/mail.crt -noout -subject -dates

python3 - "$PW" <<'PY'
import json, sys, subprocess
pw = sys.argv[1]
crt = open('/tmp/mail.crt').read()
key = open('/tmp/mail.key').read()

def jmap(method, args):
    payload = {"using": ["urn:ietf:params:jmap:core", "urn:stalwart:jmap"],
               "methodCalls": [[method, args, "0"]]}
    p = subprocess.run(["curl", "-s", "-u", f"admin:{pw}", "-H", "Content-Type: application/json",
                        "-d", json.dumps(payload), "http://127.0.0.1:8080/jmap/"],
                       capture_output=True, text=True)
    return p.stdout

# current certificate ids
g = json.loads(jmap("x:Certificate/get", {}))
lst = g["methodResponses"][0][1]["list"]
print("certificates:", [(c.get("subjectAlternativeNames"), c.get("id")) for c in lst])
if not lst:
    print("нет сертификатов"); sys.exit(1)
cid = lst[0]["id"]

r = jmap("x:Certificate/set", {"update": {cid: {
    "certificate": {"@type": "Text", "value": crt},
    "privateKey": {"@type": "Text", "secret": key},
}}})
print("update result:", r[:400])
PY
echo "=== проверка сертификата на 465 ==="
sleep 3
echo | openssl s_client -connect 127.0.0.1:465 -servername mail.msp-claude.online 2>/dev/null | openssl x509 -noout -subject -issuer -dates 2>/dev/null
echo DONE
