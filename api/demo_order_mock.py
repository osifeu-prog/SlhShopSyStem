import uuid
from fastapi import APIRouter, Query
from pydantic import BaseModel

router = APIRouter()


class DemoOrderResponse(BaseModel):
    ok: bool
    order_id: str
    item_name: str
    amount_slh: float
    payment_address: str
    chain_id: int


@router.get("/shops/demo-order-bot", response_model=DemoOrderResponse)
async def demo_order_bot(telegram_id: int = Query(...)):
    """
    Demo endpoint for the Telegram bot.
    NOTE: This version does NOT touch the database.
    It only returns a fake demo order so that /demo_order בבוט יעבוד.
    """

    order_id = str(uuid.uuid4())

    return DemoOrderResponse(
        ok=True,
        order_id=order_id,
        item_name="Love Card 39 NIS",
        amount_slh=39.0,
        payment_address="0xACb0A09414CEA1C879c67bB7A877E4e19480f022",
        chain_id=56,
    )
