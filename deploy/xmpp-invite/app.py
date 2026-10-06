"""MSPShield XMPP Invite Portal.

Сервис приглашений для XMPP (Prosody):
- админ создаёт приглашение (просто ссылку) → гость на /i/<token> сам выбирает логин и пароль;
- админка: /admin?token=<XMPP_INVITE_ADMIN_TOKEN>.

Деплой: /opt/xmpp-invite (systemd xmpp-invite.service, порт 8895,
Caddy: invite.msp-claude.online → 127.0.0.1:8895).
"""
import base64
import io
import os
import re
import secrets
import socket
import sqlite3
import ssl
import subprocess
from datetime import datetime, timedelta, timezone

import qrcode
from fastapi import FastAPI, Header, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse, Response

DB_DIR = os.getenv("DB_DIR", "/opt/xmpp-invite/data")
DB = os.path.join(DB_DIR, "invites.db")
ADMIN_TOKEN = os.getenv("ADMIN_TOKEN", "")
XMPP_DOMAIN = os.getenv("XMPP_DOMAIN", "x.msp-claude.online")
PROSODY_CONTAINER = os.getenv("PROSODY_CONTAINER", "msp-prosody")
INVITE_BASE = os.getenv("INVITE_BASE", "https://invite.msp-claude.online")
BRAND = os.getenv("BRAND", "MSPShield Chat")

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
             username    TEXT,
             password    TEXT,
             note        TEXT DEFAULT '',
             created_at  TEXT,
             expires_at  TEXT,
             used_at     TEXT
           )"""
    )
    try:
        c.execute("ALTER TABLE invites ADD COLUMN created_by TEXT DEFAULT 'admin'")
    except sqlite3.OperationalError:
        pass
    c.execute(
        """CREATE TABLE IF NOT EXISTS sessions (
             token      TEXT PRIMARY KEY,
             jid        TEXT,
             created_at TEXT,
             expires_at TEXT
           )"""
    )
    c.commit()
    c.close()


def _run(cmd):
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        return r.returncode, ((r.stdout or "") + (r.stderr or "")).strip()
    except Exception as e:
        return 1, str(e)


def prosody_register(username, password):
    rc, out = _run(
        ["docker", "exec", "-u", "prosody", PROSODY_CONTAINER, "prosodyctl",
         "register", username, XMPP_DOMAIN, password]
    )
    low = out.lower()
    if rc == 0 and "created" in low:
        return True, "ok"
    if "already" in low or "exist" in low:
        return False, "taken"
    if rc == 0:
        return True, "ok"
    return False, (out[:200] or "prosodyctl error")


def _enc_path(s):
    return "".join(c if c.isalnum() else ("%%%02x" % ord(c)) for c in s)


def _account_file(username):
    return "/var/lib/prosody/%s/accounts/%s.dat" % (_enc_path(XMPP_DOMAIN), _enc_path(username))


def account_exists(username):
    path = _account_file(username)
    rc, out = _run(["docker", "exec", PROSODY_CONTAINER, "sh", "-c", "test -f '%s' && echo YES || echo NO" % path])
    return "YES" in out


def prosody_delete(username):
    path = _account_file(username)
    cmd = "rm -f '%s' && (test ! -f '%s' && echo REMOVED || echo STILL)" % (path, path)
    rc, out = _run(["docker", "exec", PROSODY_CONTAINER, "sh", "-c", cmd])
    if "REMOVED" not in out:
        return False, ("не удалось удалить файл аккаунта: " + out[:200])
    rc2, out2 = _run(["docker", "restart", PROSODY_CONTAINER])
    return rc2 == 0, out2[:200]


def gen_password():
    alphabet = "abcdefghjkmnpqrstuvwxyzABCDEFGHJKMNPQRSTUVWXYZ23456789"
    body = "".join(secrets.choice(alphabet) for _ in range(14))
    return body + "!" + str(secrets.randbelow(90) + 10)


def _qr_png(data):
    img = qrcode.make(data)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


COOKIE = "xmpp_cab"


def sasl_check(username, password):
    host = XMPP_DOMAIN
    try:
        s = socket.create_connection((host, 5222), timeout=12)
        s.settimeout(12)
        s.sendall(("<stream:stream to='%s' xmlns='jabber:client' xmlns:stream='http://etherx.jabber.org/streams' version='1.0'>" % host).encode())
        data = s.recv(8192)
        if b"starttls" in data:
            s.sendall(b"<starttls xmlns='urn:ietf:params:xml:ns:xmpp-tls'/>")
            s.recv(1024)
            ctx = ssl.create_default_context()
            s = ctx.wrap_socket(s, server_hostname=host)
            s.sendall(("<stream:stream to='%s' xmlns='jabber:client' xmlns:stream='http://etherx.jabber.org/streams' version='1.0'>" % host).encode())
            s.recv(8192)
        auth = base64.b64encode(("\x00%s\x00%s" % (username, password)).encode()).decode()
        s.sendall(("<auth xmlns='urn:ietf:params:xml:ns:xmpp-sasl' mechanism='PLAIN'>%s</auth>" % auth).encode())
        r = s.recv(2048)
        s.close()
        return b"success" in r
    except Exception:
        return False


def _unescape_name(n):
    return re.sub(r"%([0-9a-f]{2})", lambda m: chr(int(m.group(1), 16)), n)


def list_accounts():
    enc = _enc_path(XMPP_DOMAIN)
    rc, out = _run(["docker", "exec", PROSODY_CONTAINER, "sh", "-c",
                    "stat -c '%%Y %%n' /var/lib/prosody/%s/accounts/*.dat 2>/dev/null" % enc])
    users = []
    for line in out.splitlines():
        parts = line.strip().split()
        if len(parts) >= 2 and parts[1].endswith(".dat"):
            try:
                mt = int(parts[0])
            except Exception:
                mt = 0
            users.append({"username": _unescape_name(parts[1].split("/")[-1][:-4]), "mtime": mt})
    users.sort(key=lambda x: -x["mtime"])
    return users


def _get_session(request):
    tok = request.cookies.get(COOKIE, "")
    if not tok:
        return None
    c = db()
    r = c.execute("SELECT * FROM sessions WHERE token=?", (tok,)).fetchone()
    c.close()
    if not r or datetime.fromisoformat(r["expires_at"]) < datetime.now(timezone.utc):
        return None
    return r


def _new_session(jid):
    tok = secrets.token_urlsafe(24)
    now = datetime.now(timezone.utc)
    c = db()
    c.execute("INSERT INTO sessions (token, jid, created_at, expires_at) VALUES (?,?,?,?)",
              (tok, jid, now.isoformat(), (now + timedelta(days=30)).isoformat()))
    c.commit()
    c.close()
    return tok


_HTML = """<!doctype html>
<html lang="ru"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{{title}}</title>
<style>
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
  input { width:100%; padding:11px 12px; font-size:15px; border:1px solid #cfd8de;
          border-radius:8px; margin:4px 0 10px; }
  label { font-size:13px; color:#68757f; }
  ol.steps { padding-left:20px; margin:6px 0; }
  ol.steps li { margin:6px 0; }
  .qr { text-align:center; }
  .qr img { width:200px; height:200px; }
  table { width:100%; border-collapse:collapse; font-size:14px; }
  th,td { text-align:left; padding:8px 8px 8px 0; border-bottom:1px solid #e6ebef; }
  a { color:#005699; }
</style></head><body><div class="wrap">{{body}}</div></body></html>"""


def _page(title, body, status_code=200):
    return HTMLResponse(_HTML.replace("{{title}}", title).replace("{{body}}", body), status_code=status_code)


def _status(row):
    if row["used_at"]:
        return "использовано"
    if datetime.fromisoformat(row["expires_at"]) < datetime.now(timezone.utc):
        return "истекло"
    return "активно"


@app.get("/health")
def health():
    return {"ok": True}


# ─── публичные страницы ─────────────────────────────────────────────────────

@app.get("/")
def index() -> HTMLResponse:
    return _page(
        "MSPShield · Приглашения",
        '<div class="card"><h1>MSPShield · Приглашения</h1>'
        '<p class="muted">Сервис приглашений в чат MSPShield (XMPP). '
        'Персональная ссылка: /i/… · личный кабинет: /login · админка: /admin.</p></div>',
    )


@app.get("/i/{token}")
def invite_page(token: str) -> HTMLResponse:
    c = db()
    row = c.execute("SELECT * FROM invites WHERE token=?", (token,)).fetchone()
    c.close()
    if not row:
        return _page("Приглашение не найдено",
                     '<div class="card"><h1>Приглашение не найдено</h1>'
                     '<p class="muted">Ссылка неверная или удалена. Попросите новую.</p></div>')
    used = bool(row["used_at"])
    expired = datetime.fromisoformat(row["expires_at"]) < datetime.now(timezone.utc)
    if used:
        jid = ("%s@%s" % (row["username"], XMPP_DOMAIN)) if row["username"] else ""
        jidline = ('<p>Ваш адрес: <span class="mono">%s</span></p>' % jid) if jid else ""
        return _page(
            "Приглашение уже использовано",
            '<div class="card"><h1>Приглашение уже использовано</h1>'
            '<p class="ok">По этой ссылке аккаунт уже создан.</p>' + jidline +
            '<p class="muted">Войти в личный кабинет: <a href="/login">/login</a>. '
            'Забыли пароль — попросите администратора выдать новый.</p></div>',
        )
    if expired:
        return _page(
            "Приглашение истекло",
            '<div class="card"><h1>Приглашение истекло</h1>'
            '<p class="muted">Попросите администратора создать новое.</p></div>',
        )
    body = f"""<div class="card">
  <h1>Вас приглашают в MSPShield Chat</h1>
  <p class="muted">Приватный мессенджер на нашем сервере: сообщения, голосовые, файлы и звонки — всё внутри контура.</p>
</div>
<div class="card">
  <h2>1. Установите приложение</h2>
  <a class="btn btn-main" href="https://play.google.com/store/apps/details?id=eu.siacs.conversations">Conversations — Google Play (Android)</a>
  <a class="btn btn-main" href="https://f-droid.org/packages/eu.siacs.conversations/">Conversations — F-Droid</a>
  <a class="btn btn-main" href="https://apps.apple.com/app/monal-xmpp-chat/id317711500">Monal — App Store (iPhone / iPad)</a>
  <a class="btn btn-sec" href="https://gajim.org/">Gajim — Windows / macOS / Linux</a>
</div>
<div class="card">
  <h2>2. Создайте аккаунт</h2>
  <div id="reg-form">
    <p class="muted">Придумайте логин — его увидят коллеги (латиница/цифры, 2–32 символа). Логин создаётся здесь; регистрация в приложении не нужна.</p>
    <label>Логин</label>
    <input id="r-user" placeholder="например: ivan" autocomplete="off">
    <label>Пароль (можно сгенерировать)</label>
    <input id="r-pass" autocomplete="off">
    <p class="muted"><button class="btn btn-small btn-sec" onclick="genPass()">Сгенерировать пароль</button></p>
    <button class="btn btn-main" onclick="registerAcc()">Создать аккаунт</button>
    <p class="muted" id="reg-res"></p>
    <p class="muted">После создания приглашение станет недействительным — это нормально.</p>
  </div>
  <div id="reg-done" style="display:none"></div>
</div>
<div class="card">
  <h2>3. Подключение</h2>
  <ol class="steps">
    <li><b>Откройте приложение → «Добавить аккаунт» → «У меня уже есть аккаунт».</b> Не выбирайте «Регистрация / Создать аккаунт»: регистрация на сервере выключена, аккаунт уже создан на шаге 2.</li>
    <li>Введите адрес (JID) и пароль, которые появятся на экране после создания.</li>
    <li>Готово — можно писать. Голосовые сообщения, файлы и звонки работают сразу.</li>
  </ol>
  <p class="muted">Пишет «регистрация запрещена / не работает»? Это приложение про свой пункт «Зарегистрироваться» — он не нужен: аккаунт уже создан, выбирайте «У меня уже есть аккаунт».</p>
  <p class="muted">Если приложение спросит хост и порт вручную: <b>{XMPP_DOMAIN}</b>, порт <b>5222</b> (TLS).</p>
</div>
<div class="card">
  <h2>Дальше</h2>
  <p class="muted">Личный кабинет — свои данные, приглашения коллег и смена пароля: <a href="/login">/login</a>.</p>
</div>
<script>
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
    const el = document.getElementById("reg-res");
    el.innerHTML = "Создаю…";
    const r = await fetch("/i/{token}/register", {{
      method: "POST",
      headers: {{"Content-Type": "application/json"}},
      body: JSON.stringify({{
        username: document.getElementById("r-user").value,
        password: document.getElementById("r-pass").value,
      }}),
    }});
    const d = await r.json().catch(() => ({{}}));
    if (d.ok) {{
      document.getElementById("reg-form").style.display = "none";
      const done = document.getElementById("reg-done");
      done.style.display = "block";
      done.innerHTML = '<p class="ok">Аккаунт создан!</p>' +
        '<div class="kv"><span class="k">Сервер</span> <span class="mono" id="srv">{XMPP_DOMAIN}</span> <button class="btn btn-small btn-sec" onclick="copyText(&quot;srv&quot;)">копировать</button></div>' +
        '<div class="kv"><span class="k">Адрес (JID)</span> <span class="mono" id="jad">' + d.jid + '</span> <button class="btn btn-small btn-sec" onclick="copyText(&quot;jad&quot;)">копировать</button></div>' +
        '<div class="kv"><span class="k">Пароль</span> <span class="mono" id="pwd">' + document.getElementById("r-pass").value + '</span> <button class="btn btn-small btn-sec" onclick="copyText(&quot;pwd&quot;)">копировать</button></div>' +
        '<p class="muted">В приложении выберите «У меня уже есть аккаунт» (НЕ «Регистрация») и введите эти данные (шаг 3). Аккаунт уже работает.</p>';
    }} else {{
      el.innerHTML = '<span class="warn">' + (d.message || d.detail || "Не получилось — проверьте данные.") + "</span>";
    }}
  }}
</script>"""
    return _page("Приглашение — MSPShield Chat", body)


@app.post("/i/{token}/register")
def invite_register(token: str, payload: dict) -> dict:
    c = db()
    row = c.execute("SELECT * FROM invites WHERE token=?", (token,)).fetchone()
    if not row:
        c.close()
        raise HTTPException(status_code=404, detail="not found")
    if row["used_at"]:
        c.close()
        return {"ok": False, "message": "Приглашение уже использовано."}
    if datetime.fromisoformat(row["expires_at"]) < datetime.now(timezone.utc):
        c.close()
        return {"ok": False, "message": "Приглашение истекло — попросите новое."}
    username = (payload.get("username") or "").strip().lower()
    password = payload.get("password") or ""
    if not USER_RE.fullmatch(username):
        c.close()
        return {"ok": False, "message": "Логин: латиница/цифры/._- (2–32), начните с буквы или цифры."}
    if len(password) < 8:
        c.close()
        return {"ok": False, "message": "Пароль — минимум 8 символов."}
    if account_exists(username):
        c.close()
        return {"ok": False, "message": "Этот логин занят — выберите другой."}
    ok, reason = prosody_register(username, password)
    if not ok:
        c.close()
        return {"ok": False, "message": "Не получилось создать аккаунт: " + reason}
    now = datetime.now(timezone.utc).isoformat()
    c.execute("UPDATE invites SET username=?, password=?, used_at=? WHERE token=?",
              (username, password, now, token))
    c.commit()
    c.close()
    return {"ok": True, "jid": "%s@%s" % (username, XMPP_DOMAIN), "server": XMPP_DOMAIN}


@app.get("/welcome/{token}")
def welcome_redirect(token: str) -> Response:
    return RedirectResponse(f"/i/{token}")


@app.get("/i/{token}/qr.png")
def invite_qr(token: str) -> Response:
    c = db()
    row = c.execute("SELECT username FROM invites WHERE token=?", (token,)).fetchone()
    c.close()
    if not row:
        raise HTTPException(status_code=404, detail="not found")
    jid = "%s@%s" % (row["username"], XMPP_DOMAIN)
    return Response(_qr_png("xmpp:" + jid), media_type="image/png")


@app.post("/i/{token}/confirm")
def invite_confirm(token: str) -> dict:
    c = db()
    row = c.execute("SELECT * FROM invites WHERE token=?", (token,)).fetchone()
    if not row:
        c.close()
        raise HTTPException(status_code=404, detail="not found")
    if not row["used_at"]:
        c.execute("UPDATE invites SET used_at=? WHERE token=?",
                  (datetime.now(timezone.utc).isoformat(), token))
        c.commit()
    c.close()
    return {"ok": True}


# ─── личный кабинет пользователя ──────────────────────────────────────────

@app.get("/login")
def login_page() -> HTMLResponse:
    body = f"""<div class="card">
  <h1>Вход в личный кабинет</h1>
  <p class="muted">Логин и пароль — от вашего аккаунта MSPShield Chat (JID вида имя@{XMPP_DOMAIN}).</p>
  <label>Логин или JID</label>
  <input id="lu" placeholder="ivan или ivan@{XMPP_DOMAIN}" autocomplete="username">
  <label>Пароль</label>
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
    if (d.ok) {{ window.location.href = "/u"; return; }}
    el.innerHTML = '<span class="warn">' + (d.message || "Не получилось войти — проверьте логин и пароль.") + "</span>";
  }}
