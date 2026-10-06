"""MSPShield Matrix Invite Portal.

Назначение: приглашения в Matrix (Synapse).
- админ создаёт приглашение (просто ссылку) -> гость на /i/<token> сам выбирает логин и пароль;
- аккаунт создаётся в Synapse через Admin API (без публичной регистрации).
Админка: /admin?token=<ADMIN_TOKEN>.
Хостинг: /opt/matrix-invite (systemd matrix-invite.service, порт 8896;
Caddy: names.msp-claude.online -> 127.0.0.1:8896).
"""
import json
import os
import re
import secrets
import sqlite3
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone

from fastapi import FastAPI, Header, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse, Response

DB_DIR = os.getenv("DB_DIR", "/opt/matrix-invite/data")
DB = os.path.join(DB_DIR, "invites.db")
ADMIN_TOKEN = os.getenv("ADMIN_TOKEN", "")
MATRIX_DOMAIN = os.getenv("MATRIX_DOMAIN", "m.msp-claude.online")
SYNAPSE_URL = os.getenv("SYNAPSE_URL", "https://m.msp-claude.online")
SYNAPSE_ADMIN_TOKEN = os.getenv("SYNAPSE_ADMIN_TOKEN", "")
ELEMENT_URL = os.getenv("ELEMENT_URL", "https://e.msp-claude.online")
INVITE_BASE = os.getenv("INVITE_BASE", "https://names.msp-claude.online")
BRAND = os.getenv("BRAND", "MSPShield")

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
    c.commit()
    c.close()


# ── Synapse Admin API ────────────────────────────────────────────────────────

