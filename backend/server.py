"""
MSPShield Backend API
=====================

RU: Это backend лендинга и админки MSPShield. Отвечает за:
  1. POST /api/leads       — приём заявки с лендинга (rate-limit,
                             honeypot, consent 152-ФЗ, SmartCaptcha).
  2. GET  /api/leads       — список заявок для админки (X-Admin-Token).
  3. PATCH /api/leads/{id}/status — смена статуса (новый → связались → …).
  4. GET  /api/stats       — агрегаты для дашборда.
  5. GET  /metrics         — Prometheus scrape-эндпоинт.
  6. GET  /api/health      — liveness probe.

Секреты и конфиг — через .env (см. backend/.env.example).
База — MongoDB через Motor (async).

v4.1 security additions:
- Per-IP rate limiting on POST /api/leads
- Honeypot field `website` (bot trap)
- Required PD-consent (152-ФЗ)
- Optional Yandex SmartCaptcha verification
- Prometheus /metrics (requires prometheus_client)
"""
from __future__ import annotations

import logging
import os
import re
import time
import uuid
from collections import defaultdict, deque
from datetime import datetime, timezone
from pathlib import Path
from typing import Deque, Dict, List, Optional

import httpx
from dotenv import load_dotenv
from fastapi import APIRouter, Depends, FastAPI, Header, HTTPException, Request, status
from motor.motor_asyncio import AsyncIOMotorClient
from pydantic import BaseModel, ConfigDict, Field, field_validator
from starlette.middleware.cors import CORSMiddleware
from starlette.responses import PlainTextResponse, Response

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / ".env")

# ───────────────────────────────────────────────────────────
# Config
# ───────────────────────────────────────────────────────────
MONGO_URL = os.environ["MONGO_URL"]
DB_NAME = os.environ["DB_NAME"]
ADMIN_TOKEN = os.environ.get("ADMIN_TOKEN", "")
TG_BOT_TOKEN = os.environ.get("TG_BOT_TOKEN", "")
TG_CHAT_ID = os.environ.get("TG_CHAT_ID", "")

# Rate limit: default 10 lead-submissions per IP per 60s window.
RATE_LIMIT_PER_MIN = int(os.environ.get("RATE_LIMIT_PER_MIN", "10"))
RATE_LIMIT_WINDOW_SEC = int(os.environ.get("RATE_LIMIT_WINDOW_SEC", "60"))

# Optional: Yandex SmartCaptcha server-side verification.
SMARTCAPTCHA_SERVER_KEY = os.environ.get("SMARTCAPTCHA_SERVER_KEY", "")
SMARTCAPTCHA_VERIFY_URL = os.environ.get(
    "SMARTCAPTCHA_VERIFY_URL",
    "https://smartcaptcha.yandexcloud.net/validate",
)

client = AsyncIOMotorClient(MONGO_URL)
db = client[DB_NAME]

app = FastAPI(title="MSPShield API", version="4.2.0")
api_router = APIRouter(prefix="/api")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("mspshield")

# ───────────────────────────────────────────────────────────
# Models
# ───────────────────────────────────────────────────────────
SERVERS_OPTIONS = {"1-3", "4-10", "11-30", "30+"}
TARIFF_OPTIONS = {"bronze", "silver", "gold", "undecided"}


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
    downtime_loss: Optional[str] = None  # calculator result for CRM context
    # v4.1 additions
    consent: Optional[bool] = None  # PD consent (152-ФЗ). Required when non-legacy.
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


class LeadCreatedResponse(BaseModel):
    ok: bool = True
    id: str


class StatsResponse(BaseModel):
    total_leads: int
    leads_today: int
    by_tariff: dict


# ───────────────────────────────────────────────────────────
# Metrics (Prometheus, optional)
# ───────────────────────────────────────────────────────────
try:
    from prometheus_client import CONTENT_TYPE_LATEST, Counter, Histogram, generate_latest

    _METRICS_ENABLED = True
    LEADS_TOTAL = Counter(
        "mspshield_leads_total",
        "Total leads accepted",
        ("tariff", "source"),
    )
    LEADS_REJECTED = Counter(
        "mspshield_leads_rejected_total",
        "Leads rejected before persistence",
        ("reason",),  # honeypot | consent | rate_limit | captcha
    )
    API_LATENCY = Histogram(
        "mspshield_api_latency_seconds",
        "API latency by path",
        ("path", "method", "status"),
    )
except Exception:  # noqa: BLE001
    _METRICS_ENABLED = False

    def _rejected(_reason: str) -> None:
        return None


def inc_rejected(reason: str) -> None:
    if _METRICS_ENABLED:
        LEADS_REJECTED.labels(reason=reason).inc()


def inc_lead_accepted(tariff: str, source: str) -> None:
    if _METRICS_ENABLED:
        LEADS_TOTAL.labels(tariff=tariff, source=source).inc()


# ───────────────────────────────────────────────────────────
# Rate limit (in-memory, per-IP sliding window)
# ───────────────────────────────────────────────────────────
_rate_buckets: Dict[str, Deque[float]] = defaultdict(deque)


def _client_ip(request: Request) -> str:
    xff = request.headers.get("x-forwarded-for")
    if xff:
        return xff.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def rate_limit_check(request: Request) -> None:
    """Raise 429 if this IP exceeded the window. In-memory, per-process."""
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


