import asyncio
import logging
from email.message import EmailMessage

import aiosmtplib
import httpx

from ..config import settings
from ..models import Lead

log = logging.getLogger("domik.notifications")


def _format_lead_text(lead: Lead) -> str:
    lines = [
        "Новая заявка с сайта Domik Alina",
        "",
        f"Имя:    {lead.name}",
        f"Телефон: {lead.phone}",
    ]
    if lead.email:
        lines.append(f"Email:   {lead.email}")
    if lead.guests:
        lines.append(f"Гостей:  {lead.guests}")
    if lead.date_from or lead.date_to:
        lines.append(f"Даты:    {lead.date_from or '?'} — {lead.date_to or '?'}")
    if lead.message:
        lines += ["", "Сообщение:", lead.message]
    lines += ["", f"ID: #{lead.id}", f"Создано: {lead.created_at:%Y-%m-%d %H:%M}"]
    return "\n".join(lines)


async def _send_email(lead: Lead) -> None:
    if not (settings.SMTP_HOST and settings.SMTP_USER and settings.NOTIFY_EMAIL_TO):
        log.info("SMTP not configured, skip email")
        return
    msg = EmailMessage()
    msg["From"] = settings.SMTP_FROM or settings.SMTP_USER
    msg["To"] = settings.NOTIFY_EMAIL_TO
    msg["Subject"] = f"[Domik] Новая заявка #{lead.id} — {lead.name}"
    msg.set_content(_format_lead_text(lead))
    try:
        await aiosmtplib.send(
            msg,
            hostname=settings.SMTP_HOST,
            port=settings.SMTP_PORT,
            username=settings.SMTP_USER,
            password=settings.SMTP_PASSWORD,
            use_tls=settings.SMTP_USE_TLS,
            timeout=15,
        )
        log.info("Email sent for lead #%s", lead.id)
    except Exception as e:
        log.exception("Email send failed: %s", e)


async def _send_telegram(lead: Lead) -> None:
    if not (settings.TG_BOT_TOKEN and settings.TG_CHAT_ID):
        log.info("Telegram not configured, skip")
        return
    text = _format_lead_text(lead)
    url = f"https://api.telegram.org/bot{settings.TG_BOT_TOKEN}/sendMessage"
    payload = {"chat_id": settings.TG_CHAT_ID, "text": text, "disable_web_page_preview": True}
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            r = await client.post(url, json=payload)
            r.raise_for_status()
        log.info("Telegram sent for lead #%s", lead.id)
    except Exception as e:
        log.exception("Telegram send failed: %s", e)


async def notify_new_lead(lead: Lead) -> None:
    await asyncio.gather(_send_email(lead), _send_telegram(lead), return_exceptions=True)
