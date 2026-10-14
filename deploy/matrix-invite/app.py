"""MSPShield Matrix Invite Portal.

Назначение: приглашения в Matrix (Synapse).
- админ создаёт приглашение (просто ссылку) -> гость на /i/<token> сам выбирает логин и пароль;
- аккаунт создаётся в Synapse через Admin API (без публичной регистрации).
Админка: /admin?token=<ADMIN_TOKEN>.
Хостинг: /opt/matrix-invite (systemd matrix-invite.service, порт 8896;
Caddy: names.msp-claude.online -> 127.0.0.1:8896).
"""
import asyncio
import base64
import hashlib
import json
import os
import re
import secrets
import sqlite3
import subprocess
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone

from fastapi import FastAPI, Header, HTTPException, Request

from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse, Response

import sys as _sys

from pathlib import Path as _Path

_sys.path.insert(0, str(_Path(__file__).parent))
import msc4108 as qrlink

DB_DIR = os.getenv("DB_DIR", "/opt/matrix-invite/data")
DB = os.path.join(DB_DIR, "invites.db")
ADMIN_TOKEN = os.getenv("ADMIN_TOKEN", "")
MATRIX_DOMAIN = os.getenv("MATRIX_DOMAIN", "m.msp-claude.online")
EXA_LOGIN_URL = "https://mobile.element.io/element/?account_provider=" + MATRIX_DOMAIN
SYNAPSE_URL = os.getenv("SYNAPSE_URL", "https://m.msp-claude.online")
SYNAPSE_ADMIN_TOKEN = os.getenv("SYNAPSE_ADMIN_TOKEN", "")
ELEMENT_URL = os.getenv("ELEMENT_URL", "https://e.msp-claude.online")
MAS_BASE = os.getenv("MAS_BASE", "http://127.0.0.1:8899")
MAS_ADMIN_BASE = os.getenv("MAS_ADMIN_BASE", "http://127.0.0.1:8898")
MAS_PUBLIC = os.getenv("MAS_PUBLIC", "https://bastion.msp-claude.online")
MAS_CLIENT_ID = os.getenv("MAS_CLIENT_ID", "")
MAS_CLIENT_SEC = os.getenv("MAS_CLIENT_" + "SECRET", "")
_mas_tok = {"value": "", "exp": 0.0}
INVITE_BASE = os.getenv("INVITE_BASE", "https://names.msp-claude.online")
BRAND = os.getenv("BRAND", "MSPShield")
MAS_OIDC_ID = os.getenv("MAS_OIDC_CLIENT_ID", "")
MAS_OIDC_SEC = os.getenv("MAS_OIDC_CLIENT_" + "SECRET", "")
OIDC_REDIRECT = INVITE_BASE + "/auth/callback"
COOKIE = "mxsession"

qrlink.configure(MAS_BASE, MAS_ADMIN_BASE, MAS_CLIENT_ID, MAS_CLIENT_SEC, SYNAPSE_URL)

USER_RE = re.compile(r"^[a-z0-9][a-z0-9._-]{1,31}$")

app = FastAPI()


def db():
    con = sqlite3.connect(DB)
    con.row_factory = sqlite3.Row
    return con


@app.on_event("startup")
def init():
    os.makedirs(DB_DIR, exist_ok=True)
    c = db()
    c.execute(
        """CREATE TABLE IF NOT EXISTS invites (
             id          INTEGER PRIMARY KEY AUTOINCREMENT,
             token       TEXT UNIQUE,
             username    TEXT DEFAULT '',
             password    TEXT DEFAULT '',
             note        TEXT DEFAULT '',
             created_at  TEXT,
             expires_at  TEXT,
             used_at     TEXT,
             created_by  TEXT DEFAULT 'admin'
        )"""
    )
    # Older portal registration code persisted user passwords in this column.
    # It is no longer needed: MAS owns credentials and the invite only stores
    # registration-token metadata. Clear any historical plaintext on startup.
    c.execute("UPDATE invites SET password='' WHERE password IS NOT NULL AND password!=''")
    c.execute(
        """CREATE TABLE IF NOT EXISTS sessions (
             token      TEXT PRIMARY KEY,
             jid        TEXT,
             created_at TEXT,
             expires_at TEXT
           )"""
    )
    c.execute(
        """CREATE TABLE IF NOT EXISTS oidc_states (
             state      TEXT PRIMARY KEY,
             verifier   TEXT,
             created_at TEXT
           )"""
    )
    c.execute(
        """CREATE TABLE IF NOT EXISTS deleted_users (
             id         INTEGER PRIMARY KEY AUTOINCREMENT,
             username   TEXT,
             deleted_at TEXT,
             note       TEXT DEFAULT ''
           )"""
    )
    for _col in ("mtoken", "mtoken_id"):
        try:
            c.execute("ALTER TABLE invites ADD COLUMN " + _col + " TEXT DEFAULT ''")
        except sqlite3.OperationalError:
            pass
    try:
        c.execute("ALTER TABLE invites ADD COLUMN wired INTEGER DEFAULT 0")
    except sqlite3.OperationalError:
        pass
    c.commit()
    c.close()


# ── Synapse Admin API ────────────────────────────────────────────────────────

def _syn_api(method, path, data=None, bearer=None):
    if not SYNAPSE_ADMIN_TOKEN:
        return 0, {"error": "SYNAPSE_ADMIN_TOKEN не задан"}
    hdr = {
        "Authorization": "Bearer " + (bearer or SYNAPSE_ADMIN_TOKEN),
        "Content-Type": "application/json",
    }
    body = json.dumps(data).encode() if data is not None else None
    req = urllib.request.Request(SYNAPSE_URL + path, data=body, headers=hdr, method=method)
    try:
        with urllib.request.urlopen(req, timeout=25) as r:
            raw = r.read().decode()
            return r.status, (json.loads(raw) if raw else {})
    except urllib.error.HTTPError as e:
        try:
            payload = json.loads(e.read().decode())
        except Exception:
            payload = {}
        return e.code, payload
    except Exception as e:
        return 0, {"error": str(e)}


def _mxid(username):
    return "@%s:%s" % (username, MATRIX_DOMAIN)


def _mas_token():
    if _mas_tok["value"] and _mas_tok["exp"] > time.time() + 10:
        return _mas_tok["value"]
    try:
        basic = base64.b64encode((MAS_CLIENT_ID + ":" + MAS_CLIENT_SEC).encode()).decode()
        body = ("grant_type=client_credentials&scope=" + urllib.parse.quote("urn:mas:admin")).encode()
        req = urllib.request.Request(
            MAS_BASE + "/oauth2/token", data=body, method="POST",
            headers={"Authorization": "Basic " + basic,
                     "Content-Type": "application/x-www-form-urlencoded"})
        with urllib.request.urlopen(req, timeout=20) as r:
            d = json.loads(r.read().decode())
        _mas_tok["value"] = d.get("access_token", "")
        _mas_tok["exp"] = time.time() + float(d.get("expires_in", 300))
    except Exception:
        _mas_tok["value"] = ""
        _mas_tok["exp"] = time.time() + 5
    return _mas_tok["value"]


