import csv
import io
from datetime import date
from decimal import Decimal, InvalidOperation
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, Query, Response, UploadFile
from sqlalchemy import String, cast, func, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.db import get_db
from app.core.security import current_user
from app.models import Account, Attachment, Category, Transaction
from app.schemas import TransactionIn, TransactionOut, TransactionPage
from app.services.ownership import check_refs, get_owned

router = APIRouter(prefix="/transactions", tags=["transactions"])


def _filtered(user, from_, to, kind, category_id, account_id, q, tag):
    stmt = select(Transaction).where(Transaction.user_id == user.id)
    if from_:
        stmt = stmt.where(Transaction.date >= from_)
    if to:
        stmt = stmt.where(Transaction.date <= to)
    if kind:
        stmt = stmt.where(Transaction.kind == kind)
    if category_id:
        stmt = stmt.where(Transaction.category_id == category_id)
    if account_id:
        stmt = stmt.where(Transaction.account_id == account_id)
    if q:
        stmt = stmt.where(Transaction.note.ilike(f"%{q}%"))
    if tag:
        # JSON containment is portable enough via text match on the serialized list
        stmt = stmt.where(cast(Transaction.tags, String).ilike(f'%"{tag}"%'))
    return stmt


@router.get("", response_model=TransactionPage)
def list_transactions(
    from_: date | None = Query(None, alias="from"), to: date | None = None,
    kind: str | None = None, category_id: int | None = None, account_id: int | None = None,
    q: str | None = None, tag: str | None = None,
    page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=200),
    db: Session = Depends(get_db), user=Depends(current_user),
):
    stmt = _filtered(user, from_, to, kind, category_id, account_id, q, tag)
    total = db.scalar(select(func.count()).select_from(stmt.subquery()))
    items = db.scalars(
        stmt.order_by(Transaction.date.desc(), Transaction.id.desc()).offset((page - 1) * page_size).limit(page_size)
    ).unique().all()
    return TransactionPage(items=items, total=total, page=page, page_size=page_size)


@router.post("", response_model=TransactionOut, status_code=201)
def create(body: TransactionIn, db: Session = Depends(get_db), user=Depends(current_user)):
    check_refs(db, user.id, body.category_id, body.account_id)
    t = Transaction(user_id=user.id, **body.model_dump())
    db.add(t)
    db.commit()
    db.refresh(t)
    return t


@router.put("/{tid}", response_model=TransactionOut)
def update(tid: int, body: TransactionIn, db: Session = Depends(get_db), user=Depends(current_user)):
    t = get_owned(db, Transaction, tid, user.id)
    check_refs(db, user.id, body.category_id, body.account_id)
    for k, v in body.model_dump().items():
        setattr(t, k, v)
    db.commit()
    db.refresh(t)
    return t


@router.delete("/{tid}", status_code=204)
def delete(tid: int, db: Session = Depends(get_db), user=Depends(current_user)):
    t = get_owned(db, Transaction, tid, user.id)
    for a in db.scalars(select(Attachment).where(Attachment.transaction_id == t.id)):
        (Path(settings.upload_dir) / a.stored_name).unlink(missing_ok=True)
        db.delete(a)  # explicit: SQLite test DBs do not enforce ON DELETE CASCADE
    db.delete(t)
    db.commit()
    return Response(status_code=204)


@router.get("/export.csv")
def export_csv(
    from_: date | None = Query(None, alias="from"), to: date | None = None,
    db: Session = Depends(get_db), user=Depends(current_user),
):
    rows = db.scalars(_filtered(user, from_, to, None, None, None, None, None).order_by(Transaction.date)).unique().all()
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["date", "kind", "amount", "category", "account", "note", "tags"])
    for t in rows:
        w.writerow([t.date, t.kind, t.amount, t.category.name if t.category else "",
                    t.account.name if t.account else "", t.note or "", ";".join(t.tags or [])])
    return Response(buf.getvalue(), media_type="text/csv",
                    headers={"Content-Disposition": "attachment; filename=transactions.csv"})


@router.post("/import")
async def import_csv(file: UploadFile = File(...), db: Session = Depends(get_db), user=Depends(current_user)):
    """CSV columns: date, kind, amount, category, account, note, tags. Unknown categories/accounts are created."""
    text = (await file.read()).decode("utf-8-sig")
    cats = {c.name.lower(): c for c in db.scalars(select(Category).where(Category.user_id == user.id))}
    accs = {a.name.lower(): a for a in db.scalars(select(Account).where(Account.user_id == user.id))}
    created, errors = 0, []
    for i, row in enumerate(csv.DictReader(io.StringIO(text)), start=2):
        # Fixed messages per field: the user gets a clear reason and no exception text leaves the server.
        kind = (row.get("kind") or "expense").strip().lower()
        if kind not in ("expense", "income"):
            errors.append(f"line {i}: kind must be expense or income")
            continue
        try:
            amount = Decimal((row.get("amount") or "").strip())
        except InvalidOperation:
            amount = None
        if amount is None or not amount.is_finite() or amount <= 0:
            errors.append(f"line {i}: amount must be a positive number")
            continue
        try:
            d = date.fromisoformat((row.get("date") or "").strip())
        except ValueError:
            errors.append(f"line {i}: date must be YYYY-MM-DD")
            continue
        cname, aname = (row.get("category") or "").strip(), (row.get("account") or "").strip()
        cat = acc = None
        if cname:
            cat = cats.get(cname.lower())
            if not cat:
                cat = cats[cname.lower()] = Category(user_id=user.id, name=cname, kind=kind)
                db.add(cat)
        if aname:
            acc = accs.get(aname.lower())
            if not acc:
                acc = accs[aname.lower()] = Account(user_id=user.id, name=aname, currency=user.default_currency)
                db.add(acc)
        db.flush()
        tags = [t for t in (row.get("tags") or "").split(";") if t]
        db.add(Transaction(user_id=user.id, amount=amount, kind=kind, date=d, note=row.get("note") or None,
                           category_id=cat.id if cat else None, account_id=acc.id if acc else None, tags=tags))
        created += 1
    db.commit()
    if not created and errors:
        raise HTTPException(422, {"errors": errors[:20]})
    return {"created": created, "errors": errors[:20]}
