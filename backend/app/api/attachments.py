import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, Response, UploadFile
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.db import get_db
from app.core.security import current_user
from app.models import Attachment, Transaction
from app.schemas import AttachmentOut
from app.services.ownership import get_owned

router = APIRouter(tags=["attachments"])
ALLOWED = {"image/jpeg": ".jpg", "image/png": ".png", "image/webp": ".webp", "image/gif": ".gif", "application/pdf": ".pdf"}
MAGIC = {"image/jpeg": b"\xff\xd8\xff", "image/png": b"\x89PNG", "image/gif": b"GIF8", "application/pdf": b"%PDF"}
MAX_PER_TX = 5


def _dir() -> Path:
    p = Path(settings.upload_dir)
    p.mkdir(parents=True, exist_ok=True)
    return p


@router.get("/transactions/{tid}/attachments", response_model=list[AttachmentOut])
def list_attachments(tid: int, db: Session = Depends(get_db), user=Depends(current_user)):
    get_owned(db, Transaction, tid, user.id)
    return db.scalars(select(Attachment).where(Attachment.transaction_id == tid, Attachment.user_id == user.id)).all()


@router.post("/transactions/{tid}/attachments", response_model=AttachmentOut, status_code=201)
async def upload(tid: int, file: UploadFile = File(...), db: Session = Depends(get_db), user=Depends(current_user)):
    get_owned(db, Transaction, tid, user.id)
    ctype = file.content_type or ""
    if ctype not in ALLOWED:
        raise HTTPException(415, "Only JPG, PNG, WebP, GIF or PDF files are allowed")
    existing = len(db.scalars(select(Attachment.id).where(Attachment.transaction_id == tid)).all())
    if existing >= MAX_PER_TX:
        raise HTTPException(422, f"At most {MAX_PER_TX} attachments per transaction")
    data = await file.read(settings.max_upload_mb * 1024 * 1024 + 1)
    if len(data) > settings.max_upload_mb * 1024 * 1024:
        raise HTTPException(413, f"File is larger than {settings.max_upload_mb} MB")
    magic = MAGIC.get(ctype)
    if magic and not data.startswith(magic):
        raise HTTPException(415, "File content does not match its type")
    if ctype == "image/webp" and not (data[:4] == b"RIFF" and data[8:12] == b"WEBP"):
        raise HTTPException(415, "File content does not match its type")
    stored = uuid.uuid4().hex + ALLOWED[ctype]
    (_dir() / stored).write_bytes(data)
    a = Attachment(user_id=user.id, transaction_id=tid, filename=Path(file.filename or "file").name[:200],
                   content_type=ctype, size=len(data), stored_name=stored)
    db.add(a)
    db.commit()
    return a


@router.get("/attachments/{aid}")
def download(aid: int, db: Session = Depends(get_db), user=Depends(current_user)):
    a = get_owned(db, Attachment, aid, user.id)
    path = _dir() / a.stored_name
    if not path.is_file():
        raise HTTPException(404, "File missing")
    return Response(path.read_bytes(), media_type=a.content_type,
                    headers={"Content-Disposition": f'inline; filename="{a.filename}"', "X-Content-Type-Options": "nosniff"})


@router.delete("/attachments/{aid}", status_code=204)
def delete(aid: int, db: Session = Depends(get_db), user=Depends(current_user)):
    a = get_owned(db, Attachment, aid, user.id)
    (_dir() / a.stored_name).unlink(missing_ok=True)
    db.delete(a)
    db.commit()
