# Backend, MongoDB и устойчивая доставка заявки

FastAPI сопоставляет метод и путь с функцией. Pydantic проверяет форму данных. Middleware выполняет общие проверки, например обязательное согласие. MongoDB хранит заявку как документ. Индекс ускоряет поиск и может обеспечивать уникальность ключа.

Главная бизнес-гарантия: временный отказ Kaiten или почты не должен удалить уже принятую заявку. Поэтому запись заявки и запись задания outbox выполняются в локальной базе, а внешняя доставка идёт отдельно с повторами. Семантика at-least-once означает «как минимум один раз»: получатель обязан переживать повтор без второго бизнес-результата.

Проверяйте четыре состояния: HTTP-ответ, документ заявки, запись outbox и подтверждённый результат внешнего канала. Только их сочетание описывает полный путь.

## Как работать с материалом

Сначала прочитайте объяснение главы. Затем откройте перечисленные файлы в рабочем репозитории и сопоставьте текст с текущим кодом. Команды изменения выполняйте на учебной среде. Разделы ниже включены полностью, поэтому глава одновременно служит учебником и справочником.

## Материал проекта: `backend/secure_server.py`

<!-- SOURCE backend/secure_server.py 41d564f275a38a7f -->

```python
"""Production wrapper: strict consent, configurable CAPTCHA and durable delivery.

The existing server module remains usable for local development. Production
Docker images start this module so pilot safety policy cannot be skipped.
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
from datetime import datetime, timedelta, timezone
from typing import Any, Dict

import httpx
from starlette.responses import JSONResponse

import server

logger = logging.getLogger("mspshield.production")
app = server.app


class RequireExplicitConsentMiddleware:
    """Reject lead payloads unless consent is explicitly true.

    The body is replayed to FastAPI after validation so the normal Pydantic
    validation and route behavior remain unchanged.
    """

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http" or scope["method"] != "POST" or scope["path"] != "/api/leads":
            await self.app(scope, receive, send)
            return

        chunks = []
        more = True
        while more:
            message = await receive()
            chunks.append(message.get("body", b""))
            more = message.get("more_body", False)
        body = b"".join(chunks)
        try:
            payload = json.loads(body or b"{}")
        except (json.JSONDecodeError, UnicodeDecodeError):
            payload = {}
        if payload.get("consent") is not True:
            response = JSONResponse(
                {"detail": "consent_required"}, status_code=400
            )
            await response(scope, receive, send)
            return

        sent = False

        async def replay_receive():
            nonlocal sent
            if sent:
                return {"type": "http.request", "body": b"", "more_body": False}
            sent = True
            return {"type": "http.request", "body": body, "more_body": False}

        await self.app(scope, replay_receive, send)


app.add_middleware(RequireExplicitConsentMiddleware)


async def verify_smartcaptcha_strict(token: str | None, client_ip: str) -> bool:
    """Fail closed by default; SMARTCAPTCHA_FAIL_OPEN=true is an explicit choice."""
    if not server.SMARTCAPTCHA_SERVER_KEY:
        return True
    if not token:
        return False
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(
                server.SMARTCAPTCHA_VERIFY_URL,
                params={
                    "secret": server.SMARTCAPTCHA_SERVER_KEY,
                    "token": token,
                    "ip": client_ip,
                },
            )
        return response.json().get("status") == "ok"
    except Exception as exc:  # noqa: BLE001
        fail_open = os.environ.get("SMARTCAPTCHA_FAIL_OPEN", "false").lower() == "true"
        logger.error("SmartCaptcha verification unavailable; fail_open=%s: %s", fail_open, exc)
        return fail_open


server.verify_smartcaptcha = verify_smartcaptcha_strict


def _enabled_channels() -> list[str]:
    channels = []
    if server.telegram.is_enabled():
        channels.append("telegram")
    if server.email_integration.is_enabled():
        channels.append("email")
    if server.webhook.is_enabled():
        channels.append("webhook")
    if server.max_integration.is_alert_channel():
        channels.append("max")
    if server.kaiten.is_enabled():
        channels.append("kaiten")
    return channels


async def _send_channel(channel: str, lead: Dict[str, Any]) -> bool:
    if channel == "telegram":
        await server.telegram.send(lead)
        return True
    if channel == "email":
        await server.email_integration.send(lead)
        return True
    if channel == "webhook":
        code = await server.webhook.send(lead)
        return bool(code and 200 <= code < 300)
    if channel == "max":
        await server.max_integration.send(lead)
        return True
    if channel == "kaiten":
        card = await server.kaiten.create_card(lead)
        if not card or not card.get("id"):
            return False
        await server.db.leads.update_one(
            {"id": lead["id"]},
            {"$set": {"kaiten_card_id": card["id"]}},
        )
        return True
    return True


async def _process_delivery(lead_id: str) -> None:
    job = await server.db.crm_outbox.find_one({"lead_id": lead_id})
    if not job:
        return
    pending = list(job.get("pending") or [])
    failures: Dict[str, str] = {}
    for channel in pending:
        try:
            if await _send_channel(channel, job["payload"]):
                await server.db.crm_outbox.update_one(
                    {"lead_id": lead_id}, {"$pull": {"pending": channel}}
                )
                server.inc_crm(channel, "ok")
            else:
                failures[channel] = "delivery returned false"
                server.inc_crm(channel, "error")
        except Exception as exc:  # noqa: BLE001
            failures[channel] = str(exc)[:300]
            server.inc_crm(channel, "error")

    current = await server.db.crm_outbox.find_one({"lead_id": lead_id})
    if current and not current.get("pending"):
        await server.db.crm_outbox.delete_one({"lead_id": lead_id})
        return
    attempts = int((current or job).get("attempts", 0)) + 1
    delay = min(3600, 30 * (2 ** min(attempts, 7)))
    await server.db.crm_outbox.update_one(
        {"lead_id": lead_id},
        {"$set": {
            "attempts": attempts,
            "last_errors": failures,
            "next_retry_at": datetime.now(timezone.utc) + timedelta(seconds=delay),
            "updated_at": datetime.now(timezone.utc),
        }},
    )


async def durable_deliver_to_crm(lead: Dict[str, Any]) -> None:
    channels = _enabled_channels()
    if not channels:
        return
    now = datetime.now(timezone.utc)
    await server.db.crm_outbox.update_one(
        {"lead_id": lead["id"]},
        {"$setOnInsert": {
            "lead_id": lead["id"],
            "payload": lead,
            "pending": channels,
            "attempts": 0,
            "created_at": now,
            "next_retry_at": now,
        }},
        upsert=True,
    )
    await _process_delivery(lead["id"])


server.deliver_to_crm = durable_deliver_to_crm


async def _outbox_worker() -> None:
    while True:
        now = datetime.now(timezone.utc)
        cursor = server.db.crm_outbox.find(
            {"next_retry_at": {"$lte": now}}, {"lead_id": 1}
        ).limit(20)
        async for job in cursor:
            await _process_delivery(job["lead_id"])
        await asyncio.sleep(30)


@app.on_event("startup")
async def _start_outbox_worker() -> None:
    await server.db.crm_outbox.create_index("lead_id", unique=True)
    await server.db.crm_outbox.create_index("next_retry_at")
    app.state.outbox_task = asyncio.create_task(_outbox_worker())


@app.on_event("shutdown")
async def _stop_outbox_worker() -> None:
    task = getattr(app.state, "outbox_task", None)
    if task:
        task.cancel()

```

