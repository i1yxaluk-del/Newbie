from datetime import date, datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..db import get_db
from ..models import BlockedDate, Lead, LandingContent
from ..schemas import (
    BlockedDayIn,
    BlockedDayOut,
    BlockedDaysList,
    BlockedRangeIn,
    BookingsModeIn,
)
from ..security import get_current_admin

router = APIRouter(prefix="/api/calendar", tags=["calendar"])

DATE_FMT = "%Y-%m-%d"


def _parse_day(s: str) -> date:
    try:
        return datetime.strptime(s, DATE_FMT).date()
    except Exception:
        raise HTTPException(status_code=400, detail=f"Bad date: {s}")


def _daterange(a: date, b: date):
    cur = a
    while cur <= b:
        yield cur
        cur += timedelta(days=1)


def _content_value(db: Session, key: str, default: str = "") -> str:
    row = db.query(LandingContent).filter(LandingContent.key == key).first()
    return row.value if row and row.value is not None else default


def _set_content_value(db: Session, key: str, value: str) -> None:
    row = db.query(LandingContent).filter(LandingContent.key == key).first()
    if row:
        row.value = value
    else:
        db.add(LandingContent(key=key, value=value))


@router.get("/public")
def public_state(db: Session = Depends(get_db)):
    """Информация для публичной страницы: даты + статус приёма заявок."""
    today = date.today()
    horizon = today + timedelta(days=365)

    leads = db.query(Lead).filter(Lead.status.in_(["new", "in_progress", "confirmed"])).all()
    occupied = set()
    for l in leads:
        if not l.date_from or not l.date_to:
            continue
        try:
            a = datetime.strptime(l.date_from, DATE_FMT).date()
            b = datetime.strptime(l.date_to, DATE_FMT).date()
        except Exception:
            continue
        if b < a:
            a, b = b, a
        if a < today:
            a = today
        if b > horizon:
            b = horizon
        for d in _daterange(a, b):
            occupied.add(d.isoformat())

    blocked = {
        d.day.isoformat()
        for d in db.query(BlockedDate).filter(BlockedDate.day >= today).all()
    }

    open_value = _content_value(db, "bookings.open", "true").strip().lower()
    bookings_open = open_value not in {"false", "0", "no", "off"}

    return {
        "today": today.isoformat(),
        "bookings_open": bookings_open,
        "blocked_dates": sorted(blocked),
        "occupied_dates": sorted(occupied),
        "unavailable_dates": sorted(blocked | occupied),
    }


@router.get("/admin")
def admin_state(db: Session = Depends(get_db), _=Depends(get_current_admin)):
    today = date.today()
    leads = (
        db.query(Lead)
        .filter(Lead.status.in_(["new", "in_progress", "confirmed"]))
        .all()
    )
    occupied_map = {}
    for l in leads:
        if not l.date_from or not l.date_to:
            continue
        try:
            a = datetime.strptime(l.date_from, DATE_FMT).date()
            b = datetime.strptime(l.date_to, DATE_FMT).date()
        except Exception:
            continue
        if b < a:
            a, b = b, a
        for d in _daterange(a, b):
            occupied_map.setdefault(d.isoformat(), []).append(
                {"lead_id": l.id, "name": l.name, "status": l.status}
            )

    blocked = [
        BlockedDayOut(day=d.day.isoformat(), note=d.note)
        for d in db.query(BlockedDate).order_by(BlockedDate.day.asc()).all()
    ]

    open_value = _content_value(db, "bookings.open", "true").strip().lower()
    bookings_open = open_value not in {"false", "0", "no", "off"}
    closed_message = _content_value(db, "bookings.closed_message", "")

    return {
        "today": today.isoformat(),
        "bookings_open": bookings_open,
        "closed_message": closed_message,
        "blocked": [b.model_dump() for b in blocked],
        "occupied": occupied_map,
    }


@router.post("/block")
def block_day(payload: BlockedDayIn, db: Session = Depends(get_db), _=Depends(get_current_admin)):
    d = _parse_day(payload.day)
    existing = db.query(BlockedDate).filter(BlockedDate.day == d).first()
    if existing:
        existing.note = payload.note
    else:
        db.add(BlockedDate(day=d, note=payload.note))
    db.commit()
    return {"ok": True}


@router.post("/block-range")
def block_range(payload: BlockedRangeIn, db: Session = Depends(get_db), _=Depends(get_current_admin)):
    a = _parse_day(payload.date_from)
    b = _parse_day(payload.date_to)
    if b < a:
        a, b = b, a
    inserted = 0
    for d in _daterange(a, b):
        if not db.query(BlockedDate).filter(BlockedDate.day == d).first():
            db.add(BlockedDate(day=d, note=payload.note))
            inserted += 1
    db.commit()
    return {"ok": True, "blocked": inserted}


@router.post("/unblock")
def unblock_days(payload: BlockedDaysList, db: Session = Depends(get_db), _=Depends(get_current_admin)):
    removed = 0
    for s in payload.days:
        d = _parse_day(s)
        row = db.query(BlockedDate).filter(BlockedDate.day == d).first()
        if row:
            db.delete(row)
            removed += 1
    db.commit()
    return {"ok": True, "removed": removed}


@router.post("/bookings-mode")
def set_bookings_mode(payload: BookingsModeIn, db: Session = Depends(get_db), _=Depends(get_current_admin)):
    _set_content_value(db, "bookings.open", "true" if payload.open else "false")
    db.commit()
    return {"ok": True, "open": payload.open}
