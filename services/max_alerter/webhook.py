"""Внутренний webhook Alertmanager → MAX userbot.

Junior: endpoint нельзя публиковать наружу. В production Bearer token обязателен.
Telegram вызывается внутри sender.py только как fallback после отказа MAX.
"""
from __future__ import annotations

import hmac
import logging
import os
from typing import Any

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.responses import JSONResponse

from .sender import deliver_max

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)-7s %(name)s %(message)s")
log = logging.getLogger("max_alerter.webhook")
WEBHOOK_TOKEN = os.environ.get("WEBHOOK_TOKEN", "").strip()
ALLOW_INSECURE_WEBHOOK = os.environ.get("ALLOW_INSECURE_WEBHOOK", "false").lower() == "true"
MAX_CHAT_ID_RAW = os.environ.get("MAX_CHAT_ID", "").strip()
app = FastAPI(title="max-alerter", docs_url=None, redoc_url=None)
_SEVERITY = {"critical": ("🔴", "P1"), "p1": ("🔴", "P1"), "warning": ("🟡", "P2"), "p2": ("🟡", "P2"), "info": ("🔵", "P3"), "p3": ("🔵", "P3")}
_STATUS = {"firing": "АЛЕРТ", "resolved": "РЕШЕНО"}


def _check_token(request: Request) -> None:
    """Fail closed: пустой production token — ошибка, а не открытый доступ."""
    if not WEBHOOK_TOKEN:
        if ALLOW_INSECURE_WEBHOOK:
            return
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Webhook token is not configured")
    if not hmac.compare_digest(request.headers.get("Authorization", ""), f"Bearer {WEBHOOK_TOKEN}"):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")


def _chat_id() -> int:
    try:
        return int(MAX_CHAT_ID_RAW)
    except ValueError as exc:
        raise HTTPException(status_code=503, detail="MAX_CHAT_ID is invalid") from exc


def _format_alert(alert: dict[str, Any], payload_status: str) -> str:
    labels, annotations = alert.get("labels", {}), alert.get("annotations", {})
    severity_raw = str(labels.get("severity", "info")).lower()
    status_raw = str(payload_status).lower()
    icon, severity = _SEVERITY.get(severity_raw, ("⚪", "P3"))
    if status_raw == "resolved":
        icon = "✅"
    title = annotations.get("summary") or labels.get("alertname", "Alert")
    lines = [f"{icon} {severity} · {_STATUS.get(status_raw, 'АЛЕРТ')} · {str(labels.get('env', 'prod')).upper()}", "", str(title)]
    if annotations.get("description"):
        lines.append(str(annotations["description"]))
    lines.append("")
    host = labels.get("instance") or labels.get("host")
    if host:
        lines.append(f"узел: {host}")
    lines.append(f"важность: {severity}")
    if annotations.get("metric"):
        lines.append(f"метрика: {annotations['metric']}")
    if annotations.get("runbook"):
        lines.append(f"runbook: {annotations['runbook']}")
    return "\n".join(lines)


def _format_payload(payload: dict[str, Any]) -> str:
    alerts = payload.get("alerts")
    if not isinstance(alerts, list) or not alerts:
        raise HTTPException(status_code=422, detail="Alertmanager payload has no alerts")
    payload_status = str(payload.get("status", "firing"))
    header = f"{'✅' if payload_status == 'resolved' else '🔥'} {_STATUS.get(payload_status, 'АЛЕРТ')} MSPShield"
    return header + "\n\n" + "\n\n".join(_format_alert(item, payload_status) for item in alerts)


@app.post("/alert")
async def receive_alert(request: Request) -> JSONResponse:
    _check_token(request)
    try:
        payload = await request.json()
    except Exception as exc:
        raise HTTPException(status_code=400, detail="Invalid JSON") from exc
    delivered = await deliver_max(chat_id=_chat_id(), text=_format_payload(payload))
    if not delivered:
        raise HTTPException(status_code=502, detail="MAX delivery failed; fallback attempted")
    return JSONResponse({"status": "ok", "channel": "max"})


@app.get("/health")
async def health() -> JSONResponse:
    configured = bool(WEBHOOK_TOKEN and MAX_CHAT_ID_RAW)
    code = 200 if configured or ALLOW_INSECURE_WEBHOOK else 503
    return JSONResponse({"status": "ok" if code == 200 else "misconfigured", "configured": configured}, status_code=code)
