import logging
import os
from typing import Dict, Any

import httpx
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    CallbackQueryHandler,
    filters,
)

# ==== הגדרות בסיס ====
API_BASE = os.getenv("API_BASE", "http://slhshopsystem:8080")
BOT_TOKEN = os.environ["BOT_TOKEN"]

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("slh_bot")


# ==== קריאות ל-API ====

async def call_api_telegram_sync(
    telegram_id: int,
    telegram_username: str,
    display_name: str,
    referral_code: str | None = None,
) -> Dict[str, Any]:
    """
    סנכרון משתמש טלגרם עם ה-API.
    """
    payload = {
        "telegram_id": telegram_id,
        "telegram_username": telegram_username or "",
        "display_name": display_name,
        "referral_code": referral_code,
    }
    logger.info("POST %s/users/telegram-sync %s", API_BASE, payload)
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.post(f"{API_BASE}/users/telegram-sync", json=payload)
        resp.raise_for_status()
        return resp.json()


async def call_api_demo_order(telegram_id: int) -> Dict[str, Any]:
    """
    יוצר הזמנת דמו דרך /shops/demo-order-bot.

    חשוב: ה-API כרגע מגדיר את המסלול הזה כ-GET,
    ולכן אנחנו משתמשים ב-GET עם פרמטר telegram_id.
    """
    params = {"telegram_id": telegram_id}
    logger.info("GET %s/shops/demo-order-bot %s", API_BASE, params)
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.get(f"{API_BASE}/shops/demo-order-bot", params=params)
        resp.raise_for_status()
        return resp.json()


async def call_api_upload_proof(
    order_id: str,
    file_bytes: bytes,
    content_type: str = "image/jpeg",
) -> Dict[str, Any]:
    """
    מעלה צילום אישור תשלום אל /payments/upload-proof כ-multipart/form-data.
    """
    data = {"order_id": order_id}
    files = {
        "file": ("payment_proof.jpg", file_bytes, content_type),
    }
    logger.info("POST %s/payments/upload-proof (order_id=%s)", API_BASE, order_id)
    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.post(
            f"{API_BASE}/payments/upload-proof",
            data=data,
            files=files,
        )
        resp.raise_for_status()
        return resp.json()


# ==== פקודות בוט ====

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    /start  סנכרון משתמש והצגת תפריט בסיסי.
    תומך גם ב-/start shop_<referral_code>.
    """
    user = update.effective_user
    referral_code = None

    # /start shop_<ref>
    if context.args:
        first_arg = context.args[0]
        if isinstance(first_arg, str) and first_arg.startswith("shop_"):
            referral_code = first_arg.split("shop_", 1)[1]
            context.user_data["referral_code"] = referral_code

    try:
        await call_api_telegram_sync(
            telegram_id=user.id,
            telegram_username=user.username or "",
            display_name=user.full_name,
            referral_code=referral_code,
        )
    except Exception:
        logger.exception("Error syncing user with API")
        if update.message:
            await update.message.reply_text(
                "❌ שגיאה בסנכרון משתמש עם ה-API.\n"
                "אנא נסה שוב מאוחר יותר."
            )
        return

    text = (
        f"היי {user.full_name}! 👋\n"
        "חיברתי אותך ל-SLH Shop Core.\n\n"
        "פקודות זמינות:\n"
        "/myshop  לראות/ליצור את החנות שלך (כרגע בתהליך פיתוח)\n"
        "/demo_order  ליצור הזמנת ניסיון ולקבל הוראות תשלום\n"
        "/help  לקבל מדריך קצר לשימוש בבוט\n\n"
        "אחרי יצירת הזמנה, שלח צילום אישור תשלום, ואני אקשר אותו להזמנה האחרונה שלך.\n"
    )

    if referral_code:
        text += f"\n🔗 נכנסת דרך קוד הפניה: {referral_code}\n"

    if update.message:
        await update.message.reply_text(text)


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    /help  מדריך שימוש קצר.
    """
    text = (
        "📖 *מדריך שימוש בבוט SLH Shop*\n\n"
        "1️⃣ /demo_order  יצירת הזמנת ניסיון.\n"
        "   אחרי ההזמנה תקבל מספר הזמנה (order_id).\n\n"
        "2️⃣ תשלום  בצע את העברה לכתובת שמופיעה בהודעה.\n\n"
        "3️⃣ צילום אישור  שלח כאן צילום מסך/תמונה של אישור התשלום.\n"
        "   • אם תשלח *בלי כיתוב*  התמונה תיקשר *להזמנה האחרונה*.\n"
        "   • אם תוסיף בכיתוב את מספר ההזמנה (order_id)  אקשר לתהזמנה הזו.\n\n"
        "4️⃣ /myshop  כרגע רק מקום שמור לניהול חנות, עדיין בפיתוח.\n\n"
        "אם משהו לא עובד, תמיד אפשר לשלוח שוב /start.\n"
    )
    if update.message:
        await update.message.reply_text(text, parse_mode="Markdown")


