"""MSPShield Jami Invite Portal.

- Публично: /i/{token} — страница приглашения (данные JAMS, QR контакта, «Я добавил»).
- Публично: /qr/{jami_id}.png — QR-код контакта (payload jami:<id>), /c/{jami_id} — карточка контакта.
- Админка: /admin?token=<INVITE_ADMIN_TOKEN> — список приглашений + создание новых (веб-форма).
- API: POST/GET /admin/invites (X-Admin-Token), GET /i/{token}/qr.png, POST /i/{token}/confirm.
"""
import io
import os
import re
import secrets
import sqlite3
from datetime import datetime, timedelta, timezone

import qrcode
from fastapi import FastAPI, Header, HTTPException, Request
from fastapi.responses import HTMLResponse, Response

DB = "/data/invites.db"
ADMIN_TOKEN = os.environ["ADMIN_TOKEN"]
JAMS_URL = os.environ.get("JAMS_URL", "https://m.msp-claude.online")
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
    for col in ("jams_username", "jams_password"):
        try:
            c.execute(f"ALTER TABLE invites ADD COLUMN {col} TEXT DEFAULT ''")
        except sqlite3.OperationalError:
            pass
    c.commit()
    c.close()


@app.on_event("startup")
def startup() -> None:
    init()


@app.get("/health")
def health() -> dict:
    return {"ok": True}


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
        "INSERT INTO invites (token, inviter_name, inviter_id, created_at, expires_at, used_at, note, jams_username, jams_password) VALUES (?,?,?,?,?,?,?,?,?)",
        (
            tok,
            payload.get("inviter_name") or BRAND,
            (payload.get("inviter_id") or "").strip().lower(),
            now.isoformat(),
            (now + timedelta(hours=ttl)).isoformat(),
            None,
            payload.get("note", ""),
            (payload.get("jams_username") or "").strip(),
            payload.get("jams_password") or "",
        ),
    )
    c.commit()
    c.close()
    return {
        "ok": True,
        "url": f"https://invite.msp-claude.online/i/{tok}",
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
    row = c.execute("SELECT inviter_id FROM invites WHERE token=?", (token,)).fetchone()
    c.close()
    if not row:
        raise HTTPException(status_code=404, detail="not found")
    inviter_id = (row["inviter_id"] or "").strip().lower()
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
    juser = (row["jams_username"] or "").strip()
    jpass = (row["jams_password"] or "").strip()
    iid = (row["inviter_id"] or "").strip().lower()
    has_iid = bool(JAMI_ID_RE.fullmatch(iid))
    user_row = (
        f'<div class="kv"><span class="muted">Логин</span> <span class="mono" id="juser">{juser}</span> <button class="btn btn-small btn-sec" onclick="copyText(&quot;juser&quot;)">копировать</button></div>'
        if juser else
        '<div class="kv"><span class="muted">Логин</span> <span class="muted">— запросите у приглашающего</span></div>'
    )
    pass_row = (
        f'<div class="kv"><span class="muted">Пароль</span> <span class="mono" id="jpass">{jpass}</span> <button class="btn btn-small btn-sec" onclick="copyText(&quot;jpass&quot;)">копировать</button></div>'
        if jpass else
        '<div class="kv"><span class="muted">Пароль</span> <span class="muted">— пришлёт приглашающий отдельным сообщением</span></div>'
    )
    creds_block = f"""<div class="card">
  <h2>2. Подключение к JAMS</h2>
  <p class="muted">В Jami откройте «Добавить аккаунт» → «Подключиться к JAMS-серверу» и введите данные:</p>
  <div class="kv"><span class="muted">Сервер</span> <span class="mono" id="jserver">{JAMS_URL}</span> <button class="btn btn-small btn-sec" onclick="copyText(&quot;jserver&quot;)">копировать</button></div>
  {user_row}
  {pass_row}
  <p class="muted">При первом входе клиент может показать окно «миграции» и попросить пароль — это пароль вашей учётной записи в JAMS.</p>
</div>"""
    if has_iid:
        contact_block = f"""<div class="card qr">
  <h2>3. Добавьте контакт приглашающего</h2>
  <p class="muted">В Jami: «Добавить контакт» → «Сканировать QR» — или вставьте ID вручную.</p>
  <img src="/i/{token}/qr.png" alt="QR-код контакта">
  <p class="mono">{iid}</p>
  <p class="muted"><a href="/c/{iid}">Карточка контакта</a> — можно переслать или открыть на другом устройстве.</p>
</div>"""
    else:
        contact_block = """<div class="card">
  <h2>3. Добавьте контакт приглашающего</h2>
  <p class="muted">Попросите приглашающего прислать его Jami ID или ссылку-карточку контакта.</p>
</div>"""

    if used:
        return _page(
            "Приглашение уже использовано",
            f'<div class="card done"><h1>Приглашение уже использовано</h1>'
            f'<p class="ok">Контакт «{name}» уже добавлен ранее — повторное использование не нужно.</p></div>',
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
  <p>Jami — мессенджер, где переписка хранится только у участников.</p>
</div>
<div class="card">
  <h2>1. Установите Jami</h2>
  <a class="btn btn-main" id="store-android" href="https://play.google.com/store/apps/details?id=cx.ring">Установить из Google Play</a>
  <a class="btn btn-main" id="store-ios" href="https://apps.apple.com/app/jami/id1306951055">Установить из App Store</a>
</div>
{creds_block}
{contact_block}
<div class="card">
  <h2>4. Подтвердите</h2>
  <p class="muted">Дождитесь, пока контакт станет доступен, и нажмите кнопку:</p>
  <button class="btn btn-sec" onclick="markUsed()">Я добавил(а) контакт</button>
  <p class="muted" id="result"></p>
</div>
<script>
  const ua = navigator.userAgent || "";
  const isIOS = /iPhone|iPad|iPod/i.test(ua);
  document.getElementById("store-android").style.display = isIOS ? "none" : "block";
  document.getElementById("store-ios").style.display = isIOS ? "block" : "none";
  function markUsed() {{
    fetch("/i/{token}/confirm", {{method: "POST"}})
      .then(r => r.json())
      .then(() => {{ document.getElementById("result").innerHTML = '<span class="ok">Готово — приглашение помечено использованным.</span>'; }})
      .catch(() => {{ document.getElementById("result").innerHTML = '<span class="warn">Не получилось отметить. Ничего страшного — просто сообщите пригласившему.</span>'; }});
  }}
  function copyText(id) {{
    const el = document.getElementById(id);
    if (el) {{ navigator.clipboard.writeText(el.textContent.trim()); }}
  }}
</script>"""
    return _page(f"Приглашение в Jami от {name}", body)


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
  <h2>Новое приглашение</h2>
  <label class="muted">Имя приглашающего</label>
  <input id="f-name" placeholder="Например: Максим">
  <label class="muted">Jami ID приглашающего (40 hex, необязательно)</label>
  <input id="f-id" placeholder="7b1cf78913278f3b854286e36abf82b723ce971b">
  <label class="muted">Срок действия, часов</label>
  <input id="f-ttl" type="number" value="72" min="1" max="720">
  <label class="muted">Заметка (кто приглашён — для себя)</label>
  <input id="f-note" placeholder="Бабуля, Ивановы…">
  <label class="muted">JAMS-логин нового пользователя (необязательно — покажется получателю)</label>
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
        "</td><td>" + (i.jams_username || "") + "</td><td>" + (i.note || "") + "</td><td>" + status(i) +
        '</td><td><a href="' + "/i/" + i.token + '" target="_blank">открыть</a> <button class="btn btn-small btn-sec" onclick="copyUrl(\\'' + i.token + '\\')">копировать</button> <button class="btn btn-small btn-sec" onclick="delInvite(\\'' + i.token + '\\')">удалить</button></td>';
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
    navigator.clipboard.writeText("https://invite.msp-claude.online/i/" + tok);
  }}
  async function delInvite(tok) {{
    if (!confirm("Удалить приглашение?")) return;
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
</script>"""
    return _page("Админка приглашений — MSPShield", body)


@app.get("/")
def index() -> HTMLResponse:
    return _page("MSPShield · Приглашения", '<div class="card"><h1>MSPShield Jami</h1><p class="muted">Сервис приглашений. Персональная ссылка: /i/… · Карточка контакта: /c/…</p></div>')
