"""MAX Bot API: уведомления о лидах и меню актуальных тарифов.

Junior: сетевой сбой здесь не должен ронять API заявки. Production outbox
повторит доставку. Никогда не журналируйте токен и полный payload клиента.
"""
from __future__ import annotations

import logging
import os
from typing import Any, Dict, List, Optional

import httpx

logger = logging.getLogger("mspshield.max")
MAX_BOT_TOKEN = os.environ.get("MAX_BOT_TOKEN", "").strip()
MAX_ALERT_CHAT_ID = os.environ.get("MAX_ALERT_CHAT_ID", "").strip()
MAX_WEBHOOK_SECRET = os.environ.get("MAX_WEBHOOK_SECRET", "").strip()
MAX_BOT_USERNAME = os.environ.get("MAX_BOT_USERNAME", "").strip().lstrip("@")
MAX_API_BASE = os.environ.get("MAX_API_BASE", "https://platform-api.max.ru").rstrip("/")
HTTP_TIMEOUT = 8.0


def is_enabled() -> bool:
    """Интеграция включена только при явно заданном токене."""
    return bool(MAX_BOT_TOKEN)


def is_alert_channel() -> bool:
    """Для алертов нужны и токен, и идентификатор служебного чата."""
    return bool(MAX_BOT_TOKEN and MAX_ALERT_CHAT_ID)


def bot_deeplink() -> Optional[str]:
    """Возвращает обычный URL без служебных фигурных скобок."""
    return "https://max.ru/" + MAX_BOT_USERNAME if MAX_BOT_USERNAME else None


def _headers() -> Dict[str, str]:
    """Собирает заголовки API; значение Authorization не печатается в лог."""
    return {"Authorization": MAX_BOT_TOKEN, "Content-Type": "application/json", "Accept": "application/json"}


def _format_alert(lead: Dict[str, Any]) -> str:
    """Формирует короткое уведомление; источник истины остаётся в CRM."""
    pairs = [("Имя", lead.get("name", "—")), ("Компания", lead.get("company", "—")),
             ("Контакт", lead.get("contact", "—")), ("Email", lead.get("email") or "—"),
             ("Серверы", lead.get("servers", "—")), ("Тариф", lead.get("tariff", "—")),
             ("Сообщение", lead.get("message") or "—"), ("Источник", lead.get("source") or "landing")]
    return "🛡 **Новая заявка МСП Облако**\n" + "\n".join(f"**{key}:** {value}" for key, value in pairs)


async def send_message(chat_id: Optional[str | int] = None, user_id: Optional[str | int] = None,
                       text: str = "", buttons: Optional[List[List[Dict[str, Any]]]] = None,
                       fmt: str = "markdown", notify: bool = True) -> Optional[Dict[str, Any]]:
    """Отправляет сообщение и возвращает None при ошибке для последующего retry."""
    if not is_enabled() or not (chat_id or user_id):
        return None
    key = "chat_id" if chat_id is not None else "user_id"
    params = {key: chat_id if chat_id is not None else user_id}
    body: Dict[str, Any] = {"text": text, "notify": notify}
    if fmt in {"markdown", "html"}:
        body["format"] = fmt
    if buttons:
        body["attachments"] = [{"type": "inline_keyboard", "payload": {"buttons": buttons}}]
    try:
        async with httpx.AsyncClient(timeout=HTTP_TIMEOUT) as client:
            response = await client.post(f"{MAX_API_BASE}/messages", params=params, json=body, headers=_headers())
        if 200 <= response.status_code < 300:
            return response.json() if response.content else {}
        logger.warning("MAX вернул HTTP %s: %s", response.status_code, response.text[:300])
    except Exception as exc:  # noqa: BLE001 — внешний канал не должен остановить приём заявки.
        logger.warning("Не удалось отправить сообщение в MAX: %s", exc)
    return None


async def send(lead: Dict[str, Any]) -> None:
    """Отправляет лид в чат; durable outbox отвечает за повтор после сбоя."""
    if is_alert_channel():
        await send_message(chat_id=MAX_ALERT_CHAT_ID, text=_format_alert(lead))


