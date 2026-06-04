"""
max_alerter/sender.py — send messages to MAX via pymax Client.

Maintains a single persistent TCP connection (reconnect built into pymax).
On delivery failure — fallback to Telegram + write to failed_alerts.log.
"""

from __future__ import annotations

import asyncio
import logging
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

log = logging.getLogger("max_alerter.sender")

MAX_PHONE: str = os.environ.get("MAX_PHONE", "")
MAX_SESSION_DIR: Path = Path(os.environ.get("MAX_SESSION_DIR", "/session"))
MAX_SESSION_NAME: str = os.environ.get("MAX_SESSION_NAME", "max.db")
TG_BOT_TOKEN: str = os.environ.get("TG_BOT_TOKEN", "")
TG_CHAT_ID: str = os.environ.get("TG_CHAT_ID", "")

FAILED_LOG: Path = Path(os.environ.get("FAILED_LOG", "/data/failed_alerts.log"))

_client: Optional[object] = None
_client_lock = asyncio.Lock()


async def get_client():
    """Returns a running pymax Client (creates on first call)."""
    global _client

    async with _client_lock:
        if _client is not None:
            return _client

        try:
            from pymax import Client
        except ImportError as exc:
            raise RuntimeError("pymax not installed: pip install maxapi-python") from exc

        if not MAX_PHONE:
            raise RuntimeError("MAX_PHONE not set in environment")

        MAX_SESSION_DIR.mkdir(parents=True, exist_ok=True)

        log.info("Starting pymax Client (phone=%s, session=%s/%s)",
                 MAX_PHONE, MAX_SESSION_DIR, MAX_SESSION_NAME)

        client = Client(
            phone=MAX_PHONE,
            work_dir=str(MAX_SESSION_DIR),
            session_name=MAX_SESSION_NAME,
        )

        loop = asyncio.get_event_loop()
        ready = asyncio.Event()

        @client.on_start()
        async def _on_start(c) -> None:
            uid = c.me.contact.id if c.me else "unknown"
            log.info("MAX client ready. user_id=%s", uid)
            ready.set()

        loop.create_task(client.start())
        await asyncio.wait_for(ready.wait(), timeout=30)

        _client = client
        return _client


async def send_to_max(chat_id: int, text: str) -> bool:
    """Send text to MAX chat. Returns True on success, False on error."""
    try:
        client = await get_client()
        await client.send_message(chat_id=chat_id, text=text)
        log.info("MAX OK chat_id=%s len=%d", chat_id, len(text))
        return True
    except Exception as exc:
        log.error("MAX FAIL chat_id=%s error=%s", chat_id, exc)
        return False


async def send_to_telegram(chat_id: str, text: str) -> bool:
    """Send text to Telegram chat. Returns True on success."""
    if not TG_BOT_TOKEN:
        log.warning("Telegram not configured (TG_BOT_TOKEN empty)")
        return False

    try:
        import httpx

        url = f"https://api.telegram.org/bot{TG_BOT_TOKEN}/sendMessage"
        payload: dict[str, Any] = {
            "chat_id": chat_id,
            "text": text,
            "parse_mode": "HTML",
        }

        async with httpx.AsyncClient(timeout=10) as http:
            r = await http.post(url, json=payload)
            r.raise_for_status()
        log.info("Telegram OK chat_id=%s", chat_id)
        return True
    except Exception as exc:
        log.error("Telegram FAIL chat_id=%s error=%s", chat_id, exc)
        return False


def _write_failed_log(chat_id: int | str, text: str, error: str) -> None:
    try:
        FAILED_LOG.parent.mkdir(parents=True, exist_ok=True)
        ts = datetime.now(timezone.utc).isoformat()
        with FAILED_LOG.open("a", encoding="utf-8") as f:
            f.write(f"[{ts}] chat_id={chat_id} error={error!r}\n{text}\n---\n")
    except Exception as exc:
        log.error("Cannot write failed_alerts.log: %s", exc)


async def deliver_max(chat_id: int, text: str) -> None:
    """Deliver alert to MAX. No fallback — webhook handles separate channels."""
    ok = await send_to_max(chat_id, text)
    if not ok:
        _write_failed_log(chat_id, text, "send_to_max failed")


async def deliver_telegram(chat_id: str, text: str) -> None:
    """Deliver alert to Telegram."""
    ok = await send_to_telegram(chat_id, text)
    if not ok:
        _write_failed_log(chat_id, text, "send_to_telegram failed")