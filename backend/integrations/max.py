"""
MAX мессенджер (Bot API) — нотификации + входящие лиды.

MAX — российский мессенджер от VK, у которого с конца 2024 года есть
официальный публичный **бесплатный** Bot API (https://dev.max.ru/docs-api),
аналог Telegram Bot API.

Конфиг через env:

- MAX_BOT_TOKEN        — токен, выдаётся при регистрации бота
                         в `@MasterBot` внутри MAX (либо на dev.max.ru).
- MAX_ALERT_CHAT_ID    — чат (или user_id владельца), куда уходят
                         алерты о новых лидах с лендинга. Можно оставить
                         пустым, если бот используется только для
                         входящих заявок.
- MAX_WEBHOOK_SECRET   — произвольная случайная строка. Указывается при
                         подписке на webhook и проверяется на каждом
                         входящем запросе (заголовок `X-Max-Bot-Api-Secret`).
- MAX_BOT_USERNAME     — username бота без `@` (для построения deep-link
                         `https://max.ru/<username>` в UI).

API:

- Базовый URL: `https://platform-api.max.ru`
- Авторизация: заголовок `Authorization: <token>` (без префикса Bearer)
- Webhook: POST на ваш HTTPS-endpoint, ответ `200` за 30 секунд.

Если `MAX_BOT_TOKEN` не задан — интеграция отключена (no-op),
вебхук-эндпоинт возвращает 200 на любой запрос (молча).
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
    """Включена ли интеграция (есть токен)."""
    return bool(MAX_BOT_TOKEN)


def is_alert_channel() -> bool:
    """Используется ли MAX как канал для алертов о лидах."""
    return bool(MAX_BOT_TOKEN and MAX_ALERT_CHAT_ID)


def bot_deeplink() -> Optional[str]:
    """Публичная ссылка вида `https://max.ru/<username>` для лендинга."""
    if not MAX_BOT_USERNAME:
        return None
    return f"https://max.ru/{MAX_BOT_USERNAME}"


def _headers() -> Dict[str, str]:
    return {
        "Authorization": MAX_BOT_TOKEN,
        "Content-Type": "application/json",
        "Accept": "application/json",
    }


def _format_alert(lead: Dict[str, Any]) -> str:
    """Текстовый шаблон алерта (формат markdown — MAX поддерживает)."""
    lines = [
        "🛡 **Новая заявка МСП Облако**",
        f"**Имя:** {lead.get('name', '—')}",
        f"**Компания:** {lead.get('company', '—')}",
        f"**Контакт:** {lead.get('contact', '—')}",
        f"**Email:** {lead.get('email') or '—'}",
        f"**Серверы:** {lead.get('servers', '—')}",
        f"**Тариф:** {lead.get('tariff', '—')}",
        f"**Потери/год:** {lead.get('downtime_loss') or '—'}",
        f"**Сообщение:** {lead.get('message') or '—'}",
        f"**Источник:** {lead.get('source') or 'landing'}",
    ]
    return "\n".join(lines)


async def send_message(
    chat_id: Optional[str | int] = None,
    user_id: Optional[str | int] = None,
    text: str = "",
    buttons: Optional[List[List[Dict[str, Any]]]] = None,
    fmt: str = "markdown",
    notify: bool = True,
) -> Optional[Dict[str, Any]]:
    """
    Отправить произвольное сообщение от имени бота.

    Указывается либо `chat_id`, либо `user_id` (приоритет — chat_id).
    `buttons` — двумерный массив объектов кнопок согласно докам
    https://dev.max.ru/docs/chatbots/keyboards (тип link / callback / message).
    """
    if not is_enabled():
        return None
    if not (chat_id or user_id):
        logger.warning("max.send_message called without chat_id/user_id")
        return None

    params: Dict[str, Any] = {}
    if chat_id is not None:
        params["chat_id"] = chat_id
    elif user_id is not None:
        params["user_id"] = user_id

    body: Dict[str, Any] = {"text": text, "notify": notify}
    if fmt in {"markdown", "html"}:
        body["format"] = fmt
    if buttons:
        body["attachments"] = [
            {"type": "inline_keyboard", "payload": {"buttons": buttons}}
        ]

    url = f"{MAX_API_BASE}/messages"
    try:
        async with httpx.AsyncClient(timeout=HTTP_TIMEOUT) as http:
            r = await http.post(url, params=params, json=body, headers=_headers())
        if 200 <= r.status_code < 300:
            return r.json() if r.content else {}
        logger.warning(
            "max send_message %d to %s: %s",
            r.status_code,
            chat_id or user_id,
            r.text[:300],
        )
    except Exception as exc:  # noqa: BLE001
        logger.warning("max send_message failed: %s", exc)
    return None


async def send(lead: Dict[str, Any]) -> None:
    """
    Алерт о новом лиде. Аналог `telegram.send` / `webhook.send` —
    дёргается из `deliver_to_crm` фоновой задачей.
    """
    if not is_alert_channel():
        return
    text = _format_alert(lead)
    # Кнопка-ссылка на карточку Kaiten добавится позже, в момент,
    # когда у нас уже будет URL карточки (в обновлении статуса).
    await send_message(chat_id=MAX_ALERT_CHAT_ID, text=text)


async def send_alert_text(
    text: str,
    chat_id: Optional[str | int] = None,
    fmt: str = "markdown",
) -> bool:
    """
    Отправить произвольный текст в чат (по умолчанию — MAX_ALERT_CHAT_ID).
    Используется Alertmanager-приёмником.
    """
    target = chat_id if chat_id is not None else MAX_ALERT_CHAT_ID
    if not (MAX_BOT_TOKEN and target):
        return False
    result = await send_message(chat_id=target, text=text, fmt=fmt)
    return result is not None


# ─── Webhook helpers ────────────────────────────────────────────

def verify_webhook_secret(received_secret: Optional[str]) -> bool:
    """
    Сверяет заголовок `X-Max-Bot-Api-Secret` со значением из env.

    Если `MAX_WEBHOOK_SECRET` пуст — секрет не задан, считаем валидным
    (например, в dev). На проде секрет обязательно должен быть.
    """
    if not MAX_WEBHOOK_SECRET:
        return True
    return (received_secret or "") == MAX_WEBHOOK_SECRET


def extract_chat_and_text(update: Dict[str, Any]) -> Dict[str, Any]:
    """
    Достаёт нужные поля из webhook-update в плоский dict, чтобы дальше
    в server.py не возиться с вложенностью.

    Возвращает: { update_type, chat_id, user_id, user_name, text, mid, payload }
    Все поля nullable.
    """
    out: Dict[str, Any] = {
        "update_type": update.get("update_type"),
        "chat_id": None,
        "user_id": None,
        "user_name": None,
        "text": None,
        "mid": None,
        "payload": None,
    }

    msg = update.get("message") or {}
    recipient = msg.get("recipient") or {}
    sender = msg.get("sender") or {}
    body = msg.get("body") or {}

    out["chat_id"] = recipient.get("chat_id")
    out["user_id"] = sender.get("user_id") or recipient.get("user_id")
    out["user_name"] = sender.get("name") or sender.get("first_name")
    out["text"] = body.get("text")
    out["mid"] = body.get("mid")

    # bot_started — без message, данные на корне
    if not out["chat_id"] and update.get("chat_id"):
        out["chat_id"] = update.get("chat_id")
    if not out["user_id"] and update.get("user"):
        out["user_id"] = (update["user"] or {}).get("user_id")
        out["user_name"] = (update["user"] or {}).get("name") or out["user_name"]

    # callback button
    callback = update.get("callback")
    if callback:
        out["payload"] = callback.get("payload")
        out["mid"] = callback.get("callback_id") or out["mid"]
        if not out["user_id"]:
            out["user_id"] = (callback.get("user") or {}).get("user_id")

    return out


# ─── Кнопки и сценарии для входящего бота ───────────────────────

def welcome_buttons() -> List[List[Dict[str, Any]]]:
    """Стартовое меню после `bot_started`."""
    rows = [
        [
            {
                "type": "callback",
                "text": "📊 Рассчитать стоимость",
                "payload": "calc_start",
            }
        ],
        [
            {
                "type": "callback",
                "text": "📋 Тарифы Bronze / Silver / Gold",
                "payload": "show_tariffs",
            }
        ],
        [
            {
                "type": "request_contact",
                "text": "📞 Связаться со мной",
            }
        ],
    ]
    landing_url = os.environ.get("LANDING_URL", "").strip()
    if landing_url:
        rows.append([{"type": "link", "text": "🌐 Сайт msp-oblako", "url": landing_url}])
    return rows


def tariffs_buttons() -> List[List[Dict[str, Any]]]:
    """Меню выбора тарифа."""
    return [
        [{"type": "callback", "text": "Bronze · мониторинг", "payload": "tariff_bronze"}],
        [{"type": "callback", "text": "Silver · автоматизация + AD/DNS", "payload": "tariff_silver"}],
        [{"type": "callback", "text": "Gold · 24/7 + KES + Wazuh", "payload": "tariff_gold"}],
        [{"type": "callback", "text": "← Назад", "payload": "back_to_welcome"}],
    ]


WELCOME_TEXT = (
    "Здравствуйте 👋\n\n"
    "Я — бот **МСП Облако**. Помогу:\n"
    "- посчитать стоимость по вашей инфраструктуре,\n"
    "- сравнить тарифы Bronze / Silver / Gold,\n"
    "- передать заявку нашему специалисту.\n\n"
    "Выберите, с чего начать:"
)

TARIFFS_TEXT = (
    "**Тарифы:**\n\n"
    "**Bronze** — базовый мониторинг и backup, P1 24/7 best-effort.\n"
    "**Silver** — Ansible/Puppet, поддержка AD/DNS/GPO, P1 SLA 1 ч.\n"
    "**Gold** — всё из Silver + 24/7/365, Kaspersky KES/KSC, Wazuh SIEM, "
    "пост-мортем после каждого P1.\n\n"
    "Что подходит вам?"
)

TARIFF_DETAILS: Dict[str, str] = {
    "tariff_bronze": (
        "**Bronze**\n\n"
        "Что входит:\n"
        "- 24/7 мониторинг через Prometheus/Grafana/Loki,\n"
        "- ежедневный backup (Restic), хранение 14 дней,\n"
        "- best-effort реакция на инциденты,\n"
        "- ежемесячный отчёт.\n\n"
        "Подходит для 1–10 серверов, простой инфраструктуры."
    ),
    "tariff_silver": (
        "**Silver**\n\n"
        "Всё из Bronze + автоматизация (Ansible/Puppet), поддержка "
        "Active Directory / DNS / GPO, P2 в течение 4 часов, P1 в течение "
        "часа в рабочее окно, мониторинг до 25 серверов.\n\n"
        "Подходит, если есть AD, рост числа серверов, нужна автоматика."
    ),
    "tariff_gold": (
        "**Gold**\n\n"
        "Всё из Silver + дежурство 24/7/365 (P1 в течение 30 мин), "
        "Kaspersky KES/KSC на рабочих станциях, Wazuh SIEM + reagent "
        "по runbook'ам R-01...R-11, пост-мортем после каждого P1.\n\n"
        "Подходит, если простой = критические потери."
    ),
}

CALC_TEXT = (
    "Чтобы посчитать стоимость, ответьте парой строк:\n\n"
    "1. **Сколько серверов / VM** в инфраструктуре?\n"
    "2. **Есть ли Active Directory** (Да/Нет)?\n"
    "3. **Сколько рабочих станций** нужно администрировать (если есть)?\n"
    "4. Как вас зовут и название компании?\n\n"
    "Можно одним сообщением. Я передам вашему персональному инженеру, "
    "и он вернётся с расчётом в рабочее время."
)