async def myshop_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    /myshop  כרגע רק הודעת placeholder.
    """
    if update.message:
        await update.message.reply_text(
            "🔧 /myshop עדיין בפיתוח בגרסה הזו של הבוט.\n"
            "כרגע אפשר לשחק עם /demo_order וצילום אישור תשלום."
        )


async def demo_order_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    /demo_order  יצירת הזמנת ניסיון דרך ה-API.
    """
    user = update.effective_user

    try:
        data = await call_api_demo_order(user.id)
    except httpx.HTTPStatusError as e:
        logger.error("HTTP error creating demo order: %s", e)
        if update.message:
            await update.message.reply_text(
                "❌ שגיאה ביצירת הזמנת ניסיון.\n"
                "יתכן שאין חנות דמו מוגדרת, או שיש בעיה בשרת."
            )
        return
    except Exception:
        logger.exception("Unexpected error creating demo order")
        if update.message:
            await update.message.reply_text("❌ שגיאה בלתי צפויה ביצירת הזמנת ניסיון.")
        return

    if not data.get("ok"):
        msg = data.get("error", "Unknown error")
        if update.message:
            await update.message.reply_text(f"❌ שגיאה ביצירת הזמנת ניסיון: {msg}")
        return

    order_id = data.get("order_id")
    item_name = data.get("item_name", "Love Card 39 NIS")
    amount_slh = data.get("amount_slh", 39.0)
    payment_address = data.get("payment_address", "0xACb0A09414CEA1C879c67bB7A877E4e19480f022")
    chain_id = data.get("chain_id", 56)

    # שמירת מזהה ההזמנה האחרונה
    context.user_data["last_order_id"] = order_id

    msg = (
        "✅ יצרתי עבורך הזמנת ניסיון.\n\n"
        f"🎴 פריט: {item_name}\n"
        f"💰 סכום: {amount_slh} SLH\n\n"
        "שלם לכתובת:\n"
        f"`{payment_address}`\n"
        f"Chain ID: {chain_id}\n\n"
        f"מספר הזמנה: `{order_id}`\n\n"
        "לאחר ששילמת, שלח לי כאן צילום של אישור התשלום,\n"
        "ואקשר אותו להזמנה הזאת (לשימוש פנימי ואימות ידני).\n\n"
        "אפשר גם לשלוח את הצילום עם כיתוב שמכיל את מספר ההזמנה."
    )

    if update.message:
        await update.message.reply_text(msg, parse_mode="Markdown")


async def photo_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    טיפול בתמונות  צילום אישור תשלום.

    לוגיקה:
    - אם יש כיתוב (caption)  ננסה להשתמש בו כ-order_id.
    - אחרת  ניקח את last_order_id מה-user_data.
    """
    message = update.message
    user = update.effective_user

    if not message or not message.photo:
        return

    caption = (message.caption or "").strip()

    if caption:
        order_id = caption
    else:
        order_id = context.user_data.get("last_order_id")

    if not order_id:
        await message.reply_text(
            "❌ לא הצלחתי לזהות איזו הזמנה לעדכן.\n\n"
            "אפשרויות:\n"
            "1. צור הזמנה חדשה עם /demo_order ואז שלח שוב את התמונה.\n"
            "2. שלח את התמונה *עם כיתוב* שמכיל את מספר ההזמנה (order_id)."
        )
        return

    try:
        processing_msg = await message.reply_text("📥 מוריד את התמונה...")

        photo = message.photo[-1]
        file = await photo.get_file()
        file_bytearray = await file.download_as_bytearray()
        file_bytes = bytes(file_bytearray)

        await processing_msg.edit_text("📤 מעלה את צילום האישור לשרת...")

        result = await call_api_upload_proof(order_id=order_id, file_bytes=file_bytes)

        await processing_msg.delete()
    except httpx.HTTPStatusError as e:
        logger.error("Error uploading payment proof to API: %s", e)
        await message.reply_text(
            "❌ שגיאה בשליחת צילום האישור לשרת.\n"
            "אנא נסה שוב מאוחר יותר."
        )
        return
    except Exception:
        logger.exception("Unexpected error in photo_handler")
        await message.reply_text("❌ שגיאה בלתי צפויה בטיפול בתמונה.")
        return

    if not result.get("ok"):
        err = result.get("error", "Unknown error")
        await message.reply_text(f"❌ שגיאה בשרת: {err}")
        return

    await message.reply_text(
        "📸 קיבלתי את צילום האישור!\n"
        f"הזמנה {order_id} עודכנה למצב waiting_verification.\n"
        "אימות התשלום יתבצע ידנית על בסיס הרשומה במערכת."
    )


async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE):
    """
    טיפול בשגיאות גלובלי.
    """
    logger.error("Exception while handling an update:", exc_info=context.error)
    try:
        if update and isinstance(update, Update) and update.effective_message:
            await update.effective_message.reply_text(
                "❌ אירעה שגיאה בלתי צפויה.\n"
                "אם זה חוזר על עצמו, פנה לתמיכה."
            )
    except Exception:
        # לא נרצה ששגיאה בטיפול בשגיאה תפרק את הבוט
        pass


def main() -> None:
    """
    פונקציית ההרצה הראשית של הבוט.
    """
    logger.info("Bot starting. API_BASE=%s", API_BASE)

    application = Application.builder().token(BOT_TOKEN).build()

    # פקודות בסיס
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("myshop", myshop_command))
    application.add_handler(CommandHandler("demo_order", demo_order_command))

    # תמונות (אישור תשלום)
    application.add_handler(MessageHandler(filters.PHOTO, photo_handler))

    # שגיאות
    application.add_error_handler(error_handler)

    # הרצה
    application.run_polling()


if __name__ == "__main__":
    main()
