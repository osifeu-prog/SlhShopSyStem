import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import text

from .db import get_db

router = APIRouter(prefix="/shops", tags=["shops"])


@router.get("/demo-order-bot")
def create_demo_order_bot(
    telegram_id: int = Query(..., description="Telegram user id"),
    db: Session = Depends(get_db),
):
    """
    Endpoint דמו עבור הבוט:

    קלט:
      - telegram_id: מזהה המשתמש בטלגרם

    לוגיקה:
      - מאתר משתמש בטבלה public."users" לפי telegram_id
      - בוחר חנות דמו כלשהי (הראשונה בזמינות)
      - בוחר פריט כלשהו מהחנות (הראשון בזמינות)
      - יוצר רשומת הזמנה בטבלה public."orders"
      - מחזיר JSON ידידותי לבוט
    """

    # 1) למצוא משתמש (buyer)
    buyer = db.execute(
        text('SELECT id, display_name FROM public."users" WHERE telegram_id = :tid'),
        {"tid": telegram_id},
    ).fetchone()

    if not buyer:
        raise HTTPException(status_code=404, detail="User not found for given telegram_id")

    # 2) לבחור חנות דמו כלשהי
    shop = db.execute(
        text('SELECT id, name FROM public."shops" ORDER BY created_at LIMIT 1')
    ).fetchone()

    if not shop:
        raise HTTPException(status_code=400, detail="No demo shop configured in database")

    # 3) לבחור פריט דמו מהחנות
    item = db.execute(
        text(
            'SELECT id, name, price_slh '
            'FROM public."items" '
            'WHERE shop_id = :sid '
            "ORDER BY created_at LIMIT 1"
        ),
        {"sid": shop.id},
    ).fetchone()

    if not item:
        raise HTTPException(status_code=400, detail="No demo item configured for demo shop")

    # 4) ליצור הזמנה חדשה
    order_id = str(uuid.uuid4())
    amount_slh = float(item.price_slh)

    db.execute(
        text(
            '''
            INSERT INTO public."orders"
            (id, buyer_user_id, shop_id, item_id,
             amount_slh, amount_bnb,
             status, tx_hash,
             created_at, updated_at, payment_proof_url)
            VALUES
            (:id, :buyer, :shop, :item,
             :amount_slh, NULL,
             :status, NULL,
             NOW(), NOW(), NULL)
            '''
        ),
        {
            "id": order_id,
            "buyer": buyer.id,
            "shop": shop.id,
            "item": item.id,
            "amount_slh": amount_slh,
            "status": "pending",
        },
    )
    db.commit()

    # 5) להחזיר JSON לבוט
    return {
        "ok": True,
        "order_id": order_id,
        "item_name": item.name,
        "amount_slh": amount_slh,
        "payment_address": "0xACb0A09414CEA1C879c67bB7A877E4e19480f022",
        "chain_id": 56,
        "shop": shop.name,
        "buyer": buyer.display_name,
    }
