import uuid
from fastapi import APIRouter, Query

router = APIRouter(prefix="/shops", tags=["demo-order-bot"])


@router.get("/demo-order-bot")
async def demo_order_bot(telegram_id: int = Query(...)):
    """
    Mock endpoint for the Telegram bot demo order.

    The bot calls:
      GET /shops/demo-order-bot?telegram_id=224223270

    We ignore the telegram_id and just return a fake demo order.
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
