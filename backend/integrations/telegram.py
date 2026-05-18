"""Telegram-уведомления о новых лидах + Alertmanager-алерты.

Включается через TG_BOT_TOKEN + TG_CHAT_ID.
Опционально TG_ALERT_CHAT_ID — отдельный канал для Alertmanager (если не задан,
используется TG_CHAT_ID).
"""
from __future__ import annotations

import logging
import os
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
        async with httpx.AsyncClient(timeout=HTTP_TIMEOUT) as http:
            await http.post(
                url,
                json={"chat_id": TG_CHAT_ID, "text": text, "parse_mode": "HTML"},
            )
    except Exception as exc:  # noqa: BLE001
        logger.warning("telegram notify failed lead=%s: %s", lead.get("id"), exc)


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
