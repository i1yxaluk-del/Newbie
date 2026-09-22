"""Kaiten CRM integration.

MongoDB remains the source of truth. Kaiten is an optional work surface for the
pilot team and may run on the free plan while it satisfies the team's needs.
"""
from __future__ import annotations

import asyncio
import logging
import os
from typing import Any, Dict, Iterable, Optional

import httpx

logger = logging.getLogger("mspshield.kaiten")

KAITEN_DOMAIN = os.environ.get("KAITEN_DOMAIN", "").strip().rstrip("/")
KAITEN_API_TOKEN = os.environ.get("KAITEN_API_TOKEN", "").strip()
KAITEN_BOARD_ID = os.environ.get("KAITEN_BOARD_ID", "").strip()
KAITEN_COLUMN_ID = os.environ.get("KAITEN_COLUMN_ID", "").strip()
KAITEN_LANE_ID = os.environ.get("KAITEN_LANE_ID", "").strip()

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


def _as_int(value: str) -> Any:
    return int(value) if value.isdigit() else value


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
    body = "\n".join(rows)
    if lead.get("message"):
        body += f"\n\n**Сообщение клиента:**\n\n> {lead['message']}"
    body += f"\n\n_lead\\_id:_ `{lead.get('id')}`"
    return body


def build_card_payload(lead: Dict[str, Any]) -> Dict[str, Any]:
    title = (
        f"[{lead.get('tariff', 'undecided')}] "
        f"{lead.get('company', '')} · {lead.get('name', '')}"
    ).strip()
    payload: Dict[str, Any] = {
        "title": title or "Новая заявка MSPShield",
        "description": _format_description(lead),
        "board_id": _as_int(KAITEN_BOARD_ID),
        "column_id": _as_int(KAITEN_COLUMN_ID),
        "external_id": str(lead.get("id") or ""),
    }
    if KAITEN_LANE_ID:
        payload["lane_id"] = _as_int(KAITEN_LANE_ID)
    return payload


def _select_exact_card(
    cards: Iterable[Dict[str, Any]], external_id: str
) -> Optional[Dict[str, Any]]:
    """Return only an exact external_id match.

    Kaiten may return a non-empty result set that does not contain the requested
    card. Falling back to the first card would attach a lead to somebody else's
    card and suppress creation of the correct one.
    """
    expected = str(external_id)
    for card in cards:
        if str(card.get("external_id") or "") == expected:
            return card
    return None


async def find_card_by_external_id(external_id: str) -> Optional[Dict[str, Any]]:
    if not external_id or not is_enabled():
        return None
    try:
        async with httpx.AsyncClient(timeout=HTTP_TIMEOUT) as http:
            response = await http.get(
                f"{_api_base()}/cards",
                params={"external_id": external_id},
                headers=_headers(),
            )
        if 200 <= response.status_code < 300 and response.content:
            data = response.json()
            cards = data if isinstance(data, list) else data.get("cards", [])
            return _select_exact_card(cards, external_id)
        logger.debug(
            "kaiten lookup external_id=%s -> %d", external_id, response.status_code
        )
    except Exception as exc:  # noqa: BLE001
        logger.warning("kaiten lookup failed external_id=%s: %s", external_id, exc)
    return None


async def create_card(lead: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    if not is_enabled():
        return None

    external_id = str(lead.get("id") or "")
    existing = await find_card_by_external_id(external_id)
    if existing:
        logger.info(
            "kaiten card already exists lead=%s card_id=%s — skip create",
            external_id,
            existing.get("id"),
        )
        return existing

    payload = build_card_payload(lead)
    last_error: Optional[Exception] = None
    for attempt, delay in enumerate(RETRY_DELAYS, start=1):
        try:
            async with httpx.AsyncClient(timeout=HTTP_TIMEOUT) as http:
                response = await http.post(
                    f"{_api_base()}/cards", json=payload, headers=_headers()
                )
            if 200 <= response.status_code < 300:
                data = response.json() if response.content else {}
                logger.info(
                    "kaiten card created lead=%s card_id=%s",
                    external_id,
                    data.get("id"),
                )
                return data
            if 400 <= response.status_code < 500 and response.status_code != 429:
                logger.error(
                    "kaiten %d on lead=%s: %s",
                    response.status_code,
                    external_id,
                    response.text[:300],
                )
                return None
            logger.warning(
                "kaiten %d on lead=%s (attempt %d)",
                response.status_code,
                external_id,
                attempt,
            )
        except Exception as exc:  # noqa: BLE001
            last_error = exc
            logger.warning(
                "kaiten request failed lead=%s attempt=%d: %s",
                external_id,
                attempt,
                exc,
            )
        if attempt < len(RETRY_DELAYS):
            await asyncio.sleep(delay)

    logger.error(
        "kaiten failed after %d attempts lead=%s last_error=%s",
        len(RETRY_DELAYS),
        external_id,
        last_error,
    )
    return None


async def verify() -> Dict[str, Any]:
    if not (KAITEN_DOMAIN and KAITEN_API_TOKEN):
        return {
            "ok": False,
            "status": None,
            "detail": "KAITEN_DOMAIN/KAITEN_API_TOKEN не заданы",
        }
    try:
        async with httpx.AsyncClient(timeout=HTTP_TIMEOUT) as http:
            response = await http.get(
                f"{_api_base()}/users/current", headers=_headers()
            )
        if 200 <= response.status_code < 300:
            data = response.json() if response.content else {}
            who = (
                data.get("email")
                or data.get("username")
                or data.get("full_name")
                or data.get("id")
            )
            return {
                "ok": True,
                "status": response.status_code,
                "detail": f"авторизован как {who}",
            }
        hints = {
            401: "невалидный токен (перевыпусти в /profile/api-token)",
            403: "токен без доступа к workspace",
            404: "неверный KAITEN_DOMAIN",
        }
        return {
            "ok": False,
            "status": response.status_code,
            "detail": hints.get(response.status_code, response.text[:200]),
        }
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "status": None, "detail": f"сетевая ошибка: {exc}"}
