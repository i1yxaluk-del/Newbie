"""MSPShield Jami Invite Portal (v3).

- Публично: /i/{token} — приглашение: установка Jami + саморегистрация учётной записи JAMS (одноразово).
- Публично: /welcome/{ctoken} — после регистрации: данные подключения + шаги; /u/{ctoken} — личный кабинет.
- Публично: /qr/{jami_id}.png — QR-контакт (jami:<id>); /c/{jami_id} — карточка контакта.
- Админка: /admin?token=<INVITE_ADMIN_TOKEN> — приглашения + «профиль приглашающего по умолчанию».
- API: POST/GET/DELETE /admin/invites, GET/POST /admin/settings, POST /i/{token}/register, POST /i/{token}/confirm,
  GET/POST/DELETE /u/{ctoken}/* (кабинет).
"""
import io
import json
import os
import re
import secrets
import sqlite3
import time
from datetime import datetime, timedelta, timezone

import qrcode
import requests
from fastapi import FastAPI, Header, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse, Response

DB = "/data/invites.db"
ADMIN_TOKEN = os.environ["ADMIN_TOKEN"]
JAMS_URL = os.environ.get("JAMS_URL", "https://m.msp-claude.online")
JAMS_ADMIN_USER = os.getenv("JAMS_ADMIN_USER", "admin")
JAMS_ADMIN_PASS = os.getenv("JAMS_ADMIN_PASS", "")
JAMS_GROUP = os.getenv("JAMS_GROUP", "MSPShield")
INVITE_BASE = os.getenv("INVITE_BASE", "https://invite.msp-claude.online")
BRAND = os.environ.get("BRAND", "MSPShield")

app = FastAPI(title="MSPShield Invite Portal")


def db():
    c = sqlite3.connect(DB)
    c.row_factory = sqlite3.Row
    return c


def init() -> None:
    c = db()
    c.execute(
        """CREATE TABLE IF NOT EXISTS invites (
             token        TEXT PRIMARY KEY,
             inviter_name TEXT,
             inviter_id   TEXT,
             created_at   TEXT,
             expires_at   TEXT,
             used_at      TEXT,
             note         TEXT,
             jams_username TEXT DEFAULT '',
             jams_password TEXT DEFAULT ''
           )"""
    )
    for col in ("jams_username", "jams_password", "created_by", "member_id"):
        try:
            c.execute(f"ALTER TABLE invites ADD COLUMN {col} TEXT DEFAULT ''")
        except sqlite3.OperationalError:
            pass
    c.execute(
        """CREATE TABLE IF NOT EXISTS members (
             id            INTEGER PRIMARY KEY AUTOINCREMENT,
             jams_username TEXT UNIQUE,
             jams_password TEXT,
             cabinet_token TEXT UNIQUE,
             jami_id       TEXT DEFAULT '',
             display_name  TEXT DEFAULT '',
             created_at    TEXT,
             source_invite TEXT
           )"""
    )
    c.execute("CREATE TABLE IF NOT EXISTS settings (k TEXT PRIMARY KEY, v TEXT DEFAULT '')")
    c.execute("INSERT OR IGNORE INTO settings (k, v) VALUES ('inviter_name', '')")
    c.execute("INSERT OR IGNORE INTO settings (k, v) VALUES ('inviter_id', '')")
    c.commit()
    c.close()


@app.on_event("startup")
def startup() -> None:
    init()


@app.get("/health")
def health() -> dict:
    return {"ok": True}


# ─── интеграция с JAMS (admin API) ───────────────────────────────────────────

_JAMS_TOKEN = {"value": ""}


def _jams_login() -> None:
    r = requests.post(
        JAMS_URL.rstrip("/") + "/api/login",
        json={"username": JAMS_ADMIN_USER, "password": JAMS_ADMIN_PASS},
        timeout=15,
    )
    _JAMS_TOKEN["value"] = r.json().get("access_token", "") if r.status_code == 200 else ""


def _jams_admin(method: str, path: str, params=None, body=None, retry: bool = True):
    if not _JAMS_TOKEN["value"]:
        _jams_login()
    r = requests.request(
        method,
        JAMS_URL.rstrip("/") + path,
        params=params,
        json=body,
        headers={"Authorization": "Bearer " + _JAMS_TOKEN["value"]},
        timeout=20,
    )
    if r.status_code == 401 and retry:
        _jams_login()
        return _jams_admin(method, path, params=params, body=body, retry=False)
    return r


def _jams_user(username: str):
    r = _jams_admin("GET", "/api/admin/user", params={"username": username})
    if r.status_code == 200:
        try:
            return r.json()
        except Exception:
            return None
    return None


def _jams_create_user(username: str, password: str) -> bool:
    r = _jams_admin("POST", "/api/admin/user", body={"username": username, "password": password})
    return r.status_code == 201


def _jams_add_to_group(username: str) -> None:
    try:
        r = _jams_admin("GET", "/api/admin/groups")
        if r.status_code != 200:
            return
        gid = None
        for g in r.json():
            if g.get("name") == JAMS_GROUP:
                gid = g.get("id")
                break
        if gid:
            _jams_admin("POST", "/api/admin/group/members/" + str(gid), body={"username": username})
    except Exception:
        pass


def _jams_admin_jamiid() -> str:
    u = _jams_user(JAMS_ADMIN_USER)
    return ((u or {}).get("jamiId") or "").strip().lower()


def _get_setting(k: str) -> str:
    c = db()
    row = c.execute("SELECT v FROM settings WHERE k=?", (k,)).fetchone()
    c.close()
    return ((row["v"] if row else "") or "").strip()


def _get_member(ctoken: str):
    c = db()
    row = c.execute("SELECT * FROM members WHERE cabinet_token=?", (ctoken,)).fetchone()
    c.close()
    return row


# ─── админ-API ──────────────────────────────────────────────────────────────

