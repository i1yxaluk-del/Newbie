import os
from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import FileResponse

from ..security import get_current_admin

router = APIRouter(prefix="/api/uploads", tags=["uploads"])

UPLOAD_ROOT = Path("data/uploads")
ALLOWED_EXT = {".jpg", ".jpeg", ".png", ".webp", ".gif"}


def _safe_scope(scope: str) -> str:
    safe = "".join(ch for ch in scope.lower() if ch.isalnum() or ch in {"-", "_"}).strip("-_")
    return safe or "general"


@router.post("")
async def upload_file(
    scope: str = "general",
    file: UploadFile = File(...),
    _=Depends(get_current_admin),
):
    ext = Path(file.filename or "").suffix.lower()
    if ext not in ALLOWED_EXT:
        raise HTTPException(status_code=400, detail="Unsupported file type")
    safe_scope = _safe_scope(scope)
    target_dir = UPLOAD_ROOT / safe_scope
    target_dir.mkdir(parents=True, exist_ok=True)
    name = f"{uuid4().hex}{ext}"
    target = target_dir / name
    content = await file.read()
    if len(content) > 12 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="File too large")
    target.write_bytes(content)
    return {"url": f"/uploads/{safe_scope}/{name}"}


@router.delete("/{scope}/{filename}")
def delete_file(scope: str, filename: str, _=Depends(get_current_admin)):
    safe_scope = _safe_scope(scope)
    safe_name = Path(filename).name
    target = UPLOAD_ROOT / safe_scope / safe_name
    if target.exists():
        target.unlink()
    return {"ok": True}


@router.get("/{scope}/{filename}")
def serve_upload(scope: str, filename: str):
    safe_scope = _safe_scope(scope)
    safe_name = Path(filename).name
    target = UPLOAD_ROOT / safe_scope / safe_name
    if not target.exists():
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(target)
