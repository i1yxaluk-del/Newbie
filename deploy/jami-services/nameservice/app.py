"""MSPShield Jami Name Service.

Резолвер коротких имён: username → Jami ID (40-hex).

Публичный API (протокол Jami Name Server):
  GET /name/{username}            → text/plain: <jami_id>   (основной формат)
  GET /name/{username}?json=1     → {"username": ..., "address": ...}

Админ-API (X-Admin-Token):
  POST   /admin/names            {"username": "...", "jami_id": "..."}  — создать/обновить
  GET    /admin/names            — список
  DELETE /admin/names/{username} — удалить

Аудит: таблица audit. Rate-limit: 60 запросов/мин на IP для GET, 10/мин для админ-записей.
Регистрация имён — только администратором JAMS.
"""
import logging
import os
import re
import time
from collections import defaultdict, deque

import psycopg
from fastapi import FastAPI, Header, HTTPException, Request, Response
from psycopg.rows import dict_row

DATABASE_URL = os.environ["DATABASE_URL"]
ADMIN_TOKEN = os.environ["ADMIN_TOKEN"]

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("nameservice")

app = FastAPI(title="MSPShield Jami Name Service")

USERNAME_RE = re.compile(r"^[a-z0-9][a-z0-9_-]{1,31}$")
JAMI_ID_RE = re.compile(r"^[0-9a-f]{40}$")

_rate: dict[str, deque] = defaultdict(deque)


def rate_limit(ip: str, limit: int, window: float = 60.0) -> None:
    q = _rate[ip]
    now = time.time()
    while q and now - q[0] > window:
        q.popleft()
    if len(q) >= limit:
        raise HTTPException(status_code=429, detail="rate limit exceeded")
    q.append(now)


def db():
    return psycopg.connect(DATABASE_URL, row_factory=dict_row)


def ensure_schema() -> None:
    with db() as c:
        c.execute(
            """CREATE TABLE IF NOT EXISTS names (
                 username   text PRIMARY KEY,
                 jami_id    text NOT NULL,
                 created_at timestamptz NOT NULL DEFAULT now(),
                 updated_at timestamptz NOT NULL DEFAULT now()
               )"""
        )
        c.execute(
            """CREATE TABLE IF NOT EXISTS audit (
                 id       bigserial PRIMARY KEY,
                 ts       timestamptz NOT NULL DEFAULT now(),
                 action   text NOT NULL,
                 username text,
                 jami_id  text,
                 actor    text,
                 ip       text
               )"""
        )
        c.commit()


@app.on_event("startup")
def startup() -> None:
    last = None
    for _ in range(30):
        try:
            ensure_schema()
            log.info("schema ready")
            return
        except Exception as exc:  # noqa: BLE001
            last = exc
            time.sleep(2)
    raise RuntimeError(f"db not ready: {last}")


@app.get("/health")
def health() -> dict:
    return {"ok": True}


@app.get("/name/{username}")
def resolve(username: str, request: Request, json: int = 0):
    rate_limit(request.client.host, 60)
    u = username.strip().lower()
    if not USERNAME_RE.match(u):
        raise HTTPException(status_code=400, detail="bad username")
    with db() as c:
        row = c.execute("SELECT jami_id FROM names WHERE username=%s", (u,)).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="not found")
    if json or "application/json" in (request.headers.get("accept") or ""):
        return {"username": u, "address": row["jami_id"]}
    return Response(row["jami_id"], media_type="text/plain")


def _check_admin(token: str) -> None:
    if not token or token != ADMIN_TOKEN:
        raise HTTPException(status_code=401, detail="unauthorized")


@app.post("/admin/names")
def admin_register(request: Request, payload: dict, x_admin_token: str = Header("")) -> dict:
    _check_admin(x_admin_token)
    rate_limit(request.client.host, 10)
    u = str(payload.get("username", "")).strip().lower()
    jid = str(payload.get("jami_id", "")).strip().lower()
    if not USERNAME_RE.match(u):
        raise HTTPException(status_code=400, detail="bad username")
    if not JAMI_ID_RE.match(jid):
        raise HTTPException(status_code=400, detail="bad jami_id (40 hex chars)")
    with db() as c:
        old = c.execute("SELECT jami_id FROM names WHERE username=%s", (u,)).fetchone()
        c.execute(
            """INSERT INTO names (username, jami_id) VALUES (%s, %s)
               ON CONFLICT (username) DO UPDATE SET jami_id = excluded.jami_id, updated_at = now()""",
            (u, jid),
        )
        c.execute(
            "INSERT INTO audit (action, username, jami_id, actor, ip) VALUES (%s,%s,%s,%s,%s)",
            ("update" if old else "create", u, jid, "admin", request.client.host),
        )
        c.commit()
    log.info("registered name %s -> %s", u, jid)
    return {"ok": True, "username": u, "jami_id": jid}


@app.get("/admin/names")
def admin_list(x_admin_token: str = Header("")) -> dict:
    _check_admin(x_admin_token)
    with db() as c:
        rows = c.execute("SELECT username, jami_id, updated_at FROM names ORDER BY username").fetchall()
    return {"names": rows}


@app.delete("/admin/names/{username}")
def admin_delete(username: str, request: Request, x_admin_token: str = Header("")) -> dict:
    _check_admin(x_admin_token)
    rate_limit(request.client.host, 10)
    u = username.strip().lower()
    with db() as c:
        c.execute("DELETE FROM names WHERE username=%s", (u,))
        c.execute(
            "INSERT INTO audit (action, username, actor, ip) VALUES ('delete',%s,'admin',%s)",
            (u, request.client.host),
        )
        c.commit()
    return {"ok": True}
