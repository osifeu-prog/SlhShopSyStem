from fastapi import APIRouter
from typing import Dict, Any

router = APIRouter(prefix="/shops", tags=["demo-order-bot"])


@router.get("/demo-order-bot")
async def create_demo_order_mock(telegram_id: int) -> Dict[str, Any]:
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
        "note": "Mock response from /shops/demo-order-bot (overrides real route)",
    }
