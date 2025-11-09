from fastapi import APIRouter
from typing import Dict

router = APIRouter()

@router.get("/shops/demo-order-bot")
async def create_demo_order_mock(telegram_id: int) -> Dict:
    """
    Mock endpoint for demo order used by the Telegram bot.
    Always returns a fake order for testing.
    """
    return {
        "ok": True,
        "order_id": "MOCK123456",
        "shop_id": 1,
        "telegram_id": telegram_id,
        "amount": 100.0,
        "currency": "USDT",
        "payment_address": "demo_wallet_address_123",
        "note": "Mock response from /shops/demo-order-bot",
    }
