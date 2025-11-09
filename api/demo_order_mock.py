from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional

router = APIRouter()


class DemoOrderResponse(BaseModel):
    ok: bool
    order_id: str
    item_name: str
    amount_slh: float
    payment_address: str
    chain_id: int


MOCK_ADDRESS = "0xACb0A09414CEA1C879c67bB7A877E4e19480f022"


@router.get("/shops/demo-order-bot", response_model=DemoOrderResponse)
async def demo_order_bot_get(telegram_id: Optional[int] = None):
    """
    Mock endpoint בשביל הבוט /demo_order.
    לא נוגעים בבסיס נתונים, רק מחזירים הזמנת דמו קבועה.
    """
    return DemoOrderResponse(
        ok=True,
        order_id="91aa91e9-8601-4a4c-bf7b-5cfcb7061434",
        item_name="Love Card 39 NIS",
        amount_slh=39.0,
        payment_address=MOCK_ADDRESS,
        chain_id=56,
    )