def _syn_api(method, path, data=None):
    if not SYNAPSE_ADMIN_TOKEN:
        return 0, {"error": "SYNAPSE_ADMIN_TOKEN не задан"}
    hdr = {
        "Authorization": "Bearer " + SYNAPSE_ADMIN_TOKEN,
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


def matrix_user_exists(username):
    st, _ = _syn_api("GET", "/_synapse/admin/v2/users/" + urllib.parse.quote(_mxid(username), safe=""))
    return st == 200


def matrix_create(username, password):
    st, data = _syn_api(
        "PUT",
        "/_synapse/admin/v2/users/" + urllib.parse.quote(_mxid(username), safe=""),
        {"password": password, "displayname": username, "admin": False, "deactivated": False},
    )
    if st in (200, 201):
        return True, "ok"
    return False, (data.get("error") or ("HTTP %s" % st))


def matrix_deactivate(username):
    st, data = _syn_api(
        "POST",
        "/_synapse/admin/v1/deactivate/" + urllib.parse.quote(_mxid(username), safe=""),
        {"erase": True},
    )
    if st in (200, 201):
        return True, "ok"
    return False, (data.get("error") or ("HTTP %s" % st))


# ── общее ────────────────────────────────────────────────────────────────────

def _admin_check(tok: str):
    if not ADMIN_TOKEN or tok != ADMIN_TOKEN:
        raise HTTPException(status_code=403, detail="forbidden")


def _create_invite(note, ttl, created_by="admin"):
    ttl = max(1, min(720, int(ttl or 72)))
    tok = secrets.token_urlsafe(24)
    now = datetime.now(timezone.utc)
    c = db()
    c.execute(
        "INSERT INTO invites (token, username, password, note, created_at, expires_at, used_at, created_by) "
        "VALUES (?,?,?,?,?,?,?,?)",
        (tok, "", "", note or "", now.isoformat(),
         (now + timedelta(hours=ttl)).isoformat(), None, created_by),
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
        '<p class="muted">Сервис приглашений. Ссылка-приглашение выглядит как '
        '<span class="mono">/i/&lt;token&gt;</span>.</p></div>',
    )


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
            '<p class="muted">Войти: <a href="' + ELEMENT_URL + '">' + ELEMENT_URL + '</a>. '
            'Забыли пароль — попросите администратора выдать новый.</p></div>',
        )

    body = f"""<div class="card">
  <h1>Вас приглашают в MSPShield Chat</h1>
  <p class="muted">Мессенджер на базе Matrix: сообщения, голосовые, файлы и звонки — всё внутри контура.</p>
</div>
<div class="card">
  <h2>1. Приложение (Element)</h2>
  <a class="btn btn-main" href="{ELEMENT_URL}">Element — веб-версия (в браузере)</a>
  <a class="btn btn-main" href="https://play.google.com/store/apps/details?id=im.vector.app">Element — Google Play (Android)</a>
  <a class="btn btn-main" href="https://apps.apple.com/app/element-messenger/id1083446067">Element — App Store (iPhone / iPad)</a>
  <a class="btn btn-sec" href="https://f-droid.org/packages/im.vector.app/">Element — F-Droid</a>
</div>
<div class="card">
  <h2>2. Создайте аккаунт</h2>
  <div id="reg-form">
    <p class="muted">Придумайте логин — он станет вашим адресом @логин:{MATRIX_DOMAIN} (латиница/цифры, 2–32 символа). Логин создаётся здесь; регистрация в приложении не нужна.</p>
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
  <h2>3. Войдите в Element</h2>
  <ol class="steps">
    <li>Откройте приложение или {ELEMENT_URL} в браузере.</li>
    <li>Нажмите <b>«Войти»</b> — <b>не</b> «Создать аккаунт»: аккаунт уже создан на шаге 2.</li>
    <li>Если спросит адрес сервера — укажите <b>{MATRIX_DOMAIN}</b> (в мобильном приложении: «Изменить»).</li>
    <li>Введите Matrix ID (<span class="mono">@имя:{MATRIX_DOMAIN}</span>) и пароль.</li>
  </ol>
</div>
<div class="card">
  <h2>Как добавить коллег</h2>
  <p class="muted">Нажмите «＋» → введите полный адрес коллеги — он выглядит как <b>@имя:{MATRIX_DOMAIN}</b> — и пишите. Важно: в поиске сервера видны только те, с кем уже есть общие комнаты, поэтому вводите адрес целиком. Позвать коллегу в общий чат: в комнате → «Пригласить» → введите его адрес.</p>
</div>
<div class="card">
  <h2>Дальше</h2>
  <p class="muted">Веб-версия: <a href="{ELEMENT_URL}">{ELEMENT_URL}</a>. Если потеряете пароль — обратитесь к администратору.</p>
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
        '<div class="kv"><span class="k">Сервер</span> <span class="mono" id="srv">{MATRIX_DOMAIN}</span> <button class="btn btn-small btn-sec" onclick="copyText(&quot;srv&quot;)">копировать</button></div>' +
        '<div class="kv"><span class="k">Matrix ID</span> <span class="mono" id="mxid">' + d.mxid + '</span> <button class="btn btn-small btn-sec" onclick="copyText(&quot;mxid&quot;)">копировать</button></div>' +
        '<div class="kv"><span class="k">Пароль</span> <span class="mono" id="pwd">' + document.getElementById("r-pass").value + '</span> <button class="btn btn-small btn-sec" onclick="copyText(&quot;pwd&quot;)">копировать</button></div>' +
        '<p class="muted">В приложении выберите «Войти» (НЕ «Создать аккаунт») и введите эти данные — аккаунт уже работает.</p>';
    }} else {{
      el.innerHTML = '<span class="warn">' + (d.message || d.detail || "Не получилось — проверьте данные.") + "</span>";
    }}
  }}
</script>"""
    return _page("Приглашение — MSPShield Matrix", body)


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
    if matrix_user_exists(username):
        c.close()
        return {"ok": False, "message": "Этот логин занят — выберите другой."}
    ok, reason = matrix_create(username, password)
    if not ok:
        c.close()
        return {"ok": False, "message": "Не получилось создать аккаунт: " + reason}
    now = datetime.now(timezone.utc).isoformat()
    c.execute("UPDATE invites SET username=?, password=?, used_at=? WHERE token=?",
              (username, password, now, token))
    c.commit()
    c.close()
    return {"ok": True, "mxid": _mxid(username), "server": MATRIX_DOMAIN}


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
  async function deactivateAcc(btn) {{
    if (!confirm("Деактивировать и стереть аккаунт @" + btn.dataset.u + "? Это необратимо.")) return;
    await fetch("/admin/accounts/deactivate", {{
      method: "POST",
      headers: {{"Content-Type": "application/json", "X-Admin-Token": TOKEN}},
      body: JSON.stringify({{username: btn.dataset.u}}),
    }});
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
        (i.username ? ' <button class="btn btn-small btn-sec" onclick="deactivateAcc(this)" data-u="' + i.username + '">−аккаунт</button>' : '') +
        '</td>';
      tb.appendChild(tr);
    }});
  }}
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
    c.execute("DELETE FROM invites WHERE id=?", (inv_id,))
    c.commit()
    c.close()
    return {"ok": True}


@app.post("/admin/accounts/deactivate")
def admin_deactivate(payload: dict, x_admin_token: str = Header("")) -> dict:
    _admin_check(x_admin_token)
    username = (payload.get("username") or "").strip().lower()
    if not USER_RE.fullmatch(username):
        return {"ok": False, "message": "Некорректный логин."}
    ok, reason = matrix_deactivate(username)
    return {"ok": ok, "message": "" if ok else reason}


@app.get("/welcome/{token}")
def welcome_redirect(token: str) -> Response:
    return RedirectResponse(f"/i/{token}")
