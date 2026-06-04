"""
max_alerter/webhook.py — FastAPI server, receives alerts from Alertmanager.

Alertmanager sends POST /alert with Bearer token.
Server formats the alert and delivers to MAX via sender.deliver().
"""

from __future__ import annotations

import logging
import os
from typing import Any

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.responses import JSONResponse

from .sender import deliver

log = logging.getLogger("max_alerter.webhook")

WEBHOOK_TOKEN: str = os.environ.get("WEBHOOK_TOKEN", "")
MAX_CHAT_ID: int = int(os.environ.get("MAX_CHAT_ID", "0"))

app = FastAPI(title="max-alerter", docs_url=None, redoc_url=None)

_SEV = {
    "critical": "🔴",
    "p1": "🔴",
    "warning": "🟡",
    "p2": "🟡",
    "info": "🔵",
    "p3": "🔵",
}
_STATUS = {
    "firing": "🔥",
    "resolved": "✅",
}


def _fmt_alert(alert: dict[str, Any]) -> str:
    labels = alert.get("labels", {})
    annotations = alert.get("annotations", {})

    sev = labels.get("severity", "info").lower()
    status_str = alert.get("status", "firing").lower()

    sev_icon = _SEV.get(sev, "⚪")
    status_icon = _STATUS.get(status_str, "❓")

    name = labels.get("alertname", "Alert")
    summary = annotations.get("summary", "")
    host = annotations.get("host", labels.get("instance", ""))

    lines = [f"{status_icon} {sev_icon} <b>[{sev.upper()}] {name}</b>"]
    if host:
        lines.append(f"host: <code>{host}</code>")
    if summary:
        lines.append(summary)

    return "\n".join(lines)


def _fmt_payload(payload: dict[str, Any]) -> str:
    alerts: list[dict] = payload.get("alerts", [])
    if not alerts:
        return "Empty payload from Alertmanager"

    parts = [_fmt_alert(a) for a in alerts]
    header = f"<b>{_STATUS.get(payload.get('status', 'firing'), '❓')} MSPShield</b>"
    return header + "\n\n" + "\n".join(parts)


def _check_token(request: Request) -> None:
    if not WEBHOOK_TOKEN:
        return
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer ") or auth[7:] != WEBHOOK_TOKEN:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
        )


@app.post("/alert")
async def receive_alert(request: Request) -> JSONResponse:
    _check_token(request)

    try:
        payload = await request.json()
    except Exception as exc:
        log.error("Cannot parse JSON: %s", exc)
        raise HTTPException(status_code=400, detail="Invalid JSON") from exc

    if not MAX_CHAT_ID:
        log.error("MAX_CHAT_ID not set")
        raise HTTPException(status_code=500, detail="MAX_CHAT_ID not configured")

    text = _fmt_payload(payload)
    log.info("Alert received, delivering to MAX chat_id=%s", MAX_CHAT_ID)

    await deliver(chat_id=MAX_CHAT_ID, text=text)

    return JSONResponse({"status": "ok"})


@app.get("/health")
async def health() -> JSONResponse:
    return JSONResponse({"status": "ok"})


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "max_alerter.webhook:app",
        host=os.environ.get("HOST", "0.0.0.0"),
        port=int(os.environ.get("PORT", "9095")),
        log_level="info",
    )
