import os
import logging
from typing import Dict, Any, List, Optional

import httpx
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

# =========================
# Logging
# =========================
logger = logging.getLogger("slh_bot")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)

# =========================
# Config
# =========================
API_BASE = os.getenv("API_BASE", "http://slhshopsystem:8080").rstrip("/")

BOT_TOKEN = (
    os.getenv("BOT_TOKEN")
    or os.getenv("TELEGRAM_BOT_TOKEN")
    or os.getenv("TELEGRAM_TOKEN")
)

if not BOT_TOKEN:
    raise RuntimeError(
        "Bot token not found. Please set BOT_TOKEN or TELEGRAM_BOT_TOKEN or TELEGRAM_TOKEN."
    )

_http_client: Optional[httpx.AsyncClient] = None


def get_client() -> httpx.AsyncClient:
    global _http_client
    if _http_client is None:
        _http_client = httpx.AsyncClient(timeout=10.0)
    return _http_client


async def api_get(path: str, params: Dict[str, Any] | None = None) -> Any:
    url = f"{API_BASE}{path}"
    logger.info("GET %s %s", url, params or {})
    client = get_client()
    resp = await client.get(url, params=params)
    resp.raise_for_status()
    return resp.json()


async def api_post(path: str, payload: Dict[str, Any]) -> Any:
    url = f"{API_BASE}{path}"
    logger.info("POST %s %s", url, payload)
    client = get_client()
    resp = await client.post(url, json=payload)
    resp.raise_for_status()
    return resp.json()

# =========================
# Helpers (API side)
# =========================


async def ensure_user_from_telegram(update: Update) -> Dict[str, Any]:
    user = update.effective_user
    display_name = user.full_name or user.username or str(user.id)

    referral_code: Optional[str] = None
    if update.message and update.message.text:
        parts = update.message.text.split()
        if len(parts) > 1 and parts[1].startswith("shop_"):
            referral_code = parts[1][5:]

    payload = {
        "telegram_id": user.id,
        "telegram_username": user.username,
        "display_name": display_name,
        "referral_code": referral_code,
    }

    data = await api_post("/users/telegram-sync", payload)
    return data  # User מה-API


async def ensure_shop_and_default_item(api_user: Dict[str, Any]) -> tuple[Dict[str, Any], Dict[str, Any]]:
    user_id = api_user["id"]

    shops: List[Dict[str, Any]] = await api_get(f"/users/{user_id}/shops")
    if shops:
        shop = shops[0]
    else:
        shop_payload = {
            "owner_user_id": user_id,
            "title": "Sela Shop של המשתמש",
            "description": "חנות שנוצרה אוטומטית מהבוט",
            "shop_type": "basic",
        }
        shop = await api_post("/shops", shop_payload)

    items: List[Dict[str, Any]] = await api_get(f"/shops/{shop['id']}/items")
    default_item: Optional[Dict[str, Any]] = None
    for it in items:
        if it.get("name", "").startswith("Love Card 39"):
            default_item = it
            break

    if not default_item:
        item_payload = {
            "name": "Love Card 39 NIS",
            "description": "כרטיס ניסוי שנוצר מהבוט",
            "image_url": None,
            "price_slh": "39.0",
            "price_bnb": None,
            "price_nis": 39.0,
            "metadata": {"rarity": "common", "level": 1},
        }
        default_item = await api_post(f"/shops/{shop['id']}/items", item_payload)

    return shop, default_item


async def create_demo_order(api_user: Dict[str, Any]) -> Dict[str, Any]:
    shop, item = await ensure_shop_and_default_item(api_user)

    order_payload = {
        "buyer_user_id": api_user["id"],
        "shop_id": shop["id"],
        "item_id": item["id"],
        "payment_method": "slh",
    }

    order_with_payment = await api_post("/orders", order_payload)
    return order_with_payment

# =========================
# Telegram Handlers
# =========================


async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    api_user = await ensure_user_from_telegram(update)
    name = api_user.get("display_name") or update.effective_user.full_name

    text = (
        f"היי {name}! 👋\n"
        f"חיברתי אותך ל-SLH Shop Core.\n\n"
        f"פקודות זמינות:\n"
        f"/myshop  לראות/ליצור את החנות שלך\n"
        f"/demo_order  ליצור הזמנת ניסיון ולקבל הוראות תשלום\n"
        f"(אפשר גם להשתמש בלינקים עם /start shop_<referral_code> כדי להיכנס לחנות של מישהו אחר.)"
    )

    if update.message:
        await update.message.reply_text(text)


async def cmd_myshop(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    api_user = await ensure_user_from_telegram(update)
    shop, item = await ensure_shop_and_default_item(api_user)

    bot_username = context.bot.username
    referral_code = shop.get("referral_code")
    referral_link = f"https://t.me/{bot_username}?start=shop_{referral_code}" if referral_code else "—"

    text = (
        "📦 החנות שלך מוכנה!\n\n"
        f"שם החנות: {shop.get('title')}\n"
        f"קוד הפניה: {referral_code}\n\n"
        f"פריט ברירת מחדל:\n"
        f"• {item.get('name')}  {item.get('price_nis')} \n\n"
        f"לינק שיתוף לחנות:\n"
        f"{referral_link}"
    )

    if update.message:
        await update.message.reply_text(text)


async def cmd_demo_order(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    api_user = await ensure_user_from_telegram(update)
    order_with_payment = await create_demo_order(api_user)

    order = order_with_payment["order"]
    payment = order_with_payment["payment_instructions"]

    shop, item = await ensure_shop_and_default_item(api_user)

    text = (
        "✅ יצרתי עבורך הזמנת ניסיון.\n\n"
        f"🎴 פריט: {item.get('name')}\n"
        f"💰 סכום: {order.get('amount_slh')} {payment.get('symbol')}\n\n"
        f"שלם לכתובת:\n"
        f"{payment.get('to_address')}\n"
        f"Chain ID: {payment.get('chain_id')}\n\n"
        "(בשלב זה זו רק סימולציה  אין אימות on-chain עדיין.)\n\n"
        f"מזהה הזמנה (לשימוש עתידי):\n"
        f"`{order.get('id')}`"
    )

    if update.message:
        await update.message.reply_text(text, parse_mode="Markdown")

# =========================
# Application setup
# =========================


def build_application() -> Application:
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("myshop", cmd_myshop))
    app.add_handler(CommandHandler("demo_order", cmd_demo_order))
    return app


def main() -> None:
    logger.info("Bot starting. API_BASE=%s", API_BASE)
    application = build_application()
    logger.info("Starting polling...")
    application.run_polling()


if __name__ == "__main__":
    main()