</script>"""
    return _page("Вход — MSPShield Chat", body)


@app.post("/login")
def login_submit(payload: dict) -> Response:
    raw = (payload.get("username") or "").strip().lower()
    password = payload.get("password") or ""
    username = raw.split("@")[0] if "@" in raw else raw
    if not username or not password:
        return JSONResponse({"ok": False, "message": "Заполните логин и пароль."}, status_code=400)
    if not USER_RE.fullmatch(username):
        return JSONResponse({"ok": False, "message": "Проверьте логин."}, status_code=400)
    if not sasl_check(username, password):
        return JSONResponse({"ok": False, "message": "Неверный логин или пароль."}, status_code=401)
    tok = _new_session("%s@%s" % (username, XMPP_DOMAIN))
    resp = JSONResponse({"ok": True})
    resp.set_cookie(COOKIE, tok, max_age=30 * 24 * 3600, httponly=True, samesite="lax")
    return resp


@app.get("/logout")
def logout_page() -> Response:
    resp = RedirectResponse("/login")
    resp.delete_cookie(COOKIE)
    return resp


@app.get("/u")
def cabinet(request: Request) -> Response:
    sess = _get_session(request)
    if not sess:
        return RedirectResponse("/login")
    jid = sess["jid"]
    body = f"""<div class="card">
  <h1>Личный кабинет</h1>
  <p class="muted">Вы вошли как <b>{jid}</b>. <a href="/logout">Выйти</a></p>
