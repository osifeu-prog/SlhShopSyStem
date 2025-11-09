import os
import logging
import httpx

from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

logging.basicConfig(
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger("slh_bot")


API_BASE = os.getenv("API_BASE", "http://slhshopsystem:8080")
BOT_TOKEN = os.getenv("BOT_TOKEN")


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Start command - sync user with SLH Shop Core and show help."""
    user = update.effective_user

    payload = {
        "telegram_id": user.id,
        "telegram_username": user.username or "",
        "display_name": user.full_name,
        "referral_code": None,
    }

    logger.info("POST %s/users/telegram-sync %s", API_BASE, payload)

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(f"{API_BASE}/users/telegram-sync", json=payload)
            resp.raise_for_status()
    except Exception as e:
        logger.exception("Error syncing user with API: %s", e)
        await update.message.reply_text("❌ שגיאה בסנכרון משתמש עם ה-API.")
        return

    text = (
        f"היי {user.full_name}! 👋\n"
        "חיברתי אותך ל-SLH Shop Core.\n\n"
        "פקודות זמינות:\n"
        "/myshop  לראות/ליצור את החנות שלך\n"
        "/demo_order  ליצור הזמנת ניסיון ולקבל הוראות תשלום\n"
        "(אפשר גם להשתמש בלינקים עם /start shop_<referral_code> כדי להיכנס לחנות של מישהו אחר.)"
    )
    await update.message.reply_text(text)


async def myshop_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text("🔧 /myshop עדיין בפיתוח בגרסה הזו של הבוט.")


async def demo_order_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Create demo order via API and show payment instructions."""
    user = update.effective_user
    payload = {"telegram_id": user.id}

    logger.info("POST %s/shops/demo-order %s", API_BASE, payload)

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(f"{API_BASE}/shops/demo-order", json=payload)
            resp.raise_for_status()
            data = resp.json()
    except Exception as e:
        logger.exception("Error creating demo order: %s", e)
        await update.message.reply_text("❌ שגיאה ביצירת הזמנת ניסיון.")
        return

    item_name = data.get("item_name", "פריט")
    amount_slh = data.get("amount_slh", 0)
    pay_address = data.get("pay_address", "0xACb0A09414CEA1C879c67bB7A877E4e19480f022")
    chain_id = data.get("chain_id", 56)

    text = (
        "✅ יצרתי עבורך הזמנת ניסיון.\n\n"
        f"🎴 פריט: {item_name}\n"
        f"💰 סכום: {amount_slh} SLH\n\n"
        "שלם לכתובת:\n"
        f"{pay_address}\n"
        f"Chain ID: {chain_id}\n\n"
        "(בשלב זה זו רק סימולציה  אין אימות on-chain עדיין.)"
    )
    await update.message.reply_text(text)


def main() -> None:
    token = BOT_TOKEN
    if not token:
        raise RuntimeError("BOT_TOKEN is not set in environment variables")

    app = Application.builder().token(token).build()

    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("myshop", myshop_command))
    app.add_handler(CommandHandler("demo_order", demo_order_command))

    logger.info("Bot starting. API_BASE=%s", API_BASE)
    app.run_polling()


if __name__ == "__main__":
    main()
