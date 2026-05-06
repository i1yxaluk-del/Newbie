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

Интеграции CRM:
- backend/integrations/kaiten.py    — Kaiten REST API (Bearer-токен).
- backend/integrations/webhook.py   — универсальный outbound webhook.
- backend/integrations/telegram.py  — Telegram-нотификации (как канал).

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
from integrations import kaiten, telegram, webhook  # noqa: E402

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
    smartcaptcha: bool


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

    if webhook.is_enabled():
        code = await webhook.send(lead_doc)
        inc_crm("webhook", "ok" if code and 200 <= code < 300 else "error")

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
        smartcaptcha=bool(SMARTCAPTCHA_SERVER_KEY),
    )


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
app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get("CORS_ORIGINS", "*").split(","),
    allow_methods=["*"],
    allow_headers=["*"],
)


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