</div>
<div class="card">
  <h2>Мои данные</h2>
  <div class="kv"><span class="k">Сервер</span> <span class="mono" id="srv">{XMPP_DOMAIN}</span>
    <button class="btn btn-small btn-sec" onclick="copyText('srv')">копировать</button></div>
  <div class="kv"><span class="k">Адрес (JID)</span> <span class="mono" id="jad">{jid}</span>
    <button class="btn btn-small btn-sec" onclick="copyText('jad')">копировать</button></div>
  <p class="muted">Чтобы подключить новое устройство — установите приложение и войдите этим JID и паролем. Пароль можно сменить ниже. Чтобы коллега добавил вас в контакты — передайте ему свой адрес (JID).</p>
</div>
<div class="card">
  <h2>Пригласить коллег</h2>
  <p class="muted">Создайте ссылку и отправьте её коллеге: он сам выберет логин и пароль.</p>
  <label>Заметка (кому)</label>
  <input id="iv-note" placeholder="Пётр, отдел продаж…">
  <button class="btn btn-main" onclick="createInvite()">Создать приглашение</button>
  <p class="muted" id="iv-res"></p>
  <table>
    <thead><tr><th>Создано</th><th>Логин</th><th>Заметка</th><th>Статус</th><th></th></tr></thead>
    <tbody id="iv-rows"><tr><td colspan="5" class="muted">Загрузка…</td></tr></tbody>
  </table>