@app.post("/admin/invites")
def create_invite(request: Request, payload: dict, x_admin_token: str = Header("")) -> dict:
    if x_admin_token != ADMIN_TOKEN:
        raise HTTPException(status_code=401, detail="unauthorized")
    now = datetime.now(timezone.utc)
    ttl = int(payload.get("ttl_hours", 72))
    tok = secrets.token_urlsafe(24)
    c = db()
    c.execute(
        "INSERT INTO invites (token, inviter_name, inviter_id, created_at, expires_at, used_at, note, jams_username, jams_password, created_by, member_id) VALUES (?,?,?,?,?,?,?,?,?,?,?)",
        (
            tok,
            (payload.get("inviter_name") or "").strip() or _get_setting("inviter_name") or JAMS_ADMIN_USER,
            ((payload.get("inviter_id") or "").strip() or _get_setting("inviter_id") or _jams_admin_jamiid()).lower(),
            now.isoformat(),
            (now + timedelta(hours=ttl)).isoformat(),
            None,
            payload.get("note", ""),
            (payload.get("jams_username") or "").strip(),
            payload.get("jams_password") or "",
            payload.get("created_by") or "admin",
            "",
        ),
    )
    c.commit()
    c.close()
    return {
        "ok": True,
        "url": f"{INVITE_BASE}/i/{tok}",
        "token": tok,
        "expires_at": (now + timedelta(hours=ttl)).isoformat(),
    }


@app.get("/admin/invites")
def list_invites(x_admin_token: str = Header("")) -> dict:
    if x_admin_token != ADMIN_TOKEN:
        raise HTTPException(status_code=401, detail="unauthorized")
    c = db()
    rows = [dict(r) for r in c.execute("SELECT * FROM invites ORDER BY created_at DESC LIMIT 200")]
    c.close()
    return {"invites": rows}


@app.delete("/admin/invites/{token}")
def delete_invite(token: str, x_admin_token: str = Header("")) -> dict:
    if x_admin_token != ADMIN_TOKEN:
        raise HTTPException(status_code=401, detail="unauthorized")
    c = db()
    cur = c.execute("DELETE FROM invites WHERE token=?", (token,))
    c.commit()
    c.close()
    return {"ok": cur.rowcount > 0}


@app.get("/admin/settings")
def get_settings(x_admin_token: str = Header("")) -> dict:
    if x_admin_token != ADMIN_TOKEN:
        raise HTTPException(status_code=401, detail="unauthorized")
    return {"inviter_name": _get_setting("inviter_name"), "inviter_id": _get_setting("inviter_id")}


@app.get("/admin/defaults")
def admin_defaults(x_admin_token: str = Header("")) -> dict:
    if x_admin_token != ADMIN_TOKEN:
        raise HTTPException(status_code=401, detail="unauthorized")
    saved_id = _get_setting("inviter_id")
    iid = saved_id or _jams_admin_jamiid()
    return {
        "inviter_name": _get_setting("inviter_name") or JAMS_ADMIN_USER,
        "inviter_id": iid,
        "from_admin": bool(iid and not saved_id),
    }


@app.post("/admin/settings")
def save_settings(payload: dict, x_admin_token: str = Header("")) -> dict:
    if x_admin_token != ADMIN_TOKEN:
        raise HTTPException(status_code=401, detail="unauthorized")
    c = db()
    for k in ("inviter_name", "inviter_id"):
        v = (payload.get(k) or "").strip()
        if k == "inviter_id":
            v = v.lower()
        c.execute(
            "INSERT INTO settings (k, v) VALUES (?, ?) ON CONFLICT(k) DO UPDATE SET v=excluded.v",
            (k, v),
        )
    c.commit()
    c.close()
    return {"ok": True}


# ─── публичные страницы ─────────────────────────────────────────────────────

JAMI_ID_RE = re.compile(r"^[0-9a-fA-F]{40}$")


def _qr_png(data: str) -> bytes:
    img = qrcode.make(data)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


@app.get("/i/{token}/qr.png")
def qr(token: str) -> Response:
    c = db()
    row = c.execute("SELECT inviter_id, created_by FROM invites WHERE token=?", (token,)).fetchone()
    c.close()
    if not row:
        raise HTTPException(status_code=404, detail="not found")
    inviter_id = (row["inviter_id"] or "").strip().lower()
    if not JAMI_ID_RE.fullmatch(inviter_id) and (row["created_by"] or "admin") == "admin":
        inviter_id = _get_setting("inviter_id").lower()
    if not JAMI_ID_RE.fullmatch(inviter_id):
        raise HTTPException(status_code=404, detail="inviter id not set")
    return Response(_qr_png("jami:" + inviter_id), media_type="image/png")


@app.post("/i/{token}/confirm")
def confirm(token: str) -> dict:
    c = db()
    row = c.execute("SELECT * FROM invites WHERE token=?", (token,)).fetchone()
    if not row:
        c.close()
        raise HTTPException(status_code=404, detail="not found")
    if not row["used_at"]:
        c.execute(
            "UPDATE invites SET used_at=? WHERE token=?",
            (datetime.now(timezone.utc).isoformat(), token),
        )
        c.commit()
    c.close()
    return {"ok": True}


@app.post("/i/{token}/register")
def register(token: str, payload: dict) -> dict:
    c = db()
    row = c.execute("SELECT * FROM invites WHERE token=?", (token,)).fetchone()
    if not row:
        c.close()
        raise HTTPException(status_code=404, detail="not found")
    if row["used_at"]:
        c.close()
        raise HTTPException(status_code=410, detail="already used")
    if datetime.fromisoformat(row["expires_at"]) < datetime.now(timezone.utc):
        c.close()
        raise HTTPException(status_code=410, detail="expired")
    username = (payload.get("username") or "").strip().lower()
    password = payload.get("password") or ""
    display = (payload.get("display_name") or "").strip() or username
    if not re.fullmatch(r"[a-z0-9][a-z0-9._-]{2,31}", username):
        c.close()
        raise HTTPException(status_code=400, detail="bad username")
    if len(password) < 8:
        c.close()
        raise HTTPException(status_code=400, detail="weak password")
    if _jams_user(username) is not None:
        c.close()
        return {"ok": False, "error": "taken", "message": "Логин занят — выберите другой."}
    if not _jams_create_user(username, password):
        c.close()
        return {"ok": False, "error": "jams", "message": "Не удалось создать учётную запись (логин занят или сервер недоступен)."}
    _jams_add_to_group(username)
    ctoken = secrets.token_urlsafe(24)
    now_iso = datetime.now(timezone.utc).isoformat()
    c.execute(
        "INSERT INTO members (jams_username, jams_password, cabinet_token, jami_id, display_name, created_at, source_invite) VALUES (?,?,?,?,?,?,?)",
        (username, password, ctoken, "", display, now_iso, token),
    )
    c.execute("UPDATE invites SET used_at=? WHERE token=?", (now_iso, token))
    c.commit()
    c.close()
    return {"ok": True, "cabinet_url": f"{INVITE_BASE}/welcome/{ctoken}", "login": username}


