from collections import defaultdict
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.security import current_user
from app.models import Account, Transaction, Transfer
from app.services.ownership import get_owned

router = APIRouter(tags=["accounts"])


def _balances(db: Session, user) -> list[dict]:
    accounts = db.scalars(select(Account).where(Account.user_id == user.id).order_by(Account.name)).all()
    flows: dict[int, Decimal] = defaultdict(Decimal)
    for acc_id, kind, total in db.execute(
        select(Transaction.account_id, Transaction.kind, func.sum(Transaction.amount))
        .where(Transaction.user_id == user.id, Transaction.account_id.is_not(None))
        .group_by(Transaction.account_id, Transaction.kind)
    ):
        flows[acc_id] += total if kind == "income" else -total
    for from_id, total in db.execute(select(Transfer.from_account_id, func.sum(Transfer.amount))
                                     .where(Transfer.user_id == user.id).group_by(Transfer.from_account_id)):
        flows[from_id] -= total
    for to_id, total in db.execute(select(Transfer.to_account_id, func.sum(Transfer.amount))
                                   .where(Transfer.user_id == user.id).group_by(Transfer.to_account_id)):
        flows[to_id] += total
    return [{"id": a.id, "name": a.name, "type": a.type, "currency": a.currency,
             "balance": a.opening_balance + flows[a.id]} for a in accounts]


@router.get("/accounts/balances")
def balances(db: Session = Depends(get_db), user=Depends(current_user)):
    rows = _balances(db, user)
    net: dict[str, Decimal] = defaultdict(Decimal)
    for r in rows:
        # credit cards hold debt: their balance is already negative when spent, so a plain sum is net worth
        net[r["currency"]] += r["balance"]
    return {"accounts": rows, "net_worth_by_currency": dict(net)}


from app.schemas import TransferIn, TransferOut  # noqa: E402


def _check(db, user, body: TransferIn):
    if body.from_account_id == body.to_account_id:
        raise HTTPException(422, "Choose two different accounts")
    a = get_owned(db, Account, body.from_account_id, user.id)
    b = get_owned(db, Account, body.to_account_id, user.id)
    if a.currency != b.currency:
        raise HTTPException(422, "Transfers between different currencies are not supported")


@router.get("/transfers", response_model=list[TransferOut])
def list_transfers(db: Session = Depends(get_db), user=Depends(current_user)):
    return db.scalars(select(Transfer).where(Transfer.user_id == user.id)
                      .order_by(Transfer.date.desc(), Transfer.id.desc())).all()


@router.post("/transfers", response_model=TransferOut, status_code=201)
def create_transfer(body: TransferIn, db: Session = Depends(get_db), user=Depends(current_user)):
    _check(db, user, body)
    t = Transfer(user_id=user.id, **body.model_dump())
    db.add(t)
    db.commit()
    return t


@router.delete("/transfers/{tid}", status_code=204)
def delete_transfer(tid: int, db: Session = Depends(get_db), user=Depends(current_user)):
    db.delete(get_owned(db, Transfer, tid, user.id))
    db.commit()