</div>
<div class="card">
  <h2>Смена пароля</h2>
  <label>Текущий пароль</label>
  <input id="p-old" type="password" autocomplete="current-password">
  <label>Новый пароль (минимум 8 символов)</label>
  <input id="p-new" type="password" autocomplete="new-password">
  <button class="btn btn-main" onclick="changePass()">Сменить пароль</button>
  <p class="muted" id="pw-res"></p>
</div>
<script>
  function copyText(id) {{
    const el = document.getElementById(id);
    if (el) {{ navigator.clipboard.writeText(el.textContent.trim()); }}
  }}
  function fmt(ts) {{ return ts ? new Date(ts).toLocaleString("ru-RU") : ""; }}
  function status(i) {{
    if (i.used_at) return '<span class="ok">использовано</span>';
    if (new Date(i.expires_at) < new Date()) return '<span class="warn">истекло</span>';
    return "активно";
  }}
  async function loadInvites() {{
    const r = await fetch("/u/invites");
    const d = await r.json().catch(() => ({{invites: []}}));
    const rows = document.getElementById("iv-rows");
    rows.innerHTML = "";
    (d.invites || []).forEach(i => {{
      const tr = document.createElement("tr");
      tr.innerHTML = "<td>" + fmt(i.created_at) + "</td><td class=\\"mono\\">" + (i.username || "—") +
        "</td><td>" + (i.note || "") + "</td><td>" + status(i) +
        '</td><td><a href="/i/' + i.token + '" target="_blank">открыть</a> ' +
        '<button class="btn btn-small btn-sec" onclick="delInvite(' + i.id + ')">удалить</button></td>';
      rows.appendChild(tr);
    }});
  }}
  async function createInvite() {{
    const el = document.getElementById("iv-res");
    el.innerHTML = "Создаю…";
    const r = await fetch("/u/invites", {{
      method: "POST",
      headers: {{"Content-Type": "application/json"}},
      body: JSON.stringify({{note: document.getElementById("iv-note").value}}),
    }});
    const d = await r.json().catch(() => ({{}}));
    if (d.ok) {{
      el.innerHTML = '<span class="ok">Создано:</span> <span class="mono">' + d.url + "</span> — отправьте коллеге.";
      document.getElementById("iv-note").value = "";
    }} else {{
      el.innerHTML = '<span class="warn">' + (d.message || "Ошибка") + "</span>";
    }}
    loadInvites();
  }}
  async function delInvite(id) {{
    if (!confirm("Удалить приглашение?")) return;
    await fetch("/u/invites/" + id, {{method: "DELETE"}});
    loadInvites();
  }}
  async function changePass() {{
    const el = document.getElementById("pw-res");
    el.innerHTML = "Меняю…";
    const r = await fetch("/u/password", {{
      method: "POST",
      headers: {{"Content-Type": "application/json"}},
      body: JSON.stringify({{old_password: document.getElementById("p-old").value, new_password: document.getElementById("p-new").value}}),
    }});
    const d = await r.json().catch(() => ({{}}));
    el.innerHTML = d.ok ? '<span class="ok">Пароль изменён — на новых устройствах вводите его.</span>' : '<span class="warn">' + (d.message || "Ошибка") + "</span>";
  }}
  loadInvites();
