"""Production wrapper: strict consent, configurable CAPTCHA and durable delivery.

The existing server module remains usable for local development. Production
Docker images start this module so pilot safety policy cannot be skipped.
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
from datetime import datetime, timedelta, timezone
from typing import Any, Dict

import httpx
from starlette.responses import JSONResponse

import server

logger = logging.getLogger("mspshield.production")
app = server.app


class RequireExplicitConsentMiddleware:
    """Reject lead payloads unless consent is explicitly true.

    The body is replayed to FastAPI after validation so the normal Pydantic
    validation and route behavior remain unchanged.
    """

    def __init__(self, asgi_app):
        self.asgi_app = asgi_app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http" or scope["method"] != "POST" or scope["path"] != "/api/leads":
            await self.asgi_app(scope, receive, send)
            return

        chunks = []
        more = True
        while more:
            message = await receive()
            chunks.append(message.get("body", b""))
            more = message.get("more_body", False)
        body = b"".join(chunks)
        try:
            payload = json.loads(body or b"{}")
        except (json.JSONDecodeError, UnicodeDecodeError):
            payload = {}
        if payload.get("consent") is not True:
            response = JSONResponse(
                {"detail": "consent_required"}, status_code=400
            )
            await response(scope, receive, send)
            return

        sent = False

        async def replay_receive():
            nonlocal sent
            if sent:
                return {"type": "http.request", "body": b"", "more_body": False}
            sent = True
            return {"type": "http.request", "body": body, "more_body": False}

        await self.asgi_app(scope, replay_receive, send)


app.add_middleware(RequireExplicitConsentMiddleware)


async def verify_smartcaptcha_strict(token: str | None, client_ip: str) -> bool:
    """Fail closed by default; SMARTCAPTCHA_FAIL_OPEN=true is an explicit choice."""
    if not server.SMARTCAPTCHA_SERVER_KEY:
        return True
    if not token:
        return False
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(
                server.SMARTCAPTCHA_VERIFY_URL,
                params={
                    "secret": server.SMARTCAPTCHA_SERVER_KEY,
                    "token": token,
                    "ip": client_ip,
                },
            )
        return response.json().get("status") == "ok"
    except Exception as exc:  # noqa: BLE001
        fail_open = os.environ.get("SMARTCAPTCHA_FAIL_OPEN", "false").lower() == "true"
        logger.error("SmartCaptcha verification unavailable; fail_open=%s: %s", fail_open, exc)
        return fail_open


server.verify_smartcaptcha = verify_smartcaptcha_strict


def _enabled_channels() -> list[str]:
    channels = []
    if server.telegram.is_enabled():
        channels.append("telegram")
    if server.email_integration.is_enabled():
        channels.append("email")
    if server.webhook.is_enabled():
        channels.append("webhook")
    if server.max_integration.is_alert_channel():
        channels.append("max")
    if server.kaiten.is_enabled():
        channels.append("kaiten")
    return channels


async def _send_channel(channel: str, lead: Dict[str, Any]) -> bool:
    if channel == "telegram":
        await server.telegram.send(lead)
        return True
    if channel == "email":
        await server.email_integration.send(lead)
        return True
    if channel == "webhook":
        code = await server.webhook.send(lead)
        return bool(code and 200 <= code < 300)
    if channel == "max":
        await server.max_integration.send(lead)
        return True
    if channel == "kaiten":
        card = await server.kaiten.create_card(lead)
        if not card or not card.get("id"):
            return False
        await server.db.leads.update_one(
            {"id": lead["id"]},
            {"$set": {"kaiten_card_id": card["id"]}},
        )
        return True
    return True


async def _process_delivery(lead_id: str) -> None:
    job = await server.db.crm_outbox.find_one({"lead_id": lead_id})
    if not job:
        return
    pending = list(job.get("pending") or [])
    failures: Dict[str, str] = {}
    for channel in pending:
        try:
            if await _send_channel(channel, job["payload"]):
                await server.db.crm_outbox.update_one(
                    {"lead_id": lead_id}, {"$pull": {"pending": channel}}
                )
                server.inc_crm(channel, "ok")
            else:
                failures[channel] = "delivery returned false"
                server.inc_crm(channel, "error")
        except Exception as exc:  # noqa: BLE001
            failures[channel] = str(exc)[:300]
            server.inc_crm(channel, "error")

    current = await server.db.crm_outbox.find_one({"lead_id": lead_id})
    if current and not current.get("pending"):
        await server.db.crm_outbox.delete_one({"lead_id": lead_id})
        return
    attempts = int((current or job).get("attempts", 0)) + 1
    delay = min(3600, 30 * (2 ** min(attempts, 7)))
    await server.db.crm_outbox.update_one(
        {"lead_id": lead_id},
        {"$set": {
            "attempts": attempts,
            "last_errors": failures,
            "next_retry_at": datetime.now(timezone.utc) + timedelta(seconds=delay),
            "updated_at": datetime.now(timezone.utc),
        }},
    )


async def durable_deliver_to_crm(lead: Dict[str, Any]) -> None:
    channels = _enabled_channels()
    if not channels:
        return
    now = datetime.now(timezone.utc)
    await server.db.crm_outbox.update_one(
        {"lead_id": lead["id"]},
        {"$setOnInsert": {
            "lead_id": lead["id"],
            "payload": lead,
            "pending": channels,
            "attempts": 0,
            "created_at": now,
            "next_retry_at": now,
        }},
        upsert=True,
    )
    await _process_delivery(lead["id"])


server.deliver_to_crm = durable_deliver_to_crm


async def _outbox_worker() -> None:
    while True:
        now = datetime.now(timezone.utc)
        cursor = server.db.crm_outbox.find(
            {"next_retry_at": {"$lte": now}}, {"lead_id": 1}
        ).limit(20)
        async for job in cursor:
            await _process_delivery(job["lead_id"])
        await asyncio.sleep(30)


@app.on_event("startup")
async def _start_outbox_worker() -> None:
    await server.db.crm_outbox.create_index("lead_id", unique=True)
    await server.db.crm_outbox.create_index("next_retry_at")
    app.state.outbox_task = asyncio.create_task(_outbox_worker())


@app.on_event("shutdown")
async def _stop_outbox_worker() -> None:
    task = getattr(app.state, "outbox_task", None)
    if task:
        task.cancel()