# ───────────────────────────────────────────────────────────
# Helpers
# ───────────────────────────────────────────────────────────
def require_admin(x_admin_token: Optional[str] = Header(default=None)) -> None:
    if not ADMIN_TOKEN:
        raise HTTPException(status_code=503, detail="Admin access not configured")
    if x_admin_token != ADMIN_TOKEN:
        raise HTTPException(status_code=401, detail="Unauthorized")


async def verify_smartcaptcha(token: Optional[str], client_ip: str) -> bool:
    """Return True if captcha is disabled OR token is valid. False only on explicit rejection."""
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
        # Fail-open on upstream error to avoid blocking legit users when Yandex is down.
        return True


async def send_telegram(lead: dict) -> None:
    if not (TG_BOT_TOKEN and TG_CHAT_ID):
        return
    lines = [
        "<b>🛡 Новая заявка MSPShield</b>",
        f"<b>Имя:</b> {lead['name']}",
        f"<b>Компания:</b> {lead['company']}",
        f"<b>Контакт:</b> {lead['contact']}",
        f"<b>Email:</b> {lead.get('email') or '—'}",
        f"<b>Серверы:</b> {lead['servers']}",
        f"<b>Тариф:</b> {lead['tariff']}",
        f"<b>Потери/год:</b> {lead.get('downtime_loss') or '—'}",
        f"<b>Сообщение:</b> {lead.get('message') or '—'}",
        f"<b>Источник:</b> {lead.get('source')}",
    ]
    text = "\n".join(lines)
    url = f"https://api.telegram.org/bot{TG_BOT_TOKEN}/sendMessage"
    try:
        async with httpx.AsyncClient(timeout=8.0) as http:
            await http.post(
                url,
                json={"chat_id": TG_CHAT_ID, "text": text, "parse_mode": "HTML"},
            )
    except Exception as exc:  # noqa: BLE001
        logger.warning("telegram notify failed: %s", exc)


# ───────────────────────────────────────────────────────────
# Routes
# ───────────────────────────────────────────────────────────
@api_router.get("/")
async def root():
    return {"service": "MSPShield API", "version": "4.1.0"}


@api_router.get("/health")
async def health():
    try:
        await db.command("ping")
        return {"status": "ok", "db": "connected"}
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=503, detail=f"db: {exc}") from exc


@api_router.post(
    "/leads",
    response_model=LeadCreatedResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_lead(payload: LeadCreate, request: Request):
    # 1) Rate limit per IP.
    rate_limit_check(request)

    # 2) Honeypot — should be empty. If filled, accept silently (200) to not tip off bots,
    #    but don't persist.
    if payload.website:
        inc_rejected("honeypot")
        logger.info("honeypot triggered from %s", _client_ip(request))
        return LeadCreatedResponse(ok=True, id="00000000-0000-0000-0000-000000000000")

    # 3) Consent (152-ФЗ). Accept absence for legacy clients (older landing versions),
    #    but reject explicit false.
    if payload.consent is False:
        inc_rejected("consent")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="consent_required",
        )

    # 4) SmartCaptcha (optional).
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
    # Never persist sensitive transient fields.
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
    await send_telegram(doc)
    return LeadCreatedResponse(ok=True, id=lead_id)


@api_router.get("/leads", response_model=List[Lead])
async def list_leads(_: None = Depends(require_admin), limit: int = 200):
    limit = max(1, min(limit, 500))
    items = await db.leads.find({}, {"_id": 0}).sort("created_at", -1).to_list(limit)
    return items


@api_router.get("/stats", response_model=StatsResponse)
async def stats(_: None = Depends(require_admin)):
    total = await db.leads.count_documents({})
    today = datetime.now(timezone.utc).date().isoformat()
    today_count = await db.leads.count_documents({"created_at": {"$regex": f"^{today}"}})
    pipeline = [{"$group": {"_id": "$tariff", "n": {"$sum": 1}}}]
    by_tariff_raw = await db.leads.aggregate(pipeline).to_list(20)
    by_tariff = {row["_id"] or "undecided": row["n"] for row in by_tariff_raw}
    return StatsResponse(total_leads=total, leads_today=today_count, by_tariff=by_tariff)


@api_router.patch("/leads/{lead_id}/status")
async def update_lead_status(
    lead_id: str,
    new_status: str,
    _: None = Depends(require_admin),
):
    if new_status not in {"new", "contacted", "qualified", "won", "lost"}:
        raise HTTPException(status_code=400, detail="bad status")
    res = await db.leads.update_one({"id": lead_id}, {"$set": {"status": new_status}})
    if res.matched_count == 0:
        raise HTTPException(status_code=404, detail="lead not found")
    return {"ok": True}


# ───────────────────────────────────────────────────────────
# Metrics endpoint
# ───────────────────────────────────────────────────────────
@app.get("/metrics", include_in_schema=False)
async def metrics() -> Response:
    if not _METRICS_ENABLED:
        return PlainTextResponse("prometheus_client not installed\n", status_code=501)
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)


# ───────────────────────────────────────────────────────────
# App wiring
# ───────────────────────────────────────────────────────────
app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get("CORS_ORIGINS", "*").split(","),
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()
