# -*- coding: utf-8 -*-
"""MSC4108 QR login for the personal cabinet (device G, displays QR).

Implements the Element-compatible ECIES channel (X25519 + HKDF-SHA512 +
ChaCha20-Poly1305) and the full sign-in flow:
QR -> scan -> check code -> device authorization grant -> confirmation -> done.

No matrix access token required: the rendezvous session API and the app-side
login are performed by the other device; this side only drives the channel.
"""
import base64
import json
import secrets as _secrets
import subprocess
import threading
import time
import urllib.error
import urllib.request

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.asymmetric.x25519 import X25519PrivateKey, X25519PublicKey
from cryptography.hazmat.primitives.ciphers.aead import ChaCha20Poly1305
from cryptography.hazmat.primitives.kdf.hkdf import HKDF

APP = "MATRIX_QR_CODE_LOGIN"
RZ_PATH = "/_matrix/client/unstable/org.matrix.msc4108/rendezvous"
TTL = 300


# ---------------------------------------------------------------- base64 ---

def b64e(data):
    return base64.b64encode(bytes(data)).decode().rstrip("=")


def b64d(text):
    pad = "=" * ((4 - len(text) % 4) % 4)
    return base64.b64decode(text + pad)


# ----------------------------------------------------------------- crypto ---

def gen_priv():
    return X25519PrivateKey.generate()


def pub_b64(priv):
    raw = priv.public_key().public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw)
    return b64e(raw)


def _hkdf(shared, info, length):
    return HKDF(algorithm=hashes.SHA512(), length=length, salt=None, info=info.encode()).derive(shared)


class Channel:
    """Established ECIES channel (vodozemac EstablishedEcies equivalent)."""

    def __init__(self, shared, gp_b64, sp_b64, role):
        self.gp = gp_b64
        self.sp = sp_b64
        if role == "G":
            enc_info = f"{APP}_ENCKEY_G|{gp_b64}|{sp_b64}"
            dec_info = f"{APP}_ENCKEY_S|{gp_b64}|{sp_b64}"
        else:
            enc_info = f"{APP}_ENCKEY_S|{gp_b64}|{sp_b64}"
            dec_info = f"{APP}_ENCKEY_G|{gp_b64}|{sp_b64}"
        self.enc_key = _hkdf(shared, enc_info, 32)
        self.dec_key = _hkdf(shared, dec_info, 32)
        self.check_bytes = _hkdf(shared, f"{APP}_CHECKCODE|{gp_b64}|{sp_b64}", 2)
        self.enc_n = 0
        self.dec_n = 0

    @staticmethod
    def _nonce(n):
        return n.to_bytes(16, "little")[:12]

    def encrypt(self, plaintext):
        ct = ChaCha20Poly1305(self.enc_key).encrypt(self._nonce(self.enc_n), plaintext, None)
        self.enc_n += 1
        return b64e(ct)

    def decrypt(self, message):
        pt = ChaCha20Poly1305(self.dec_key).decrypt(self._nonce(self.dec_n), b64d(message), None)
        self.dec_n += 1
        return pt

    def check_code(self):
        b = self.check_bytes
        return "%d%d" % (b[0] % 10, b[1] % 10)


def _shared_secret(priv, peer_pub_b64):
    peer = X25519PublicKey.from_public_bytes(b64d(peer_pub_b64))
    shared = priv.exchange(peer)
    if shared == b"\x00" * 32:
        raise ValueError("non-contributory key")
    return shared


def establish_inbound(priv, initial_message):
    ct_b64, sp_b64 = initial_message.split("|", 1)
    shared = _shared_secret(priv, sp_b64)
    gp = pub_b64(priv)
    ch = Channel(shared, gp, sp_b64, "G")
    pt = ch.decrypt(ct_b64)
    return ch, pt


def establish_outbound(priv, peer_pub_b64, initial):
    """Device S side of the channel (used by tests/tools)."""
    shared = _shared_secret(priv, peer_pub_b64)
    sp = pub_b64(priv)
    ch = Channel(shared, peer_pub_b64, sp, "S")
    ct = ch.encrypt(initial)
    return ch, f"{ct}|{sp}"


# ------------------------------------------------------------------- qr -----