@app.get("/u/{ctoken}/refresh-jami")
def refresh_jami(ctoken: str) -> dict:
    row = _get_member(ctoken)
    if not row:
        raise HTTPException(status_code=404, detail="not found")
    u = _jams_user(row["jams_username"])
    jid = ((u or {}).get("jamiId") or "").strip().lower()
    if jid and JAMI_ID_RE.fullmatch(jid):
        c = db()
        c.execute("UPDATE members SET jami_id=? WHERE cabinet_token=?", (jid, ctoken))
        c.commit()
        c.close()
        return {"ok": True, "jami_id": jid}
    return {"ok": False, "jami_id": ""}


@app.post("/u/{ctoken}/invites")
def member_invite_create(ctoken: str, payload: dict) -> dict:
    row = _get_member(ctoken)
    if not row:
        raise HTTPException(status_code=404, detail="not found")
    now = datetime.now(timezone.utc)
    ttl = max(1, min(720, int(payload.get("ttl_hours", 72))))
    tok = secrets.token_urlsafe(24)
    c = db()
    c.execute(
        "INSERT INTO invites (token, inviter_name, inviter_id, created_at, expires_at, used_at, note, jams_username, jams_password, created_by, member_id) VALUES (?,?,?,?,?,?,?,?,?,?,?)",
        (
            tok,
            row["display_name"] or row["jams_username"],
            (row["jami_id"] or "").strip().lower(),
            now.isoformat(),
            (now + timedelta(hours=ttl)).isoformat(),
            None,
            payload.get("note", ""),
            "",
            "",
            row["jams_username"],
            str(row["id"]),
        ),
    )
    c.commit()
    c.close()
    return {"ok": True, "url": f"{INVITE_BASE}/i/{tok}", "token": tok}


@app.get("/u/{ctoken}/invites")
def member_invites(ctoken: str) -> dict:
    row = _get_member(ctoken)
    if not row:
        raise HTTPException(status_code=404, detail="not found")
    c = db()
    rows = [
        dict(r)
        for r in c.execute(
            "SELECT * FROM invites WHERE member_id=? ORDER BY created_at DESC LIMIT 100",
            (str(row["id"]),),
        )
    ]
    c.close()
    return {"invites": rows}


@app.delete("/u/{ctoken}/invites/{token}")
def member_invite_delete(ctoken: str, token: str) -> dict:
    row = _get_member(ctoken)
    if not row:
        raise HTTPException(status_code=404, detail="not found")
    c = db()
    cur = c.execute(
        "DELETE FROM invites WHERE token=? AND member_id=?", (token, str(row["id"]))
    )
    c.commit()
    c.close()
    return {"ok": cur.rowcount > 0}


@app.get("/login")
def login_page() -> HTMLResponse:
    body = f"""<div class="card">
  <h1>Вход в личный кабинет</h1>
  <p class="muted">Логин и пароль — от вашей учётной записи Jami (те, что вы создавали по приглашению).</p>
  <label class="muted">Логин</label>
  <input id="lu" autocomplete="username">
  <label class="muted">Пароль</label>
  <input id="lp" type="password" autocomplete="current-password">
  <button class="btn btn-main" onclick="doLogin()">Войти</button>
  <p class="muted" id="lres"></p>
</div>
<script>
  async function doLogin() {{
    const el = document.getElementById("lres");
    el.innerHTML = "Проверяю…";
    const r = await fetch("/login", {{
      method: "POST",
      headers: {{"Content-Type": "application/json"}},
      body: JSON.stringify({{username: document.getElementById("lu").value, password: document.getElementById("lp").value}}),
    }});
    const d = await r.json().catch(() => ({{}}));
    if (d.ok) {{ window.location.href = "/cabinet"; return; }}
    el.innerHTML = '<span class="warn">' + (d.message || "Не получилось войти — проверьте логин и пароль.") + "</span>";
  }}
</script>"""
    return _page("Вход — MSPShield Jami", body)


@app.post("/login")
def login_submit(payload: dict) -> Response:
    username = (payload.get("username") or "").strip().lower()
    password = payload.get("password") or ""
    if not username or not password:
        return JSONResponse({"ok": False, "message": "Заполните логин и пароль."}, status_code=400)
    try:
        r = requests.post(
            JAMS_URL.rstrip("/") + "/api/login",
            json={"username": username, "password": password},
            timeout=15,
        )
    except Exception:
        return JSONResponse({"ok": False, "message": "Сервер недоступен, попробуйте позже."}, status_code=502)
    if r.status_code != 200:
        return JSONResponse({"ok": False, "message": "Неверный логин или пароль."}, status_code=401)
    c = db()
    row = c.execute("SELECT * FROM members WHERE jams_username=?", (username,)).fetchone()
    if row is None:
        ctoken = secrets.token_urlsafe(24)
        c.execute(
            "INSERT INTO members (jams_username, jams_password, cabinet_token, jami_id, display_name, created_at, source_invite) VALUES (?,?,?,?,?,?,?)",
            (username, password, ctoken, "", username, datetime.now(timezone.utc).isoformat(), ""),
        )
        c.commit()
        row = c.execute("SELECT * FROM members WHERE jams_username=?", (username,)).fetchone()
    c.close()
    resp = JSONResponse({"ok": True})
    resp.set_cookie("cab", row["cabinet_token"], max_age=30 * 24 * 3600, httponly=True, samesite="lax")
    return resp


@app.get("/cabinet")
def cabinet_alias(request: Request) -> Response:
    ct = request.cookies.get("cab", "")
    if not ct or not _get_member(ct):
        return RedirectResponse("/login")
    return cabinet_page(ct)