</script>"""
    return _page("Личный кабинет — MSPShield Chat", body)


@app.get("/u/qr.png")
def cabinet_qr(request: Request) -> Response:
    sess = _get_session(request)
    if not sess:
        raise HTTPException(status_code=401, detail="unauthorized")
    return Response(_qr_png("xmpp:" + sess["jid"]), media_type="image/png")


@app.get("/u/invites")
def cabinet_invites(request: Request) -> dict:
    sess = _get_session(request)
    if not sess:
        raise HTTPException(status_code=401, detail="unauthorized")
    uname = sess["jid"].split("@")[0]
    c = db()
    rows = []
    for r in c.execute("SELECT * FROM invites WHERE created_by=? ORDER BY id DESC LIMIT 100", (uname,)):
        d = dict(r)
        d.pop("password", None)
        rows.append(d)
    c.close()
    return {"invites": rows}


@app.post("/u/invites")
def cabinet_create(request: Request, payload: dict) -> dict:
    sess = _get_session(request)
    if not sess:
        raise HTTPException(status_code=401, detail="unauthorized")
    uname = sess["jid"].split("@")[0]
    return _create_invite(
        username="",
        note=payload.get("note", ""),
        ttl=int(payload.get("ttl_hours") or 72),
        created_by=uname,
    )


@app.delete("/u/invites/{inv_id}")
def cabinet_delete(request: Request, inv_id: int) -> dict:
    sess = _get_session(request)
    if not sess:
        raise HTTPException(status_code=401, detail="unauthorized")
    uname = sess["jid"].split("@")[0]
    c = db()
    cur = c.execute("DELETE FROM invites WHERE id=? AND created_by=?", (inv_id, uname))
    c.commit()
    c.close()
    return {"ok": cur.rowcount > 0}


@app.post("/u/password")
def cabinet_password(request: Request, payload: dict) -> dict:
    sess = _get_session(request)
    if not sess:
        raise HTTPException(status_code=401, detail="unauthorized")
    uname = sess["jid"].split("@")[0]
    old = payload.get("old_password") or ""
    new = payload.get("new_password") or ""
    if len(new) < 8:
        return {"ok": False, "message": "Новый пароль — минимум 8 символов."}
    if not sasl_check(uname, old):
        return {"ok": False, "message": "Текущий пароль неверный."}
    ok, reason = prosody_register(uname, new)
    if not ok:
        return {"ok": False, "message": "Prosody: " + reason}
    return {"ok": True}


# ─── админка ────────────────────────────────────────────────────────────────

def _admin_check(token):
    if token != ADMIN_TOKEN:
        raise HTTPException(status_code=401, detail="unauthorized")


@app.get("/admin/invites")
def admin_invites(x_admin_token: str = Header("")) -> dict:
    _admin_check(x_admin_token)
    c = db()
    rows = [dict(r) for r in c.execute("SELECT * FROM invites ORDER BY id DESC LIMIT 200")]
    c.close()
    for r in rows:
        r.pop("password", None)
    return {"invites": rows}


def _create_invite(username, note, ttl, created_by, password=None):
    ttl = max(1, min(720, int(ttl or 72)))
    tok = secrets.token_urlsafe(24)
    now = datetime.now(timezone.utc)
    c = db()
    c.execute(
        "INSERT INTO invites (token, username, password, note, created_at, expires_at, used_at, created_by) "
        "VALUES (?,?,?,?,?,?,?,?)",
        (tok, "", "", note or "", now.isoformat(),
         (now + timedelta(hours=ttl)).isoformat(), None, created_by or "admin"),
    )
    c.commit()
    c.close()
    return {"ok": True, "url": f"{INVITE_BASE}/i/{tok}", "token": tok}


@app.post("/admin/invites")
def admin_create(payload: dict, x_admin_token: str = Header("")) -> dict:
    _admin_check(x_admin_token)
    return _create_invite(
        username="",
        note=payload.get("note", ""),
        ttl=int(payload.get("ttl_hours") or 72),
        created_by="admin",
        password=payload.get("password") or "",
    )


@app.delete("/admin/invites/{inv_id}")
def admin_delete(inv_id: int, x_admin_token: str = Header("")) -> dict:
    _admin_check(x_admin_token)
    c = db()
    cur = c.execute("DELETE FROM invites WHERE id=?", (inv_id,))
    c.commit()
    c.close()
    return {"ok": cur.rowcount > 0}


@app.post("/admin/accounts/delete")
def admin_account_delete(payload: dict, x_admin_token: str = Header("")) -> dict:
    _admin_check(x_admin_token)
    username = (payload.get("username") or "").strip().lower()
    if not USER_RE.fullmatch(username):
        return {"ok": False, "message": "bad username"}
    ok, out = prosody_delete(username)
    return {"ok": ok, "message": out if not ok else "Аккаунт удалён (Prosody перезапущен)."}


@app.get("/admin/users")
def admin_users(x_admin_token: str = Header("")) -> dict:
    _admin_check(x_admin_token)
    users = list_accounts()
    c = db()
    for u in users:
        r = c.execute("SELECT used_at, expires_at FROM invites WHERE username=? ORDER BY id DESC LIMIT 1",
                      (u["username"],)).fetchone()
        if r and r["used_at"]:
            u["invite"] = "использовано"
        elif r and datetime.fromisoformat(r["expires_at"]) > datetime.now(timezone.utc):
            u["invite"] = "активно"
        elif r:
            u["invite"] = "истекло"
        else:
            u["invite"] = ""
    c.close()
    return {"users": users}


@app.post("/admin/accounts/password")
def admin_new_password(payload: dict, x_admin_token: str = Header("")) -> dict:
    _admin_check(x_admin_token)
    username = (payload.get("username") or "").strip().lower()
    if not USER_RE.fullmatch(username):
        return {"ok": False, "message": "bad username"}
    if not account_exists(username):
        return {"ok": False, "message": "Аккаунт не найден."}
    pw = gen_password()
    ok, reason = prosody_register(username, pw)
    if not ok:
        return {"ok": False, "message": "Prosody: " + reason}
    return {"ok": True, "password": pw}


@app.get("/admin")
def admin_page(token: str = "") -> HTMLResponse:
    if token != ADMIN_TOKEN:
        return _page("Доступ запрещён",
                     '<div class="card"><h1>Доступ запрещён</h1>'
                     '<p class="muted">Нужен токен администратора: /admin?token=…</p></div>',
                     status_code=401)
    body = f"""<div class="card">
  <h1>Приглашения в MSPShield Chat</h1>
  <p class="muted">Создавайте одноразовые ссылки: гость сам выберет логин и пароль на странице приглашения.</p>
