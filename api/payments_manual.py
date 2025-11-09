import os
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import text

from .db import get_db

router = APIRouter(prefix="/payments", tags=["payments"])

UPLOAD_DIR = "uploaded_proofs"
os.makedirs(UPLOAD_DIR, exist_ok=True)


class TelegramPhotoIn(BaseModel):
    telegram_id: int
    file_id: str
    caption: Optional[str] = None


@router.post("/telegram-photo")
async def telegram_photo(payload: TelegramPhotoIn, db: Session = Depends(get_db)):
    """
    מקבל צילום מסך מתשלום בטלגרם, משייך להזמנה האחרונה של המשתמש,
    ושומר את ה-file_id + caption בעמודת payment_proof_url.
    """

    # 1) למצוא משתמש לפי telegram_id
    user_row = db.execute(
        text('SELECT id FROM public."users" WHERE telegram_id = :tg_id'),
        {"tg_id": payload.telegram_id},
    ).fetchone()

    if not user_row:
        raise HTTPException(
            status_code=404,
            detail="User not found for this telegram_id",
        )

    user_id = user_row[0]

    # 2) למצוא את ההזמנה האחרונה של המשתמש
    order_row = db.execute(
        text(
            'SELECT id FROM public."orders" '
            'WHERE buyer_user_id = :user_id '
            'ORDER BY created_at DESC '
            'LIMIT 1'
        ),
        {"user_id": user_id},
    ).fetchone()

    if not order_row:
        raise HTTPException(
            status_code=404,
            detail="No orders found for this user",
        )

    order_id = order_row[0]

    # 3) לבנות ערך proof  פשוט טקסט עם file_id + caption
    proof_value = f"tg_file_id={payload.file_id};caption={payload.caption or ''}"

    # 4) לעדכן את ההזמנה
    db.execute(
        text(
            'UPDATE public."orders" '
            'SET payment_proof_url = :proof, '
            "    status = 'waiting_verification', "
            '    updated_at = :updated_at '
            'WHERE id = :order_id'
        ),
        {
            "proof": proof_value,
            "updated_at": datetime.utcnow(),
            "order_id": order_id,
        },
    )

    db.commit()

    return {
        "ok": True,
        "order_id": str(order_id),
        "stored_proof": proof_value,
    }