@app.get("/logout")
def logout_page() -> Response:
    resp = RedirectResponse("/login")
    resp.delete_cookie("cab")
    return resp


@app.post("/u/{ctoken}/password")
def member_password(ctoken: str, payload: dict) -> dict:
    row = _get_member(ctoken)
    if not row:
        raise HTTPException(status_code=404, detail="not found")
    old = payload.get("old_password") or ""
    new = payload.get("new_password") or ""
    if len(new) < 8:
        return {"ok": False, "message": "Новый пароль — минимум 8 символов."}
    try:
        r = requests.post(
            JAMS_URL.rstrip("/") + "/api/login",
            json={"username": row["jams_username"], "password": old},
            timeout=15,
        )
    except Exception:
        return {"ok": False, "message": "Сервер недоступен."}
    if r.status_code != 200:
        return {"ok": False, "message": "Текущий пароль неверный."}
    pr = _jams_admin("PUT", "/api/admin/user", body={"username": row["jams_username"], "password": new})
    if pr.status_code != 200:
        return {"ok": False, "message": "Не удалось сменить пароль (код " + str(pr.status_code) + ")."}
    c = db()
    c.execute("UPDATE members SET jams_password=? WHERE cabinet_token=?", (new, ctoken))
    c.commit()
    c.close()
    return {"ok": True}


@app.post("/u/{ctoken}/profile")
def member_profile(ctoken: str, payload: dict) -> dict:
    row = _get_member(ctoken)
    if not row:
        raise HTTPException(status_code=404, detail="not found")
    name = (payload.get("display_name") or "").strip()[:64]
    c = db()
    c.execute("UPDATE members SET display_name=? WHERE cabinet_token=?", (name, ctoken))
    c.commit()
    c.close()
    return {"ok": True}


@app.get("/qr/{jami_id}.png")
def contact_qr(jami_id: str) -> Response:
    jid = jami_id.strip().lower()
    if not JAMI_ID_RE.fullmatch(jid):
        raise HTTPException(status_code=404, detail="bad jami id")
    return Response(_qr_png("jami:" + jid), media_type="image/png")


@app.get("/c/{jami_id}")
def contact_card(jami_id: str, n: str = "") -> HTMLResponse:
    jid = jami_id.strip().lower()
    if not JAMI_ID_RE.fullmatch(jid):
        return _page("Некорректный Jami ID", '<div class="card"><h1>Некорректный Jami ID</h1><p class="muted">Ожидается 40 hex-символов.</p></div>')
    name2 = (n or "").strip()
    title = "Контакт в Jami" + (" — " + name2 if name2 else "")
    body = f"""<div class="card qr">
  <h1>{title}</h1>
  <p class="muted">Отсканируйте QR-код: в Jami откройте «Добавить контакт» → «Сканировать», или скопируйте ID.</p>
  <img src="/qr/{jid}.png" alt="QR-код контакта">
  <p class="mono" id="jid">{jid}</p>
  <button class="btn btn-sec" onclick="copyId()">Скопировать Jami ID</button>
  <p class="muted" id="copyres"></p>
</div>
<div class="card">
  <h2>Как добавить контакт</h2>
  <ol class="steps">
    <li>Откройте Jami на телефоне или компьютере.</li>
    <li>Нажмите «Добавить контакт», отсканируйте QR-код выше или вставьте ID вручную.</li>
    <li>После подтверждения контакт появится в списке разговоров.</li>
  </ol>
</div>
<script>
  function copyId() {{
    navigator.clipboard.writeText("{jid}");
    document.getElementById("copyres").innerHTML = '<span class="ok">Скопировано</span>';
  }}
</script>"""
    return _page(title, body)


def _page(title: str, body: str, extra_head: str = "", status_code: int = 200) -> HTMLResponse:
    html = f"""<!doctype html>
<html lang="ru">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
{extra_head}
<style>
  :root {{ color-scheme: light dark; }}
  * {{ box-sizing: border-box; }}
  body {{ margin:0; font:16px/1.55 -apple-system,"Segoe UI",Roboto,sans-serif; background:#f5f6f8; color:#16202a; }}
  .wrap {{ max-width:760px; margin:0 auto; padding:28px 18px 48px; }}
  .card {{ background:#fff; border:1px solid #e3e6ea; border-radius:14px; padding:22px; margin-bottom:14px; }}
  h1 {{ font-size:22px; margin:0 0 6px; }}
  h2 {{ font-size:18px; margin:0 0 8px; }}
  .muted {{ color:#69747f; font-size:14px; }}
  .brand {{ font-weight:700; color:#005699; letter-spacing:.02em; }}
  .steps {{ padding-left:20px; margin:10px 0 0; }}
  .steps li {{ margin:6px 0; }}
  .btn {{ display:block; text-align:center; text-decoration:none; border-radius:10px; padding:13px 16px; font-weight:600; margin:8px 0; cursor:pointer; border:0; }}
  .btn-main {{ background:#005699; color:#fff; }}
  .btn-sec {{ background:#eef2f6; color:#005699; }}
  .btn-small {{ display:inline-block; padding:6px 10px; font-size:13px; margin:0 4px 0 0; }}
  .qr {{ text-align:center; }}
  .qr img {{ width:220px; height:220px; image-rendering:pixelated; border:1px solid #e3e6ea; border-radius:10px; background:#fff; padding:8px; }}
  .ok {{ color:#1c6b3c; font-weight:600; }}
  .warn {{ color:#8a5a12; font-weight:600; }}
  .done {{ background:#e8f6ee; border-color:#bfe6ce; }}
  input, textarea {{ width:100%; padding:10px 12px; border:1px solid #cdd4da; border-radius:8px; font:inherit; margin:4px 0 10px; }}
  table {{ width:100%; border-collapse:collapse; font-size:14px; }}
  th, td {{ text-align:left; padding:8px 6px; border-bottom:1px solid #e3e6ea; vertical-align:top; }}
  .mono {{ font-family:Consolas,monospace; font-size:12px; word-break:break-all; }}
  .kv {{ margin:6px 0; }}
</style>
</head>
<body>
<div class="wrap">
  <p class="brand">MSPShield · Jami</p>
  {body}
  <p class="muted" style="text-align:center;margin-top:18px">MSPShield invite service</p>
</div>
</body>
</html>"""
    return HTMLResponse(html, status_code=status_code)