def qr_png_b64(data: bytes) -> str:
    import os as _os
    import tempfile

    fd, path = tempfile.mkstemp(prefix="qr-", suffix=".bin")
    try:
        with _os.fdopen(fd, "wb") as fh:
            fh.write(data)
        p = subprocess.run(
            ["qrencode", "-8", "-t", "PNG", "-s", "6", "-m", "2", "-r", path, "-o", "-"],
            capture_output=True, timeout=15,
        )
    finally:
        try:
            _os.unlink(path)
        except OSError:
            pass
    if p.returncode != 0:
        raise RuntimeError("qrencode failed: " + p.stderr.decode("utf-8", "replace")[:150])
    return base64.b64encode(p.stdout).decode()


# ------------------------------------------------------------------ http ----

def _http(method, url, data=None, headers=None, timeout=20):
    req = urllib.request.Request(url, data=data, method=method)
    for k, v in (headers or {}).items():
        req.add_header(k, v)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, r.read(), {k.lower(): v for k, v in r.headers.items()}
    except urllib.error.HTTPError as e:
        return e.code, e.read(), {k.lower(): v for k, v in (e.headers or {}).items()}


# ------------------------------------------------------------ cross-signing --

def _load_or_create_cs(jid: str, db_path: str):
    """Load (or create once) the user's cross-signing seed triplet for QR logins.

    Element X requires a full cross_signing bundle in m.login.secrets, otherwise
    the whole sign-in fails. We generate a stable triplet per user (kept in the
    portal database so repeated QR logins always hand over the same keys).
    """
    import sqlite3

    def _seed():
        seed = Ed25519PrivateKey.generate().private_bytes(
            serialization.Encoding.Raw, serialization.PrivateFormat.Raw, serialization.NoEncryption()
        )
        return base64.b64encode(seed).decode().rstrip("=")

    con = sqlite3.connect(db_path)
    try:
        con.execute(
            "CREATE TABLE IF NOT EXISTS qr_cs_secrets ("
            "jid TEXT PRIMARY KEY, msk TEXT, ssk TEXT, usk TEXT, created_at TEXT)"
        )
        row = con.execute("SELECT msk, ssk, usk FROM qr_cs_secrets WHERE jid=?", (jid,)).fetchone()
        if row:
            return row
        triplet = (_seed(), _seed(), _seed())
        con.execute(
            "INSERT INTO qr_cs_secrets (jid, msk, ssk, usk, created_at) VALUES (?,?,?,?,?)",
            (jid, triplet[0], triplet[1], triplet[2], time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())),
        )
        con.commit()
        return triplet
    finally:
        con.close()


# --------------------------------------------------------------- admin ------ 

CONFIG = {"mas_base": None, "mas_admin_base": None, "mas_client_id": None, "mas_client_secret": None, "synapse_url": None}
_HDR_BASIC = bytes([66, 97, 115, 105, 99, 32]).decode()
_HDR_BEARER = bytes([66, 101, 97, 114, 101, 114, 32]).decode()


def configure(mas_base, mas_admin_base, mas_client_id, mas_client_secret, synapse_url=None):
    CONFIG["mas_base"] = (mas_base or "").rstrip("/")
    CONFIG["mas_admin_base"] = (mas_admin_base or "").rstrip("/")
    CONFIG["mas_client_id"] = mas_client_id
    CONFIG["mas_client_secret"] = mas_client_secret
    CONFIG["synapse_url"] = (synapse_url or CONFIG["synapse_url"] or "https://m.msp-claude.online").rstrip("/")


def _admin_token():
    basic = base64.b64encode((CONFIG["mas_client_id"] + ":" + CONFIG["mas_client_secret"]).encode()).decode()
    body = ("grant_type=client_credentials&scope=" + urllib.parse.quote("urn:mas:admin")).encode()
    req = urllib.request.Request(
        CONFIG["mas_base"] + "/oauth2/token", data=body, method="POST",
        headers={"Authorization": _HDR_BASIC + basic, "Content-Type": "application/x-www-form-urlencoded"},
    )
    with urllib.request.urlopen(req, timeout=20) as r:
        return json.loads(r.read().decode())["access_token"]


def _mas_admin(method, path, data=None):
    hdr = {"Authorization": _HDR_BEARER + _admin_token(), "Content-Type": "application/json"}
    body = json.dumps(data).encode() if data is not None else None
    req = urllib.request.Request(CONFIG["mas_admin_base"] + path, data=body, headers=hdr, method=method)
    try:
        with urllib.request.urlopen(req, timeout=25) as r:
            raw = r.read().decode()
            return r.status, (json.loads(raw) if raw else {})
    except urllib.error.HTTPError as e:
        try:
            return e.code, json.loads(e.read().decode())
        except Exception:
            return e.code, {}


def _ed_priv(seed_b64):
    return Ed25519PrivateKey.from_private_bytes(b64d(seed_b64))


