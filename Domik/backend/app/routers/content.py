from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..db import get_db
from ..models import LandingContent
from ..schemas import ContentBulk
from ..security import get_current_admin

router = APIRouter(prefix="/api/content", tags=["content"])


@router.get("")
def get_content(db: Session = Depends(get_db)):
    return {c.key: c.value for c in db.query(LandingContent).all()}


@router.put("")
def update_content(payload: ContentBulk, db: Session = Depends(get_db), _=Depends(get_current_admin)):
    existing = {c.key: c for c in db.query(LandingContent).all()}
    for item in payload.items:
        if item.key in existing:
            existing[item.key].value = item.value
        else:
            db.add(LandingContent(key=item.key, value=item.value))
    db.commit()
    return {"ok": True, "count": len(payload.items)}
