"""
max_alerter/webhook.py — FastAPI-сервер, принимает алерты от Alertmanager.

Alertmanager шлёт POST /alert с Bearer-токеном.
Сервер форматирует алерт и доставляет в MAX через sender.deliver().

Переменные окружения:
WEBHOOK_TOKEN    — Bearer-токен для авторизации входящих запросов
MAX_CHAT_ID      — chat_id клиента в MAX (куда слать алерты)
HOST             — bind host (default: 0.0.0.0)
PORT             — bind port (default: 9095)
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

# ── severity → эмодзи ──────────────────────────────────────────────────────────
_SEV = {
"critical": "🔴",
"warning":  "🟡",
"info":     "🔵",
}
_STATUS = {
"firing":   "🔥",
"resolved": "✅",
}


def _fmt_alert(alert: dict[str, Any]) -> str:
"""Форматирует один алерт Alertmanager в текст для MAX."""
labels = alert.get("labels", {})
annotations = alert.get("annotations", {})

sev = labels.get("severity", "info").lower()
status_str = alert.get("status", "firing").lower()

sev_icon = _SEV.get(sev, "⚪")
status_icon = _STATUS.get(status_str, "❓")

name = labels.get("alertname", "Alert")
summary = annotations.get("summary", "")
description = annotations.get("description", "")
instance = labels.get("instance", labels.get("job", ""))

lines = [f"{status_icon} {sev_icon} *{name}*"]
if instance:
    lines.append(f"Хост: `{instance}`")
if summary:
    lines.append(summary)
if description and description != summary:
    lines.append(description)

return "
".join(lines)


def _fmt_payload(payload: dict[str, Any]) -> str:
"""Форматирует весь payload Alertmanager (может содержать несколько алертов)."""
alerts: list[dict] = payload.get("alerts", [])
if not alerts:
    return "Пустой payload от Alertmanager"

parts = [_fmt_alert(a) for a in alerts]
return "

".join(parts)


def _check_token(request: Request) -> None:
"""Проверяет Bearer-токен. Пропускает если WEBHOOK_TOKEN не задан."""
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
"""Принимает POST от Alertmanager, доставляет в MAX."""
_check_token(request)

try:
    payload = await request.json()
except Exception as exc:  # noqa: BLE001
    log.error("Не удалось распарсить JSON: %s", exc)
    raise HTTPException(status_code=400, detail="Invalid JSON") from exc

if not MAX_CHAT_ID:
    log.error("MAX_CHAT_ID не задан")
    raise HTTPException(status_code=500, detail="MAX_CHAT_ID not configured")

text = _fmt_payload(payload)
log.info("Получен алерт, доставляем в MAX chat_id=%s", MAX_CHAT_ID)

await deliver(chat_id=MAX_CHAT_ID, text=text)

return JSONResponse({"status": "ok"})


@app.get("/health")
async def health() -> JSONResponse:
"""Healthcheck для Docker/Prometheus."""
return JSONResponse({"status": "ok"})


# ── точка входа для прямого запуска ───────────────────────────────────────────
if __name__ == "__main__":
import uvicorn  # type: ignore[import]

uvicorn.run(
    "max_alerter.webhook:app",
    host=os.environ.get("HOST", "0.0.0.0"),
    port=int(os.environ.get("PORT", "9095")),
    log_level="info",
)
