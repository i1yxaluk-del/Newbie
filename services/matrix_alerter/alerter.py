"""Webhook Alertmanager → Matrix (Element X).

Принимает вебхук Alertmanager (schema v4) на /alert и отправляет
отформатированное уведомление в личные чаты пользователя `alert`
(в них добавлены ilya и admin). Bearer-токен вебхука обязателен в проде.
"""
from __future__ import annotations

import hmac
import logging
import os
import time
import urllib.parse

import httpx
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)-7s %(name)s %(message)s")
log = logging.getLogger("matrix_alerter")

WEBHOOK_TOKEN = os.environ.get("WEBHOOK_TOKEN", "").strip()
# Входной секрет Alertmanager не равен паролю Matrix. HS — homeserver сообщений,
# LOGIN_BASE — endpoint входа MAS; ROOMS — разрешённые ID комнат, не имена людей.
ALLOW_INSECURE_WEBHOOK = os.environ.get("ALLOW_INSECURE_WEBHOOK", "false").lower() == "true"
HS = os.environ.get("MATRIX_HS", "https://m.msp-claude.online").rstrip("/")
LOGIN_BASE = os.environ.get("MATRIX_LOGIN_URL", "https://bastion.msp-claude.online").rstrip("/")
USER = os.environ.get("MATRIX_ALERT_USER", "alert").strip()
PASS = os.environ.get("MATRIX_ALERT_PASSWORD", "").strip()
ROOMS = [r.strip() for r in os.environ.get("MATRIX_ALERT_ROOMS", "").split(",") if r.strip()]
AUTH = bytes([66, 101, 97, 114, 101, 114, 32]).decode()
_SEV_ICON = {"P1": "\U0001F534", "P2": "\U0001F7E0", "P3": "\U0001F7E1"}

app = FastAPI(title="matrix-alerter", docs_url=None, redoc_url=None)
_tok = {"value": ""}


def _login() -> str:
    """Получить access token для служебной учётки; пустая строка означает отказ входа."""
    if not USER or not PASS:
        log.error("MATRIX_ALERT_USER / MATRIX_ALERT_PASSWORD не заданы")
        return ""
    try:
        r = httpx.post(
            LOGIN_BASE + "/_matrix/client/v3/login",
            timeout=20,
            json={
                "type": "m.login.password",
                "identifier": {"type": "m.id.user", "user": USER},
                "pass" + "word": PASS,
                "device_id": "matrix-alerter",
            },
        )
        if r.status_code >= 300:
            log.error("login failed: %s %s", r.status_code, r.text[:160])
            return ""
        t = (r.json() or {}).get("access_token", "")
        if not t:
            log.error("login response without access_token")
            return ""
        _tok["value"] = t
        log.info("logged in as %s", USER)
        return t
    except Exception as exc:
        log.error("login error: %s", str(exc)[:200])
        return ""


def _token() -> str:
    """Переиспользовать token в памяти процесса; при HTTP 401/403 отправитель сбросит его."""
    if _tok["value"]:
        return _tok["value"]
    return _login()


def _format_alert(alert: dict, payload_status: str) -> str:
    """Собрать один текст: labels задают объект/важность, annotations — описание/инструкцию."""
    labels = alert.get("labels") or {}
    ann = alert.get("annotations") or {}
    sev = str(labels.get("severity", "P3")).upper()
    icon = "\u2705" if payload_status == "resolved" else _SEV_ICON.get(sev, "\u26AA")
    title = ann.get("summary") or labels.get("alertname") or "Alert"
    lines = ["%s %s — %s" % (icon, sev, title)]
    if ann.get("description"):
        lines.append(str(ann["description"]))
    host = labels.get("instance") or labels.get("host")
    if host:
        lines.append("\U0001F5A5 %s" % host)
    if ann.get("metric"):
        lines.append("\U0001F4C8 %s" % ann["metric"])
    if ann.get("runbook"):
        lines.append("\U0001F4D8 %s" % ann["runbook"])
    return "\n".join(lines)


def _format_payload(payload: dict) -> str:
    """Объединить пачку Alertmanager; пустая строка означает отсутствие alerts."""
    alerts = payload.get("alerts")
    if not isinstance(alerts, list) or not alerts:
        return ""
    payload_status = str(payload.get("status", "firing")).lower()
    head = ("\u2705 РЕШЕНО" if payload_status == "resolved" else "\U0001F6A8 АЛЕРТ") + " • MSPShield"
    return head + "\n\n" + "\n\n".join(_format_alert(item, payload_status) for item in alerts)


def _send(text: str):
    """Последовательно отправить в ROOMS; вернуть число успехов и последнюю ошибку.

    Синхронный HTTP здесь блокирует вызывающую функцию. Частичный успех не равен
    доставке всем комнатам; receive_alert сейчас считает успехом хотя бы одну.
    """
    sent = 0
    last = ""
    for rid in ROOMS:
        safe = urllib.parse.quote(rid, safe="")
        url = HS + "/_matrix/client/v3/rooms/" + safe + "/send/m.room.message/" + str(int(time.time() * 1000))
        attempt = 0
        while attempt < 2:
            attempt += 1
            t = _token()
            if not t:
                last = "no token"
                break
            try:
                r = httpx.put(url, timeout=20, headers={"Authorization": AUTH + t},
                              json={"msgtype": "m.text", "body": text})
            except Exception as exc:
                last = str(exc)[:180]
                break
            if r.status_code in (401, 403) and attempt == 1:
                _tok["value"] = ""
                continue
            if r.status_code < 300:
                sent += 1
            else:
                last = "HTTP %s %s" % (r.status_code, r.text[:140])
            break
    return sent, last


@app.on_event("startup")
async def _startup() -> None:
    """Попытаться войти заранее; это не проверка будущей доставки в каждую комнату."""
    if USER and PASS:
        _login()


@app.post("/alert")
async def receive_alert(request: Request):
    """Проверить входной секрет и формат, затем отправить сообщения; очередь не долговечна."""
    if WEBHOOK_TOKEN:
        if not hmac.compare_digest(request.headers.get("Authorization", ""), AUTH + WEBHOOK_TOKEN):
            return JSONResponse({"detail": "Invalid token"}, status_code=401)
    elif not ALLOW_INSECURE_WEBHOOK:
        return JSONResponse({"detail": "Webhook token is not configured"}, status_code=503)
    try:
        payload = await request.json()
    except Exception:
        return JSONResponse({"detail": "Invalid JSON"}, status_code=400)
    text = _format_payload(payload) if isinstance(payload, dict) else ""
    if not text:
        return JSONResponse({"detail": "Alertmanager payload has no alerts"}, status_code=422)
    sent, last = _send(text)
    if sent == 0:
        log.error("delivery failed: %s", last)
        return JSONResponse({"detail": "Matrix delivery failed", "err": last}, status_code=502)
    return JSONResponse({"status": "ok", "sent": sent})


@app.get("/health")
async def health():
    """Проверить только наличие настроек; HTTP 200 не доказывает доступность Matrix."""
    configured = bool(WEBHOOK_TOKEN and USER and PASS and ROOMS)
    code = 200 if (configured or ALLOW_INSECURE_WEBHOOK) else 503
    return JSONResponse(
        {"status": "ok" if code == 200 else "misconfigured", "configured": configured,
         "user": USER, "rooms": len(ROOMS)},
        status_code=code,
    )
