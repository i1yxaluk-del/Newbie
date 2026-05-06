"""
Универсальный outbound webhook для произвольной CRM/no-code платформы
(n8n, Make, Zapier, Bitrix24 inbound webhook, Notion via integration, etc.)

Конфиг:
- CRM_WEBHOOK_URL    — куда POST'ить лид (полный JSON).
- CRM_WEBHOOK_TOKEN  — опциональный Bearer-токен в `Authorization`.

Если URL не задан — no-op.
"""
from __future__ import annotations

import logging
import os
from typing import Any, Dict, Optional

import httpx

logger = logging.getLogger("mspshield.webhook")

CRM_WEBHOOK_URL = os.environ.get("CRM_WEBHOOK_URL", "").strip()
CRM_WEBHOOK_TOKEN = os.environ.get("CRM_WEBHOOK_TOKEN", "").strip()


def is_enabled() -> bool:
    return bool(CRM_WEBHOOK_URL)


async def send(lead: Dict[str, Any]) -> Optional[int]:
    if not is_enabled():
        return None
    headers = {"Content-Type": "application/json"}
    if CRM_WEBHOOK_TOKEN:
        headers["Authorization"] = f"Bearer {CRM_WEBHOOK_TOKEN}"
    try:
        async with httpx.AsyncClient(timeout=8.0) as http:
            r = await http.post(CRM_WEBHOOK_URL, json=lead, headers=headers)
        if 200 <= r.status_code < 300:
            logger.info("webhook ok lead=%s status=%d", lead.get("id"), r.status_code)
        else:
            logger.warning(
                "webhook %d lead=%s body=%s",
                r.status_code,
                lead.get("id"),
                r.text[:200],
            )
        return r.status_code
    except Exception as exc:  # noqa: BLE001
        logger.warning("webhook failed lead=%s: %s", lead.get("id"), exc)
        return None
