"""
Email-уведомления о новых лидах.

Отправляет письмо на SMTP_HOST:SMTP_PORT через SMTP_USER/SMTP_PASSWORD.
Включается через SMTP_HOST + LEAD_EMAIL_TO.

Антиспам-меры:
- From: sales@ (не alert@ — слово «alert» триггерит спам-фильтры)
- From name: «MSPShield» (не «Alert»)
- Message-ID, Date, Reply-To — обязательные заголовки
- Auto-Submitted: auto-generated (RFC 3834)
- Plain-text альтернатива + HTML
"""
from __future__ import annotations

import logging
import os
import smtplib
import uuid
from datetime import datetime, timezone
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Any, Dict, List

logger = logging.getLogger("mspshield.email")

SMTP_HOST = os.environ.get("SMTP_HOST", "").strip()
SMTP_PORT = int(os.environ.get("SMTP_PORT", "465"))
SMTP_USER = os.environ.get("SMTP_USER", "").strip()
SMTP_PASSWORD = os.environ.get("SMTP_PASSWORD", "").strip()
SMTP_FROM = os.environ.get("SMTP_FROM", "sales@msp-claude.online").strip()
SMTP_FROM_NAME = os.environ.get("SMTP_FROM_NAME", "MSPShield").strip()
LEAD_EMAIL_TO = os.environ.get("LEAD_EMAIL_TO", "").strip()

_USE_TLS = SMTP_PORT in (465, 587)


def is_enabled() -> bool:
    return bool(SMTP_HOST and LEAD_EMAIL_TO)


def _recipients() -> List[str]:
    return [r.strip() for r in LEAD_EMAIL_TO.split(",") if r.strip()]


def _build_plain(lead: Dict[str, Any]) -> str:
    lines = [
        f"Новая заявка MSPShield",
        "",
        f"Имя: {lead.get('name', '—')}",
        f"Компания: {lead.get('company', '—')}",
        f"Контакт: {lead.get('contact', '—')}",
        f"Email: {lead.get('email') or '—'}",
        f"Серверы: {lead.get('servers', '—')}",
        f"Тариф: {lead.get('tariff', '—')}",
        f"Потери/год: {lead.get('downtime_loss') or '—'}",
        f"Сообщение: {lead.get('message') or '—'}",
        f"Источник: {lead.get('source') or 'landing'}",
    ]
    return "\n".join(lines)


def _build_html(lead: Dict[str, Any]) -> str:
    rows = [
        ("Имя", lead.get("name", "—")),
        ("Компания", lead.get("company", "—")),
        ("Контакт", lead.get("contact", "—")),
        ("Email", lead.get("email") or "—"),
        ("Серверы", lead.get("servers", "—")),
        ("Тариф", lead.get("tariff", "—")),
        ("Потери/год", lead.get("downtime_loss") or "—"),
        ("Сообщение", lead.get("message") or "—"),
        ("Источник", lead.get("source") or "landing"),
    ]
    trs = "\n".join(
        f'<tr><td style="padding:6px 12px;font-weight:600;color:#1b4d3e;white-space:nowrap">{l}</td>'
        f'<td style="padding:6px 12px">{v}</td></tr>'
        for l, v in rows
    )
    return f"""<html><body style="font-family:DM Sans,Arial,sans-serif;color:#1a1815;margin:0;padding:24px;background:#f5f1e8">
<div style="max-width:560px;margin:0 auto;border:1px solid #d4cfc4;border-radius:8px;overflow:hidden;background:#fff">
<div style="background:#1b4d3e;padding:16px 24px;color:#f5f1e8;font-size:18px;font-weight:600">
MSPShield — Новая заявка</div>
<table style="width:100%;border-collapse:collapse;font-size:14px">{trs}</table>
</div></body></html>"""


async def send(lead: Dict[str, Any]) -> None:
    if not is_enabled():
        return
    recipients = _recipients()
    now = datetime.now(timezone.utc)

    msg = MIMEMultipart("alternative")
    msg["Subject"] = f"[MSPShield] Заявка: {lead.get('company', '—')} — {lead.get('name', '—')}"
    msg["From"] = f"{SMTP_FROM_NAME} <{SMTP_FROM}>"
    msg["To"] = ", ".join(recipients)
    msg["Date"] = now.strftime("%a, %d %b %Y %H:%M:%S +0000")
    msg["Message-ID"] = f"<{uuid.uuid4()}@msp-claude.online>"
    msg["Reply-To"] = lead.get("email") or SMTP_FROM
    msg["Auto-Submitted"] = "auto-generated"
    msg["X-Auto-Response-Suppress"] = "OOF, AutoReply"
    msg["X-Priority"] = "1"

    msg.attach(MIMEText(_build_plain(lead), "plain", "utf-8"))
    msg.attach(MIMEText(_build_html(lead), "html", "utf-8"))

    try:
        if SMTP_PORT == 465:
            srv = smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT, timeout=10)
        else:
            srv = smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=10)
            srv.ehlo("msp-claude.online")
            if _USE_TLS:
                srv.starttls()
                srv.ehlo("msp-claude.online")
        if SMTP_USER and SMTP_PASSWORD:
            srv.login(SMTP_USER, SMTP_PASSWORD)
        srv.sendmail(SMTP_FROM, recipients, msg.as_string())
        srv.quit()
        logger.info("lead email sent to=%s lead=%s", recipients, lead.get("id"))
    except Exception as exc:
        logger.warning("lead email failed lead=%s: %s", lead.get("id"), exc)
