from fastapi import APIRouter
import uuid

router = APIRouter()

@router.get("/shops/demo-order-bot")
async def demo_order_bot(telegram_id: int | None = None):
    """
    Demo endpoint for the Telegram bot.

    NOTE:
    - כרגע לא נוגעים בכלל ב-DB.
    - הכל סימולציה: יוצר order_id רנדומלי ומחזיר פרטי תשלום קבועים.
    - מספיק כדי שהבוט יציג הוראות תשלום ויזכור last_order_id.
    """

    order_id = str(uuid.uuid4())

    return {
        "ok": True,
        "order_id": order_id,
        "item_name": "Love Card 39 NIS",
        "amount_slh": 39.0,
        "payment_address": "0xACb0A09414CEA1C879c67bB7A877E4e19480f022",
        "chain_id": 56,
    }
