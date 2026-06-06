"""
Интеграция с Kaiten CRM
=======================

ЧТО ДЕЛАЕТ
----------
На каждый успешно прошедший валидацию лид создаёт карточку в Kaiten в колонке
«Новая» доски Lead Pipeline. Лид при этом уже сохранён в MongoDB — Kaiten это
только «рабочая поверхность», а не источник истины (см. docs/KAITEN_SETUP.md §1).

ОТ ЧЕГО ЗАВИСИТ (цепочка вызова — важно для junior'а)
-----------------------------------------------------
    .env (KAITEN_*)                — конфиг (см. backend/.env.example)
        │  читается при импорте модуля
        ▼
    is_enabled()                   — True только если заданы 4 переменные
        ▲
        │  проверяет
    server.py · deliver_to_crm()   — фоновая задача после записи лида в Mongo
        │  вызывает
        ▼
    create_card(lead)              — этот модуль; POST в Kaiten REST API
        │  использует
        ▼
    Kaiten API  https://<domain>/api/latest/cards

ВАЖНО:
- Если хотя бы одна из 4 переменных пуста → is_enabled() = False → модуль no-op
  (ничего не делает, ошибок не кидает). Так задумано: интеграция опциональна.
- Ошибка Kaiten НЕ блокирует ответ пользователю. Лид уже в Mongo и виден в
  /admin/leads; падение Kaiten только пишется в лог `mspshield.kaiten` и в
  метрику crm_kaiten_error_total (см. server.py · inc_crm).

КОНФИГ (через переменные окружения, см. backend/.env.example)
-------------------------------------------------------------
- KAITEN_DOMAIN     — поддомен `<workspace>.kaiten.ru` (можно с https://)
- KAITEN_API_TOKEN  — Bearer-токен (Профиль → API → Создать токен)
- KAITEN_BOARD_ID   — id доски Lead Pipeline (выводит scripts/kaiten_bootstrap.py)
- KAITEN_COLUMN_ID  — id колонки «Новая» (там же)
- KAITEN_LANE_ID    — опционально: id дорожки (если в доске несколько дорожек)

ИДЕМПОТЕНТНОСТЬ
---------------
В Kaiten у карточки есть поле `external_id`. Мы пишем туда UUID лида из Mongo.
Перед созданием карточки модуль проверяет, нет ли уже карточки с таким
external_id (GET /cards?external_id=...). Если есть — вторую НЕ создаём.
Это защищает от:
  - двойного клика «Отправить» на лендинге;
  - повторной фоновой доставки при рестарте backend в момент обработки лида.
Если проверка существования по какой-то причине не сработала (сеть/таймаут),
мы НЕ блокируем создание — лучше дубль карточки, чем потерянный лид.
"""
from __future__ import annotations

import asyncio
import logging
import os
from typing import Any, Dict, List, Optional

import httpx

logger = logging.getLogger("mspshield.kaiten")

# ── Конфиг читается один раз при импорте модуля. ───────────────────────────
# ВАЖНО: после правки backend/.env нужно ПЕРЕЗАПУСТИТЬ backend, иначе значения
# останутся старыми (Python не перечитывает окружение на лету).
KAITEN_DOMAIN = os.environ.get("KAITEN_DOMAIN", "").strip().rstrip("/")
KAITEN_API_TOKEN = os.environ.get("KAITEN_API_TOKEN", "").strip()
KAITEN_BOARD_ID = os.environ.get("KAITEN_BOARD_ID", "").strip()
KAITEN_COLUMN_ID = os.environ.get("KAITEN_COLUMN_ID", "").strip()
KAITEN_LANE_ID = os.environ.get("KAITEN_LANE_ID", "").strip()

# Backoff между попытками: 1s → 4s → 16s, итого ~21 сек на 3 попытки.
RETRY_DELAYS = (1, 4, 16)
HTTP_TIMEOUT = 10.0


def is_enabled() -> bool:
    """Интеграция активна только когда заданы все 4 обязательные переменные.

    Используется в server.py · deliver_to_crm() и в GET /api/integrations/status.
    KAITEN_LANE_ID не обязателен — дорожка опциональна.
    """
    return bool(
        KAITEN_DOMAIN
        and KAITEN_API_TOKEN
        and KAITEN_BOARD_ID
        and KAITEN_COLUMN_ID
    )


def _api_base() -> str:
    """Базовый URL Kaiten REST API: https://<domain>/api/latest."""
    domain = KAITEN_DOMAIN
    if "://" not in domain:
        domain = f"https://{domain}"
    return f"{domain}/api/latest"


