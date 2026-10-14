# -*- coding: utf-8 -*-
"""E2E simulation: acts as the phone app (new device) for the cabinet QR login."""
import base64
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

sys.path.insert(0, "/opt/matrix-invite")
from msc4108 import b64e, establish_outbound, gen_priv  # noqa: E402

import zxingcpp  # noqa: E402
from PIL import Image  # noqa: E402

PORTAL = "http://127.0.0.1:8896"
BASTION = "https://bastion.msp-claude.online"
COOKIE = open("/tmp/link_cookie").read().strip()


def log(*a):
    print(*a, flush=True)


def http(method, url, data=None, headers=None, timeout=25):
    req = urllib.request.Request(url, data=data, method=method)
    for k, v in (headers or {}).items():
        req.add_header(k, v)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, r.read(), {k.lower(): v for k, v in r.headers.items()}
    except urllib.error.HTTPError as e:
        return e.code, e.read(), {k.lower(): v for k, v in (e.headers or {}).items()}


def portal_status(sid):
    st, raw, h = http("GET", PORTAL + "/u/link/status?sid=" + urllib.parse.quote(sid),
                      headers={"Cookie": "mxsession=" + COOKIE})
    return json.loads(raw.decode())


# --- 0. fresh session via portal ---
st, raw, h = http("POST", PORTAL + "/u/link/start", headers={"Cookie": "mxsession=" + COOKIE})
d = json.loads(raw.decode())
SID = d["sid"]
log("S: portal start ok, sid:", SID)
png = base64.b64decode(d["qr"].split(",", 1)[1])
open("/tmp/sim_qr.png", "wb").write(png)

# --- 1. decode QR (as the phone camera would) ---
img = Image.open("/tmp/sim_qr.png").convert("RGB")
data = bytes(zxingcpp.read_barcodes(img)[0].bytes)
assert data[:6] == b"MATRIX" and data[6] == 0x02 and data[7] == 0x04
url_len = int.from_bytes(data[40:42], "big")
URL = data[42:42 + url_len].decode()
PUB = b64e(data[8:40])
log("S: QR decoded: url =", URL, "| pub =", PUB[:12] + "...")

# --- 2. ECIES outbound (as the app would) ---
priv = gen_priv()
ch, init_msg = establish_outbound(priv, PUB, b"MATRIX_QR_CODE_LOGIN_INITIATE")
log("S: init message ready")

st, raw, h = http("GET", URL)
etag = h.get("etag")
st, raw, h = http("PUT", URL, data=init_msg.encode(),
                  headers={"Content-Type": "text/plain", "If-Match": etag})
log("S: PUT init ->", st)
if h.get("etag"):
    etag = h["etag"]

# --- 2b. nudge the portal so it processes the init message ---
for _ in range(8):
    time.sleep(1.2)
    ss = portal_status(SID)
    log("S: portal status (after init):", ss.get("state"))
    if ss.get("state") == "code":
        break

# --- 3. wait for LoginOk ---
ok_plain = None
for _ in range(30):
    time.sleep(1.2)
    st, raw, h = http("GET", URL, headers={"If-None-Match": etag})
    if h.get("etag"):
        etag = h["etag"]
    if st == 200 and h.get("content-type", "").startswith("text/plain"):
        ok_plain = ch.decrypt(raw.decode())
        break
log("S: LoginOk:", ok_plain)
assert ok_plain == b"MATRIX_QR_CODE_LOGIN_OK"

code = ch.check_code()
log("S: check code to display =", code)

# --- 4. submit check code into the cabinet (user action) ---
st, raw, h = http("POST", PORTAL + "/u/link/code",
                  data=json.dumps({"sid": SID, "code": code}).encode(),
                  headers={"Content-Type": "application/json", "Cookie": "mxsession=" + COOKIE})
log("S: submit code ->", st, raw[:140].decode())

# --- 5. DCR + device authorization ---
st, raw, h = http("POST", BASTION + "/oauth2/registration",
                  data=json.dumps({"client_name": "MSPShield Phone (sim)", "client_uri": "https://m.msp-claude.online",
                                   "grant_types": ["urn:ietf:params:oauth:grant-type:device_code", "refresh_token"],
                                   "response_types": [], "redirect_uris": [], "token_endpoint_auth_method": "none"}).encode(),
                  headers={"Content-Type": "application/json"})