@app.get("/i/{token}")
def invite_page(token: str) -> HTMLResponse:
    c = db()
    row = c.execute("SELECT * FROM invites WHERE token=?", (token,)).fetchone()
    c.close()
    if not row:
        return _page("Приглашение не найдено", '<div class="card"><h1>Приглашение не найдено</h1><p class="muted">Ссылка неверная или была удалена.</p></div>')

    used = bool(row["used_at"])
    expired = datetime.fromisoformat(row["expires_at"]) < datetime.now(timezone.utc)
    name = row["inviter_name"] or BRAND
    iid = (row["inviter_id"] or "").strip().lower()
    if not JAMI_ID_RE.fullmatch(iid) and (row["created_by"] or "admin") == "admin":
        iid = _get_setting("inviter_id").lower()
    has_iid = bool(JAMI_ID_RE.fullmatch(iid))
    if has_iid:
        inviter_block = f"""<div class="card qr">
  <h2>Контакт приглашающего</h2>
  <p class="muted">После подключения добавьте контакт: «Добавить контакт» → «Сканировать QR».</p>
  <img src="/i/{token}/qr.png" alt="QR-код контакта">
  <p class="mono">{iid}</p>
</div>"""
    else:
        inviter_block = ""

    if used:
        c2 = db()
        mem = c2.execute("SELECT cabinet_token FROM members WHERE source_invite=?", (token,)).fetchone()
        c2.close()
        cab = f'<p><a href="/u/{mem["cabinet_token"]}">Открыть мой кабинет</a></p>' if mem else ""
        return _page(
            "Приглашение уже использовано",
            f'<div class="card done"><h1>Приглашение уже использовано</h1>'
            f'<p class="ok">Учётная запись по этой ссылке уже создана.</p>{cab}</div>',
        )
    if expired:
        return _page(
            "Срок приглашения истёк",
            f'<div class="card"><h1>Срок приглашения истёк</h1>'
            f'<p class="warn">Попросите «{name}» создать новое приглашение.</p></div>',
        )

    body = f"""<div class="card">
  <h1>Вас приглашают в Jami</h1>
  <p class="muted">Пригласил(а): <b>{name}</b></p>
  <p>Jami — мессенджер со сквозным шифрованием. Здесь можно создать учётную запись и подключить приложение к серверу MSPShield.</p>
</div>
<div class="card">
  <h2>1. Установите Jami</h2>
  <a class="btn btn-main" id="store-android" href="https://play.google.com/store/apps/details?id=cx.ring">Установить из Google Play</a>
  <a class="btn btn-main" id="store-ios" href="https://apps.apple.com/app/jami/id1306951055">Установить из App Store</a>
  <a class="btn btn-sec" href="https://jami.net/download/" style="display:block">Скачать для Windows / macOS / Linux</a>
</div>
<div class="card">
  <h2>2. Создайте учётную запись</h2>
  <p class="muted">Логин — латиница/цифры (3–32 символа). Пароль понадобится при подключении приложения.</p>
  <label class="muted">Логин</label>
  <input id="r-user" placeholder="например: ivan" autocomplete="off">
  <label class="muted">Пароль (можно сгенерировать заново)</label>
  <input id="r-pass" autocomplete="off">
  <p class="muted"><button class="btn btn-small btn-sec" onclick="genPass()">Сгенерировать пароль</button></p>
  <label class="muted">Ваше имя (как вас увидят в контактах; необязательно)</label>
  <input id="r-name" placeholder="Иван">
  <button class="btn btn-main" onclick="registerAcc()">Создать учётную запись</button>
  <p class="muted" id="reg-result"></p>
  <p class="muted">После создания ссылка-приглашение станет недействительной — это нормально.</p>
</div>
<div class="card">
  <h2>Уже есть учётная запись?</h2>
  <p class="muted">В Jami: «Добавить аккаунт» → «Подключиться к JAMS-серверу». Сервер: <span class="mono" id="jserver">{JAMS_URL}</span> <button class="btn btn-small btn-sec" onclick="copyText('jserver')">копировать</button></p>
  {inviter_block}
  <button class="btn btn-sec" onclick="markUsed()">Отметить приглашение использованным</button>
  <p class="muted" id="result"></p>
</div>
<script>
  const ua = navigator.userAgent || "";
  const isIOS = /iPhone|iPad|iPod/i.test(ua);
  document.getElementById("store-android").style.display = isIOS ? "none" : "block";
  document.getElementById("store-ios").style.display = isIOS ? "block" : "none";
  function rndPass() {{
    const a = new Uint8Array(12);
    crypto.getRandomValues(a);
    const chars = "abcdefghjkmnpqrstuvwxyzABCDEFGHJKMNPQRSTUVWXYZ23456789";
    let s = "";
    for (const x of a) {{ s += chars[x % chars.length]; }}
    return s + "!" + (Math.floor(Math.random() * 90) + 10);
  }}
  function genPass() {{ document.getElementById("r-pass").value = rndPass(); }}
  if (!document.getElementById("r-pass").value) {{ document.getElementById("r-pass").value = rndPass(); }}
  function copyText(id) {{
    const el = document.getElementById(id);
    if (el) {{ navigator.clipboard.writeText(el.textContent.trim()); }}
  }}
  async function registerAcc() {{
    const el = document.getElementById("reg-result");
    el.innerHTML = "Создаю учётную запись…";
    const r = await fetch("/i/{token}/register", {{
      method: "POST",
      headers: {{"Content-Type": "application/json"}},
      body: JSON.stringify({{
        username: document.getElementById("r-user").value,
        password: document.getElementById("r-pass").value,
        display_name: document.getElementById("r-name").value,
      }}),
    }});
    const d = await r.json().catch(() => ({{}}));
    if (d.ok) {{ window.location.href = d.cabinet_url; return; }}
    el.innerHTML = '<span class="warn">' + (d.message || d.detail || "Не получилось. Проверьте данные и попробуйте ещё раз.") + "</span>";
  }}
  function markUsed() {{
    fetch("/i/{token}/confirm", {{method: "POST"}})
      .then(r => r.json())
      .then(() => {{ document.getElementById("result").innerHTML = '<span class="ok">Готово — приглашение помечено использованным.</span>'; }})
      .catch(() => {{ document.getElementById("result").innerHTML = '<span class="warn">Не получилось отметить.</span>'; }});
  }}
</script>"""
    return _page(f"Приглашение в Jami от {name}", body)