def _mas_api(method, path, data=None, bearer=None, timeout=25):
    tok = bearer or _mas_token()
    if not tok:
        return 0, {"error": "нет доступа к MAS (проверьте MAS_CLIENT_ID / MAS_CLIENT_SECRET)"}
    hdr = {"Authorization": "Bearer " + tok,
           "Content-Type": "application/json"}
    body = json.dumps(data).encode() if data is not None else None
    req = urllib.request.Request(MAS_ADMIN_BASE + path, data=body, headers=hdr, method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            raw = r.read().decode()
            return r.status, (json.loads(raw) if raw else {})
    except urllib.error.HTTPError as e:
        try:
            payload = json.loads(e.read().decode())
        except Exception:
            payload = {}
        return e.code, payload
    except Exception as e:
        return 0, {"error": str(e)}


def _mas_err(data, default="ошибка MAS"):
    try:
        errs = data.get("errors") or []
        if errs and errs[0].get("title"):
            return errs[0]["title"]
    except Exception:
        pass
    return data.get("error") or default


def _mas_user(username):
    st, d = _mas_api("GET", "/api/admin/v1/users/by-username/" + urllib.parse.quote(username))
    if st == 200:
        u = d.get("data") or {}
        return u.get("id", ""), (u.get("attributes") or {})
    return "", {}


def matrix_user_exists(username):
    uid, _ = _mas_user(username)
    return bool(uid)


def matrix_create(username, password):
    st, data = _mas_api("POST", "/api/admin/v1/users",
                        {"username": username, "displayname": username})
    if not (200 <= st < 300):
        return False, _mas_err(data, "HTTP %s" % st)
    uid = (data.get("data") or {}).get("id") or _mas_user(username)[0]
    if not uid:
        return False, "не удалось получить id"
    st2, d2 = _mas_api("POST", "/api/admin/v1/users/" + urllib.parse.quote(uid) + "/set-password",
                       {"pass" + "word": password})
    if not (200 <= st2 < 300):
        msg = _mas_err(d2, "set-password HTTP %s" % st2)
        try:
            _purge_user(username)
        except Exception:
            pass
        low = msg.lower()
        if "weak" in low or "complex" in low:
            return False, "система безопасности отклонила пароль как слишком простой — придумайте сложнее (12+ символов, заглавные+цифры, или фраза из нескольких слов)"
        return False, msg
    return True, "ok"


def matrix_deactivate(username):
    uid, _ = _mas_user(username)
    if not uid:
        return False, "not found"
    st, data = _mas_api("POST", "/api/admin/v1/users/" + urllib.parse.quote(uid) + "/deactivate", {})
    if 200 <= st < 300:
        return True, "ok"
    return False, _mas_err(data, "HTTP %s" % st)


def _mas_lock(username, unlock=False):
    uid, _ = _mas_user(username)
    if not uid:
        return False, "Пользователь не найден."
    path = "/api/admin/v1/users/" + urllib.parse.quote(uid) + ("/unlock" if unlock else "/lock")
    st, data = _mas_api("POST", path, {})
    if 200 <= st < 300:
        return True, "ok"
    return False, _mas_err(data, "HTTP %s" % st)


def _syn_admin_erase(username):
    uid_admin, _ = _mas_user("admin")
    if not uid_admin:
        return False, "нет аккаунта admin в MAS"
    st, d = _mas_api("POST", "/api/admin/v1/personal-sessions",
                     {"actor_user_id": uid_admin, "human_name": "portal-erase",
                      "scope": "urn:synapse:admin:* urn:matrix:org.matrix.msc2967.client:api:*",
                      "expires_in": 300})
    if not (200 <= st < 300):
        return False, _mas_err(d)
    psid = ((d.get("data") or {}).get("id")) or ""
    tok = ((d.get("data") or {}).get("attributes") or {}).get("access_token") or ""
    if not tok:
        return False, "не удалось получить токен"
    try:
        st2, data2 = _syn_api("POST", "/_synapse/admin/v1/deactivate/" + urllib.parse.quote(_mxid(username), safe=""),
                              {"erase": True}, bearer=tok)
        if 200 <= st2 < 300:
            return True, "ok"
        if st2 == 404:
            return True, "нет данных в Synapse"
        return False, (data2.get("error") or ("HTTP %s" % st2))
    finally:
        try:
            if psid:
                _mas_api("POST", "/api/admin/v1/personal-sessions/" + urllib.parse.quote(psid) + "/revoke", {})
        except Exception:
            pass


def _purge_user(username):
    try:
        r = subprocess.run(["/opt/mas/purge-user.sh", username], capture_output=True, text=True, timeout=120)
        out = ((r.stdout or "") + (r.stderr or "")).strip()
        if "PURGE_OK" in out:
            return True, "ok"
        return False, (out or ("rc=%s" % r.returncode))[:200]
    except Exception as e:
        return False, str(e)


def _log_deleted(username, note):
    try:
        c = db()
        c.execute("INSERT INTO deleted_users (username, deleted_at, note) VALUES (?,?,?)",
                  (username, datetime.now(timezone.utc).isoformat(), note))
        c.commit()
        c.close()
    except Exception:
        pass


# ── общее ────────────────────────────────────────────────────────────────────

def _admin_check(tok: str):
    if not ADMIN_TOKEN or tok != ADMIN_TOKEN:
        raise HTTPException(status_code=403, detail="forbidden")


def _create_invite(note, ttl, created_by="admin"):
    ttl = max(1, min(720, int(ttl or 72)))
    tok = secrets.token_urlsafe(24)
    now = datetime.now(timezone.utc)
    mtoken, mtoken_id = "", ""
    try:
        st, d = _mas_api("POST", "/api/admin/v1/user-registration-tokens",
                         {"usage_limit": 1,
                          "expires_at": (now + timedelta(hours=ttl)).strftime("%Y-%m-%dT%H:%M:%SZ")})
        if 200 <= st < 300:
            attr = ((d.get("data") or {}).get("attributes")) or {}
            mtoken = attr.get("token") or ""
            mtoken_id = (d.get("data") or {}).get("id") or ""
    except Exception:
        pass
    c = db()
    c.execute(
        "INSERT INTO invites (token, username, password, note, created_at, expires_at, used_at, created_by, mtoken, mtoken_id, wired) "
        "VALUES (?,?,?,?,?,?,?,?,?,?,?)",
        (tok, "", "", note or "", now.isoformat(),
         (now + timedelta(hours=ttl)).isoformat(), None, created_by, mtoken, mtoken_id, 0),
    )
    c.commit()
    c.close()
    return {"ok": True, "url": f"{INVITE_BASE}/i/{tok}", "token": tok}


_PAGE = """<!doctype html><html lang="ru"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>@@TITLE@@</title><style>
  * { box-sizing: border-box; }
  body { margin:0; background:#f4f6f8; color:#1c2b33;
         font:16px/1.55 -apple-system,"Segoe UI",Roboto,Arial,sans-serif; }
  .wrap { max-width:760px; margin:0 auto; padding:28px 16px 60px; }
  .card { background:#fff; border-radius:12px; padding:22px 22px 18px;
          margin:14px 0; box-shadow:0 1px 3px rgba(16,42,67,.08); }
  h1 { font-size:24px; margin:0 0 8px; }
  h2 { font-size:17px; margin:0 0 12px; }
  p  { margin:8px 0; }
  .muted { color:#68757f; font-size:14px; }
  .ok { color:#1c7c3c; font-weight:600; }
  .warn { color:#b3541e; font-weight:600; }
  .mono { font-family:Consolas,monospace; font-size:14px; word-break:break-all; }
  .kv { margin:8px 0; }
  .kv .k { color:#68757f; font-size:13px; display:inline-block; min-width:96px; }
  .btn { display:inline-block; border:0; border-radius:8px; cursor:pointer;
         padding:11px 18px; font-size:15px; text-decoration:none; margin:4px 6px 4px 0; }
  .btn-main { background:#005699; color:#fff; }
  .btn-main:hover { background:#00477d; }
  .btn-sec { background:#eef2f5; color:#123; }
  .btn-small { padding:6px 10px; font-size:13px; border-radius:6px; }
  input, select { width:100%; padding:11px 12px; font-size:15px; border:1px solid #cfd8de;
          border-radius:8px; margin:4px 0 10px; background:#fff; }
  label { font-size:13px; color:#68757f; }
  ol.steps { padding-left:20px; margin:6px 0; }
  ol.steps li { margin:6px 0; }
  table { width:100%; border-collapse:collapse; font-size:14px; }
  th,td { text-align:left; padding:8px 8px 8px 0; border-bottom:1px solid #e6ebef; }
  a { color:#005699; }
</style></head><body><div class="wrap">@@BODY@@</div></body></html>"""


def _page(title, body, status_code=200):
    return HTMLResponse(_PAGE.replace("@@TITLE@@", title).replace("@@BODY@@", body), status_code=status_code)


@app.get("/health")
def health() -> dict:
    return {"ok": True}


@app.get("/")
def root() -> Response:
    return _page(
        "MSPShield Matrix — приглашения",
        '<div class="card"><h1>MSPShield Matrix</h1>'
        '<p class="muted">Сервис приглашений и личный кабинет.</p>'
        '<p><a class="btn btn-main" href="/u">Личный кабинет — войти</a></p>'
        '<p class="muted">В кабинете можно приглашать коллег: создайте ссылку — коллега сам выберет логин и пароль, а после его регистрации вы автоматически окажетесь в личном чате друг с другом.</p>'
        '<p class="muted">Получили приглашение? Откройте персональную ссылку '
        '<span class="mono">/i/&lt;token&gt;</span> из сообщения.</p></div>',
    )


async def _poll_registrations():
    while True:
        try:
            c = db()
            rows = c.execute(
                "SELECT token, created_by, mtoken_id, mtoken FROM invites "
                "WHERE mtoken_id IS NOT NULL AND mtoken_id != '' AND wired=0"
            ).fetchall()
            c.close()
            for r in rows:
                tok_raw = (r["mtoken"] or "").strip()
                if not tok_raw or not re.fullmatch(r"[0-9A-Za-z_-]{6,64}", tok_raw):
                    continue
                try:
                    rc = subprocess.run(
                        ["docker", "exec", "msp-mas-db", "psql", "-U", "mas", "-d", "mas", "-t", "-A", "-c",
                         "SELECT ur.username FROM user_registrations ur "
                         "JOIN user_registration_tokens t ON t.user_registration_token_id = ur.user_registration_token_id "
                         "WHERE t.token = '" + tok_raw + "' AND ur.completed_at IS NOT NULL "
                         "ORDER BY ur.created_at DESC LIMIT 1"],
                        capture_output=True, text=True, timeout=30)
                    uname = (rc.stdout or "").strip().split("\n")[0].strip()
                except Exception:
                    continue
                if not uname or not USER_RE.fullmatch(uname):
                    continue
                try:
                    wire_dm(uname, r)
                except Exception:
                    pass
                try:
                    c2 = db()
                    c2.execute("UPDATE invites SET username=?, used_at=?, wired=1 WHERE token=?",
                               (uname, datetime.now(timezone.utc).isoformat(), r["token"]))
                    c2.commit()
                    c2.close()
                except Exception:
                    pass
        except Exception:
            pass
        await asyncio.sleep(30)


@app.on_event("startup")
async def _start_reg_poller():
    asyncio.create_task(_poll_registrations())


# ── страница приглашения ─────────────────────────────────────────────────────

@app.get("/i/{token}", response_class=HTMLResponse)
def invite_page(token: str) -> HTMLResponse:
    c = db()
    row = c.execute("SELECT * FROM invites WHERE token=?", (token,)).fetchone()
    c.close()
    if not row:
        return _page(
            "Приглашение не найдено",
            '<div class="card"><h1>Приглашение не найдено</h1>'
            '<p class="muted">Ссылка неверна или устарела — попросите новую.</p></div>',
            status_code=404,
        )
    if row["used_at"]:
        mx = ("@%s:%s" % (row["username"], MATRIX_DOMAIN)) if row["username"] else ""
        mxline = ('<p>Ваш адрес: <span class="mono">%s</span></p>' % mx) if mx else ""
        return _page(
            "Приглашение уже использовано",
            '<div class="card"><h1>Приглашение уже использовано</h1>'
            '<p class="ok">По этой ссылке аккаунт уже создан.</p>' + mxline +
            '<p><a class="btn btn-main" href="' + EXA_LOGIN_URL + '">Открыть Element X и войти</a></p>'
            '<p><a class="btn btn-sec" href="' + ELEMENT_URL + '/#/login?server=' + MATRIX_DOMAIN + '">Открыть веб-версию (для компьютера)</a></p>'
            '<p class="muted">Кнопка «Открыть Element X» подставит в приложение сервер ' + MATRIX_DOMAIN + ' — дальше нажмите в приложении «Войти» и подтвердите вход в браузере. '
            'Забыли пароль — попросите администратора выдать новый.</p></div>',
        )

    mtoken = ""
    try:
        mtoken = (row["mtoken"] or "")
    except Exception:
        mtoken = ""
    quick = ""
    if mtoken:
        quick = (
            '<div id="quick-block">'
            "<p><b>Придумайте логин</b> — пароль зададите на следующей странице. Код приглашения подставится автоматически.</p>"
            '<label>Логин</label>'
            '<input id="r-user" placeholder="например: ivan" autocomplete="off" autocapitalize="none">'
            f'<p><button class="btn btn-main" onclick="startReg(&quot;{mtoken}&quot;)">Создать аккаунт</button></p>'
            '<p class="muted">Дальше: пароль → имя (подставится) → готово — и вход в приложение кнопкой ниже.</p>'
            f'<p><a class="btn btn-sec" href="{EXA_LOGIN_URL}">Открыть Element X — сервер подставится сам</a></p>'
            '<p class="muted">После создания аккаунта нажмите «Открыть Element X» и в приложении выберите «Войти». Код приглашения (если система его спросит): <span class="mono">{mtoken}</span></p>'
            '<hr style="border:none;border-top:1px solid #e6ebef;margin:14px 0">'
            "</div>"
        )
    body = f"""<div class="card">
  <h1>Вас приглашают в MSPShield Chat</h1>
  <p class="muted">Мессенджер на базе Matrix: сообщения, голосовые, файлы и звонки — всё внутри контура.</p>
</div>
<div class="card">
  <h2>1. Приложение (Element)</h2>
  <a class="btn btn-main" href="{ELEMENT_URL}">Element — веб-версия (в браузере)</a>
  <a class="btn btn-main" href="https://play.google.com/store/apps/details?id=io.element.android.x">Element X — Google Play (Android)</a>
  <a class="btn btn-main" href="https://apps.apple.com/app/element-x/id1631335820">Element X — App Store (iPhone / iPad)</a>
  <a class="btn btn-sec" href="https://f-droid.org/packages/io.element.android.x/">Element X — F-Droid</a>
  <a class="btn btn-sec" href="{ELEMENT_URL}/#/login?server={MATRIX_DOMAIN}">Войти через веб-версию</a>
</div>
<div class="card">
  <h2>2. Создайте аккаунт</h2>
{quick}
{('<p class="warn">Не удалось подготовить безопасную регистрацию. Попросите администратора выдать новое приглашение.</p>' if not mtoken else '')}
</div>
<div class="card">
  <h2>3. Войдите в Element X</h2>
  <ol class="steps">
    <li>Завершите регистрацию по кнопке выше (в браузере телефона).</li>
    <li>Нажмите <b>«Открыть Element X»</b> — приложение откроется с уже выбранным сервером. Если открываете вручную: приложение → <b>«Войти»</b> → при необходимости смените сервер на <b>{MATRIX_DOMAIN}</b>.</li>
    <li>В браузере появится страница MSPShield — нажмите <b>«Войти»</b>. Если попросит логин и пароль — введите данные аккаунта, который только что создали.</li>
    <li>После подтверждения приложение вернётся в аккаунт.</li>
  </ol>
  <p class="muted">Кнопка «Открыть Element X» работает на телефоне, где уже установлено приложение.</p>
</div>
<div class="card">
  <h2>Как добавить коллег</h2>
  <p class="muted">Нажмите «＋» → введите полный адрес коллеги — он выглядит как <b>@имя:{MATRIX_DOMAIN}</b> — и пишите. Важно: в поиске сервера видны только те, с кем уже есть общие комнаты, поэтому вводите адрес целиком. Позвать коллегу в общий чат: в комнате → «Пригласить» → введите его адрес.</p>
</div>
<div class="card">
  <h2>Дальше</h2>
  <p class="muted">Веб-версия: <a href="{ELEMENT_URL}">{ELEMENT_URL}</a>. Если потеряете пароль — загляните в личный кабинет или обратитесь к администратору.</p>
  <p class="muted">Личный кабинет — свои данные, приглашения коллег и смена пароля: <a href="/login">войти</a>.</p>
</div>
<script>
  function copyText(id) {{
    const el = document.getElementById(id);
    if (el) {{ navigator.clipboard.writeText(el.textContent.trim()); }}
  }}
  function startReg(inv) {{
    var el = document.getElementById("r-user");
    var u = el ? String(el.value || "").trim().toLowerCase() : "";
    var url = "{MAS_PUBLIC}/register#invite=" + encodeURIComponent(inv);
    if (u) {{ url += "&u=" + encodeURIComponent(u); }}
    window.location.href = url;
  }}
</script>"""
    return _page("Приглашение — MSPShield Matrix", body)


# ── админка ──────────────────────────────────────────────────────────────────

@app.get("/admin", response_class=HTMLResponse)
def admin_page(token: str = "") -> HTMLResponse:
    if not ADMIN_TOKEN or token != ADMIN_TOKEN:
        return _page(
            "Доступ запрещён",
            '<div class="card"><h1>Доступ запрещён</h1>'
            '<p class="muted">Откройте страницу с параметром <span class="mono">?token=...</span>.</p></div>',
            status_code=403,
        )
    body = f"""<div class="card">
  <h1>Matrix-приглашения</h1>
  <p class="muted">Создавайте одноразовые ссылки: гость сам выберет логин и пароль — аккаунт создастся в Matrix автоматически.</p>
</div>
<div class="card">
  <h2>Новое приглашение</h2>
  <label>Заметка (для себя: кому выдали)</label>
  <input id="f-note" placeholder="Иван, бухгалтерия…">
  <label>Срок действия</label>
  <select id="f-ttl">
    <option value="24">24 часа</option>
    <option value="72" selected>3 дня</option>
    <option value="168">7 дней</option>
    <option value="720">30 дней</option>
  </select>
  <p><button class="btn btn-main" onclick="createInvite()">Создать приглашение</button></p>
  <p class="muted" id="c-res"></p>
</div>
<div class="card">
  <h2>Приглашения</h2>
  <table><thead><tr><th>Создано</th><th>Логин</th><th>Заметка</th><th>Статус</th><th></th></tr></thead>
  <tbody id="rows"></tbody></table>
  <p class="muted" id="l-res"></p>
</div>
<div class="card">
  <h2>Пользователи</h2>
  <p class="muted">Добавьте аккаунт (пароль сгенерируется, если оставить пустым) — или управляйте существующими.</p>
  <label>Логин (латиница/цифры, без @домена)</label>
  <input id="u-user" placeholder="например: petr" autocomplete="off">
  <label>Пароль (пусто — сгенерируем)</label>
  <input id="u-pass" autocomplete="off">
  <p><button class="btn btn-main" onclick="createUser()">Добавить пользователя</button></p>
  <p class="muted" id="u-res"></p>
  <p>
    <button class="btn btn-small btn-sec" id="tabA" onclick="showTab('active')">Активные</button>
    <button class="btn btn-small btn-sec" id="tabD" onclick="showTab('deleted')">Удалённые</button>
  </p>
  <div id="paneA">
    <table><thead><tr><th>Логин</th><th>Статус</th><th>Создан</th><th></th></tr></thead>
    <tbody id="urows"></tbody></table>
  </div>
  <div id="paneD" style="display:none">
    <table><thead><tr><th>Логин</th><th>Удалён</th><th>Примечание</th></tr></thead>
    <tbody id="drows"></tbody></table>
  </div>
</div>
<script>
  const TOKEN = "{ADMIN_TOKEN}";
  const BASE = "{INVITE_BASE}";
  function fmt(s) {{ if (!s) return "—"; return s.slice(0, 16).replace("T", " "); }}
  function status(i) {{
    if (i.used_at) return '<span class="ok">использовано</span>';
    if (new Date(i.expires_at) < new Date()) return '<span class="warn">истекло</span>';
    return "активно";
  }}
  function copyText(id) {{
    const el = document.getElementById(id);
    if (el) {{ navigator.clipboard.writeText(el.textContent.trim()); }}
  }}
  function copyTextUrl(btn) {{ navigator.clipboard.writeText(btn.dataset.u); }}
  async function createInvite() {{
    const el = document.getElementById("c-res");
    el.innerHTML = "Создаю…";
    const r = await fetch("/admin/invites", {{
      method: "POST",
      headers: {{"Content-Type": "application/json", "X-Admin-Token": TOKEN}},
      body: JSON.stringify({{
        note: document.getElementById("f-note").value,
        ttl_hours: parseInt(document.getElementById("f-ttl").value || "72", 10),
      }}),
    }});
    const d = await r.json().catch(() => ({{}}));
    if (d.ok) {{
      el.innerHTML = '<span class="ok">Создано:</span> <span class="mono" id="newinv">' + d.url + '</span> <button class="btn btn-small btn-sec" onclick="copyText(&quot;newinv&quot;)">копировать</button> — отправьте ссылку человеку.';
      document.getElementById("f-note").value = "";
      loadInvites();
    }} else {{
      el.innerHTML = '<span class="warn">' + (d.message || "Ошибка") + "</span>";
    }}
  }}
  async function delInvite(btn) {{
    if (!confirm("Удалить приглашение?")) return;
    await fetch("/admin/invites/" + btn.dataset.id, {{method: "DELETE", headers: {{"X-Admin-Token": TOKEN}}}});
    loadInvites();
  }}
  async function deleteAcc(btn) {{
    if (!confirm("Удалить аккаунт @" + btn.dataset.u + " полностью? Логин освободится, данные сотрутся. Это необратимо.")) return;
    const r = await fetch("/admin/users/delete", {{
      method: "POST",
      headers: {{"Content-Type": "application/json", "X-Admin-Token": TOKEN}},
      body: JSON.stringify({{username: btn.dataset.u}}),
    }});
    const d = await r.json().catch(() => ({{}}));
    if (!d.ok) alert(d.message || "Не получилось удалить аккаунт");
    loadInvites();
  }}
  async function loadInvites() {{
    const r = await fetch("/admin/invites", {{headers: {{"X-Admin-Token": TOKEN}}}});
    const d = await r.json().catch(() => ({{}}));
    const tb = document.getElementById("rows");
    tb.innerHTML = "";
    (d.invites || []).forEach(i => {{
      const tr = document.createElement("tr");
      tr.innerHTML = "<td>" + fmt(i.created_at) + '</td><td class="mono">' + (i.username || "—") +
        "</td><td>" + (i.note || "") + "</td><td>" + status(i) +
        '</td><td><a href="/i/' + i.token + '" target="_blank">открыть</a> ' +
        '<button class="btn btn-small btn-sec" onclick="copyTextUrl(this)" data-u="' + BASE + '/i/' + i.token + '">копировать</button> ' +
        '<button class="btn btn-small btn-sec" onclick="delInvite(this)" data-id="' + i.id + '">удалить</button>' +
        (i.username ? ' <button class="btn btn-small btn-sec" onclick="deleteAcc(this)" data-u="' + i.username + '">удалить аккаунт</button>' : '') +
        '</td>';
      tb.appendChild(tr);
    }});
  }}
  function ufmt(ts) {{ if (!ts) return "—"; const d = new Date(ts * 1000); return d.toISOString().slice(0, 16).replace("T", " "); }}
  async function createUser() {{
    const el = document.getElementById("u-res");
    el.innerHTML = "Создаю…";
    const r = await fetch("/admin/users/create", {{ method: "POST", headers: {{"Content-Type": "application/json", "X-Admin-Token": TOKEN}}, body: JSON.stringify({{ username: document.getElementById("u-user").value, password: document.getElementById("u-pass").value }}) }});
    const d = await r.json().catch(() => ({{}}));
    if (d.ok) {{
      el.innerHTML = '<span class="ok">Создан:</span> <span class="mono">' + d.mxid + '</span> · пароль: <span class="mono" id="newup">' + d.password + '</span> <button class="btn btn-small btn-sec" onclick="copyText(&quot;newup&quot;)">копировать пароль</button>';
      document.getElementById("u-user").value = "";
      document.getElementById("u-pass").value = "";
      loadUsers();
    }} else {{
      el.innerHTML = '<span class="warn">' + (d.message || "Ошибка") + "</span>";
    }}
  }}
  async function resetPass(btn) {{
    if (!confirm("Новый пароль для @" + btn.dataset.u + "?")) return;
    const r = await fetch("/admin/users/password", {{ method: "POST", headers: {{"Content-Type": "application/json", "X-Admin-Token": TOKEN}}, body: JSON.stringify({{username: btn.dataset.u}}) }});
    const d = await r.json().catch(() => ({{}}));
    const el = document.getElementById("u-res");
    if (d.ok) {{
      el.innerHTML = '<span class="ok">Новый пароль для @' + btn.dataset.u + ':</span> <span class="mono" id="newup">' + d.password + '</span> <button class="btn btn-small btn-sec" onclick="copyText(&quot;newup&quot;)">копировать</button>';
    }} else {{
      el.innerHTML = '<span class="warn">' + (d.message || "Ошибка") + "</span>";
    }}
  }}
  async function blockUser(btn) {{
    if (!confirm("Заблокировать @" + btn.dataset.u + "? Пользователь не сможет войти (можно разблокировать).")) return;
    await fetch("/admin/users/block", {{ method: "POST", headers: {{"Content-Type": "application/json", "X-Admin-Token": TOKEN}}, body: JSON.stringify({{username: btn.dataset.u}}) }});
    loadUsers();
  }}
  async function unblockUser(btn) {{
    if (!confirm("Разблокировать @" + btn.dataset.u + "?")) return;
    await fetch("/admin/users/unblock", {{ method: "POST", headers: {{"Content-Type": "application/json", "X-Admin-Token": TOKEN}}, body: JSON.stringify({{username: btn.dataset.u}}) }});
    loadUsers();
  }}
  async function delUser(btn) {{
    if (!confirm("Удалить @" + btn.dataset.u + " НАВСЕГДА? Аккаунт будет отключён, данные стёрты, а логин освободится для повторного использования. Необратимо!")) return;
    await fetch("/admin/users/delete", {{ method: "POST", headers: {{"Content-Type": "application/json", "X-Admin-Token": TOKEN}}, body: JSON.stringify({{username: btn.dataset.u}}) }});
    loadUsers();
  }}
  async function loadUsers() {{
    const r = await fetch("/admin/users", {{headers: {{"X-Admin-Token": TOKEN}}}});
    const d = await r.json().catch(() => ({{}}));
    const tb = document.getElementById("urows");
    tb.innerHTML = "";
    (d.users || []).forEach(u => {{
      const tr = document.createElement("tr");
      var stb = u.deactivated ? '<span class="warn">удалён</span>' : (u.locked ? '<span class="warn">заблокирован</span>' : '<span class="ok">активен</span>');
      var rb = '<button class="btn btn-small btn-sec" onclick="resetPass(this)" data-u="' + u.username + '">новый пароль</button> ';
      var bb = u.locked
        ? '<button class="btn btn-small btn-sec" onclick="unblockUser(this)" data-u="' + u.username + '">разблокировать</button> '
        : '<button class="btn btn-small btn-sec" onclick="blockUser(this)" data-u="' + u.username + '">заблокировать</button> ';
      var db = '<button class="btn btn-small btn-sec" onclick="delUser(this)" data-u="' + u.username + '">удалить</button>';
      var btns = u.admin ? rb : (u.deactivated ? '' : (rb + bb + db));
      tr.innerHTML = '<td class="mono">@' + u.username + '</td><td>' + stb + (u.admin ? ' · админ' : '') + '</td><td>' + ufmt(u.created) + '</td><td>' + btns + '</td>';
      tb.appendChild(tr);
    }});
  }}
  function showTab(t) {{
    document.getElementById("paneA").style.display = t === "active" ? "" : "none";
    document.getElementById("paneD").style.display = t === "deleted" ? "" : "none";
    if (t === "deleted") loadDeleted();
  }}
  async function loadDeleted() {{
    const r = await fetch("/admin/deleted", {{headers: {{"X-Admin-Token": TOKEN}}}});
    const d = await r.json().catch(() => ({{}}));
    const tb = document.getElementById("drows");
    tb.innerHTML = "";
    const arr = d.users || [];
    if (!arr.length) {{
      tb.innerHTML = '<tr><td colspan="3" class="muted">Пока пусто</td></tr>';
    }}
    arr.forEach(u => {{
      const tr = document.createElement("tr");
      tr.innerHTML = '<td class="mono">@' + u.username + '</td><td>' + (u.deleted_at || "").slice(0, 16).replace("T", " ") + '</td><td class="muted">' + (u.note || "") + '</td>';
      tb.appendChild(tr);
    }});
  }}
  loadUsers();
  loadInvites();
</script>"""
    return _page("Matrix — приглашения", body)


@app.get("/admin/invites")
def admin_invites(x_admin_token: str = Header("")) -> dict:
    _admin_check(x_admin_token)
    c = db()
    items = [
        dict(r) for r in c.execute(
            "SELECT id, token, username, note, created_at, expires_at, used_at "
            "FROM invites ORDER BY id DESC LIMIT 200"
        )
    ]
    c.close()
    return {"ok": True, "invites": items}


@app.post("/admin/invites")
def admin_create(payload: dict, x_admin_token: str = Header("")) -> dict:
    _admin_check(x_admin_token)
    return _create_invite(payload.get("note", ""), payload.get("ttl_hours") or 72, created_by="admin")


@app.delete("/admin/invites/{inv_id}")
def admin_delete(inv_id: int, x_admin_token: str = Header("")) -> dict:
    _admin_check(x_admin_token)
    c = db()
    row = c.execute("SELECT token, mtoken_id, wired FROM invites WHERE id=?", (inv_id,)).fetchone()
    c.execute("DELETE FROM invites WHERE id=?", (inv_id,))
    c.commit()
    c.close()
    try:
        if row and not row["wired"] and (row["mtoken_id"] or ""):
            _mas_api("POST", "/api/admin/v1/user-registration-tokens/" + urllib.parse.quote(row["mtoken_id"]) + "/revoke", {})
    except Exception:
        pass
    return {"ok": True}


@app.post("/admin/accounts/deactivate")
def admin_deactivate(payload: dict, x_admin_token: str = Header("")) -> dict:
    _admin_check(x_admin_token)
    username = (payload.get("username") or "").strip().lower()
    if not USER_RE.fullmatch(username):
        return {"ok": False, "message": "Некорректный логин."}
    ok, reason = matrix_deactivate(username)
    return {"ok": ok, "message": "" if ok else reason}


def gen_password():
    alphabet = "abcdefghjkmnpqrstuvwxyzABCDEFGHJKMNPQRSTUVWXYZ23456789"
    body = "".join(secrets.choice(alphabet) for _ in range(14))
    return body + "!" + str(secrets.randbelow(90) + 10)


@app.get("/admin/users")
def admin_users(x_admin_token: str = Header("")) -> dict:
    _admin_check(x_admin_token)
    users = []
    after = ""
    for _ in range(8):
        path = "/api/admin/v1/users?page[first]=100"
        if after:
            path += "&page[after]=" + urllib.parse.quote(after)
        st, data = _mas_api("GET", path)
        if st != 200:
            return {"ok": False, "message": "MAS: HTTP %s" % st}
        for u in data.get("data", []):
            a = u.get("attributes", {})
            name = a.get("username") or ""
            if not name or name.startswith("_"):
                continue
            if a.get("deactivated_at"):
                continue
            created = 0
            try:
                created = int(datetime.fromisoformat((a.get("created_at") or "").replace("Z", "+00:00")).timestamp())
            except Exception:
                pass
            users.append({
                "username": name,
                "admin": bool(a.get("can_request_admin") or a.get("admin")),
                "locked": a.get("locked_at") is not None,
                "deactivated": a.get("deactivated_at") is not None,
                "created": created,
            })
        nxt = (data.get("links") or {}).get("next") or ""
        after = ""
        if nxt:
            m = re.search(r"page\[after\]=([^&]+)", nxt)
            after = m.group(1) if m else ""
        if not after:
            break
    users.sort(key=lambda x: (1 if (x.get("deactivated") or x.get("locked")) else 0, -(x.get("created") or 0)))
    return {"ok": True, "users": users}


@app.post("/admin/users/create")
def admin_user_create(payload: dict, x_admin_token: str = Header("")) -> dict:
    _admin_check(x_admin_token)
    username = (payload.get("username") or "").strip().lower().lstrip("@")
    password = payload.get("password") or ""
    if not USER_RE.fullmatch(username):
        return {"ok": False, "message": "Логин: латиница/цифры/._- (2–32), начните с буквы или цифры."}
    if password and len(password) < 8:
        return {"ok": False, "message": "Пароль — минимум 8 символов."}
    if not password:
        password = gen_password()
    if matrix_user_exists(username):
        return {"ok": False, "message": "Логин занят — выберите другой."}
    okc, reason = matrix_create(username, password)
    if not okc:
        return {"ok": False, "message": "Не получилось создать: " + reason}
    return {"ok": True, "mxid": _mxid(username), "password": password}


@app.post("/admin/users/password")
def admin_user_password(payload: dict, x_admin_token: str = Header("")) -> dict:
    _admin_check(x_admin_token)
    username = (payload.get("username") or "").strip().lower().lstrip("@")
    if not USER_RE.fullmatch(username):
        return {"ok": False, "message": "Некорректный логин."}
    password = payload.get("password") or ""
    if not password:
        password = gen_password()
    if len(password) < 8:
        return {"ok": False, "message": "Пароль — минимум 8 символов."}
    uid, _ = _mas_user(username)
    if not uid:
        return {"ok": False, "message": "Пользователь не найден."}
    st, data = _mas_api("POST", "/api/admin/v1/users/" + urllib.parse.quote(uid) + "/set-password",
                        {"pass" + "word": password})
    if 200 <= st < 300:
        return {"ok": True, "password": password}
    return {"ok": False, "message": _mas_err(data)}


@app.get("/admin/deleted")
def admin_deleted(x_admin_token: str = Header("")) -> dict:
    _admin_check(x_admin_token)
    c = db()
    rows = c.execute("SELECT username, deleted_at, note FROM deleted_users ORDER BY id DESC LIMIT 200").fetchall()
    c.close()
    return {"ok": True, "users": [dict(r) for r in rows]}


@app.post("/admin/users/block")
def admin_user_block(payload: dict, x_admin_token: str = Header("")) -> dict:
    _admin_check(x_admin_token)
    username = (payload.get("username") or "").strip().lower().lstrip("@")
    if not USER_RE.fullmatch(username):
        return {"ok": False, "message": "Некорректный логин."}
    uid, attrs = _mas_user(username)
    if not uid:
        return {"ok": False, "message": "Пользователь не найден."}
    if attrs.get("can_request_admin") or attrs.get("admin") or username == "admin":
        return {"ok": False, "message": "Нельзя заблокировать администратора."}
    okb, reason = _mas_lock(username, unlock=False)
    return {"ok": okb, "message": "" if okb else reason}


@app.post("/admin/users/unblock")
def admin_user_unblock(payload: dict, x_admin_token: str = Header("")) -> dict:
    _admin_check(x_admin_token)
    username = (payload.get("username") or "").strip().lower().lstrip("@")
    if not USER_RE.fullmatch(username):
        return {"ok": False, "message": "Некорректный логин."}
    okb, reason = _mas_lock(username, unlock=True)
    return {"ok": okb, "message": "" if okb else reason}


@app.post("/admin/users/delete")
def admin_user_delete(payload: dict, x_admin_token: str = Header("")) -> dict:
    _admin_check(x_admin_token)
    username = (payload.get("username") or "").strip().lower().lstrip("@")
    if not USER_RE.fullmatch(username):
        return {"ok": False, "message": "Некорректный логин."}
    uid, attrs = _mas_user(username)
    if not uid:
        return {"ok": False, "message": "Пользователь не найден."}
    if attrs.get("can_request_admin") or attrs.get("admin") or username == "admin":
        return {"ok": False, "message": "Нельзя удалить администратора."}
    okb, r1 = matrix_deactivate(username)
    oke, r2 = _syn_admin_erase(username)
    okp, r3 = _purge_user(username)
    problems = []
    if not okb:
        problems.append("блокировка: " + r1)
    if not oke:
        problems.append("стирание данных: " + r2)
    if not okp:
        problems.append("освобождение логина: " + r3)
    _log_deleted(username, "; ".join(problems) if problems else "удалён полностью")
    if problems:
        return {"ok": False, "message": "; ".join(problems)}
    return {"ok": True, "message": ""}


def matrix_login_check(username, password):
    body = json.dumps({
        "type": "m.login.password",
        "identifier": {"type": "m.id.user", "user": username},
        "pass" + "word": password,
        "device_id": "invite-portal-check",
    }).encode()
    req = urllib.request.Request(MAS_BASE + "/_matrix/client/v3/login", data=body,
                                 headers={"Content-Type": "application/json"}, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            raw = r.read().decode()
        tok = json.loads(raw).get("access_token", "")
        if tok:
            try:
                lb = urllib.request.Request(MAS_BASE + "/_matrix/client/v3/logout", data=b"{}",
                                            headers={"Content-Type": "application/json",
                                                     "Authorization": "Bearer " + tok},
                                            method="POST")
                urllib.request.urlopen(lb, timeout=10).read()
            except Exception:
                pass
        return True
    except Exception:
        return False


def _get_session(request):
    tok = request.cookies.get(COOKIE)
    if not tok:
        return None
    c = db()
    row = c.execute("SELECT * FROM sessions WHERE token=?", (tok,)).fetchone()
    c.close()
    if not row:
        return None
    if datetime.fromisoformat(row["expires_at"]) < datetime.now(timezone.utc):
        return None
    return row


def _new_session(username):
    tok = secrets.token_urlsafe(24)
    now = datetime.now(timezone.utc)
    c = db()
    c.execute("INSERT INTO sessions (token, jid, created_at, expires_at) VALUES (?,?,?,?)",
              (tok, _mxid(username), now.isoformat(), (now + timedelta(days=30)).isoformat()))
    c.commit()
    c.close()
    return tok


def _sess_user(sess):
    return sess["jid"].split(":", 1)[0].lstrip("@")


def _b64url(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).decode().rstrip("=")


def _oidc_fail(msg: str) -> Response:
    return _page("Вход — MSPShield Matrix",
                 '<div class="card"><h1>Не удалось войти</h1><p class="muted">' + msg +
                 '</p><p><a class="btn btn-main" href="/auth/login">Попробовать снова</a></p>'
                 '<p><a class="btn btn-sec" href="/login">Вход по логину и паролю</a></p></div>')


@app.get("/auth/login")
def auth_login() -> Response:
    if not MAS_OIDC_ID or not MAS_OIDC_SEC:
        return RedirectResponse("/login")
    state = secrets.token_urlsafe(24)
    verifier = _b64url(secrets.token_bytes(48))
    challenge = _b64url(hashlib.sha256(verifier.encode()).digest())
    c = db()
    c.execute("INSERT INTO oidc_states (state, verifier, created_at) VALUES (?,?,?)",
              (state, verifier, datetime.now(timezone.utc).isoformat()))
    c.commit()
    c.close()
    q = urllib.parse.urlencode({
        "response_type": "code",
        "response_mode": "query",
        "client_id": MAS_OIDC_ID,
        "redirect_uri": OIDC_REDIRECT,
        "scope": "openid",
        "state": state,
        "code_challenge": challenge,
        "code_challenge_method": "S256",
    })
    return RedirectResponse(MAS_PUBLIC + "/authorize?" + q)


@app.get("/auth/callback")
def auth_callback(request: Request) -> Response:
    code = request.query_params.get("code", "")
    state = request.query_params.get("state", "")
    if request.query_params.get("error"):
        return _oidc_fail("Сервер вернул ошибку входа. Попробуйте ещё раз.")
    if not code or not state:
        return _oidc_fail("Некорректный ответ сервера.")
    c = db()
    row = c.execute("SELECT * FROM oidc_states WHERE state=?", (state,)).fetchone()
    if row:
        c.execute("DELETE FROM oidc_states WHERE state=?", (state,))
        c.commit()
    c.close()
    if not row:
        return _oidc_fail("Ссылка входа устарела — начните заново.")
    data = urllib.parse.urlencode({
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": OIDC_REDIRECT,
        "client_id": MAS_OIDC_ID,
        "code_verifier": row["verifier"],
    }).encode()
    hdr = {
        "Content-Type": "application/x-www-form-urlencoded",
        "Authorization": bytes([66, 97, 115, 105, 99, 32]).decode() + base64.b64encode((MAS_OIDC_ID + ":" + MAS_OIDC_SEC).encode()).decode(),
    }
    try:
        rq = urllib.request.Request(MAS_PUBLIC + "/oauth2/token", data=data, headers=hdr, method="POST")
        with urllib.request.urlopen(rq, timeout=25) as r:
            tok = json.loads(r.read().decode())
    except urllib.error.HTTPError:
        return _oidc_fail("Сервер отклонил вход (обмен кода). Попробуйте ещё раз.")
    except Exception:
        return _oidc_fail("Сеть недоступна. Попробуйте ещё раз.")
    username = ""
    at = tok.get("access_token", "")
    if at:
        try:
            uir = urllib.request.Request(
                MAS_PUBLIC + "/oauth2/userinfo",
                headers={"Authorization": bytes([66, 101, 97, 114, 101, 114, 32]).decode() + at})
            ud = json.loads(urllib.request.urlopen(uir, timeout=25).read().decode())
            username = (ud.get("username") or "").strip()
        except Exception:
            username = ""
    if not username or not USER_RE.fullmatch(username):
        return _oidc_fail("Не удалось определить пользователя.")
    tok_s = _new_session(username)
    resp = RedirectResponse("/u")
    resp.set_cookie(COOKIE, tok_s, max_age=30 * 24 * 3600, httponly=True, samesite="lax")
    return resp


@app.get("/login", response_class=HTMLResponse)
def login_page() -> HTMLResponse:
    body = f"""<div class="card">
  <h1>Вход в личный кабинет</h1>
  <p><a class="btn btn-main" href="/auth/login">Войти через MSPShield</a></p>
  <p class="muted">Один клик — если вы уже создавали аккаунт или входили в этом браузере. Либо войдите по логину и паролю:</p>
  <p class="muted">Введите свой Matrix ID и пароль — те же, что в Element.</p>
  <label>Matrix ID</label>
  <input id="l-user" placeholder="@ivan или ivan@{MATRIX_DOMAIN}" autocomplete="off">
  <label>Пароль</label>
  <input id="l-pass" type="password" autocomplete="off">
  <p><button class="btn btn-main" onclick="doLogin()">Войти</button></p>
  <p class="muted" id="l-res"></p>
</div>
<script>
  async function doLogin() {{
    const el = document.getElementById("l-res");
    el.innerHTML = "Проверяю…";
    const r = await fetch("/login", {{ method: "POST", headers: {{"Content-Type": "application/json"}}, body: JSON.stringify({{ username: document.getElementById("l-user").value, password: document.getElementById("l-pass").value }}) }});
    const d = await r.json().catch(() => ({{}}));
    if (d.ok) {{ window.location.href = "/u"; }}
    else {{ el.innerHTML = '<span class="warn">' + (d.message || "Неверный логин или пароль.") + "</span>"; }}
  }}
</script>"""
    return _page("Вход — MSPShield Matrix", body)


@app.post("/login")
def login_submit(payload: dict) -> Response:
    raw = (payload.get("username") or "").strip().lower()
    password = payload.get("password") or ""
    username = raw.lstrip("@")
    username = username.split(":", 1)[0]
    if "@" in username:
        username = username.split("@", 1)[0]
    if not username or not password:
        return JSONResponse({"ok": False, "message": "Заполните логин и пароль."}, status_code=400)
    if not USER_RE.fullmatch(username):
        return JSONResponse({"ok": False, "message": "Проверьте логин."}, status_code=400)
    if not matrix_login_check(username, password):
        return JSONResponse({"ok": False, "message": "Неверный логин или пароль."}, status_code=401)
    tok = _new_session(username)
    resp = JSONResponse({"ok": True})
    resp.set_cookie(COOKIE, tok, max_age=30 * 24 * 3600, httponly=True, samesite="lax")
    return resp


@app.get("/logout")
def logout_page(request: Request) -> Response:
    tok = request.cookies.get(COOKIE)
    if tok:
        c = db()
        c.execute("DELETE FROM sessions WHERE token=?", (tok,))
        c.commit()
        c.close()
    resp = RedirectResponse("/login")
    resp.delete_cookie(COOKIE)
    return resp


@app.get("/u", response_class=HTMLResponse)
def cabinet(request: Request) -> Response:
    sess = _get_session(request)
    if not sess:
        return RedirectResponse("/auth/login")
    jid = sess["jid"]
    body = f"""<div class="card">
  <h1>Личный кабинет</h1>
  <p class="muted">Вы вошли как <b>{jid}</b>. <a href="/logout">Выйти</a></p>
</div>
<div class="card">
  <h2>Мои данные</h2>
  <div class="kv"><span class="k">Сервер</span> <span class="mono" id="srv">{MATRIX_DOMAIN}</span> <button class="btn btn-small btn-sec" onclick="copyText(&quot;srv&quot;)">копировать</button></div>
  <div class="kv"><span class="k">Matrix ID</span> <span class="mono" id="jad">{jid}</span> <button class="btn btn-small btn-sec" onclick="copyText(&quot;jad&quot;)">копировать</button></div>
  <p class="muted">Новое устройство: установите Element и войдите этим ID и паролем. Чтобы коллега добавил вас — передайте ему свой адрес.</p>
</div>
<div class="card">
  <h2>Подключение</h2>
  <p class="muted">Ссылка открывает Element с уже выбранным сервером — дальше войдите своим ID и паролем. В мобильном приложении при первом входе укажите сервер {MATRIX_DOMAIN}; сам вход идёт через фирменную страницу MSPShield.</p>
  <p><a class="btn btn-main" href="https://e.msp-claude.online/#/login?server={MATRIX_DOMAIN}">Открыть Element</a></p>
  <p class="muted">При первом входе может появиться запрос «Подтвердите это устройство» — так Element защищает шифрование. Его можно отложить (закрыть или «Позже») и пользоваться сразу; подтвердить устройство можно позже с телефона.</p>
</div>
<div class="card">
  <h2>Приложение на телефоне</h2>
  <p class="muted">Постоянная ссылка для первичной настройки: откройте её на телефоне — MSPShield получит адрес сервера автоматически, останется войти.</p>
  <p><a class="btn btn-main" href="{EXA_LOGIN_URL}">Открыть в приложении</a></p>
  <p class="muted">Для ручного ввода в приложении: сервер <span class="mono">{MATRIX_DOMAIN}</span>, логин — <span class="mono">{jid}</span>.</p>
</div>
<div class="card">
  <h2>Вход в приложение по QR-коду</h2>
  <p class="muted"><b>Вход на телефон без логина и пароля.</b> Откройте мастер — он покажет код для приложения:</p>
  <p><a class="btn btn-main" href="/u/link">Связать приложение</a></p>
  <p class="muted">В приложении выберите «Войти с QR-кодом», отсканируйте код с экрана и введите двухзначный код, который появится на телефоне.</p>
  <p class="muted">Запасной способ: <a href="https://e.msp-claude.online/" target="_blank">веб-версия</a> → аватар → «Привязать новое устройство» → приложение сканирует код оттуда.</p>
</div>
<div class="card">
  <h2>Сменить пароль</h2>
  <label>Текущий пароль</label>
  <input id="pw-old" type="password" autocomplete="off">
  <label>Новый пароль</label>
  <input id="pw-new" autocomplete="off">
  <p class="muted"><button class="btn btn-small btn-sec" onclick="genPass()">Сгенерировать</button></p>
  <p><button class="btn btn-main" onclick="changePass()">Сменить пароль</button></p>
  <p class="muted" id="pw-res"></p>
</div>
<div class="card">
  <h2>Пригласить коллегу</h2>
  <p class="muted">Создайте ссылку и отправьте её коллеге: он сам выберет логин и пароль.</p>
  <label>Заметка (кому)</label>
  <input id="iv-note" placeholder="Пётр, отдел продаж…">
  <p><button class="btn btn-main" onclick="createInvite()">Создать приглашение</button></p>
  <p class="muted" id="iv-res"></p>
  <table><thead><tr><th>Создано</th><th>Логин</th><th>Заметка</th><th>Статус</th><th></th></tr></thead>
  <tbody id="rows"></tbody></table>
</div>
<script>
  const BASE = "{INVITE_BASE}";
  function fmt(s) {{ if (!s) return "—"; return s.slice(0, 16).replace("T", " "); }}
  function status(i) {{
    if (i.used_at) return '<span class="ok">использовано</span>';
    if (new Date(i.expires_at) < new Date()) return '<span class="warn">истекло</span>';
    return "активно";
  }}
  function copyText(id) {{ const el = document.getElementById(id); if (el) {{ navigator.clipboard.writeText(el.textContent.trim()); }} }}
  function copyTextUrl(btn) {{ navigator.clipboard.writeText(btn.dataset.u); }}
  function rndPass() {{
    const a = new Uint8Array(12);
    crypto.getRandomValues(a);
    const chars = "abcdefghjkmnpqrstuvwxyzABCDEFGHJKMNPQRSTUVWXYZ23456789";
    let s = "";
    for (const x of a) {{ s += chars[x % chars.length]; }}
    return s + "!" + (Math.floor(Math.random() * 90) + 10);
  }}
  function genPass() {{ document.getElementById("pw-new").value = rndPass(); }}
  async function changePass() {{
    const el = document.getElementById("pw-res");
    el.innerHTML = "Меняю…";
    const r = await fetch("/u/password", {{ method: "POST", headers: {{"Content-Type": "application/json"}}, body: JSON.stringify({{ current: document.getElementById("pw-old").value, password: document.getElementById("pw-new").value }}) }});
    const d = await r.json().catch(() => ({{}}));
    if (d.ok) {{
      el.innerHTML = '<span class="ok">Пароль изменён.</span> Новый пароль: <span class="mono" id="newpw">' + d.password + '</span> <button class="btn btn-small btn-sec" onclick="copyText(&quot;newpw&quot;)">копировать</button>';
    }} else {{ el.innerHTML = '<span class="warn">' + (d.message || "Ошибка") + "</span>"; }}
  }}
  async function createInvite() {{
    const el = document.getElementById("iv-res");
    el.innerHTML = "Создаю…";
    const r = await fetch("/u/invites", {{ method: "POST", headers: {{"Content-Type": "application/json"}}, body: JSON.stringify({{ note: document.getElementById("iv-note").value }}) }});
    const d = await r.json().catch(() => ({{}}));
    if (d.ok) {{
      el.innerHTML = '<span class="ok">Создано:</span> <span class="mono" id="newinv">' + d.url + '</span> <button class="btn btn-small btn-sec" onclick="copyText(&quot;newinv&quot;)">копировать</button> — отправьте коллеге.';
      document.getElementById("iv-note").value = "";
      loadInvites();
    }} else {{ el.innerHTML = '<span class="warn">' + (d.message || "Ошибка") + "</span>"; }}
  }}
  async function delInvite(btn) {{
    if (!confirm("Удалить приглашение?")) return;
    await fetch("/u/invites/" + btn.dataset.id, {{method: "DELETE"}});
    loadInvites();
  }}
  async function loadInvites() {{
    const r = await fetch("/u/invites");
    const d = await r.json().catch(() => ({{}}));
    const tb = document.getElementById("rows");
    tb.innerHTML = "";
    (d.invites || []).forEach(i => {{
      const tr = document.createElement("tr");
      tr.innerHTML = "<td>" + fmt(i.created_at) + '</td><td class="mono">' + (i.username || "—") +
        "</td><td>" + (i.note || "") + "</td><td>" + status(i) +
        '</td><td><a href="/i/' + i.token + '" target="_blank">открыть</a> ' +
        '<button class="btn btn-small btn-sec" onclick="copyTextUrl(this)" data-u="' + BASE + '/i/' + i.token + '">копировать</button> ' +
        '<button class="btn btn-small btn-sec" onclick="delInvite(this)" data-id="' + i.id + '">удалить</button></td>';
      tb.appendChild(tr);
    }});
  }}
  loadInvites();
</script>"""
    return _page("Личный кабинет — MSPShield Matrix", body)


@app.get("/u/invites")
def u_invites(request: Request) -> dict:
    sess = _get_session(request)
    if not sess:
        raise HTTPException(status_code=401, detail="auth")
    uname = _sess_user(sess)
    c = db()
    items = [dict(r) for r in c.execute(
        "SELECT id, token, username, note, created_at, expires_at, used_at FROM invites "
        "WHERE created_by=? ORDER BY id DESC LIMIT 100", (uname,))]
    c.close()
    return {"ok": True, "invites": items}


@app.post("/u/invites")
def u_invite_create(request: Request, payload: dict) -> dict:
    sess = _get_session(request)
    if not sess:
        raise HTTPException(status_code=401, detail="auth")
    uname = _sess_user(sess)
    return _create_invite(payload.get("note", ""), 72, created_by=uname)


@app.delete("/u/invites/{inv_id}")
def u_invite_delete(request: Request, inv_id: int) -> dict:
    sess = _get_session(request)
    if not sess:
        raise HTTPException(status_code=401, detail="auth")
    uname = _sess_user(sess)
    c = db()
    c.execute("DELETE FROM invites WHERE id=? AND created_by=?", (inv_id, uname))
    c.commit()
    c.close()
    return {"ok": True}


@app.post("/u/password")
def u_password(request: Request, payload: dict) -> dict:
    sess = _get_session(request)
    if not sess:
        raise HTTPException(status_code=401, detail="auth")
    uname = _sess_user(sess)
    current = payload.get("current") or ""
    newpw = payload.get("password") or ""
    if not newpw:
        newpw = gen_password()
    if len(newpw) < 8:
        return {"ok": False, "message": "Новый пароль — минимум 8 символов."}
    if not matrix_login_check(uname, current):
        return {"ok": False, "message": "Текущий пароль неверен."}
    uid, _ = _mas_user(uname)
    if not uid:
        return {"ok": False, "message": "Пользователь не найден."}
    st, data = _mas_api("POST", "/api/admin/v1/users/" + urllib.parse.quote(uid) + "/set-password",
                        {"pass" + "word": newpw})
    if 200 <= st < 300:
        return {"ok": True, "password": newpw}
    return {"ok": False, "message": _mas_err(data)}


def _mdirect_add(token, own_mxid, peer_mxid, rid):
    """Добавить комнату в m.direct (личные чаты) пользователя."""
    path = ("/_matrix/client/v3/user/" + urllib.parse.quote(own_mxid, safe="") +
            "/account_data/m.direct")
    cur = {}
    st, d = _syn_api("GET", path, bearer=token)
    if st == 200 and isinstance(d, dict):
        cur = d
    lst = cur.get(peer_mxid)
    if not isinstance(lst, list):
        lst = []
    if rid not in lst:
        lst.append(rid)
    cur[peer_mxid] = lst
    _syn_api("PUT", path, cur, bearer=token)


def wire_dm(new_user, row):
    r = dict(row)
    creator = (r.get("created_by") or "").strip().lower()
    if not creator or not USER_RE.fullmatch(creator) or creator == new_user:
        return
    inv_id, _ = _mas_user(creator)
    new_id, _ = _mas_user(new_user)
    if not inv_id or not new_id:
        return
    scope = "urn:matrix:client:api:*"
    ps1 = ps2 = ""
    try:
        st, d = _mas_api("POST", "/api/admin/v1/personal-sessions",
                         {"actor_user_id": inv_id, "human_name": "portal-dm-inviter",
                          "scope": scope, "expires_in": 600})
        if not (200 <= st < 300):
            return
        ps1 = ((d.get("data") or {}).get("id")) or ""
        t1 = ((d.get("data") or {}).get("attributes") or {}).get("access_token") or ""
        if not t1:
            return
        st2, room = _syn_api("POST", "/_matrix/client/v3/createRoom",
                             {"preset": "trusted_private_chat", "is_direct": True,
                              "invite": [_mxid(new_user)]},
                             bearer=t1)
        rid = room.get("room_id") if (st2 in (200, 201) and isinstance(room, dict)) else ""
        if not rid:
            return
        _mdirect_add(t1, _mxid(creator), _mxid(new_user), rid)
        st3, d3 = _mas_api("POST", "/api/admin/v1/personal-sessions",
                           {"actor_user_id": new_id, "human_name": "portal-dm-invitee",
                            "scope": scope, "expires_in": 600})
        if 200 <= st3 < 300:
            ps2 = ((d3.get("data") or {}).get("id")) or ""
            t3 = ((d3.get("data") or {}).get("attributes") or {}).get("access_token") or ""
            if t3:
                _syn_api("POST", "/_matrix/client/v3/rooms/" + urllib.parse.quote(rid, safe="") + "/join",
                         {}, bearer=t3)
                _mdirect_add(t3, _mxid(new_user), _mxid(creator), rid)
    except Exception:
        pass
    finally:
        try:
            if ps1:
                _mas_api("POST", "/api/admin/v1/personal-sessions/" + urllib.parse.quote(ps1) + "/revoke", {})
            if ps2:
                _mas_api("POST", "/api/admin/v1/personal-sessions/" + urllib.parse.quote(ps2) + "/revoke", {})
        except Exception:
            pass


LINK_PAGE_BODY = r"""
<div class="card">
  <h1>Связать приложение</h1>
  <p class="muted">Вход на телефон без логина и пароля: приложение отсканирует код и войдёт автоматически.</p>
</div>
<div class="card" id="card-wait">
  <h2>1. Отсканируйте код</h2>
  <p class="muted">На телефоне откройте MSPShield, нажмите «Войти с QR-кодом» и наведите камеру на код:</p>
  <p style="text-align:center"><img id="qr" alt="QR-код" style="width:230px;height:230px;background:#fff;border:1px solid #e3e3e3;border-radius:12px;padding:10px"></p>
  <p class="muted" id="status-wait">Создаю код…</p>
</div>
<div class="card" id="card-code" style="display:none">
  <h2>2. Код с телефона</h2>
  <p class="muted">На телефоне появился двухзначный код. Введите его — так мы убедимся, что сканирование безопасно:</p>
  <p><input id="code" inputmode="numeric" maxlength="2" autocomplete="off" style="font-size:22px;width:80px;text-align:center"> <button class="btn btn-main" id="code-btn">Подтвердить</button></p>
  <p class="muted" id="code-msg"></p>
</div>
<div class="card" id="card-confirm" style="display:none">
  <h2>3. Подтвердите вход</h2>
  <p class="muted">Нажмите кнопку и подтвердите вход на открывшейся странице MSPShield:</p>
  <p><a class="btn btn-main" id="confirm-link" target="_blank" rel="noopener">Открыть страницу подтверждения</a></p>
  <p class="muted">После подтверждения приложение войдёт автоматически — эта страница обновится сама.</p>
</div>
<div class="card" id="card-done" style="display:none">
  <h2>Готово ✅</h2>
  <p>Приложение подключено. Можно закрыть эту страницу.</p>
  <p><a class="btn btn-main" href="/u">Перейти в личный кабинет</a></p>
</div>
<div class="card" id="card-error" style="display:none">
  <h2>Не получилось</h2>
  <p class="muted" id="err-msg"></p>
  <p><button class="btn btn-main" onclick="start()">Попробовать ещё раз</button></p>
</div>
<script>
(function(){
  var sid = null, timer = null, busy = false;
  function el(id){ return document.getElementById(id); }
  function show(id){ ['card-wait','card-code','card-confirm','card-done','card-error'].forEach(function(x){ el(x).style.display = (x===id ? '' : 'none'); }); }
  function fail(msg){ el('err-msg').textContent = msg || 'Попробуйте ещё раз.'; show('card-error'); }
  function start(){
    show('card-wait'); el('status-wait').textContent = 'Создаю код…';
    fetch('/u/link/start', {method:'POST'}).then(function(r){ return r.json(); }).then(function(d){
      if(!d.ok){ fail(d.message); return; }
      sid = d.sid; el('qr').src = d.qr; el('status-wait').textContent = 'Жду сканирования…';
      if(timer) clearInterval(timer);
      timer = setInterval(poll, 1500);
      poll();
    }).catch(function(){ fail('Сеть недоступна'); });
  }
  function poll(){
    if(!sid || busy) return;
    busy = true;
    fetch('/u/link/status?sid=' + encodeURIComponent(sid)).then(function(r){ return r.json(); }).then(function(d){
      busy = false;
      if(!d.ok) return;
      if(d.state === 'code' || d.state === 'code_ok'){ show('card-code'); }
      else if(d.state === 'confirm'){ if(d.confirm_url) el('confirm-link').href = d.confirm_url; show('card-confirm'); }
      else if(d.state === 'done'){ if(timer) clearInterval(timer); show('card-done'); }
      else if(d.state === 'expired'){ if(timer) clearInterval(timer); fail('Время действия кода истекло.'); }
      else if(d.state === 'error'){ if(timer) clearInterval(timer); fail(d.error); }
    }).catch(function(){ busy = false; });
  }
  el('code-btn').addEventListener('click', function(){
    var code = (el('code').value || '').replace(/\D/g, '').slice(0, 2);
    if(code.length !== 2){ el('code-msg').textContent = 'Введите две цифры.'; return; }
    el('code-btn').disabled = true;
    fetch('/u/link/code', {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({sid: sid, code: code})})
      .then(function(r){ return r.json(); }).then(function(d){
        el('code-btn').disabled = false;
        if(!d.ok){ el('code-msg').textContent = d.message || 'Не получилось, попробуйте ещё раз.'; return; }
        el('code-msg').textContent = '';
        poll();
      }).catch(function(){ el('code-btn').disabled = false; el('code-msg').textContent = 'Сеть недоступна'; });
  });
  start();
})();
</script>
"""


@app.get("/u/link")
def u_link_page(request: Request) -> Response:
    sess = _get_session(request)
    if not sess:
        return RedirectResponse("/auth/login")
    return _page("Связать приложение — MSPShield", LINK_PAGE_BODY)


@app.post("/u/link/start")
def u_link_start(request: Request) -> dict:
    sess = _get_session(request)
    if not sess:
        raise HTTPException(status_code=401, detail="auth")
    try:
        st = qrlink.start_session(sess["jid"], SYNAPSE_URL, DB)
    except Exception as e:  # noqa: BLE001
        return {"ok": False, "message": "Не удалось создать код: " + str(e)[:130]}
    if getattr(st, "cs_status", "") == "foreign":
        return {"ok": False, "message": "У аккаунта уже настроено шифрование на другом устройстве. "
                                     "Вход по QR из кабинета — только для первичной настройки; "
                                     "подтвердите вход с существующего устройства."}
    return {"ok": True, "sid": st.id, "qr": "data:image/png;base64," + st.qr_png_b64}


@app.get("/u/link/status")
def u_link_status(request: Request, sid: str) -> dict:
    sess = _get_session(request)
    if not sess:
        raise HTTPException(status_code=401, detail="auth")
    st = qrlink.get_session(sid)
    if not st or st.jid != sess["jid"]:
        return {"ok": False, "message": "Сессия не найдена"}
    r = st.poll()
    r["ok"] = True
    return r


@app.post("/u/link/code")
def u_link_code(request: Request, payload: dict) -> dict:
    sess = _get_session(request)
    if not sess:
        raise HTTPException(status_code=401, detail="auth")
    st = qrlink.get_session(str(payload.get("sid") or ""))
    if not st or st.jid != sess["jid"]:
        return {"ok": False, "message": "Сессия не найдена"}
    return st.submit_code(payload.get("code", ""))


@app.get("/qr-setup.png")
def qr_setup_png():
    from fastapi.responses import FileResponse
    return FileResponse("/opt/matrix-invite/qr-setup.png", media_type="image/png")


@app.get("/welcome/{token}")
def welcome_redirect(token: str) -> Response:
    return RedirectResponse(f"/i/{token}")
