"""MSPShield Jami Invite Portal.

Одноразовые приглашения: админ создаёт токен, приглашаемый открывает страницу,
видит QR/имя/ссылку, а после добавления контакта токен помечается использованным.

Админ-API (X-Admin-Token):
  POST /admin/invites  {"inviter_name": "...", "inviter_id": "<40hex>", "ttl_hours": 72, "note": "..."}
  GET  /admin/invites

Публично:
  GET  /i/{token}          — HTML-страница приглашения (детект платформы на клиенте)
  GET  /i/{token}/qr.png   — QR-код (jami://<inviter_id>)
  POST /i/{token}/confirm  — пометить использованным ("Я добавил контакт")
"""
import io
import os
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
             note         TEXT
           )"""
    )
    c.commit()
    c.close()


@app.on_event("startup")
def startup() -> None:
    init()


@app.get("/health")
def health() -> dict:
    return {"ok": True}


@app.post("/admin/invites")
def create_invite(request: Request, payload: dict, x_admin_token: str = Header("")) -> dict:
    if x_admin_token != ADMIN_TOKEN:
        raise HTTPException(status_code=401, detail="unauthorized")
    now = datetime.now(timezone.utc)
    ttl = int(payload.get("ttl_hours", 72))
    tok = secrets.token_urlsafe(24)
    c = db()
    c.execute(
        "INSERT INTO invites (token, inviter_name, inviter_id, created_at, expires_at, used_at, note) VALUES (?,?,?,?,?,?,?)",
        (
            tok,
            payload.get("inviter_name") or BRAND,
            (payload.get("inviter_id") or "").strip().lower(),
            now.isoformat(),
            (now + timedelta(hours=ttl)).isoformat(),
            None,
            payload.get("note", ""),
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


@app.get("/i/{token}/qr.png")
def qr(token: str) -> Response:
    c = db()
    row = c.execute("SELECT inviter_id FROM invites WHERE token=?", (token,)).fetchone()
    c.close()
    if not row:
        raise HTTPException(status_code=404, detail="not found")
    content = f"jami://{row['inviter_id']}" if row["inviter_id"] else JAMS_URL
    img = qrcode.make(content)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return Response(buf.getvalue(), media_type="image/png")


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


def _page(title: str, body: str) -> HTMLResponse:
    html = f"""<!doctype html>
<html lang="ru">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
<style>
  :root {{ color-scheme: light dark; }}
  * {{ box-sizing: border-box; }}
  body {{ margin:0; font:16px/1.55 -apple-system,"Segoe UI",Roboto,sans-serif; background:#f5f6f8; color:#16202a; }}
  .wrap {{ max-width:560px; margin:0 auto; padding:28px 18px 48px; }}
  .card {{ background:#fff; border:1px solid #e3e6ea; border-radius:14px; padding:22px; margin-bottom:14px; }}
  h1 {{ font-size:22px; margin:0 0 6px; }}
  .muted {{ color:#69747f; font-size:14px; }}
  .brand {{ font-weight:700; color:#005699; letter-spacing:.02em; }}
  .steps {{ padding-left:20px; margin:10px 0 0; }}
  .steps li {{ margin:6px 0; }}
  .btn {{ display:block; text-align:center; text-decoration:none; border-radius:10px; padding:13px 16px; font-weight:600; margin:8px 0; }}
  .btn-main {{ background:#005699; color:#fff; }}
  .btn-sec {{ background:#eef2f6; color:#005699; }}
  .qr {{ text-align:center; }}
  .qr img {{ width:220px; height:220px; image-rendering:pixelated; border:1px solid #e3e6ea; border-radius:10px; background:#fff; padding:8px; }}
  .ok {{ color:#1c6b3c; font-weight:600; }}
  .warn {{ color:#8a5a12; font-weight:600; }}
  button.btn {{ border:0; width:100%; cursor:pointer; font-size:16px; }}
  .done {{ background:#e8f6ee; border-color:#bfe6ce; }}
</style>
</head>
<body>
<div class="wrap">
  <p class="brand">MSPShield · Jami</p>
  {body}
  <p class="muted" style="text-align:center;margin-top:18px">Если что-то не получается — напишите пригласившему. Инструкция: 3 шага, 5 минут.</p>
</div>
</body>
</html>"""
    return HTMLResponse(html)


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
  <h2 style="margin:0 0 8px;font-size:18px">1. Установите Jami</h2>
  <a class="btn btn-main" id="store-android" href="https://play.google.com/store/apps/details?id=cx.ring">Установить из Google Play</a>
  <a class="btn btn-main" id="store-ios" href="https://apps.apple.com/app/jami/id1306951055">Установить из App Store</a>
  <p class="muted" id="store-hint"></p>
</div>
<div class="card qr">
  <h2 style="margin:0 0 8px;font-size:18px">2. Добавьте контакт</h2>
  <p class="muted">Откройте в Jami «Добавить контакт» и отсканируйте QR-код:</p>
  <img src="/i/{token}/qr.png" alt="QR-код приглашения">
  <p class="muted">или попросите прислать Jami ID напрямую.</p>
</div>
<div class="card">
  <h2 style="margin:0 0 8px;font-size:18px">3. Подтвердите</h2>
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
</script>"""
    return _page(f"Приглашение в Jami от {name}", body)


@app.get("/")
def index() -> HTMLResponse:
    return _page("MSPShield · Приглашения", '<div class="card"><h1>MSPShield Jami</h1><p class="muted">Сервис приглашений. Откройте персональную ссылку вида /i/…</p></div>')