@app.get("/welcome/{ctoken}")
def welcome_page(ctoken: str) -> HTMLResponse:
    row = _get_member(ctoken)
    if not row:
        return _page("Кабинет не найден", '<div class="card"><h1>Кабинет не найден</h1><p class="muted">Ссылка неверная или устарела.</p></div>')
    u = _jams_user(row["jams_username"])
    jid = ((u or {}).get("jamiId") or "").strip().lower()
    if not JAMI_ID_RE.fullmatch(jid):
        jid = ""
    id_row = (
        f'<div class="kv"><span class="muted">Ваш Jami ID</span> <span class="mono" id="mid">{jid}</span> <button class="btn btn-small btn-sec" onclick="copyText(&quot;mid&quot;)">копировать</button></div>'
        if jid else
        '<div class="kv"><span class="muted">Ваш Jami ID</span> <span class="muted">появится после подключения — смотрите в кабинете</span></div>'
    )
    body = f"""<div class="card done">
  <h1>Учётная запись создана</h1>
  <p class="ok">Логин: <b>{row["jams_username"]}</b></p>
  <p class="muted">Сохраните ссылку на личный кабинет — через неё вы будете создавать приглашения и смотреть свой Jami ID.</p>
</div>
<div class="card">
  <h2>1. Установите Jami</h2>
  <a class="btn btn-main" href="https://play.google.com/store/apps/details?id=cx.ring">Установить из Google Play (Android)</a>
  <a class="btn btn-main" href="https://apps.apple.com/app/jami/id1306951055">Установить из App Store (iPhone / iPad)</a>
  <a class="btn btn-sec" href="https://jami.net/download/" style="display:block">Скачать для Windows / macOS / Linux</a>
</div>
<div class="card">
  <h2>2. Данные для входа (в приложении)</h2>
  <div class="kv"><span class="muted">Сервер</span> <span class="mono" id="srv">{JAMS_URL}</span> <button class="btn btn-small btn-sec" onclick="copyText(&quot;srv&quot;)">копировать</button></div>
  <div class="kv"><span class="muted">Логин</span> <span class="mono" id="lgn">{row["jams_username"]}</span> <button class="btn btn-small btn-sec" onclick="copyText(&quot;lgn&quot;)">копировать</button></div>
  <div class="kv"><span class="muted">Пароль</span> <span class="mono" id="pwd">{row["jams_password"]}</span> <button class="btn btn-small btn-sec" onclick="copyText(&quot;pwd&quot;)">копировать</button></div>
  {id_row}
</div>
<div class="card">
  <h2>3. Подключение</h2>
  <ol class="steps">
    <li>Откройте «Добавить аккаунт» → «Подключиться к JAMS-серверу».</li>
    <li>Введите сервер, логин и пароль из блока выше. Если появится окно «миграции» — введите тот же пароль.</li>
    <li>Настройки связи (TURN и DHT) применятся автоматически.</li>
  </ol>
</div>
<div class="card">
  <h2>Дальше</h2>
  <p><a class="btn btn-main" href="/u/{ctoken}">Открыть личный кабинет</a></p>
  <p class="muted">Заходить в кабинет можно и по логину с паролем: <a href="/login">страница входа</a>. В кабинете: ваш Jami ID с QR-кодом, приглашения для коллег, смена пароля. Учётная запись добавлена в группу MSPShield — после подключения клиент получит наши настройки связи (TURN/DHT).</p>
</div>
<script>
  function copyText(id) {{
    const el = document.getElementById(id);
    if (el) {{ navigator.clipboard.writeText(el.textContent.trim()); }}
  }}
</script>"""
    return _page("Учётная запись создана — MSPShield", body)


