#!/usr/bin/env bash
set -uo pipefail
PW=$(sudo grep '^STALWART_ADMIN_PASSWORD=' /opt/msp/Newbie/deploy/yandex/.env | cut -d= -f2-)
JMAP=http://127.0.0.1:8080/jmap/

# пароль для postmaster
PM_PASS=$(head -c 24 /dev/urandom | base64 | tr -d '/+=' | head -c 24)
python3 - "$PW" "$PM_PASS" <<'PY'
import json, sys, subprocess
pw, pmpass = sys.argv[1], sys.argv[2]
def jmap(method, args):
    payload = {"using":["urn:ietf:params:jmap:core","urn:stalwart:jmap"],
               "methodCalls":[[method,args,"0"]]}
    p = subprocess.run(["curl","-s","-u",f"admin:{pw}","-H","Content-Type: application/json",
                        "-d",json.dumps(payload),"http://127.0.0.1:8080/jmap/"],
                       capture_output=True, text=True)
    return json.loads(p.stdout)

# domainId домена
d = jmap("x:Domain/get", {})
dom = d["methodResponses"][0][1]["list"][0]
domain_id = dom["id"]
print("domainId:", domain_id)

# уже есть postmaster?
a = jmap("x:Account/get", {})
names = [x.get("name") for x in a["methodResponses"][0][1]["list"]]
print("existing accounts:", names)

if "postmaster" in names:
    print("postmaster уже существует — пропускаю создание")
else:
    res = jmap("x:Account/set", {"create": {"0": {
        "@type": "User",
        "name": "postmaster",
        "domainId": domain_id,
        "description": "RFC 5321 postmaster mailbox",
        "roles": {"@type": "User"},
        "permissions": {"@type": "Inherit"},
        "credentials": {"0": {"@type": "Password", "secret": pmpass}},
    }}})
    print("create result:", json.dumps(res["methodResponses"][0][1], ensure_ascii=False)[:600])

# проверка
a2 = jmap("x:Account/get", {})
for x in a2["methodResponses"][0][1]["list"]:
    print(" -", x.get("name"), "|", x.get("emailAddress"), "| aliases:", x.get("aliases"))
PY
echo "POSTMASTER_PASSWORD=$PM_PASS" | sudo tee /root/.postmaster-pass >/dev/null
echo "--- пароль сохранён в /root/.postmaster-pass ---"
echo DONE