</div>
<div class="card">
  <h2>Новое приглашение</h2>
  <p class="muted">Создайте ссылку и отправьте её человеку: он сам выберет логин и пароль на странице приглашения.</p>
  <label>Заметка (для себя: кому выдали)</label>
  <input id="f-note" placeholder="Иван, бухгалтерия…">
  <label>Срок действия, часов</label>
  <input id="f-ttl" type="number" value="72" min="1" max="720">
  <button class="btn btn-main" onclick="createInvite()">Создать приглашение</button>
  <p class="muted" id="c-res"></p>
</div>
<div class="card">
  <h2>Список</h2>
  <table>
    <thead><tr><th>Создано</th><th>Логин</th><th>Заметка</th><th>Статус</th><th></th></tr></thead>
    <tbody id="rows"><tr><td colspan="5" class="muted">Загрузка…</td></tr></tbody>
  </table>
</div>
<div class="card">
  <h2>Пользователи</h2>
  <p class="muted">Все аккаунты Prosody. «Новый пароль» — сгенерировать и показать (старый перестанет работать), «удалить» — убрать аккаунт.</p>
  <table>
    <thead><tr><th>Логин</th><th>Обновлён</th><th>Приглашение</th><th></th></tr></thead>
    <tbody id="urows"><tr><td colspan="4" class="muted">Загрузка…</td></tr></tbody>
  </table>
