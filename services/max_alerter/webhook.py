"""
max_alerter/webhook.py — FastAPI server, receives alerts from Alertmanager.

Alertmanager sends POST /alert with Bearer token.
Server formats the alert:
- Telegram: HTML + inline keyboard (ACK, silence, runbook buttons)
- MAX: plain text + markdown links (no buttons — pymax limitation)
"""

from __future__ import annotations

import logging
import os
from typing import Any

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.responses import JSONResponse

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-7s %(name)s %(message)s",
    datefmt="%H:%M:%S",
)

from .sender import deliver_max, deliver_telegram

log = logging.getLogger("max_alerter.webhook")

WEBHOOK_TOKEN: str = os.environ.get("WEBHOOK_TOKEN", "")
MAX_CHAT_ID: int = int(os.environ.get("MAX_CHAT_ID", "0"))
TG_CHAT_ID: str = os.environ.get("TG_CHAT_ID", "")

app = FastAPI(title="max-alerter", docs_url=None, redoc_url=None)

_SEV = {
  "critical": ("🔴", "P1"),
  "p1": ("🔴", "P1"),
  "warning": ("🟡", "P2"),
  "p2": ("🟡", "P2"),
  "info": ("🔵", "P3"),
  "p3": ("🔵", "P3"),
}
_STATUS = {
  "firing": "ALERT",
  "resolved": "RESOLVED",
}


def _fmt_alert_tg(alert: dict[str, Any]) -> tuple[str, dict]:
  """Format for Telegram: HTML text + inline keyboard."""
  labels = alert.get("labels", {})
  annotations = alert.get("annotations", {})

  sev_raw = labels.get("severity", "info").lower()
  status_raw = alert.get("status", "firing").lower()

  sev_icon, sev_label = _SEV.get(sev_raw, ("⚪", "P3"))
  status_label = _STATUS.get(status_raw, "ALERT")

  name = labels.get("alertname", "Alert")
  summary = annotations.get("summary", "")
  description = annotations.get("description", "")
  host = labels.get("instance", labels.get("host", ""))
  env = labels.get("env", "prod")
  runbook = annotations.get("runbook", "")

  # Header line
  lines = [f"{sev_icon} <b>{sev_label} · {status_label} · {env.upper()}</b>"]
  lines.append("")

  # Alert title
  title = summary or name
  lines.append(f"<b>{title}</b>")

  # Description
  if description:
      lines.append(description)

  lines.append("")

  # Details
  if host:
      lines.append(f"host: <code>{host}</code>")
  lines.append(f"severity: {sev_label}")

  metric = annotations.get("metric", "")
  if metric:
      lines.append(f"metric: <code>{metric}</code>")

  if runbook:
      lines.append(f"runbook: <code>{runbook}</code>")

  text = "\n".join(lines)

  # Inline keyboard
  keyboard: dict[str, Any] = {"inline_keyboard": [[]]}
  row = keyboard["inline_keyboard"][0]

  # ACK button
  ack_data = f"ack:{name}:{host}".replace(" ", "_")[:64]
  row.append({"text": "ACK · взять", "callback_data": ack_data})

  # Silence button
  silence_data = f"silence:30m:{name}:{host}".replace(" ", "_")[:64]
  row.append({"text": "silence 30m", "callback_data": silence_data})

  # Runbook button (URL)
  if runbook:
      runbook_url = runbook if runbook.startswith("http") else f"https://docs.msp-claude.online/{runbook}"
      row.append({"text": "runbook", "url": runbook_url})

  return text, keyboard


def _fmt_alert_max(alert: dict[str, Any]) -> str:
  """Format for MAX: plain text with markdown links, no buttons."""
  labels = alert.get("labels", {})
  annotations = alert.get("annotations", {})

  sev_raw = labels.get("severity", "info").lower()
  status_raw = alert.get("status", "firing").lower()

  sev_icon, sev_label = _SEV.get(sev_raw, ("⚪", "P3"))
  status_label = _STATUS.get(status_raw, "ALERT")

  name = labels.get("alertname", "Alert")
  summary = annotations.get("summary", "")
  description = annotations.get("description", "")
  host = labels.get("instance", labels.get("host", ""))
  env = labels.get("env", "prod")
  runbook = annotations.get("runbook", "")

  lines = [f"{sev_icon} {sev_label} · {status_label} · {env.upper()}"]
  lines.append("")

  title = summary or name
  lines.append(title)

  if description:
      lines.append(description)

  lines.append("")

  if host:
      lines.append(f"host: {host}")
  lines.append(f"severity: {sev_label}")

  metric = annotations.get("metric", "")
  if metric:
      lines.append(f"metric: {metric}")

  if runbook:
      runbook_url = runbook if runbook.startswith("http") else f"https://docs.msp-claude.online/{runbook}"
      lines.append(f"runbook: {runbook_url}")

  return "\n".join(lines)


def _fmt_payload_tg(payload: dict[str, Any]) -> tuple[str, list[dict]]:
  alerts: list[dict] = payload.get("alerts", [])
  if not alerts:
      return "Empty payload from Alertmanager", []

  texts = []
  keyboards = []
  for a in alerts:
      t, k = _fmt_alert_tg(a)
      texts.append(t)
      keyboards.append(k)

  header = f"<b>{_STATUS.get(payload.get('status', 'firing'), 'ALERT')} MSPShield</b>"
  text = header + "\n\n" + "\n\n".join(texts)

  # Merge keyboards — one keyboard per message, use first alert's keyboard
  # For multiple alerts, Telegram allows one keyboard per message
  keyboard = keyboards[0] if keyboards else {}

  return text, keyboard


def _fmt_payload_max(payload: dict[str, Any]) -> str:
  alerts: list[dict] = payload.get("alerts", [])
  if not alerts:
      return "Empty payload from Alertmanager"

  parts = [_fmt_alert_max(a) for a in alerts]
  header = f"{_STATUS.get(payload.get('status', 'firing'), 'ALERT')} MSPShield"
  return header + "\n\n" + "\n\n".join(parts)


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

  status_raw = payload.get("status", "firing")

  # Telegram delivery (with inline keyboard)
  if TG_CHAT_ID:
      tg_text, tg_keyboard = _fmt_payload_tg(payload)
      log.info("Alert received, delivering to Telegram chat_id=%s", TG_CHAT_ID)
      await deliver_telegram(chat_id=TG_CHAT_ID, text=tg_text, keyboard=tg_keyboard)

  # MAX delivery (plain text)
  if MAX_CHAT_ID:
      max_text = _fmt_payload_max(payload)
      log.info("Alert received, delivering to MAX chat_id=%s", MAX_CHAT_ID)
      await deliver_max(chat_id=MAX_CHAT_ID, text=max_text)

  return JSONResponse({"status": "ok", "channels": {"telegram": bool(TG_CHAT_ID), "max": bool(MAX_CHAT_ID)}})


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