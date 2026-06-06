from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from sqlalchemy.orm import Session

from ..db import get_db
from ..models import Lead
from ..schemas import LeadIn, LeadOut, LeadStatusUpdate
from ..security import get_current_admin
from ..services.notifications import notify_new_lead

router = APIRouter(prefix="/api/leads", tags=["leads"])


@router.post("", response_model=LeadOut)
async def create_lead(data: LeadIn, background: BackgroundTasks, db: Session = Depends(get_db)):
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