</div>
<script>
  const TOKEN = "{token}";
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
    (d.invites || []).forEach(i => {{
      const tr = document.createElement("tr");
      tr.innerHTML = "<td>" + fmt(i.created_at) + "</td><td class=\\"mono\\">" + (i.username || "—") +
        "</td><td>" + (i.note || "") + "</td><td>" + status(i) +
        '</td><td><a href="/i/' + i.token + '" target="_blank">открыть</a> ' +
        '<button class="btn btn-small btn-sec" onclick="copyUrl(\\'' + i.token + '\\')">копировать</button> ' +
        '<button class="btn btn-small btn-sec" onclick="delInvite(' + i.id + ')">удалить</button>' +
        (i.username ? ' <button class="btn btn-small btn-sec" onclick="delAccount(\\'' + i.username + '\\')">−аккаунт</button>' : '') +
        '</td>';
      rows.appendChild(tr);
    }});
  }}
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
      el.innerHTML = '<span class="ok">Создано:</span> <span class="mono">' + d.url +
        "</span> — отправьте ссылку человеку.";
      document.getElementById("f-note").value = "";
    }} else {{
      el.innerHTML = '<span class="warn">' + (d.message || "Ошибка") + "</span>";
    }}
    load();
  }}
  function copyUrl(tok) {{ navigator.clipboard.writeText("{INVITE_BASE}/i/" + tok); }}
  async function delInvite(id) {{
    if (!confirm("Удалить приглашение?")) return;
    await fetch("/admin/invites/" + id, {{method: "DELETE", headers: {{"X-Admin-Token": TOKEN}}}});
    load();
  }}
  async function delAccount(username) {{
    if (!confirm("Удалить аккаунт " + username + " из Prosody? (короткий перезапуск)")) return;
    await fetch("/admin/accounts/delete", {{
      method: "POST",
      headers: {{"Content-Type": "application/json", "X-Admin-Token": TOKEN}},
      body: JSON.stringify({{username: username}}),
    }});
    alert("Готово (если аккаунт существовал)");
    loadUsers();
  }}
  async function loadUsers() {{
    const r = await fetch("/admin/users", {{headers: {{"X-Admin-Token": TOKEN}}}});
    const d = await r.json().catch(() => ({{users: []}}));
    const rows = document.getElementById("urows");
    rows.innerHTML = "";
    (d.users || []).forEach(u => {{
      const tr = document.createElement("tr");
      tr.innerHTML = "<td class=\\"mono\\">" + u.username + "</td><td>" + new Date(u.mtime * 1000).toLocaleString("ru-RU") +
        "</td><td>" + (u.invite || "—") +
        '</td><td><button class="btn btn-small btn-sec" onclick="newPass(\\'' + u.username + '\\')">новый пароль</button> ' +
        '<button class="btn btn-small btn-sec" onclick="delAccount(\\'' + u.username + '\\')">удалить</button></td>';
      rows.appendChild(tr);
    }});
  }}
  async function newPass(username) {{
    if (!confirm("Сгенерировать новый пароль для " + username + "?")) return;
    const r = await fetch("/admin/accounts/password", {{
      method: "POST",
      headers: {{"Content-Type": "application/json", "X-Admin-Token": TOKEN}},
      body: JSON.stringify({{username: username}}),
    }});
    const d = await r.json().catch(() => ({{}}));
    if (d.ok) {{ alert("Новый пароль для " + username + ": " + d.password + "\\n(передайте лично; старый больше не действует)"); }}
    else {{ alert(d.message || "Ошибка"); }}
  }}
  load();
  loadUsers();
</script>"""
    return _page("MSPShield · Приглашения (админка)", body)