async def send_alert_text(text: str, chat_id: Optional[str | int] = None, fmt: str = "markdown") -> bool:
    """Используется Alertmanager-приёмником и явно сообщает об успехе."""
    target = chat_id if chat_id is not None else MAX_ALERT_CHAT_ID
    if not (MAX_BOT_TOKEN and target):
        return False
    return await send_message(chat_id=target, text=text, fmt=fmt) is not None


def verify_webhook_secret(received_secret: Optional[str]) -> bool:
    """Сравнивает webhook secret; production-конфигурация обязана задать его."""
    return True if not MAX_WEBHOOK_SECRET else (received_secret or "") == MAX_WEBHOOK_SECRET


def extract_chat_and_text(update: Dict[str, Any]) -> Dict[str, Any]:
    """Приводит message, bot_started и callback к единому словарю."""
    message = update.get("message") or {}
    recipient, sender, body = message.get("recipient") or {}, message.get("sender") or {}, message.get("body") or {}
    result = {"update_type": update.get("update_type"), "chat_id": recipient.get("chat_id"),
              "user_id": sender.get("user_id") or recipient.get("user_id"),
              "user_name": sender.get("name") or sender.get("first_name"), "text": body.get("text"),
              "mid": body.get("mid"), "payload": None}
    result["chat_id"] = result["chat_id"] or update.get("chat_id")
    if not result["user_id"] and update.get("user"):
        result["user_id"] = (update["user"] or {}).get("user_id")
        result["user_name"] = (update["user"] or {}).get("name")
    callback = update.get("callback") or {}
    if callback:
        result["payload"] = callback.get("payload")
        result["mid"] = callback.get("callback_id") or result["mid"]
        result["user_id"] = result["user_id"] or (callback.get("user") or {}).get("user_id")
    return result


def welcome_buttons() -> List[List[Dict[str, Any]]]:
    """Стартовое меню. Ссылка добавляется только при заданном LANDING_URL."""
    rows = [[{"type": "callback", "text": "📊 Рассчитать стоимость", "payload": "calc_start"}],
            [{"type": "callback", "text": "📋 Тарифы Bronze / Silver / Gold", "payload": "show_tariffs"}],
            [{"type": "request_contact", "text": "📞 Связаться со мной"}]]
    url = os.environ.get("LANDING_URL", "").strip()
    if url:
        rows.append([{"type": "link", "text": "🌐 Сайт МСП Облако", "url": url}])
    return rows


def tariffs_buttons() -> List[List[Dict[str, Any]]]:
    """Gold показывается как roadmap, а не как доступное круглосуточное обслуживание."""
    return [[{"type": "callback", "text": "Bronze · от 25 000 ₽", "payload": "tariff_bronze"}],
            [{"type": "callback", "text": "Silver · от 50 000 ₽", "payload": "tariff_silver"}],
            [{"type": "callback", "text": "Gold Future · от 120 000 ₽", "payload": "tariff_gold"}],
            [{"type": "callback", "text": "← Назад", "payload": "back_to_welcome"}]]


WELCOME_TEXT = "Здравствуйте 👋\n\nЯ — бот МСП Облако. Помогу сравнить пакеты и передать заявку специалисту."
TARIFFS_TEXT = ("**Bronze** — автомониторинг, backup, P1 до 4 рабочих часов.\n"
                "**Silver** — AD/логи/Ansible, P1 до 2 рабочих часов.\n"
                "**Gold Future** — roadmap от 120 000 ₽, закрыт до on-call ротации.\n\n"
                "Мониторинг 24/7 не означает круглосуточное дежурство инженера.")
TARIFF_DETAILS: Dict[str, str] = {
    "tariff_bronze": "**Bronze от 25 000 ₽**\n2 инженерных часа; сверхлимит от 3 500 ₽/ч.",
    "tariff_silver": "**Silver от 50 000 ₽**\n4 инженерных часа; проекты и лицензии отдельно.",
    "tariff_gold": "**Gold Future от 120 000 ₽**\nЗакрыт до ротации и подтверждения DR.",
}
CALC_TEXT = "Укажите серверы, AD, критичные системы, рабочее окно и контакт. Цена определяется после аудита."