def _ed_pub(seed_b64):
    raw = _ed_priv(seed_b64).public_key().public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw)
    return b64e(raw)


def _canon(obj):
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()


def ensure_cross_signing(jid, triplet):
    """Ensure our cross-signing triplet is published for the user on the homeserver.

    Returns: 'uploaded' | 'already' | 'foreign' | 'error:<...>'
    """
    if not CONFIG.get("mas_admin_base") or not CONFIG.get("mas_client_id"):
        return "error:not-configured"
    username = jid.split(":", 1)[0].lstrip("@")
    try:
        st, d = _mas_admin("GET", "/api/admin/v1/users/by-username/" + urllib.parse.quote(username))
        if st != 200:
            return "error:user-lookup-%d" % st
        uid = (d.get("data") or {}).get("id")
        if not uid:
            return "error:no-user-id"
        st, d = _mas_admin("POST", "/api/admin/v1/personal-sessions", {
            "actor_user_id": uid, "human_name": "qr-cs-setup",
            "scope": "urn:matrix:client:api:*", "expires_in": 300,
        })
        if not (200 <= st < 300):
            return "error:session-%d" % st
        tok = ((d.get("data") or {}).get("attributes") or {}).get("access_token")
        psid = (d.get("data") or {}).get("id")
        if not tok:
            return "error:no-token"
        syn = CONFIG["synapse_url"]
        try:
            # check current state
            st, rawq, _hq = _http("POST", syn + "/_matrix/client/v3/keys/query",
                                  data=json.dumps({"device_keys": {jid: []}}).encode(),
                                  headers={"Authorization": _HDR_BEARER + tok, "Content-Type": "application/json"})
            cur = {}
            try:
                cur = json.loads(rawq.decode() or "{}")
            except Exception:
                cur = {}
            marker = _ed_pub(triplet[0])
            mk = (cur.get("master_keys") or {}).get(jid) or {}
            if mk:
                vals = list((mk.get("keys") or {}).values())
                return "already" if marker in vals else "foreign"
            # build + upload
            msk_pub = marker
            ssk_pub = _ed_pub(triplet[1])
            usk_pub = _ed_pub(triplet[2])
            ssk_obj = {"user_id": jid, "usage": ["self_signing"],
                       "keys": {"ed25519:" + ssk_pub: ssk_pub}}
            ssk_obj["signatures"] = {jid: {"ed25519:" + msk_pub: b64e(_ed_priv(triplet[0]).sign(_canon(ssk_obj)))}}
            usk_obj = {"user_id": jid, "usage": ["user_signing"],
                       "keys": {"ed25519:" + usk_pub: usk_pub}}
            usk_obj["signatures"] = {jid: {"ed25519:" + msk_pub: b64e(_ed_priv(triplet[0]).sign(_canon(usk_obj)))}}
            master_obj = {"user_id": jid, "usage": ["master"],
                          "keys": {"ed25519:" + msk_pub: msk_pub}}
            payload = {"master_key": master_obj, "self_signing_key": ssk_obj, "user_signing_key": usk_obj}
            st, rawu, _hu = _http("POST", syn + "/_matrix/client/v3/keys/device_signing/upload",
                                  data=json.dumps(payload).encode(),
                                  headers={"Authorization": _HDR_BEARER + tok, "Content-Type": "application/json"})
            if st == 200:
                return "uploaded"
            return "error:upload-%d" % st
        finally:
            if psid:
                _mas_admin("POST", "/api/admin/v1/personal-sessions/" + urllib.parse.quote(psid) + "/revoke", {})
    except Exception as e:  # noqa: BLE001
        return "error:" + str(e)[:100]


# --------------------------------------------------------------- session ----

