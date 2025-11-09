import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import text

from .db import get_db

router = APIRouter(prefix="/shops", tags=["shops"])


@router.post("/demo-order-bot")
async def create_demo_order_bot(payload: dict, db: Session = Depends(get_db)):
    """
    יוצר הזמנת דמו עבור משתמש לפי telegram_id.

    לוגיקה:
    1. מאתר את המשתמש בטבלת users לפי telegram_id.
    2. מאתר חנות (shops) של המשתמש.
    3. מאתר פריט (items) בחנות (Love Card 39 NIS שכבר קיים).
    4. יוצר רשומה חדשה ב-orders עם סטטוס pending.
    5. מחזיר לבוט פרטים להצגה למשתמש.
    """
    telegram_id = payload.get("telegram_id")
    if telegram_id is None:
        raise HTTPException(status_code=400, detail="telegram_id is required")

    # 1. משתמש
    user_row = db.execute(
        text('SELECT id FROM public."users" WHERE telegram_id = :tid'),
        {"tid": telegram_id},
    ).first()
    if not user_row:
        raise HTTPException(status_code=404, detail="User not found for this telegram_id")
    user_id = user_row[0]

    # 2. חנות של המשתמש
    shop_row = db.execute(
        text(
            'SELECT id FROM public."shops" '
            'WHERE owner_user_id = :uid ORDER BY created_at LIMIT 1'
        ),
        {"uid": user_id},
    ).first()
    if not shop_row:
        raise HTTPException(status_code=404, detail="Shop not found for user")
    shop_id = shop_row[0]

    # 3. פריט בחנות
    item_row = db.execute(
        text(
            'SELECT id, name, price_slh FROM public."items" '
            'WHERE shop_id = :sid ORDER BY created_at LIMIT 1'
        ),
        {"sid": shop_id},
    ).first()
    if not item_row:
        raise HTTPException(status_code=404, detail="No items found for this shop")

    item_id, item_name, price_slh = item_row

    # 4. יצירת הזמנה בטבלת orders
    order_id = str(uuid.uuid4())
    now = datetime.utcnow()

    db.execute(
        text(
            '''
            INSERT INTO public."orders"
            (id, buyer_user_id, shop_id, item_id, amount_slh, amount_bnb,
             status, tx_hash, created_at, updated_at, payment_proof_url)
            VALUES
            (:id, :buyer_user_id, :shop_id, :item_id, :amount_slh, NULL,
             :status, NULL, :created_at, :updated_at, NULL)
            '''
        ),
        {
            "id": order_id,
            "buyer_user_id": user_id,
            "shop_id": shop_id,
            "item_id": item_id,
            "amount_slh": float(price_slh),
            "status": "pending",
            "created_at": now,
            "updated_at": now,
        },
    )

    db.commit()

    # 5. החזרה לבוט
    return {
        "ok": True,
        "order_id": order_id,
        "item_name": item_name,
        "amount_slh": float(price_slh),
        "payment_address": "0xACb0A09414CEA1C879c67bB7A877E4e19480f022",
        "chain_id": 56,
    }
