"""
MSPShield Backend API
Lead capture + admin dashboard for Managed Service Provider landing.
"""
from fastapi import FastAPI, APIRouter, HTTPException, Header, Depends, status
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import re
import logging
import uuid
import httpx
from pathlib import Path
from pydantic import BaseModel, Field, ConfigDict, EmailStr, field_validator
from typing import List, Optional
from datetime import datetime, timezone

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

client = AsyncIOMotorClient(MONGO_URL)
db = client[DB_NAME]

app = FastAPI(title="MSPShield API", version="3.1.0")
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
# Helpers
# ───────────────────────────────────────────────────────────
def require_admin(x_admin_token: Optional[str] = Header(default=None)) -> None:
    if not ADMIN_TOKEN:
        raise HTTPException(status_code=503, detail="Admin access not configured")
    if x_admin_token != ADMIN_TOKEN:
        raise HTTPException(status_code=401, detail="Unauthorized")


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
    return {"service": "MSPShield API", "version": "3.1.0"}


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
async def create_lead(payload: LeadCreate):
    lead_id = str(uuid.uuid4())
    doc = {
        "id": lead_id,
        **payload.model_dump(),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "status": "new",
    }
    await db.leads.insert_one(doc)
    logger.info("lead created: %s · %s · %s", doc["id"], doc["company"], doc["tariff"])
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
