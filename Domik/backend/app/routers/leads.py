from datetime import datetime, timedelta

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from sqlalchemy.orm import Session

from ..db import get_db
from ..models import BlockedDate, LandingContent, Lead
from ..schemas import LeadIn, LeadOut, LeadStatusUpdate
from ..security import get_current_admin
from ..services.notifications import notify_new_lead

DATE_FMT = "%Y-%m-%d"


def _bookings_open(db: Session) -> bool:
    row = db.query(LandingContent).filter(LandingContent.key == "bookings.open").first()
    value = (row.value if row else "true").strip().lower()
    return value not in {"false", "0", "no", "off"}


def _check_dates_available(db: Session, date_from: str | None, date_to: str | None) -> None:
    if not date_from or not date_to:
        return
    try:
        a = datetime.strptime(date_from, DATE_FMT).date()
        b = datetime.strptime(date_to, DATE_FMT).date()
    except Exception:
        return
    if b < a:
        a, b = b, a
    blocked_days = {
        d.day for d in db.query(BlockedDate).filter(BlockedDate.day >= a, BlockedDate.day <= b).all()
    }
    if blocked_days:
        raise HTTPException(status_code=400, detail="Выбранные даты недоступны для бронирования.")
    overlap = (
        db.query(Lead)
        .filter(Lead.status.in_(["new", "in_progress", "confirmed"]))
        .filter(Lead.date_from.isnot(None), Lead.date_to.isnot(None))
        .all()
    )
    for l in overlap:
        try:
            la = datetime.strptime(l.date_from, DATE_FMT).date()
            lb = datetime.strptime(l.date_to, DATE_FMT).date()
        except Exception:
            continue
        if lb < la:
            la, lb = lb, la
        if not (b < la or a > lb):
            raise HTTPException(status_code=400, detail="На эти даты уже есть заявка.")

router = APIRouter(prefix="/api/leads", tags=["leads"])


@router.post("", response_model=LeadOut)
async def create_lead(data: LeadIn, background: BackgroundTasks, db: Session = Depends(get_db)):
    if not _bookings_open(db):
        raise HTTPException(status_code=400, detail="Бронирование временно закрыто.")
    _check_dates_available(db, data.date_from, data.date_to)
    lead = Lead(**data.model_dump())
    db.add(lead)
    db.commit()
    db.refresh(lead)
    background.add_task(_notify_task, lead.id)
    return lead


async def _notify_task(lead_id: int):
    from ..db import SessionLocal
    db = SessionLocal()
    try:
        lead = db.query(Lead).get(lead_id)
        if lead:
            await notify_new_lead(lead)
    finally:
        db.close()


@router.get("", response_model=list[LeadOut])
def list_leads(db: Session = Depends(get_db), _=Depends(get_current_admin)):
    return db.query(Lead).order_by(Lead.created_at.desc()).all()


@router.patch("/{lead_id}", response_model=LeadOut)
def update_status(
    lead_id: int,
    data: LeadStatusUpdate,
    db: Session = Depends(get_db),
    _=Depends(get_current_admin),
):
    lead = db.query(Lead).get(lead_id)
    if not lead:
        raise HTTPException(status_code=404, detail="Заявка не найдена")
    lead.status = data.status
    db.commit()
    db.refresh(lead)
    return lead


@router.delete("/{lead_id}")
def delete_lead(lead_id: int, db: Session = Depends(get_db), _=Depends(get_current_admin)):
    lead = db.query(Lead).get(lead_id)
    if not lead:
        raise HTTPException(status_code=404, detail="Заявка не найдена")
    db.delete(lead)
    db.commit()
    return {"ok": True}
