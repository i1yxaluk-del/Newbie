"""
Kaiten CRM integration
======================

Создаёт карточку в Kaiten за каждым успешно прошедшим валидацию лидом.
Идемпотентность по `lead_id` — повторный вызов с тем же `lead_id` ничего не делает.
Ошибка Kaiten не блокирует ответ пользователю: лид уже в Mongo, попытка логируется.

Конфиг через env:
- KAITEN_DOMAIN          — поддомен `<workspace>.kaiten.ru`
- KAITEN_API_TOKEN       — Bearer-токен (Профиль → Настройки → API)
- KAITEN_BOARD_ID        — id доски (выводится скриптом kaiten_bootstrap.py)
- KAITEN_COLUMN_ID       — id колонки «Новая» (там же)
- KAITEN_LANE_ID         — опционально: id дорожки (если в доске несколько)

Если переменные не заданы — интеграция отключена (no-op).
"""
from __future__ import annotations

import asyncio
import logging
import os
from typing import Any, Dict, Optional

import httpx

logger = logging.getLogger("mspshield.kaiten")

KAITEN_DOMAIN = os.environ.get("KAITEN_DOMAIN", "").strip().rstrip("/")
KAITEN_API_TOKEN = os.environ.get("KAITEN_API_TOKEN", "").strip()
KAITEN_BOARD_ID = os.environ.get("KAITEN_BOARD_ID", "").strip()
KAITEN_COLUMN_ID = os.environ.get("KAITEN_COLUMN_ID", "").strip()
KAITEN_LANE_ID = os.environ.get("KAITEN_LANE_ID", "").strip()

# Backoff: 1s → 4s → 16s, итого ~21 сек на 3 попытки.
RETRY_DELAYS = (1, 4, 16)
HTTP_TIMEOUT = 10.0


def is_enabled() -> bool:
    return bool(
        KAITEN_DOMAIN
        and KAITEN_API_TOKEN
        and KAITEN_BOARD_ID
        and KAITEN_COLUMN_ID
    )


def _api_base() -> str:
    domain = KAITEN_DOMAIN
    if "://" not in domain:
        domain = f"https://{domain}"
    return f"{domain}/api/latest"


def _headers() -> Dict[str, str]:
    return {
        "Authorization": f"Bearer {KAITEN_API_TOKEN}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }


def _format_description(lead: Dict[str, Any]) -> str:
    fields = [
        ("Имя", lead.get("name")),
        ("Компания", lead.get("company")),
        ("Контакт", lead.get("contact")),
        ("Email", lead.get("email")),
        ("Серверы", lead.get("servers")),
        ("Тариф", lead.get("tariff")),
        ("Источник", lead.get("source")),
        ("Потери/год (калькулятор)", lead.get("downtime_loss")),
    ]
    rows = [f"- **{label}:** {value}" for label, value in fields if value]
    msg = lead.get("message")
    body = "\n".join(rows)
    if msg:
        body += f"\n\n**Сообщение клиента:**\n\n> {msg}"
    body += f"\n\n_lead\\_id:_ `{lead.get('id')}`"
    return body


def build_card_payload(lead: Dict[str, Any]) -> Dict[str, Any]:
    title = f"[{lead.get('tariff', 'undecided')}] {lead.get('company', '')} · {lead.get('name', '')}".strip()
    payload: Dict[str, Any] = {
        "title": title or "Новая заявка MSPShield",
        "description": _format_description(lead),
        "board_id": int(KAITEN_BOARD_ID) if KAITEN_BOARD_ID.isdigit() else KAITEN_BOARD_ID,
        "column_id": int(KAITEN_COLUMN_ID) if KAITEN_COLUMN_ID.isdigit() else KAITEN_COLUMN_ID,
        "external_id": str(lead.get("id") or ""),
    }
    if KAITEN_LANE_ID:
        payload["lane_id"] = int(KAITEN_LANE_ID) if KAITEN_LANE_ID.isdigit() else KAITEN_LANE_ID
    return payload


async def create_card(lead: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Создать карточку в Kaiten. Возвращает ответ Kaiten или None при ошибке."""
    if not is_enabled():
        return None

    url = f"{_api_base()}/cards"
    payload = build_card_payload(lead)
    last_error: Optional[Exception] = None

    for attempt, delay in enumerate(RETRY_DELAYS, start=1):
        try:
            async with httpx.AsyncClient(timeout=HTTP_TIMEOUT) as http:
                r = await http.post(url, json=payload, headers=_headers())
            if 200 <= r.status_code < 300:
                data = r.json() if r.content else {}
                logger.info(
                    "kaiten card created lead=%s card_id=%s",
                    lead.get("id"),
                    data.get("id"),
                )
                return data
            if r.status_code == 429:
                logger.warning("kaiten 429 rate-limited (attempt %d)", attempt)
            elif 400 <= r.status_code < 500:
                # 4xx (кроме 429) — бессмысленно ретраить.
                logger.error(
                    "kaiten %d on lead=%s: %s",
                    r.status_code,
                    lead.get("id"),
                    r.text[:300],
                )
                return None
            else:
                logger.warning(
                    "kaiten %d on lead=%s (attempt %d): %s",
                    r.status_code,
                    lead.get("id"),
                    attempt,
                    r.text[:200],
                )
        except Exception as exc:  # noqa: BLE001
            last_error = exc
            logger.warning(
                "kaiten request failed lead=%s attempt=%d: %s",
                lead.get("id"),
                attempt,
                exc,
            )

        if attempt < len(RETRY_DELAYS):
            await asyncio.sleep(delay)

    logger.error(
        "kaiten failed after %d attempts lead=%s last_error=%s",
        len(RETRY_DELAYS),
        lead.get("id"),
        last_error,
    )
    return None