## Материал проекта: `backend/server.py`

<!-- SOURCE backend/server.py bf2fe520a741eb88 -->

```python
"""
MSPShield Backend API
=====================

Лендинг + админка для MSPShield (FastAPI + Motor/MongoDB).

Эндпоинты:
- POST /api/leads               — приём заявки с лендинга (rate-limit, honeypot,
                                  consent 152-ФЗ, опциональная SmartCaptcha).
- POST /api/admin/login         — обмен ADMIN_TOKEN на JWT (24 ч).
- GET  /api/leads               — список заявок (X-Admin-Token ИЛИ Bearer JWT).
- PATCH /api/leads/{id}/status  — смена статуса.
- GET  /api/stats               — агрегаты для дашборда.
- GET  /api/leads.csv           — выгрузка в CSV.
- GET  /api/health              — liveness + DB-проба.
- GET  /metrics                 — Prometheus.

Интеграции CRM и мессенджеры:
- backend/integrations/kaiten.py    — Kaiten REST API (Bearer-токен).
- backend/integrations/webhook.py   — универсальный outbound webhook.
- backend/integrations/telegram.py  — Telegram-нотификации (как канал).
- backend/integrations/max.py       — MAX Bot API (алерты + входящие лиды).

Интеграции вызываются через `BackgroundTasks` — пользователь получает 201
сразу, не дожидаясь сетевых вызовов.
"""
from __future__ import annotations

import csv
import io
import logging
import os
import re
import time
import uuid
from collections import defaultdict, deque
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Deque, Dict, List, Optional

import httpx
from dotenv import load_dotenv
from fastapi import (
    APIRouter,
    BackgroundTasks,
    FastAPI,
    HTTPException,
    Query,
    Request,
    status,
)
from fastapi.responses import StreamingResponse
from motor.motor_asyncio import AsyncIOMotorClient
from pydantic import BaseModel, ConfigDict, Field, field_validator
from starlette.middleware.cors import CORSMiddleware
from starlette.middleware.gzip import GZipMiddleware
from starlette.responses import PlainTextResponse, Response

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / ".env")

# Импорт интеграций ПОСЛЕ load_dotenv — они читают env на module level.
from auth import (  # noqa: E402
    AdminDep,
    JWT_TTL_SECONDS,
    _admin_token,
    issue_admin_jwt,
)
from integrations import (  # noqa: E402
    alertmanager,
    email as email_integration,
    kaiten,
    max as max_integration,
    telegram,
    webhook,
)

# ─── Config ────────────────────────────────────────────────
MONGO_URL = os.environ["MONGO_URL"]
DB_NAME = os.environ["DB_NAME"]

RATE_LIMIT_PER_MIN = int(os.environ.get("RATE_LIMIT_PER_MIN", "10"))
RATE_LIMIT_WINDOW_SEC = int(os.environ.get("RATE_LIMIT_WINDOW_SEC", "60"))

SMARTCAPTCHA_SERVER_KEY = os.environ.get("SMARTCAPTCHA_SERVER_KEY", "")
SMARTCAPTCHA_VERIFY_URL = os.environ.get(
    "SMARTCAPTCHA_VERIFY_URL",
    "https://smartcaptcha.yandexcloud.net/validate",
)

client = AsyncIOMotorClient(MONGO_URL)
db = client[DB_NAME]

app = FastAPI(title="MSPShield API", version="4.5.0")
api_router = APIRouter(prefix="/api")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("mspshield")

# ─── Models ────────────────────────────────────────────────
SERVERS_OPTIONS = {"1-3", "4-10", "11-30", "30+"}
TARIFF_OPTIONS = {"bronze", "silver", "gold", "undecided"}
STATUS_OPTIONS = {"new", "contacted", "qualified", "won", "lost"}


class LeadCreate(BaseModel):
    model_config = ConfigDict(extra="ignore", str_strip_whitespace=True)

    name: str = Field(min_length=2, max_length=80)
    company: str = Field(min_length=2, max_length=120)
    contact: str = Field(min_length=3, max_length=80)
    email: Optional[str] = Field(default=None, max_length=120)
    servers: str
    tariff: Optional[str] = "undecided"
    message: Optional[str] = Field(default="", max_length=1500)
    source: Optional[str] = Field(default="landing", max_length=40)
    downtime_loss: Optional[str] = None
    consent: Optional[bool] = None
    website: Optional[str] = Field(default=None, max_length=200)  # honeypot
    smartcaptcha_token: Optional[str] = Field(default=None, max_length=2048)

    @field_validator("servers")
    @classmethod
    def _v_servers(cls, v: str) -> str:
        if v not in SERVERS_OPTIONS:
            raise ValueError(f"servers must be one of {SERVERS_OPTIONS}")
        return v

    @field_validator("tariff")
    @classmethod
    def _v_tariff(cls, v: Optional[str]) -> str:
        v = (v or "undecided").lower()
        if v not in TARIFF_OPTIONS:
            v = "undecided"
        return v

    @field_validator("email")
    @classmethod
    def _v_email(cls, v: Optional[str]) -> Optional[str]:
        if not v:
            return None
        if not re.match(r"^[^\s@]+@[^\s@]+\.[^\s@]+$", v):
            raise ValueError("invalid email")
        return v.lower()


class Lead(BaseModel):
    id: str
    name: str
    company: str
    contact: str
    email: Optional[str] = None
    servers: str
    tariff: str
    message: str = ""
    source: str = "landing"
    downtime_loss: Optional[str] = None
    created_at: str
    status: str = "new"
    kaiten_card_id: Optional[int] = None
    kaiten_card_url: Optional[str] = None


class LeadCreatedResponse(BaseModel):
    ok: bool = True
    id: str


class StatsResponse(BaseModel):
    total_leads: int
    leads_today: int
    by_tariff: Dict[str, int]
    by_status: Dict[str, int]


class AdminLoginRequest(BaseModel):
    password: str = Field(min_length=1, max_length=512)


class AdminLoginResponse(BaseModel):
    token: str
    expires_at: int


class IntegrationsStatus(BaseModel):
    kaiten: bool
    telegram: bool
    webhook: bool
    max: bool
    max_alert_channel: bool
    max_bot_username: Optional[str] = None
    smartcaptcha: bool
    alertmanager: bool = False


# ─── Metrics (Prometheus, optional) ────────────────────────
try:
    from prometheus_client import CONTENT_TYPE_LATEST, Counter, generate_latest

    _METRICS_ENABLED = True
    LEADS_TOTAL = Counter(
        "mspshield_leads_total",
        "Total leads accepted",
        ("tariff", "source"),
    )
    LEADS_REJECTED = Counter(
        "mspshield_leads_rejected_total",
        "Leads rejected before persistence",
        ("reason",),
    )
    CRM_DELIVERIES = Counter(
        "mspshield_crm_deliveries_total",
        "CRM delivery attempts",
        ("integration", "result"),
    )
except Exception:  # noqa: BLE001
    _METRICS_ENABLED = False


def inc_rejected(reason: str) -> None:
    if _METRICS_ENABLED:
        LEADS_REJECTED.labels(reason=reason).inc()


def inc_lead_accepted(tariff: str, source: str) -> None:
    if _METRICS_ENABLED:
        LEADS_TOTAL.labels(tariff=tariff, source=source).inc()


def inc_crm(integration: str, result: str) -> None:
    if _METRICS_ENABLED:
        CRM_DELIVERIES.labels(integration=integration, result=result).inc()


# ─── Rate limit (in-memory, per-IP sliding window) ─────────
_rate_buckets: Dict[str, Deque[float]] = defaultdict(deque)


def _client_ip(request: Request) -> str:
    xff = request.headers.get("x-forwarded-for")
    if xff:
        return xff.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def rate_limit_check(request: Request) -> None:
    ip = _client_ip(request)
    now = time.monotonic()
    bucket = _rate_buckets[ip]
    cutoff = now - RATE_LIMIT_WINDOW_SEC
    while bucket and bucket[0] < cutoff:
        bucket.popleft()
    if len(bucket) >= RATE_LIMIT_PER_MIN:
        inc_rejected("rate_limit")
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="too many requests",
            headers={"Retry-After": str(RATE_LIMIT_WINDOW_SEC)},
        )
    bucket.append(now)


# ─── Helpers ───────────────────────────────────────────────
async def verify_smartcaptcha(token: Optional[str], client_ip: str) -> bool:
    if not SMARTCAPTCHA_SERVER_KEY:
        return True
    if not token:
        return False
    try:
        async with httpx.AsyncClient(timeout=5.0) as http:
            r = await http.get(
                SMARTCAPTCHA_VERIFY_URL,
                params={"secret": SMARTCAPTCHA_SERVER_KEY, "token": token, "ip": client_ip},
            )
            data = r.json()
            return data.get("status") == "ok"
    except Exception as exc:  # noqa: BLE001
        logger.warning("smartcaptcha verify failed: %s", exc)
        return True  # fail-open on upstream error


async def deliver_to_crm(lead_doc: Dict[str, Any]) -> None:
    """Background task: пробуем все настроенные каналы доставки лида."""
    if telegram.is_enabled():
        try:
            await telegram.send(lead_doc)
            inc_crm("telegram", "ok")
        except Exception:  # noqa: BLE001
            inc_crm("telegram", "error")

    if email_integration.is_enabled():
        try:
            await email_integration.send(lead_doc)
            inc_crm("email", "ok")
        except Exception:  # noqa: BLE001
            inc_crm("email", "error")

    if webhook.is_enabled():
        code = await webhook.send(lead_doc)
        inc_crm("webhook", "ok" if code and 200 <= code < 300 else "error")

    if max_integration.is_alert_channel():
        try:
            await max_integration.send(lead_doc)
            inc_crm("max", "ok")
        except Exception:  # noqa: BLE001
            inc_crm("max", "error")

    if kaiten.is_enabled():
        card = await kaiten.create_card(lead_doc)
        if card and card.get("id"):
            inc_crm("kaiten", "ok")
            card_url = None
            domain = kaiten.KAITEN_DOMAIN
            if domain:
                if "://" not in domain:
                    domain = f"https://{domain}"
                card_url = f"{domain.rstrip('/')}/space/{card.get('space_id', '')}/card/{card['id']}"
            await db.leads.update_one(
                {"id": lead_doc["id"]},
                {"$set": {"kaiten_card_id": card["id"], "kaiten_card_url": card_url}},
            )
        else:
            inc_crm("kaiten", "error")


# ─── MAX bot: state + handlers ─────────────────────────────
async def _max_get_session(user_id: int | str) -> Dict[str, Any]:
    """Простая state-machine на коллекции max_sessions."""
    doc = await db.max_sessions.find_one({"user_id": user_id}, {"_id": 0}) or {}
    return doc


async def _max_set_session(user_id: int | str, **fields: Any) -> None:
    await db.max_sessions.update_one(
        {"user_id": user_id},
        {"$set": {"user_id": user_id, "updated_at": datetime.now(timezone.utc).isoformat(), **fields}},
        upsert=True,
    )


async def _create_lead_from_max(
    user_id: Optional[int | str],
    chat_id: Optional[int | str],
    user_name: Optional[str],
    text: str,
    tariff_hint: Optional[str] = None,
) -> Dict[str, Any]:
    """Создаёт лид из входящего MAX-сообщения и доставляет его во все каналы."""
    lead_id = str(uuid.uuid4())
    doc = {
        "id": lead_id,
        "name": user_name or "MAX user",
        "company": "—",
        "contact": f"MAX user_id={user_id}",
        "email": None,
        "servers": "1-3",
        "tariff": (tariff_hint or "undecided").lower(),
        "message": (text or "").strip()[:1500],
        "source": "max_bot",
        "downtime_loss": None,
        "max_chat_id": chat_id,
        "max_user_id": user_id,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "status": "new",
    }
    await db.leads.insert_one(doc)
    logger.info("max bot lead created: %s · user=%s", lead_id, user_id)
    inc_lead_accepted(doc["tariff"], "max_bot")
    doc.pop("_id", None)
    await deliver_to_crm(doc)
    return doc


async def _handle_max_update(update: Dict[str, Any]) -> None:
    """
    Главный обработчик входящих событий MAX.
    Поддерживаемые update_type:
      - bot_started        → приветствие + меню
      - message_callback   → нажатие inline-кнопки
      - message_created    → произвольное входящее сообщение
    Любые другие — молча игнорируем.
    """
    info = max_integration.extract_chat_and_text(update)
    update_type = info["update_type"]
    chat_id = info["chat_id"]
    user_id = info["user_id"]
    user_name = info["user_name"]
    text = (info["text"] or "").strip()
    payload = info["payload"]

    if not (chat_id or user_id):
        logger.warning("max update without chat_id/user_id: %s", update_type)
        return

    target = {"chat_id": chat_id} if chat_id else {"user_id": user_id}

    if update_type == "bot_started":
        await max_integration.send_message(
            **target,
            text=max_integration.WELCOME_TEXT,
            buttons=max_integration.welcome_buttons(),
        )
        await _max_set_session(user_id or chat_id, step="welcome", name=user_name)
        return

    if update_type == "message_callback":
        if payload == "show_tariffs":
            await max_integration.send_message(
                **target,
                text=max_integration.TARIFFS_TEXT,
                buttons=max_integration.tariffs_buttons(),
            )
            return
        if payload == "back_to_welcome":
            await max_integration.send_message(
                **target,
                text=max_integration.WELCOME_TEXT,
                buttons=max_integration.welcome_buttons(),
            )
            return
        if payload in max_integration.TARIFF_DETAILS:
            await max_integration.send_message(
                **target,
                text=max_integration.TARIFF_DETAILS[payload],
                buttons=[
                    [{"type": "callback", "text": "📊 Рассчитать стоимость", "payload": "calc_start"}],
                    [{"type": "callback", "text": "← К списку тарифов", "payload": "show_tariffs"}],
                ],
            )
            await _max_set_session(
                user_id or chat_id,
                step="tariff_chosen",
                tariff_hint=payload.replace("tariff_", ""),
            )
            return
        if payload == "calc_start":
            await max_integration.send_message(
                **target,
                text=max_integration.CALC_TEXT,
            )
            await _max_set_session(user_id or chat_id, step="awaiting_calc_data")
            return
        # Неизвестный payload — отправляем приветствие.
        await max_integration.send_message(
            **target,
            text=max_integration.WELCOME_TEXT,
            buttons=max_integration.welcome_buttons(),
        )
        return

    if update_type == "message_created":
        if not text:
            return
        session = await _max_get_session(user_id or chat_id)
        step = session.get("step")
        tariff_hint = session.get("tariff_hint")
        if step in {"awaiting_calc_data", "welcome", "tariff_chosen", None}:
            # Любое содержательное сообщение трактуем как лид.
            await _create_lead_from_max(
                user_id=user_id,
                chat_id=chat_id,
                user_name=user_name,
                text=text,
                tariff_hint=tariff_hint,
            )
            await max_integration.send_message(
                **target,
                text=(
                    "Спасибо 🙏 Заявку получил. С вами свяжется наш инженер в "
                    "ближайшее рабочее окно. Если хотите ускорить — пришлите "
                    "ваш телефон или Telegram."
                ),
            )
            await _max_set_session(user_id or chat_id, step="lead_submitted")
            return


# ─── Routes ────────────────────────────────────────────────
@api_router.get("/")
async def root():
    return {"service": "MSPShield API", "version": app.version}


@api_router.get("/health")
async def health():
    try:
        await db.command("ping")
        return {"status": "ok", "db": "connected"}
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=503, detail=f"db: {exc}") from exc


@api_router.get("/integrations/status", response_model=IntegrationsStatus)
async def integrations_status():
    """Безопасный для лендинга статус интеграций (только bool, без секретов)."""
    return IntegrationsStatus(
        kaiten=kaiten.is_enabled(),
        telegram=telegram.is_enabled(),
        webhook=webhook.is_enabled(),
        max=max_integration.is_enabled(),
        max_alert_channel=max_integration.is_alert_channel(),
        max_bot_username=max_integration.MAX_BOT_USERNAME or None,
        smartcaptcha=bool(SMARTCAPTCHA_SERVER_KEY),
        alertmanager=alertmanager.is_enabled(),
    )


@api_router.post("/max/webhook", include_in_schema=False)
async def max_webhook(request: Request, background: BackgroundTasks):
    """
    Webhook-эндпоинт для MAX Bot API.

    MAX отправляет POST с объектом Update; должен вернуть 200 в течение 30 с.
    Реальная обработка идёт в BackgroundTasks, ответ — сразу.
    Защита по заголовку `X-Max-Bot-Api-Secret` (env `MAX_WEBHOOK_SECRET`).
    """
    if not max_integration.is_enabled():
        # Интеграция выключена — молча отвечаем 200, чтобы MAX не ретраил.
        return {"ok": True, "disabled": True}

    received = request.headers.get("X-Max-Bot-Api-Secret")
    if not max_integration.verify_webhook_secret(received):
        logger.warning("max webhook: bad secret from %s", _client_ip(request))
        # 200, чтобы не светить наличие/отсутствие бота наружу.
        return {"ok": True, "ignored": True}

    try:
        update = await request.json()
    except Exception:  # noqa: BLE001
        return {"ok": True, "ignored": True}

    if not isinstance(update, dict):
        return {"ok": True, "ignored": True}

    logger.info("max update: %s", update.get("update_type"))
    background.add_task(_handle_max_update, update)
    return {"ok": True}


@api_router.post("/alerts/alertmanager", include_in_schema=False)
async def alertmanager_webhook(request: Request, background: BackgroundTasks):
    """
    Webhook-приёмник для Prometheus Alertmanager.

    Alertmanager шлёт POST в формате v4 (см. integrations/alertmanager.py).
    Защита: заголовок `Authorization: Bearer <ALERTMANAGER_WEBHOOK_TOKEN>`.
    Fan-out: MAX (markdown) + Telegram (HTML), параметры через `ALERT_CHANNELS`.

    Возвращаем 200 быстро, обработку и отправку делаем в BackgroundTasks —
    Alertmanager ретраит при non-2xx или таймауте >10s.
    """
    received = request.headers.get("Authorization") or request.headers.get("X-Alertmanager-Token")
    if not alertmanager.verify_token(received):
        logger.warning("alertmanager webhook: bad token from %s", _client_ip(request))
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="bad_token")

    try:
        payload = await request.json()
    except Exception:  # noqa: BLE001
        return {"ok": True, "ignored": True}

    if not isinstance(payload, dict):
        return {"ok": True, "ignored": True}

    alerts = alertmanager.parse_alertmanager_payload(payload)
    logger.info(
        "alertmanager webhook: receiver=%s status=%s alerts=%d",
        payload.get("receiver"),
        payload.get("status"),
        len(alerts),
    )
    if not alerts:
        return {"ok": True, "alerts": 0}

    async def _dispatch_and_count() -> None:
        stats = await alertmanager.dispatch_alerts(alerts)
        for short, label in (("max", "max"), ("tg", "telegram")):
            for _ in range(stats.get(f"{short}_ok", 0)):
                inc_crm(f"alertmanager_{label}", "ok")
            for _ in range(stats.get(f"{short}_err", 0)):
                inc_crm(f"alertmanager_{label}", "error")

    background.add_task(_dispatch_and_count)
    return {"ok": True, "alerts": len(alerts)}


@api_router.post(
    "/leads",
    response_model=LeadCreatedResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_lead(
    payload: LeadCreate,
    request: Request,
    background: BackgroundTasks,
):
    rate_limit_check(request)

    # Honeypot — silent 200 (чтобы боты не подсказывали себе по reject'у).
    if payload.website:
        inc_rejected("honeypot")
        logger.info("honeypot triggered from %s", _client_ip(request))
        return LeadCreatedResponse(ok=True, id="00000000-0000-0000-0000-000000000000")

    # 152-ФЗ consent: явный false → reject.
    if payload.consent is False:
        inc_rejected("consent")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="consent_required",
        )

    if SMARTCAPTCHA_SERVER_KEY:
        ok = await verify_smartcaptcha(payload.smartcaptcha_token, _client_ip(request))
        if not ok:
            inc_rejected("captcha")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="captcha_failed",
            )

    lead_id = str(uuid.uuid4())
    data = payload.model_dump()
    data.pop("smartcaptcha_token", None)
    data.pop("website", None)
    doc = {
        "id": lead_id,
        **data,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "status": "new",
    }
    await db.leads.insert_one(doc)
    logger.info("lead created: %s · %s · %s", doc["id"], doc["company"], doc["tariff"])
    inc_lead_accepted(doc["tariff"], doc.get("source") or "landing")

    # Фоновая доставка во все включённые CRM-каналы.
    doc.pop("_id", None)
    background.add_task(deliver_to_crm, doc)

    return LeadCreatedResponse(ok=True, id=lead_id)


@api_router.post("/admin/login", response_model=AdminLoginResponse)
async def admin_login(payload: AdminLoginRequest):
    admin_token = _admin_token()
    if not admin_token:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Admin access not configured",
        )
    if payload.password != admin_token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid password")
    token, exp = issue_admin_jwt()
    logger.info("admin jwt issued ttl=%ds", JWT_TTL_SECONDS)
    return AdminLoginResponse(token=token, expires_at=exp)


@api_router.get("/admin/whoami")
async def admin_whoami(_: None = AdminDep):
    return {"role": "admin", "ok": True}


@api_router.get("/leads", response_model=List[Lead])
async def list_leads(
    _: None = AdminDep,
    limit: int = Query(200, ge=1, le=500),
    status_filter: Optional[str] = Query(None, alias="status"),
    tariff: Optional[str] = None,
):
    query: Dict[str, Any] = {}
    if status_filter and status_filter in STATUS_OPTIONS:
        query["status"] = status_filter
    if tariff and tariff in TARIFF_OPTIONS:
        query["tariff"] = tariff
    items = await db.leads.find(query, {"_id": 0}).sort("created_at", -1).to_list(limit)
    return items


@api_router.get("/leads.csv")
async def export_leads_csv(_: None = AdminDep):
    items = await db.leads.find({}, {"_id": 0}).sort("created_at", -1).to_list(5000)
    buf = io.StringIO()
    writer = csv.writer(buf, dialect="excel")
    writer.writerow(
        [
            "id",
            "created_at",
            "status",
            "tariff",
            "company",
            "name",
            "contact",
            "email",
            "servers",
            "source",
            "downtime_loss",
            "message",
            "kaiten_card_id",
        ]
    )
    for it in items:
        writer.writerow(
            [
                it.get("id", ""),
                it.get("created_at", ""),
                it.get("status", ""),
                it.get("tariff", ""),
                it.get("company", ""),
                it.get("name", ""),
                it.get("contact", ""),
                it.get("email") or "",
                it.get("servers", ""),
                it.get("source", ""),
                it.get("downtime_loss") or "",
                (it.get("message") or "").replace("\n", " "),
                it.get("kaiten_card_id") or "",
            ]
        )
    buf.seek(0)
    headers = {"Content-Disposition": 'attachment; filename="mspshield-leads.csv"'}
    return StreamingResponse(
        iter([buf.getvalue()]),
        media_type="text/csv; charset=utf-8",
        headers=headers,
    )


@api_router.get("/stats", response_model=StatsResponse)
async def stats(_: None = AdminDep):
    total = await db.leads.count_documents({})
    today = datetime.now(timezone.utc).date().isoformat()
    today_count = await db.leads.count_documents({"created_at": {"$regex": f"^{today}"}})

    pipeline = [{"$group": {"_id": "$tariff", "n": {"$sum": 1}}}]
    by_tariff_raw = await db.leads.aggregate(pipeline).to_list(20)
    by_tariff = {row["_id"] or "undecided": row["n"] for row in by_tariff_raw}

    status_pipeline = [{"$group": {"_id": "$status", "n": {"$sum": 1}}}]
    by_status_raw = await db.leads.aggregate(status_pipeline).to_list(20)
    by_status = {row["_id"] or "new": row["n"] for row in by_status_raw}

    return StatsResponse(
        total_leads=total,
        leads_today=today_count,
        by_tariff=by_tariff,
        by_status=by_status,
    )


@api_router.patch("/leads/{lead_id}/status")
async def update_lead_status(
    lead_id: str,
    new_status: str,
    _: None = AdminDep,
):
    if new_status not in STATUS_OPTIONS:
        raise HTTPException(status_code=400, detail="bad status")
    res = await db.leads.update_one({"id": lead_id}, {"$set": {"status": new_status}})
    if res.matched_count == 0:
        raise HTTPException(status_code=404, detail="lead not found")
    return {"ok": True}


# ─── Metrics endpoint ──────────────────────────────────────
@app.get("/metrics", include_in_schema=False)
async def metrics() -> Response:
    if not _METRICS_ENABLED:
        return PlainTextResponse("prometheus_client not installed\n", status_code=501)
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)


# ─── App wiring ────────────────────────────────────────────
app.include_router(api_router)

app.add_middleware(GZipMiddleware, minimum_size=512)


def _configure_cors() -> None:
    """
    Три режима, по приоритету:
    1. CORS_ALLOW_ORIGIN_REGEX задан → используем regex (удобно для LAN-dev).
    2. CORS_ORIGINS=* → wildcard БЕЗ credentials (по спецификации credentials
       несовместимы с '*'; иначе браузер режет preflight молча).
    3. CORS_ORIGINS=список через запятую → точный allow-list + credentials.
    """
    cors_regex = os.environ.get("CORS_ALLOW_ORIGIN_REGEX", "").strip()
    cors_origins_raw = os.environ.get("CORS_ORIGINS", "").strip()

    if cors_regex:
        app.add_middleware(
            CORSMiddleware,
            allow_origin_regex=cors_regex,
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
        logger.info("CORS: regex mode (%s)", cors_regex)
        return

    if cors_origins_raw == "*":
        app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=False,
            allow_methods=["*"],
            allow_headers=["*"],
        )
        logger.warning(
            "CORS: wildcard '*' включает all-origins без credentials. "
            "Для prod укажи конкретный список или regex."
        )
        return

    origins_default = "http://localhost:3000,http://127.0.0.1:3000"
    origins = [
        o.strip()
        for o in (cors_origins_raw or origins_default).split(",")
        if o.strip()
    ]
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    logger.info("CORS: explicit origins (%s)", origins)


_configure_cors()


@app.on_event("startup")
async def _on_startup() -> None:
    """Создаём индексы Mongo при старте — идемпотентно."""
    try:
        await db.leads.create_index("created_at")
        await db.leads.create_index("status")
        await db.leads.create_index("tariff")
        await db.leads.create_index([("status", 1), ("created_at", -1)])
        await db.leads.create_index("id", unique=True)
        logger.info("mongo indexes ensured")
    except Exception as exc:  # noqa: BLE001
        logger.warning("failed to ensure indexes: %s", exc)


@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()

```

## Материал проекта: `backend/integrations/kaiten.py`

<!-- SOURCE backend/integrations/kaiten.py 0eada71ab5a50cde -->

```python
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
        domain = "https://" + domain
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
    """Return only an exact external_id match."""
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

```

## Материал проекта: `backend/integrations/email.py`

<!-- SOURCE backend/integrations/email.py d2150e60ae225357 -->

```python
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

```

## Практический результат

Перескажите цепочку своими словами, выполните безопасную лабораторную работу и сохраните команды без секретов, фактический результат и способ отката. Если результат отличается от текста, остановитесь: сначала исправляется расхождение, а не подгоняется отчёт.