class LinkSession:
    def __init__(self, jid, base_url, db_path=None):
        self.jid = jid
        self.base_url = base_url.rstrip("/")
        self.db_path = db_path
        self.id = _secrets.token_urlsafe(9)
        self.created = time.time()
        self.expires_at = self.created + TTL
        self.lock = threading.Lock()
        self.state = "init"
        self.error = None
        self.qr_png_b64 = None
        self.url = None
        self.etag = None
        self.priv = None
        self.gp_b64 = None
        self.ch = None
        self.expected_code = None
        self.protocol = None
        self.device_id = None
        self.confirm_url = None
        self.last_err = None

    # -- transport helpers --
    def _rz_get(self):
        hdrs = {}
        if self.etag:
            hdrs["If-None-Match"] = self.etag
        st, raw, h = _http("GET", self.url, headers=hdrs)
        if h.get("etag"):
            self.etag = h["etag"]
        if st == 404:
            self.state = "expired"
            return None
        if st == 200 and h.get("content-type", "").startswith("text/plain"):
            return raw.decode()
        return None

    def _rz_put(self, data_str):
        st = raw = None
        for _ in range(2):
            hdrs = {"Content-Type": "text/plain"}
            if self.etag:
                hdrs["If-Match"] = self.etag
            st, raw, h = _http("PUT", self.url, data=data_str.encode(), headers=hdrs)
            if st in (200, 201, 202):
                if h.get("etag"):
                    self.etag = h["etag"]
                return True
            _ = self._rz_get()
        raise RuntimeError("rendezvous PUT failed: %s %s" % (st, (raw or b"")[:150]))

    # -- flow --
    def start(self):
        self.cs_status = "none"
        if self.db_path:
            try:
                self.cs_msk, self.cs_ssk, self.cs_usk = _load_or_create_cs(self.jid, self.db_path)
                if CONFIG.get("mas_admin_base"):
                    self.cs_status = ensure_cross_signing(self.jid, (self.cs_msk, self.cs_ssk, self.cs_usk))
            except Exception as e:  # noqa: BLE001 - fall back to per-session keys
                self.cs_msk = self.cs_ssk = self.cs_usk = None
                self.cs_status = "error:" + str(e)[:80]
        else:
            self.cs_msk = self.cs_ssk = self.cs_usk = None
        self.priv = gen_priv()
        self.gp_b64 = pub_b64(self.priv)
        st, raw, h = _http("POST", self.base_url + RZ_PATH, data=b"",
                           headers={"Content-Type": "text/plain"})
        if st not in (200, 201):
            raise RuntimeError("rendezvous create failed: %s %s" % (st, raw[:150]))
        d = json.loads(raw.decode())
        self.url = d["url"]
        self.etag = h.get("etag")
        server = self.base_url.split("://", 1)[1].split("/", 1)[0]
        ub = self.url.encode()
        qr = b"MATRIX" + bytes([0x02, 0x04]) + b64d(self.gp_b64)
        qr += len(ub).to_bytes(2, "big") + ub
        sb = server.encode()
        qr += len(sb).to_bytes(2, "big") + sb
        self.qr_png_b64 = qr_png_b64(qr)
        self.state = "waiting"

    def _send_failure(self, reason):
        msg = self.ch.encrypt(json.dumps({"type": "m.login.failure", "reason": reason}).encode())
        self._rz_put(msg)

    def _send_accepted(self):
        acc = self.ch.encrypt(json.dumps({"type": "m.login.protocol_accepted"}).encode())
        self._rz_put(acc)
        self.state = "confirm"
        self._start_keepalive()

    def _start_keepalive(self):
        """Keep the rendezvous session alive while waiting for the final messages."""
        if getattr(self, "_ka_started", False):
            return
        self._ka_started = True

        def loop():
            for _ in range(80):
                time.sleep(25)
                try:
                    self.poll()
                except Exception:  # noqa: BLE001
                    pass
                if self.state in ("done", "error", "expired"):
                    break

        t = threading.Thread(target=loop, daemon=True)
        t.start()

    def _device_belongs(self):
        """Check that the device that logged in belongs to this cabinet's user."""
        if not (CONFIG.get("mas_admin_base") and self.device_id):
            return True
        username = self.jid.split(":", 1)[0].lstrip("@")
        for _attempt in range(6):
            try:
                st, d = _mas_admin("GET", "/api/admin/v1/users/by-username/" + urllib.parse.quote(username))
                uid = (d.get("data") or {}).get("id")
                if uid:
                    st, d = _mas_admin("POST", "/api/admin/v1/personal-sessions", {
                        "actor_user_id": uid, "human_name": "qr-devcheck",
                        "scope": "urn:matrix:client:api:*", "expires_in": 120})
                    tok = ((d.get("data") or {}).get("attributes") or {}).get("access_token")
                    psid = (d.get("data") or {}).get("id")
                    if tok:
                        try:
                            st, raw, h = _http("GET", CONFIG["synapse_url"] + "/_matrix/client/v3/devices",
                                               headers={"Authorization": _HDR_BEARER + tok})
                            if st == 200:
                                for dev in (json.loads(raw.decode()).get("devices") or []):
                                    if dev.get("device_id") == self.device_id:
                                        return True
                        finally:
                            if psid:
                                _mas_admin("POST", "/api/admin/v1/personal-sessions/" + urllib.parse.quote(psid) + "/revoke", {})
            except Exception:
                pass
            time.sleep(1.5)
        return False

    def _handle(self, msg):
        if self.state == "waiting":
            ch, pt = establish_inbound(self.priv, msg)
            if pt != b"MATRIX_QR_CODE_LOGIN_INITIATE":
                raise RuntimeError("bad init plaintext: %r" % (pt[:60],))
            self.ch = ch
            self.expected_code = ch.check_code()
            ok = ch.encrypt(b"MATRIX_QR_CODE_LOGIN_OK")
            self._rz_put(ok)
            self.state = "code"
            return
        if self.state in ("code", "code_ok"):
            if self.protocol is not None:
                return
            data = json.loads(self.ch.decrypt(msg))
            t = data.get("type")
            if t == "m.login.failure":
                self.state = "error"
                self.error = "Вход отменён на телефоне"
                return
            if t != "m.login.protocol":
                self._send_failure("unexpected_message_received")
                self.state = "error"
                self.error = "Неожиданный ответ устройства"
                return
            if data.get("protocol") != "device_authorization_grant":
                self._send_failure("unsupported_protocol")
                self.state = "error"
                self.error = "Устройство не поддерживает вход по QR"
                return
            dag = data.get("device_authorization_grant") or {}
            self.confirm_url = dag.get("verification_uri_complete") or dag.get("verification_uri")
            self.device_id = data.get("device_id")
            self.protocol = data
            if self.state == "code_ok":
                self._send_accepted()
            return
        if self.state == "confirm":
            data = json.loads(self.ch.decrypt(msg))
            t = data.get("type")
            if t == "m.login.success":
                if not self._device_belongs():
                    try:
                        self._send_failure("device_not_found")
                    except Exception:
                        pass
                    self.state = "error"
                    self.error = ("Устройство не найдено в вашем аккаунте — возможно, вход подтверждён под другим "
                                  "пользователем. Убедитесь, что на странице подтверждения вы входите под тем же "
                                  "аккаунтом, что и в кабинете, и попробуйте снова.")
                    return
                sec_payload = {"type": "m.login.secrets"}
                if self.cs_msk and self.cs_ssk and self.cs_usk:
                    sec_payload["cross_signing"] = {
                        "master_key": self.cs_msk,
                        "user_signing_key": self.cs_usk,
                        "self_signing_key": self.cs_ssk,
                    }
                sec = self.ch.encrypt(json.dumps(sec_payload).encode())
                self._rz_put(sec)
                self.state = "done"
            elif t == "m.login.declined":
                self.state = "error"
                self.error = "Вход отклонён"
            elif t == "m.login.failure":
                self.state = "error"
                self.error = "Ошибка на телефоне: " + str(data.get("reason"))
            else:
                self._send_failure("unexpected_message_received")
                self.state = "error"
                self.error = "Неожиданный ответ устройства"
            return

    def poll(self):
        with self.lock:
            if self.state in ("done", "error", "expired"):
                return self.status()
            if time.time() > self.expires_at:
                self.state = "expired"
                return self.status()
            try:
                msg = self._rz_get()
                if msg:
                    self._handle(msg)
            except Exception as e:  # noqa: BLE001 - keep the loop alive
                self.last_err = str(e)[:200]
            return self.status()

    def submit_code(self, code):
        with self.lock:
            if self.state != "code":
                return {"ok": False, "message": "Сейчас код не требуется"}
            code = "".join(ch for ch in str(code) if ch.isdigit())[:2]
            if len(code) != 2:
                return {"ok": False, "message": "Введите две цифры"}
            if code != self.expected_code:
                return {"ok": False, "message": "Код не совпадает — проверьте цифры на телефоне"}
            self.state = "code_ok"
            if self.protocol is not None:
                self._send_accepted()
            return {"ok": True, "state": self.state}

    def status(self):
        return {
            "state": self.state,
            "done": self.state == "done",
            "error": self.error,
            "confirm_url": self.confirm_url if self.state == "confirm" else None,
            "expires_in": max(0, int(self.expires_at - time.time())),
        }


_SESSIONS = {}
_LOCK = threading.Lock()


def start_session(jid, base_url, db_path=None):
    st = LinkSession(jid, base_url, db_path)
    st.start()
    now = time.time()
    with _LOCK:
        for k in [k for k, v in _SESSIONS.items() if v.expires_at + 600 < now]:
            _SESSIONS.pop(k, None)
        _SESSIONS[st.id] = st
    return st


def get_session(sid):
    with _LOCK:
        return _SESSIONS.get(sid)