@app.get("/u/{ctoken}")
def cabinet_page(ctoken: str) -> HTMLResponse:
    row = _get_member(ctoken)
    if not row:
        return _page("Кабинет не найден", '<div class="card"><h1>Кабинет не найден</h1><p class="muted">Ссылка неверная или устарела.</p></div>')
    jid = (row["jami_id"] or "").strip().lower()
    if jid and JAMI_ID_RE.fullmatch(jid):
        jid_block = f"""<div class="kv"><span class="muted">Ваш Jami ID</span> <span class="mono" id="jid">{jid}</span> <button class="btn btn-small btn-sec" onclick="copyText(&quot;jid&quot;)">копировать</button></div>
  <p class="qr"><img src="/qr/{jid}.png" alt="QR-код" style="width:180px;height:180px"></p>
  <p class="muted">Карточка контакта: <a href="/c/{jid}" target="_blank">/c/{jid}</a> — отправьте её тому, кто хочет добавить вас в Jami.</p>"""
    else:
        jid_block = "<p class=\"muted\">Jami ID появится здесь после того, как вы подключите приложение к серверу. Подключили? Нажмите «Обновить».</p>"
    body = f"""<div class="card">
  <h1>Личный кабинет</h1>
  <p class="muted">Пользователь: <b>{row["jams_username"]}</b> {row["display_name"] or ""}</p>
  <p class="muted">Не пересылайте эту ссылку — она даёт доступ к вашим данным. <a href="/logout">Выйти</a></p>
</div>
<div class="card">
  <h2>Ваш Jami ID</h2>
  {jid_block}
  <button class="btn btn-sec" onclick="refreshJami()">Обновить Jami ID</button>
  <p class="muted" id="jres"></p>
</div>
<div class="card">
  <h2>Пригласить коллег</h2>
  <p class="muted">Нажмите кнопку — ссылка появится сразу (действует 72 часа); дополнительно ничего указывать не нужно.</p>
  <button class="btn btn-main" onclick="createInvite()">Создать приглашение</button>
  <p class="muted" id="ires"></p>
  <table>
    <thead><tr><th>Создано</th><th>Заметка</th><th>Статус</th><th>Ссылка</th></tr></thead>
    <tbody id="irows"><tr><td colspan="4" class="muted">Загрузка…</td></tr></tbody>
  </table>
</div>
<div class="card">
  <h2>Учётные данные</h2>
  <label class="muted">Отображаемое имя (как видят получатели ваших приглашений)</label>
  <input id="p-name" value="{row["display_name"] or row["jams_username"]}">
  <button class="btn btn-sec" onclick="saveName()">Сохранить имя</button>
  <p class="muted" id="p-res"></p>
  <hr style="border:0;border-top:1px solid #e3e6ea;margin:14px 0">
  <label class="muted">Текущий пароль</label>
  <input id="p-old" type="password" autocomplete="current-password">
  <label class="muted">Новый пароль (минимум 8 символов)</label>
  <input id="p-new" type="password" autocomplete="new-password">
  <button class="btn btn-main" onclick="changePass()">Сменить пароль</button>
  <p class="muted" id="pw-res"></p>
</div>
<script>
  function copyText(id) {{
    const el = document.getElementById(id);
    if (el) {{ navigator.clipboard.writeText(el.textContent.trim()); }}
  }}
  async function saveName() {{
    const r = await fetch("/u/{ctoken}/profile", {{
      method: "POST",
      headers: {{"Content-Type": "application/json"}},
      body: JSON.stringify({{display_name: document.getElementById("p-name").value}}),
    }});
    const d = await r.json().catch(() => ({{}}));
    document.getElementById("p-res").innerHTML = d.ok ? '<span class="ok">Сохранено</span>' : '<span class="warn">Ошибка</span>';
  }}
  async function changePass() {{
    const el = document.getElementById("pw-res");
    el.innerHTML = "Меняю…";
    const r = await fetch("/u/{ctoken}/password", {{
      method: "POST",
      headers: {{"Content-Type": "application/json"}},
      body: JSON.stringify({{
        old_password: document.getElementById("p-old").value,
        new_password: document.getElementById("p-new").value,
      }}),
    }});
    const d = await r.json().catch(() => ({{}}));
    el.innerHTML = d.ok ? '<span class="ok">Пароль изменён — используйте его при следующем входе в Jami и кабинет.</span>' : '<span class="warn">' + (d.message || "Ошибка") + "</span>";
  }}
  async function refreshJami() {{
    const el = document.getElementById("jres");
    el.innerHTML = "Спрашиваю сервер…";
    const r = await fetch("/u/{ctoken}/refresh-jami");
    const d = await r.json().catch(() => ({{}}));
    if (d.jami_id) {{ window.location.reload(); return; }}
    el.innerHTML = '<span class="warn">Пока не вижу — подключите Jami и попробуйте ещё раз через минуту.</span>';
  }}
  function fmt(ts) {{ return ts ? new Date(ts).toLocaleString("ru-RU") : ""; }}
  function status(i) {{
    if (i.used_at) return '<span class="ok">использовано</span>';
    if (new Date(i.expires_at) < new Date()) return '<span class="warn">истекло</span>';
    return "активно";
  }}
  async function loadInvites() {{
    const r = await fetch("/u/{ctoken}/invites");
    const d = await r.json().catch(() => ({{invites: []}}));
    const rows = document.getElementById("irows");
    rows.innerHTML = "";
    (d.invites || []).forEach(i => {{
      const tr = document.createElement("tr");
      tr.innerHTML = "<td>" + fmt(i.created_at) + "</td><td>" + (i.note || "") + "</td><td>" + status(i) +
        '</td><td><a href="/i/' + i.token + '" target="_blank">открыть</a> <button class="btn btn-small btn-sec" onclick="copyUrl(\\'' + i.token + '\\')">копировать</button> <button class="btn btn-small btn-sec" onclick="delInvite(\\'' + i.token + '\\')">отозвать</button></td>';
      rows.appendChild(tr);
    }});
  }}
  function copyUrl(tok) {{ navigator.clipboard.writeText("{INVITE_BASE}/i/" + tok); }}
  async function delInvite(tok) {{
    if (!confirm("Отозвать приглашение?")) return;
    await fetch("/u/{ctoken}/invites/" + tok, {{method: "DELETE"}});
    loadInvites();
  }}
  async function createInvite() {{
    const el = document.getElementById("ires");
    el.innerHTML = "Создаю…";
    const r = await fetch("/u/{ctoken}/invites", {{
      method: "POST",
      headers: {{"Content-Type": "application/json"}},
      body: JSON.stringify({{ttl_hours: 72, note: ""}}),
    }});
    const d = await r.json().catch(() => ({{}}));
    if (d.ok) {{
      el.innerHTML = '<span class="ok">Ссылка создана (скопирована):</span> <span class="mono">' + d.url + "</span>";
      try {{ await navigator.clipboard.writeText(d.url); }} catch (e) {{}}
    }} else {{
      el.innerHTML = '<span class="warn">Ошибка: ' + JSON.stringify(d) + "</span>";
    }}
    loadInvites();
  }}
  loadInvites();
</script>"""
    return _page("Личный кабинет — MSPShield Jami", body)


