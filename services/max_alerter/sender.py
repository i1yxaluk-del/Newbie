"""
max_alerter/sender.py — send messages to MAX via pymax Client.

Maintains a single persistent TCP connection (reconnect built into pymax).
On delivery failure — fallback to Telegram + write to failed_alerts.log.
"""

from __future__ import annotations

import asyncio
import logging
import os
import smtplib
from datetime import datetime, timezone
from email.mime.text import MIMEText
from pathlib import Path
from typing import Any, Optional

log = logging.getLogger("max_alerter.sender")

MAX_PHONE: str = os.environ.get("MAX_PHONE", "")
MAX_SESSION_DIR: Path = Path(os.environ.get("MAX_SESSION_DIR", "/session"))
MAX_SESSION_NAME: str = os.environ.get("MAX_SESSION_NAME", "max.db")
TG_BOT_TOKEN: str = os.environ.get("TG_BOT_TOKEN", "")
TG_CHAT_ID: str = os.environ.get("TG_CHAT_ID", "")
SMTP_HOST: str = os.environ.get("SMTP_HOST", "").strip()
SMTP_PORT: int = int(os.environ.get("SMTP_PORT", "465"))
SMTP_USER: str = os.environ.get("SMTP_USER", "").strip()
SMTP_PASSWORD: str = os.environ.get("SMTP_PASSWORD", "").strip()
SMTP_FROM: str = os.environ.get("SMTP_FROM", "").strip()
ALERT_EMAIL_TO: str = os.environ.get("ALERT_EMAIL_TO", "").strip()
MAX_FAILURE_COOLDOWN: int = int(os.environ.get("MAX_FAILURE_COOLDOWN", "300"))

FAILED_LOG: Path = Path(os.environ.get("FAILED_LOG", "/data/failed_alerts.log"))

_client: Optional[object] = None
_client_lock = asyncio.Lock()
_max_retry_after: Optional[datetime] = None


async def get_client():
    """Returns a running pymax Client (creates on first call)."""
    global _client

    async with _client_lock:
        if _client is not None:
            return _client

        if not MAX_PHONE:
            raise RuntimeError("MAX_PHONE not set in environment")

        session_file = MAX_SESSION_DIR / MAX_SESSION_NAME
        if not session_file.is_file() or session_file.stat().st_size == 0:
            raise RuntimeError(f"MAX session missing at {session_file}; manual authorization required")

        try:
            from pymax import Client
        except ImportError as exc:
            raise RuntimeError("pymax not installed: pip install maxapi-python") from exc

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
    global _max_retry_after
    try:
        now = datetime.now(timezone.utc)
        if _max_retry_after and now < _max_retry_after:
            log.warning("MAX delivery suppressed after a previous failure")
            return False
        client = await get_client()
        await client.send_message(chat_id=chat_id, text=text)
        log.info("MAX OK chat_id=%s len=%d", chat_id, len(text))
        return True
    except Exception as exc:
        from datetime import timedelta
        _max_retry_after = datetime.now(timezone.utc) + timedelta(seconds=MAX_FAILURE_COOLDOWN)
        log.error("MAX FAIL chat_id=%s error=%s", chat_id, exc)
        return False


async def send_to_email(subject: str, text: str) -> bool:
    """Send a channel-failure notice independently of MAX and Telegram."""
    if not (SMTP_HOST and SMTP_FROM and ALERT_EMAIL_TO):
        log.warning("Email channel-failure notification is not configured")
        return False
    recipients = [item.strip() for item in ALERT_EMAIL_TO.split(",") if item.strip()]
    try:
        message = MIMEText(text, "plain", "utf-8")
        message["Subject"], message["From"], message["To"] = subject, SMTP_FROM, ", ".join(recipients)
        if SMTP_PORT == 465:
            smtp = smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT, timeout=10)
        else:
            smtp = smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=10)
            smtp.starttls()
        if SMTP_USER and SMTP_PASSWORD:
            smtp.login(SMTP_USER, SMTP_PASSWORD)
        smtp.sendmail(SMTP_FROM, recipients, message.as_string())
        smtp.quit()
        return True
    except Exception as exc:
        log.error("Email channel-failure notification failed: %s", exc)
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


async def deliver_max(chat_id: int, text: str) -> bool:
    """Deliver alert to MAX. Returns True on success, False on failure."""
    ok = await send_to_max(chat_id, text)
    if not ok:
        _write_failed_log(chat_id, text, "send_to_max failed")
        warn = "MAX unavailable; original alerts continue through independent Telegram and email channels. Check the persisted MAX session before manual reauthorization."
        if TG_CHAT_ID and TG_BOT_TOKEN:
            await send_to_telegram(TG_CHAT_ID, warn)
        await send_to_email("[MSPShield] MAX channel unavailable", warn)
    return ok


async def deliver_telegram(chat_id: str, text: str) -> None:
    """Deliver alert to Telegram."""
    ok = await send_to_telegram(chat_id, text)
    if not ok:
        _write_failed_log(chat_id, text, "send_to_telegram failed")
        await send_to_email(
            "[MSPShield] Telegram channel unavailable",
            "Telegram delivery failed. MAX and email remain independent channels.\n\n" + text,
        )
