import logging
import os
import httpx
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
)

API_BASE = os.getenv("API_BASE", "http://slhshopsystem:8080")
BOT_TOKEN = os.environ["BOT_TOKEN"]

logger = logging.getLogger("slh_bot")


async def call_api_telegram_sync(
    telegram_id: int,
    telegram_username: str,
    display_name: str,
    referral_code: str | None = None,
):
    """קורא ל-API כדי לסנכרן משתמש טלגרם עם השרת."""
    payload = {
        "telegram_id": telegram_id,
        "telegram_username": telegram_username,
        "display_name": display_name,
        "referral_code": referral_code,
    }
    logger.info("POST %s/users/telegram-sync %s", API_BASE, payload)
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.post(f"{API_BASE}/users/telegram-sync", json=payload)
        resp.raise_for_status()
        return resp.json()


async def call_api_demo_order(telegram_id: int):
    """
    יוצר הזמנת דמו ב-API.
    אנחנו משתמשים במסלול חדש: POST /shops/demo-order-bot
    ושולחים לו JSON עם telegram_id.
    """
    payload = {"telegram_id": telegram_id}
    logger.info("POST %s/shops/demo-order-bot %s", API_BASE, payload)
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.post(f"{API_BASE}/shops/demo-order-bot", json=payload)
        resp.raise_for_status()
        return resp.json()


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    referral_code = None

    # אם מגיעים עם /start shop_<referral_code>
    if context.args:
        first_arg = context.args[0]
        if isinstance(first_arg, str) and first_arg.startswith("shop_"):
            referral_code = first_arg.split("shop_", 1)[1]

    try:
        await call_api_telegram_sync(
            telegram_id=user.id,
            telegram_username=user.username or "",
            display_name=user.full_name,
            referral_code=referral_code,
        )
    except Exception:
        logger.exception("Error syncing user with API")
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


async def myshop_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🔧 /myshop עדיין בפיתוח בגרסה הזו של הבוט.")


async def demo_order_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    try:
        data = await call_api_demo_order(user.id)
    except httpx.HTTPStatusError as e:
        logger.error("Error creating demo order: %s", e)
        await update.message.reply_text("❌ שגיאה ביצירת הזמנת ניסיון.")
        return
    except Exception:
        logger.exception("Error creating demo order (unexpected)")
        await update.message.reply_text("❌ שגיאה ביצירת הזמנת ניסיון.")
        return

    if not data.get("ok"):
        await update.message.reply_text("❌ שגיאה ביצירת הזמנת ניסיון.")
        return

    item_name = data.get("item_name", "פריט ניסיון")
    amount_slh = data.get("amount_slh", 0)
    payment_address = data.get("payment_address", "N/A")
    chain_id = data.get("chain_id", 56)

    msg = (
        "✅ יצרתי עבורך הזמנת ניסיון.\n\n"
        f"🎴 פריט: {item_name}\n"
        f"💰 סכום: {amount_slh} SLH\n\n"
        "שלם לכתובת:\n"
        f"{payment_address}\n"
        f"Chain ID: {chain_id}\n\n"
        "(בשלב זה זו רק סימולציה  אין אימות on-chain עדיין.)"
    )
    await update.message.reply_text(msg)


def main():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    logger.info("Bot starting. API_BASE=%s", API_BASE)

    application = Application.builder().token(BOT_TOKEN).build()

    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("myshop", myshop_command))
    application.add_handler(CommandHandler("demo_order", demo_order_command))

    application.run_polling()


if __name__ == "__main__":
    main()
