import os
import logging
from typing import Optional

import httpx
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

# ===== Config =====
API_BASE = os.getenv("API_BASE", "http://slhshopsystem:8080")
BOT_TOKEN = os.getenv("BOT_TOKEN")

logging.basicConfig(
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger("slh_bot")


# ===== Helper: sync user with API =====
async def sync_user_with_api(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> Optional[dict]:
    """Send user info to /users/telegram-sync and return JSON or None on error."""
    if update.effective_user is None:
        return None

    u = update.effective_user
    payload = {
        "telegram_id": u.id,
        "telegram_username": u.username,
        "display_name": u.full_name,
        "referral_code": None,
    }

    logger.info("POST %s/users/telegram-sync %s", API_BASE, payload)
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(f"{API_BASE}/users/telegram-sync", json=payload)
            resp.raise_for_status()
            return resp.json()
    except Exception as e:
        logger.exception("Error syncing user with API: %s", e)
        if update.message:
            await update.message.reply_text("❌ שגיאה בסנכרון משתמש עם ה-API.")
        return None


# ===== Commands =====

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /start"""
    await sync_user_with_api(update, context)

    if update.message:
        await update.message.reply_text(
            "היי {}! 👋\n"
            "חיברתי אותך ל-SLH Shop Core.\n\n"
            "פקודות זמינות:\n"
            "/myshop  לראות/ליצור את החנות שלך\n"
            "/demo_order  ליצור הזמנת ניסיון ולקבל הוראות תשלום\n"
            "(אפשר גם להשתמש בלינקים עם /start shop_<referral_code> כדי להיכנס לחנות של מישהו אחר.)".format(
                update.effective_user.full_name if update.effective_user else "חבר"
            )
        )


async def myshop(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """(בשלב הזה אפשר להוסיף בהמשך חיבור אמיתי ל-API של החנות)"""
    await sync_user_with_api(update, context)

    if update.message:
        await update.message.reply_text(
            "📦 בקרוב: מסך ניהול חנות מהמם מתוך הבוט.\n"
            "בשלב זה, /myshop הוא Placeholder ואנחנו ממשיכים לבנות את המערכת."
        )


async def demo_order(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Create demo order via API and show payment instructions."""
    user_data = await sync_user_with_api(update, context)
    if user_data is None:
        return

    telegram_id = user_data.get("telegram_id") or (update.effective_user.id if update.effective_user else None)
    if telegram_id is None:
        if update.message:
            await update.message.reply_text("❌ לא הצלחתי לזהות משתמש.")
        return

    payload = {"telegram_id": telegram_id}
    logger.info("POST %s/demo-order %s", API_BASE, payload)

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(f"{API_BASE}/demo-order", json=payload)
            resp.raise_for_status()
            data = resp.json()
    except Exception as e:
        logger.exception("Error calling /demo-order: %s", e)
        if update.message:
            await update.message.reply_text("❌ שגיאה ביצירת הזמנת ניסיון ב-API.")
        return

    item_name = data.get("item_name", "Love Card 39 NIS")
    amount_slh = data.get("amount_slh", 39.0)
    # כדי לא לסבך עכשיו עם order_id בטלגרם, נשאיר רק סימולציה כמו קודם
    # אפשר בהמשך להוסיף הצגת order_id להעלאת קבלות מדויקת

    if update.message:
        await update.message.reply_text(
            "✅ יצרתי עבורך הזמנת ניסיון.\n\n"
            f"🎴 פריט: {item_name}\n"
            f"💰 סכום: {amount_slh} SLH\n\n"
            "שלם לכתובת:\n"
            "0xACb0A09414CEA1C879c67bB7A877E4e19480f022\n"
            "Chain ID: 56\n\n"
            "(בשלב זה זו רק סימולציה  אין אימות on-chain עדיין.)"
        )


# ===== Photos: manual payment proof (קבלה מצולמת) =====

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    בשלב ראשון  רק מקבל את התמונה ומאשר שקיבלנו קבלה מצולמת.
    אפשר בהמשך לחבר ל-/payments/upload-proof עם order_id.
    """
    if update.message is None:
        return

    user = update.effective_user
    caption = update.message.caption or ""

    logger.info(
        "Received photo from user_id=%s caption=%r",
        user.id if user else None,
        caption,
    )

    # placeholder: רק אישור קבלה
    await update.message.reply_text(
        "📸 קיבלתי את צילום הקבלה.\n"
        "בשלב הזה אני רק שומר שיש קבלה מצולמת.\n"
        "בשלבים הבאים נחבר את זה להזמנה ספציפית במסד הנתונים."
    )


# ===== Main =====

def main() -> None:
    if not BOT_TOKEN:
        raise RuntimeError("BOT_TOKEN environment variable is not set")

    logger.info("Bot starting. API_BASE=%s", API_BASE)

    application = Application.builder().token(BOT_TOKEN).build()

    # commands
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("myshop", myshop))
    application.add_handler(CommandHandler("demo_order", demo_order))

    # photos (קבלות מצולמות)
    application.add_handler(
        MessageHandler(filters.PHOTO & ~filters.COMMAND, handle_photo)
    )

    logger.info("Starting polling...")
    application.run_polling()


if __name__ == "__main__":
    main()