def _headers() -> Dict[str, str]:
    """Заголовки авторизации Kaiten (Bearer-токен)."""
    return {
        "Authorization": f"Bearer {KAITEN_API_TOKEN}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }


def _as_int(value: str) -> Any:
    """Kaiten ждёт board_id/column_id как integer. Если в .env число строкой —
    приводим к int; иначе оставляем как есть (на случай нестандартных id)."""
    return int(value) if value.isdigit() else value


def _format_description(lead: Dict[str, Any]) -> str:
    """Собирает markdown-описание карточки из полей лида.

    Точная схема того, что увидит менеджер в карточке — см. KAITEN_SETUP.md §5.2.
    Пустые поля пропускаем, чтобы не засорять карточку «None».
    """
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
    """Формирует JSON-тело запроса POST /cards.

    Контракт Kaiten API (developers.kaiten.ru/cards/create-new-card):
      - title       — required (строка);
      - board_id    — required (integer);
      - column_id   — id колонки, integer | null;
      - lane_id     — id дорожки, integer | null (опционально);
      - external_id — наш внешний id (UUID лида) для идемпотентности, string | null.
    """
    title = f"[{lead.get('tariff', 'undecided')}] {lead.get('company', '')} · {lead.get('name', '')}".strip()
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


async def find_card_by_external_id(external_id: str) -> Optional[Dict[str, Any]]:
    """Ищет карточку по external_id (UUID лида). Нужна для идемпотентности.

    Возвращает первую найденную карточку или None. При сетевой ошибке/таймауте
    возвращает None и НЕ роняет вызывающий код — тогда create_card просто создаст
    карточку (риск дубля приемлемее, чем потеря лида).
    """
    if not external_id or not is_enabled():
        return None
    url = f"{_api_base()}/cards"
    try:
        async with httpx.AsyncClient(timeout=HTTP_TIMEOUT) as http:
            r = await http.get(url, params={"external_id": external_id}, headers=_headers())
        if 200 <= r.status_code < 300 and r.content:
            data = r.json()
            cards: List[Dict[str, Any]] = data if isinstance(data, list) else data.get("cards", [])
            # Подстраховка: Kaiten может вернуть карточки с похожим, но не равным
            # external_id — фильтруем строгим сравнением.
            for c in cards:
                if str(c.get("external_id") or "") == str(external_id):
                    return c
            return cards[0] if cards else None
        logger.debug("kaiten lookup external_id=%s -> %d", external_id, r.status_code)
    except Exception as exc:  # noqa: BLE001
        logger.warning("kaiten lookup failed external_id=%s: %s", external_id, exc)
    return None


async def create_card(lead: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Создаёт карточку в Kaiten за лидом. Возвращает ответ Kaiten или None.

    Поведение:
      1. Если интеграция выключена — None (no-op).
      2. Идемпотентность: если карточка с таким external_id уже есть — возвращаем
         её и НЕ создаём дубль.
      3. POST /cards с ретраями (1→4→16с) на 5xx/429/сетевые ошибки. На 4xx
         (кроме 429) ретрай бессмыслен — выходим сразу.
    """
    if not is_enabled():
        return None

    external_id = str(lead.get("id") or "")

    # (2) Идемпотентность — не плодим дубли на повторных доставках/двойном клике.
    existing = await find_card_by_external_id(external_id)
    if existing:
        logger.info(
            "kaiten card already exists lead=%s card_id=%s — skip create",
            external_id,
            existing.get("id"),
        )
        return existing

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
                # 4xx (кроме 429) — бессмысленно ретраить (401 токен, 404 board/column,
                # 422 кривой payload). Подробности — в r.text, смотри лог.
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


async def verify() -> Dict[str, Any]:
    """Диагностика связки domain+token БЕЗ создания карточки.

    Дёргает GET /users/current. Используется:
      - в scripts/kaiten_bootstrap.py (проверка перед бутстрапом);
      - вручную для отладки «kaiten:error».

    Возвращает словарь {ok, status, detail} — без утечки самого токена.
    Расшифровка статусов: 401 — токен невалиден; 404 — неверный KAITEN_DOMAIN
    (такого workspace нет); 403 — токен без доступа к workspace.
    """
    if not (KAITEN_DOMAIN and KAITEN_API_TOKEN):
        return {"ok": False, "status": None, "detail": "KAITEN_DOMAIN/KAITEN_API_TOKEN не заданы"}
    url = f"{_api_base()}/users/current"
    try:
        async with httpx.AsyncClient(timeout=HTTP_TIMEOUT) as http:
            r = await http.get(url, headers=_headers())
        if 200 <= r.status_code < 300:
            data = r.json() if r.content else {}
            who = data.get("email") or data.get("username") or data.get("full_name") or data.get("id")
            return {"ok": True, "status": r.status_code, "detail": f"авторизован как {who}"}
        hints = {
            401: "невалидный токен (перевыпусти в /profile/api-token)",
            403: "токен без доступа к workspace (выпусти из аккаунта-owner)",
            404: "неверный KAITEN_DOMAIN — такого workspace нет",
        }
        return {"ok": False, "status": r.status_code, "detail": hints.get(r.status_code, r.text[:200])}
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "status": None, "detail": f"сетевая ошибка: {exc}"}
