import logging
import os

import httpx
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

# -----------------------
# בסיס לוגים
# -----------------------
logging.basicConfig(
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger("slh_bot")

# -----------------------
# הגדרות מה-ENV
# -----------------------
load_dotenv()

API_BASE = os.getenv("API_BASE", "http://slhshopsystem:8080")
BOT_TOKEN = os.getenv("BOT_TOKEN")

if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN env var BOT_TOKEN חסר ב-ENV")


# -----------------------
# /start  סנכרון משתמש וברכת פתיחה
# -----------------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user

    payload = {
        "telegram_id": user.id,
        "telegram_username": user.username,
        "display_name": user.full_name,
        "referral_code": None,
    }

    logger.info("POST %s/users/telegram-sync %s", API_BASE, payload)

    welcome_text = (
        f"היי {user.full_name}! 👋\n"
        "חיברתי אותך ל-SLH Shop Core.\n\n"
        "פקודות זמינות:\n"
        "/myshop  לראות/ליצור את החנות שלך\n"
        "/demo_order  ליצור הזמנת ניסיון ולקבל הוראות תשלום\n"
        "(אפשר גם להשתמש בלינקים עם /start shop_<referral_code> כדי להיכנס לחנות של מישהו אחר.)"
    )

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(f"{API_BASE}/users/telegram-sync", json=payload)
            logger.info("users/telegram-sync status=%s", resp.status_code)
            resp.raise_for_status()
    except Exception as e:
        logger.exception("Error syncing user: %s", e)
        await update.effective_chat.send_message("❌ שגיאה בסנכרון משתמש עם ה-API.")
        return

    await update.effective_chat.send_message(welcome_text)


# -----------------------
# /myshop  כרגע הודעה בסיסית בלבד
# -----------------------
async def myshop(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.effective_chat.send_message(
        "🛒 בקרוב: נראה פה לינק לחנות האישית שלך דרך ה-API."
    )


# -----------------------
# /demo_order  סימולציה של הזמנת ניסיון
# (בינתיים בלי קריאה ל-API כדי להבטיח יציבות)
# -----------------------
async def demo_order(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    text = (
        "✅ יצרתי עבורך הזמנת ניסיון.\n\n"
        "🎴 פריט: Love Card 39 NIS\n"
        "💰 סכום: 39.0 SLH\n\n"
        "שלם לכתובת:\n"
        "0xACb0A09414CEA1C879c67bB7A877E4e19480f022\n"
        "Chain ID: 56\n\n"
        "(בשלב זה זו רק סימולציה  אין אימות on-chain עדיין.)"
    )
    await update.effective_chat.send_message(text)


# -----------------------
# קבלת תמונה  כרגע רק קבלה ידנית, בלי חיבור להזמנה ספציפית
# -----------------------
async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    logger.info("Got photo from user %s (%s)", user.id, user.username)

    await update.effective_chat.send_message(
        "📷 תודה! קיבלתי את צילום האישור.\n"
        "בגרסה הבאה נחבר את זה ישירות להזמנה במסד הנתונים."
    )


# -----------------------
# main  בניית האפליקציה והרצה
# -----------------------
def main() -> None:
    logger.info("Bot starting. API_BASE=%s", API_BASE)

    application = Application.builder().token(BOT_TOKEN).build()

    # פקודות
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("myshop", myshop))
    application.add_handler(CommandHandler("demo_order", demo_order))

    # כל תמונה שנשלחת לבוט
    application.add_handler(MessageHandler(filters.PHOTO, handle_photo))

    application.run_polling()


if __name__ == "__main__":
    main()