client_id = json.loads(raw.decode()).get("client_id")
log("S: DCR client_id:", client_id)

st, raw, h = http("POST", BASTION + "/oauth2/device",
                  data=urllib.parse.urlencode({"client_id": client_id,
                                               "scope": "urn:matrix:client:api:* urn:matrix:client:device:SIMDEV1234X"}).encode(),
                  headers={"Content-Type": "application/x-www-form-urlencoded"})
dag = json.loads(raw.decode())
log("S: device auth ->", st, {k: dag.get(k) for k in ("user_code", "expires_in", "interval", "error", "error_description")})
vcomplete = dag.get("verification_uri_complete")
device_code = dag.get("device_code")

# --- 6. send protocol message ---
protocol = {"type": "m.login.protocol", "protocol": "device_authorization_grant", "device_id": "SIMDEV1234X",
            "device_authorization_grant": {"verification_uri": dag.get("verification_uri"),
                                           "verification_uri_complete": vcomplete}}
st, raw, h = http("PUT", URL, data=ch.encrypt(json.dumps(protocol).encode()).encode(),
                  headers={"Content-Type": "text/plain", "If-Match": etag})
log("S: PUT protocol ->", st)
if h.get("etag"):
    etag = h["etag"]

# --- 7. nudge the portal (like the browser page does) ---
for _ in range(12):
    time.sleep(1.2)
    ss = portal_status(SID)
    log("S: portal status:", ss.get("state"), "| confirm_url:", (ss.get("confirm_url") or "")[:90])
    if ss.get("state") == "confirm":
        break

# --- 8. wait accepted ---
acc = None
for _ in range(30):
    time.sleep(1.2)
    st, raw, h = http("GET", URL, headers={"If-None-Match": etag})
    if h.get("etag"):
        etag = h["etag"]
    if st == 200 and h.get("content-type", "").startswith("text/plain"):
        acc = ch.decrypt(raw.decode())
        break
log("S: accepted:", acc)

log("S: ============== APPROVE REQUIRED ==============")
log("S: APPROVE_URL:", vcomplete)
try:
    open("/tmp/approve_url.txt", "w").write(vcomplete)
except Exception:
    pass

token = None
deadline = time.time() + 420
last_ka = 0
while time.time() < deadline:
    # keepalive the cabinet session (as the open page does with its polling)
    if time.time() - last_ka > 12:
        try:
            portal_status(SID)
            last_ka = time.time()
        except Exception:
            pass
    time.sleep(5)
    st, raw, h = http("POST", BASTION + "/oauth2/token",
                      data=urllib.parse.urlencode({"grant_type": "urn:ietf:params:oauth:grant-type:device_code",
                                                   "device_code": device_code, "client_id": client_id}).encode(),
                      headers={"Content-Type": "application/x-www-form-urlencoded"})
    try:
        d2 = json.loads(raw.decode())
    except ValueError:
        d2 = {"error": "bad-json", "raw": raw[:120].decode('utf-8', 'replace')}
    if st == 200 and d2.get("access_token"):
        token = d2["access_token"]
        log("S: TOKEN RECEIVED")
        break
    if d2.get("error") not in ("authorization_pending", "slow_down"):
        log("S: token error:", d2)
        break
if not token:
    log("S: NO TOKEN (timeout)")
    sys.exit(1)

# --- 9. success + secrets ---
st, raw, h = http("PUT", URL, data=ch.encrypt(json.dumps({"type": "m.login.success"}).encode(),
                  ).encode(), headers={"Content-Type": "text/plain", "If-Match": etag})
log("S: PUT success ->", st)
if h.get("etag"):
    etag = h["etag"]

sec = None
for _ in range(20):
    time.sleep(1.2)
    st, raw, h = http("GET", URL, headers={"If-None-Match": etag})
    if h.get("etag"):
        etag = h["etag"]
    if st == 200 and h.get("content-type", "").startswith("text/plain"):
        sec = ch.decrypt(raw.decode())
        break
log("S: secrets:", sec)
time.sleep(1.5)
ss = portal_status(SID)
log("S: portal final state:", ss.get("state"))
log("SENTINEL-SIM-DONE" if ss.get("state") == "done" else "SENTINEL-SIM-PARTIAL")
