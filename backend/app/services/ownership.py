from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models import Account, Category


def check_refs(db: Session, user_id: int, category_id=None, account_id=None):
    if category_id is not None:
        c = db.get(Category, category_id)
        if not c or c.user_id != user_id:
            raise HTTPException(422, "Invalid category")
    if account_id is not None:
        a = db.get(Account, account_id)
        if not a or a.user_id != user_id:
            raise HTTPException(422, "Invalid account")


def get_owned(db: Session, model, obj_id: int, user_id: int):
    obj = db.get(model, obj_id)
    if not obj or obj.user_id != user_id:
        raise HTTPException(404, "Not found")
    return obj