@app.get("/admin")
def admin_page(token: str = "") -> HTMLResponse:
    if token != ADMIN_TOKEN:
        return HTMLResponse(
            "<h1>Доступ закрыт</h1><p>Откройте /admin?token=&lt;INVITE_ADMIN_TOKEN&gt; — токен в ~/msp-deploy-secrets.txt</p>",
            status_code=401,
        )

    body = f"""<div class="card">
  <h1>Приглашения Jami</h1>
  <p class="muted">Создавайте одноразовые ссылки и следите за статусом. Токен уже подставлен из URL.</p>
</div>
<div class="card">
  <h2>Профиль приглашающего (ваш Jami ID)</h2>
  <p class="muted">Укажите один раз ваш Jami ID (у админ-учётки JAMS своего ID нет) — дальше он и имя подставляются во все приглашения автоматически, поля формы предзаполняются.</p>
  <label class="muted">Имя</label>
  <input id="s-name">
  <label class="muted">Jami ID (40 hex)</label>
  <input id="s-id" placeholder="7b1cf78913278f3b854286e36abf82b723ce971b">
  <button class="btn btn-sec" onclick="saveDefaults()">Сохранить</button>
  <p class="muted" id="s-res"></p>
</div>
<div class="card">
  <h2>Новое приглашение</h2>
  <label class="muted">Имя приглашающего (подставляется автоматически)</label>
  <input id="f-name" placeholder="Например: Максим">
  <label class="muted">Jami ID приглашающего (подставляется автоматически)</label>
  <input id="f-id" placeholder="7b1cf78913278f3b854286e36abf82b723ce971b">
  <label class="muted">Срок действия, часов</label>
  <input id="f-ttl" type="number" value="72" min="1" max="720">
  <label class="muted">Заметка (кто приглашён — для себя)</label>
  <input id="f-note" placeholder="Бабуля, Ивановы…">
  <label class="muted">JAMS-логин (для особого случая — обычно получатель создаёт учётку сам)</label>
  <input id="f-juser" placeholder="например: test2">
  <label class="muted">Пароль JAMS (необязательно; хранится в БД сервиса в открытом виде — используйте временные пароли)</label>
  <input id="f-jpass" placeholder="показывается получателю на странице приглашения">
  <button class="btn btn-main" onclick="createInvite()">Создать ссылку</button>
  <p class="muted" id="create-result"></p>
</div>
<div class="card">
  <h2>Последние приглашения</h2>
  <table>
    <thead><tr><th>Создано</th><th>Имя</th><th>Логин JAMS</th><th>Заметка</th><th>Статус</th><th>Ссылка</th></tr></thead>
    <tbody id="rows"><tr><td colspan="6" class="muted">Загрузка…</td></tr></tbody>
  </table>
</div>
<script>
  const TOKEN = "{token}";
  async function loadDefaults() {{
    const r = await fetch("/admin/defaults", {{headers: {{"X-Admin-Token": TOKEN}}}});
    const d = await r.json();
    document.getElementById("s-name").value = d.inviter_name || "";
    document.getElementById("s-id").value = d.inviter_id || "";
    document.getElementById("f-name").value = d.inviter_name || "";
    document.getElementById("f-id").value = d.inviter_id || "";
    document.getElementById("s-res").innerHTML = d.inviter_id
      ? '<span class="muted">Подставляется в новые приглашения автоматически.</span>'
      : '<span class="warn">Укажите ваш Jami ID один раз — дальше будет подставляться сам.</span>';
  }}
  async function saveDefaults() {{
    const r = await fetch("/admin/settings", {{
      method: "POST",
      headers: {{"Content-Type": "application/json", "X-Admin-Token": TOKEN}},
      body: JSON.stringify({{
        inviter_name: document.getElementById("s-name").value,
        inviter_id: document.getElementById("s-id").value,
      }}),
    }});
    const d = await r.json();
    if (d.ok) {{
      await loadDefaults();
      document.getElementById("s-res").innerHTML = '<span class="ok">Сохранено</span>';
    }} else {{
      document.getElementById("s-res").innerHTML = '<span class="warn">Ошибка</span>';
    }}
  }}
  function fmt(ts) {{ return ts ? new Date(ts).toLocaleString("ru-RU") : ""; }}
  function status(i) {{
    if (i.used_at) return '<span class="ok">использовано</span>';
    if (new Date(i.expires_at) < new Date()) return '<span class="warn">истекло</span>';
    return "активно";
  }}
  async function load() {{
    const r = await fetch("/admin/invites", {{headers: {{"X-Admin-Token": TOKEN}}}});
    const d = await r.json();
    const rows = document.getElementById("rows");
    rows.innerHTML = "";
    d.invites.forEach(i => {{
      const tr = document.createElement("tr");
      tr.innerHTML = "<td>" + fmt(i.created_at) + "</td><td>" + (i.inviter_name || "") +
        "</td><td>" + (i.jams_username || "") + "</td><td>" + (i.note || "") + (i.created_by && i.created_by !== "admin" ? " · создал: " + i.created_by : "") + "</td><td>" + status(i) +
        '</td><td><a href="' + "/i/" + i.token + '" target="_blank">открыть</a> <button class="btn btn-small btn-sec" onclick="copyUrl(\\'' + i.token + '\\')">копировать</button> <button class="btn btn-small btn-sec" onclick="delInvite(\\'' + i.token + '\\')">отозвать</button></td>';
      if (i.inviter_id && /^[0-9a-f]{{40}}$/.test(i.inviter_id)) {{
        const a = document.createElement("a");
        a.href = "/c/" + i.inviter_id;
        a.target = "_blank";
        a.textContent = " карточка";
        tr.cells[5].appendChild(a);
      }}
      rows.appendChild(tr);
    }});
  }}
  function copyUrl(tok) {{
    navigator.clipboard.writeText("{INVITE_BASE}/i/" + tok);
  }}
  async function delInvite(tok) {{
    if (!confirm("Отозвать приглашение?")) return;
    await fetch("/admin/invites/" + tok, {{method: "DELETE", headers: {{"X-Admin-Token": TOKEN}}}});
    load();
  }}
  async function createInvite() {{
    const payload = {{
      inviter_name: document.getElementById("f-name").value,
      inviter_id: document.getElementById("f-id").value,
      ttl_hours: parseInt(document.getElementById("f-ttl").value || "72", 10),
      note: document.getElementById("f-note").value,
      jams_username: document.getElementById("f-juser").value,
      jams_password: document.getElementById("f-jpass").value,
    }};
    const r = await fetch("/admin/invites", {{
      method: "POST",
      headers: {{"Content-Type": "application/json", "X-Admin-Token": TOKEN}},
      body: JSON.stringify(payload),
    }});
    const d = await r.json();
    document.getElementById("create-result").innerHTML = d.ok
      ? '<span class="ok">Создано:</span> <span class="mono">' + d.url + "</span>"
      : '<span class="warn">Ошибка: ' + JSON.stringify(d) + "</span>";
    load();
  }}
  load();
  loadDefaults();
</script>"""
    return _page("Админка приглашений — MSPShield", body)


@app.get("/")
def index() -> HTMLResponse:
    return _page("MSPShield · Приглашения", '<div class="card"><h1>MSPShield Jami</h1><p class="muted">Сервис приглашений и кабинета. Приглашение: /i/… · Вход в кабинет: /login · Карточка контакта: /c/…</p></div>')
