from fastapi import APIRouter, Query
from pydantic import BaseModel

router = APIRouter(prefix="/shops", tags=["demo-order-bot"])


class DemoOrderResponse(BaseModel):
    ok: bool
    order_id: str
    item_name: str
    amount_slh: float
    payment_address: str
    chain_id: int


MOCK_ADDRESS = "0xACb0A09414CEA1C879c67bB7A877E4e19480f022"


@router.get("/demo-order-bot", response_model=DemoOrderResponse)
async def demo_order_bot_get(telegram_id: int = Query(...)):
    """
    Mock endpoint בשביל הבוט /demo_order.
    לא נוגעים בבסיס נתונים, רק מחזירים הזמנה דמו קבועה.
    """
    return DemoOrderResponse(
        ok=True,
        order_id="91aa91e9-8601-4a4c-bf7b-5cfcb7061434",
        item_name="Love Card 39 NIS",
        amount_slh=39.0,
        payment_address=MOCK_ADDRESS,
        chain_id=56,
    )
