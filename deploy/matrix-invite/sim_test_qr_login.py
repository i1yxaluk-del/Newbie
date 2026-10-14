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
T0 = time.time()


def log(*a):
    print("[t=%5.1fs]" % (time.time() - T0), *a, flush=True)


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


# --- 0. prepare OAuth client + device authorization BEFORE creating QR (fast path) ---
st, raw, h = http("POST", BASTION + "/oauth2/registration",
                  data=json.dumps({"client_name": "MSPShield Phone (sim)", "client_uri": "https://m.msp-claude.online",
                                   "grant_types": ["urn:ietf:params:oauth:grant-type:device_code", "refresh_token"],
                                   "response_types": [], "redirect_uris": [], "token_endpoint_auth_method": "none"}).encode(),
                  headers={"Content-Type": "application/json"})
client_id = json.loads(raw.decode()).get("client_id")
log("S: DCR done:", client_id)

st, raw, h = http("POST", BASTION + "/oauth2/device",
                  data=urllib.parse.urlencode({"client_id": client_id,
                                               "scope": "urn:matrix:client:api:* urn:matrix:client:device:SIMDEV1234X"}).encode(),
                  headers={"Content-Type": "application/x-www-form-urlencoded"})
dag = json.loads(raw.decode())
vcomplete = dag.get("verification_uri_complete")
device_code = dag.get("device_code")
log("S: device auth done:", dag.get("user_code"))

# --- 1. fresh session via portal ---
st, raw, h = http("POST", PORTAL + "/u/link/start", headers={"Cookie": "mxsession=" + COOKIE})
d = json.loads(raw.decode())
SID = d["sid"]
log("S: portal start, sid:", SID)
png = base64.b64decode(d["qr"].split(",", 1)[1])
open("/tmp/sim_qr.png", "wb").write(png)

# --- 2. decode QR (as the phone camera would) ---
img = Image.open("/tmp/sim_qr.png").convert("RGB")
data = bytes(zxingcpp.read_barcodes(img)[0].bytes)
assert data[:6] == b"MATRIX" and data[6] == 0x02 and data[7] == 0x04
url_len = int.from_bytes(data[40:42], "big")
URL = data[42:42 + url_len].decode()
PUB = b64e(data[8:40])
log("S: QR decoded, pub:", PUB[:12] + "...")

# --- 3. ECIES outbound + init ---
priv = gen_priv()
ch, init_msg = establish_outbound(priv, PUB, b"MATRIX_QR_CODE_LOGIN_INITIATE")
st, raw, h = http("GET", URL)
etag = h.get("etag")
st, raw, h = http("PUT", URL, data=init_msg.encode(),
                  headers={"Content-Type": "text/plain", "If-Match": etag})
log("S: PUT init ->", st)
if h.get("etag"):
    etag = h["etag"]

# --- 4. nudge portal to process init; wait LoginOk ---
ok_plain = None
for _ in range(20):
    time.sleep(1.0)
    portal_status(SID)
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

# --- 5. submit code + protocol quickly ---
st, raw, h = http("POST", PORTAL + "/u/link/code",
                  data=json.dumps({"sid": SID, "code": code}).encode(),
                  headers={"Content-Type": "application/json", "Cookie": "mxsession=" + COOKIE})
log("S: submit code ->", st, raw[:80].decode())

protocol = {"type": "m.login.protocol", "protocol": "device_authorization_grant", "device_id": "SIMDEV1234X",
            "device_authorization_grant": {"verification_uri": dag.get("verification_uri"),
                                           "verification_uri_complete": vcomplete}}
st, raw, h = http("PUT", URL, data=ch.encrypt(json.dumps(protocol).encode()).encode(),
                  headers={"Content-Type": "text/plain", "If-Match": etag})
log("S: PUT protocol ->", st)
if h.get("etag"):
    etag = h["etag"]

# --- 6. portal processes -> confirm; wait accepted ---
acc = None
for _ in range(15):
    time.sleep(1.0)
    ss = portal_status(SID)
    if ss.get("state") == "confirm":
        log("S: portal state: confirm")
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
    if time.time() - last_ka > 12:
        try:
            portal_status(SID)
            last_ka = time.time()
        except Exception:
            pass
    time.sleep(4)
    st, raw, h = http("POST", BASTION + "/oauth2/token",
                      data=urllib.parse.urlencode({"grant_type": "urn:ietf:params:oauth:grant-type:device_code",
                                                   "device_code": device_code, "client_id": client_id}).encode(),
                      headers={"Content-Type": "application/x-www-form-urlencoded"})
    try:
        d2 = json.loads(raw.decode())
    except ValueError:
        d2 = {"error": "bad-json"}
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

# --- 7. success + secrets ---
st, raw, h = http("PUT", URL, data=ch.encrypt(json.dumps({"type": "m.login.success"}).encode(),
                  ).encode(), headers={"Content-Type": "text/plain", "If-Match": etag})
log("S: PUT success ->", st)
if h.get("etag"):
    etag = h["etag"]

sec = None
for _ in range(20):
    time.sleep(1.0)
    portal_status(SID)
    st, raw, h = http("GET", URL, headers={"If-None-Match": etag})
    if h.get("etag"):
        etag = h["etag"]
    if st == 200 and h.get("content-type", "").startswith("text/plain"):
        sec = ch.decrypt(raw.decode())
        break
log("S: secrets raw:", sec)
try:
    d3 = json.loads(sec)
    cs = d3.get("cross_signing") or {}
    ok_cs = all(len(str(cs.get(k, ""))) >= 40 for k in ("master_key", "user_signing_key", "self_signing_key"))
    log("S: secrets valid (as Element X expects):", d3.get("type") == "m.login.secrets" and ok_cs)
except Exception as e:
    log("S: secrets parse error:", e)

time.sleep(1.0)
ss = portal_status(SID)
log("S: portal final state:", ss.get("state"))
log("SENTINEL-SIM-DONE" if ss.get("state") == "done" else "SENTINEL-SIM-PARTIAL")
