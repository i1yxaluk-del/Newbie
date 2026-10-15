"""Telegram-уведомления о новых лидах + Alertmanager-алерты.

Включается через TG_BOT_TOKEN + TG_CHAT_ID.
- TG_CHAT_ID — чат для уведомлений о лидах (MSPleads).
- TG_ALERT_CHAT_ID — отдельный канал для Alertmanager (MSPalert).
  Если не задан, используется TG_CHAT_ID.
"""
from __future__ import annotations

import logging
import os
from html import escape
from typing import Any, Dict, Optional

import httpx

logger = logging.getLogger("mspshield.telegram")

TG_BOT_TOKEN = os.environ.get("TG_BOT_TOKEN", "").strip()
TG_CHAT_ID = os.environ.get("TG_CHAT_ID", "").strip()
TG_ALERT_CHAT_ID = os.environ.get("TG_ALERT_CHAT_ID", "").strip() or TG_CHAT_ID

HTTP_TIMEOUT = 8.0


def is_enabled() -> bool:
    return bool(TG_BOT_TOKEN and TG_CHAT_ID)


def is_alert_channel() -> bool:
    """Доступен ли Telegram как канал для Alertmanager-алертов."""
    return bool(TG_BOT_TOKEN and TG_ALERT_CHAT_ID)


def _format_message(lead: Dict[str, Any]) -> str:
    fields = [("Имя", "name"), ("Компания", "company"), ("Контакт", "contact"),
              ("Email", "email"), ("Серверы", "servers"), ("Тариф", "tariff"),
              ("Потери/год", "downtime_loss"), ("Сообщение", "message"), ("Источник", "source")]
    return "<b>🛡 Новая заявка MSPShield</b>\n" + "\n".join(
        f"<b>{label}:</b> {escape(str(lead.get(key) or '—'))}" for label, key in fields
    )


async def send(lead: Dict[str, Any]) -> bool:
    if not is_enabled():
        return False
    text = _format_message(lead)
    url = f"https://api.telegram.org/bot{TG_BOT_TOKEN}/sendMessage"
    try:
        async with httpx.AsyncClient(timeout=HTTP_TIMEOUT) as http:
            response = await http.post(
                url,
                json={"chat_id": TG_CHAT_ID, "text": text, "parse_mode": "HTML"},
            )
        return response.is_success and response.json().get("ok") is True
    except Exception:  # noqa: BLE001
        logger.warning("telegram notify failed lead=%s", lead.get("id"))
        return False


async def send_alert_text(
    text: str,
    chat_id: Optional[str] = None,
    parse_mode: str = "HTML",
) -> bool:
    """
    Отправить произвольный текст в чат (по умолчанию — TG_ALERT_CHAT_ID).
    Используется Alertmanager-приёмником.
    """
    if not TG_BOT_TOKEN:
        return False
    target = chat_id or TG_ALERT_CHAT_ID
    if not target:
        return False
    url = f"https://api.telegram.org/bot{TG_BOT_TOKEN}/sendMessage"
    try:
        async with httpx.AsyncClient(timeout=HTTP_TIMEOUT) as http:
            r = await http.post(
                url,
                json={
                    "chat_id": target,
                    "text": text,
                    "parse_mode": parse_mode,
                    "disable_web_page_preview": True,
                },
            )
        if 200 <= r.status_code < 300:
            return True
        logger.warning("telegram send_alert_text %d: %s", r.status_code, r.text[:300])
    except Exception as exc:  # noqa: BLE001
        logger.warning("telegram send_alert_text failed: %s", exc)
    return False
