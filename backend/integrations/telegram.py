"""Telegram-уведомления о новых лидах. Включается через TG_BOT_TOKEN + TG_CHAT_ID."""
from __future__ import annotations

import logging
import os
from typing import Any, Dict

import httpx

logger = logging.getLogger("mspshield.telegram")

TG_BOT_TOKEN = os.environ.get("TG_BOT_TOKEN", "").strip()
TG_CHAT_ID = os.environ.get("TG_CHAT_ID", "").strip()


def is_enabled() -> bool:
    return bool(TG_BOT_TOKEN and TG_CHAT_ID)


def _format_message(lead: Dict[str, Any]) -> str:
    lines = [
        "<b>🛡 Новая заявка MSPShield</b>",
        f"<b>Имя:</b> {lead.get('name', '—')}",
        f"<b>Компания:</b> {lead.get('company', '—')}",
        f"<b>Контакт:</b> {lead.get('contact', '—')}",
        f"<b>Email:</b> {lead.get('email') or '—'}",
        f"<b>Серверы:</b> {lead.get('servers', '—')}",
        f"<b>Тариф:</b> {lead.get('tariff', '—')}",
        f"<b>Потери/год:</b> {lead.get('downtime_loss') or '—'}",
        f"<b>Сообщение:</b> {lead.get('message') or '—'}",
        f"<b>Источник:</b> {lead.get('source') or 'landing'}",
    ]
    return "\n".join(lines)


async def send(lead: Dict[str, Any]) -> None:
    if not is_enabled():
        return
    text = _format_message(lead)
    url = f"https://api.telegram.org/bot{TG_BOT_TOKEN}/sendMessage"
    try:
        async with httpx.AsyncClient(timeout=8.0) as http:
            await http.post(
                url,
                json={"chat_id": TG_CHAT_ID, "text": text, "parse_mode": "HTML"},
            )
    except Exception as exc:  # noqa: BLE001
        logger.warning("telegram notify failed lead=%s: %s", lead.get("id"), exc)
