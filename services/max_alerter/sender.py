"""Доставка Alertmanager webhook в MAX с Telegram/email fallback.

Модуль никогда не запрашивает SMS самостоятельно. Сессию создаёт оператор
командой из docs/MAX_SETUP.md и хранит её в `/session/max.db`.
"""
from __future__ import annotations

import asyncio
import logging
import os
import smtplib
from datetime import datetime, timedelta, timezone
from email.mime.text import MIMEText
from pathlib import Path
from typing import Optional

import httpx

log = logging.getLogger("max_alerter.sender")
MAX_PHONE = os.environ.get("MAX_PHONE", "").strip()
MAX_SESSION_DIR = Path(os.environ.get("MAX_SESSION_DIR", "/session"))
MAX_SESSION_NAME = os.environ.get("MAX_SESSION_NAME", "max.db").strip()
TG_BOT_TOKEN = os.environ.get("TG_BOT_TOKEN", "").strip()
TG_CHAT_ID = os.environ.get("TG_CHAT_ID", "").strip()
SMTP_HOST = os.environ.get("SMTP_HOST", "").strip()
SMTP_PORT = int(os.environ.get("SMTP_PORT", "465"))
SMTP_USER = os.environ.get("SMTP_USER", "").strip()
SMTP_PASSWORD = os.environ.get("SMTP_PASSWORD", "").strip()
SMTP_FROM = os.environ.get("SMTP_FROM", "").strip()
ALERT_EMAIL_TO = os.environ.get("ALERT_EMAIL_TO", "").strip()
MAX_FAILURE_COOLDOWN = int(os.environ.get("MAX_FAILURE_COOLDOWN", "300"))
FAILED_LOG = Path(os.environ.get("FAILED_LOG", "/data/failed_alerts.log"))
_client: Optional[object] = None
_client_lock = asyncio.Lock()
_max_retry_after: Optional[datetime] = None


async def get_client():
    """Возвращает pymax Client только при наличии persisted session."""
    global _client
    async with _client_lock:
        if _client is not None:
            return _client
        if not MAX_PHONE:
            raise RuntimeError("MAX_PHONE не задан")
        session_file = MAX_SESSION_DIR / MAX_SESSION_NAME
        if not session_file.is_file() or session_file.stat().st_size == 0:
            raise RuntimeError(f"MAX session missing at {session_file}; manual authorization required")
        try:
            from pymax import Client
        except ImportError as exc:
            raise RuntimeError("pymax не установлен") from exc
        client = Client(phone=MAX_PHONE, work_dir=str(MAX_SESSION_DIR), session_name=MAX_SESSION_NAME)
        ready = asyncio.Event()

        @client.on_start()
        async def on_start(current_client) -> None:
            user_id = current_client.me.contact.id if current_client.me else "unknown"
            log.info("MAX client ready, user_id=%s", user_id)
            ready.set()

        asyncio.get_running_loop().create_task(client.start())
        await asyncio.wait_for(ready.wait(), timeout=30)
        _client = client
        return _client


async def send_to_max(chat_id: int, text: str) -> bool:
    """Отправляет в MAX; cooldown защищает от retry storm."""
    global _max_retry_after
    try:
        now = datetime.now(timezone.utc)
        if _max_retry_after and now < _max_retry_after:
            log.warning("MAX delivery временно подавлена после предыдущей ошибки")
            return False
        client = await get_client()
        await client.send_message(chat_id=chat_id, text=text)
        log.info("MAX delivery OK, chat_id=%s, length=%d", chat_id, len(text))
        return True
    except Exception as exc:
        _max_retry_after = datetime.now(timezone.utc) + timedelta(seconds=MAX_FAILURE_COOLDOWN)
        log.error("MAX delivery FAIL, chat_id=%s: %s", chat_id, exc)
        return False


async def send_to_telegram(chat_id: str, text: str) -> bool:
    """Отправляет резервное сообщение через Telegram Bot API."""
    if not (TG_BOT_TOKEN and chat_id):
        return False
    try:
        url = "https://api.telegram.org/bot" + TG_BOT_TOKEN + "/sendMessage"
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.post(url, json={"chat_id": chat_id, "text": text, "parse_mode": "HTML"})
            response.raise_for_status()
        return True
    except Exception as exc:
        log.error("Telegram fallback FAIL, chat_id=%s: %s", chat_id, exc)
        return False


async def send_to_email(subject: str, text: str) -> bool:
    """Сообщает об отказе канала по email."""
    recipients = [item.strip() for item in ALERT_EMAIL_TO.split(",") if item.strip()]
    if not (SMTP_HOST and SMTP_FROM and recipients):
        return False
    try:
        message = MIMEText(text, "plain", "utf-8")
        message["Subject"], message["From"], message["To"] = subject, SMTP_FROM, ", ".join(recipients)
        smtp = smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT, timeout=10) if SMTP_PORT == 465 else smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=10)
        if SMTP_PORT != 465:
            smtp.starttls()
        if SMTP_USER and SMTP_PASSWORD:
            smtp.login(SMTP_USER, SMTP_PASSWORD)
        smtp.sendmail(SMTP_FROM, recipients, message.as_string())
        smtp.quit()
        return True
    except Exception as exc:
        log.error("Email fallback FAIL: %s", exc)
        return False


def _write_failed_log(chat_id: int | str, text: str, error: str) -> None:
    """Сохраняет недоставленный алерт локально."""
    try:
        FAILED_LOG.parent.mkdir(parents=True, exist_ok=True)
        with FAILED_LOG.open("a", encoding="utf-8") as stream:
            stream.write(f"[{datetime.now(timezone.utc).isoformat()}] chat_id={chat_id} error={error!r}\n{text}\n---\n")
    except Exception as exc:
        log.error("Не удалось записать failed_alerts.log: %s", exc)


async def deliver_max(chat_id: int, text: str) -> bool:
    """Основной MAX-канал; fallback вызывается только после отказа."""
    if await send_to_max(chat_id, text):
        return True
    _write_failed_log(chat_id, text, "send_to_max failed")
    notice = "MAX недоступен. Проверьте persisted session; SMS-авторизацию запускайте вручную."
    if TG_CHAT_ID and TG_BOT_TOKEN:
        await send_to_telegram(TG_CHAT_ID, notice + "\n\n" + text)
    await send_to_email("[MSPShield] MAX channel unavailable", notice)
    return False


async def deliver_telegram(chat_id: str, text: str) -> None:
    """Совместимый интерфейс для отдельной Telegram-доставки."""
    if not await send_to_telegram(chat_id, text):
        _write_failed_log(chat_id, text, "send_to_telegram failed")
        await send_to_email("[MSPShield] Telegram channel unavailable", text)
