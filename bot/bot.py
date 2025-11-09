import logging
import os
import io

import httpx
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
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
    יוצר הזמנת דמו ב-API (צד שרת).
    משתמשים במסלול: POST /shops/demo-order-bot
    """
    payload = {"telegram_id": telegram_id}
    logger.info("POST %s/shops/demo-order-bot %s", API_BASE, payload)
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.post(f"{API_BASE}/shops/demo-order-bot", json=payload)
        resp.raise_for_status()
        return resp.json()


async def call_api_upload_proof(order_id: str, file_bytes: bytes, content_type: str = "image/jpeg"):
    """
    שולח צילום אישור תשלום אל /payments/upload-proof כ-multipart/form-data.
    """
    data = {"order_id": order_id}
    files = {
        "file": ("payment_proof.jpg", file_bytes, content_type),
    }
    logger.info("POST %s/payments/upload-proof (order_id=%s)", API_BASE, order_id)
    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.post(f"{API_BASE}/payments/upload-proof", data=data, files=files)
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
        if update.message:
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
    if update.message:
        await update.message.reply_text(text)


async def myshop_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message:
        await update.message.reply_text("🔧 /myshop עדיין בפיתוח בגרסה הזו של הבוט.")


async def demo_order_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    try:
        data = await call_api_demo_order(user.id)
    except httpx.HTTPStatusError as e:
        logger.error("Error creating demo order: %s", e)
        if update.message:
            await update.message.reply_text("❌ שגיאה ביצירת הזמנת ניסיון.")
        return
    except Exception:
        logger.exception("Error creating demo order (unexpected)")
        if update.message:
            await update.message.reply_text("❌ שגיאה ביצירת הזמנת ניסיון.")
        return

    if not data.get("ok"):
        if update.message:
            await update.message.reply_text("❌ שגיאה ביצירת הזמנת ניסיון.")
        return

    order_id = data.get("order_id")
    item_name = data.get("item_name", "פריט ניסיון")
    amount_slh = data.get("amount_slh", 0)
    payment_address = data.get("payment_address", "N/A")
    chain_id = data.get("chain_id", 56)

    # נשמור את מזהה ההזמנה האחרונה של המשתמש
    context.user_data["last_order_id"] = order_id

    msg = (
        "✅ יצרתי עבורך הזמנת ניסיון.\n\n"
        f"🎴 פריט: {item_name}\n"
        f"💰 סכום: {amount_slh} SLH\n\n"
        "שלם לכתובת:\n"
        f"{payment_address}\n"
        f"Chain ID: {chain_id}\n\n"
        f"מספר הזמנה: {order_id}\n\n"
        "לאחר ששילמת, שלח לי כאן צילום של אישור התשלום,\n"
        "ואקשר אותו להזמנה הזאת (לשימוש פנימי ואימות ידני)."
    )
    if update.message:
        await update.message.reply_text(msg)


async def photo_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    מטפל בתמונת אישור תשלום:
    - לוקח את ההזמנה האחרונה (last_order_id) של המשתמש
    - מוריד את התמונה מהטלגרם
    - שולח ל-API /payments/upload-proof
    """
    message = update.message
    user = update.effective_user

    if not message or not message.photo:
        return

    order_id = context.user_data.get("last_order_id")
    if not order_id:
        await message.reply_text(
            "לא מצאתי הזמנת ניסיון פעילה עבורך.\n"
            "שלח קודם /demo_order, ואז שלח צילום של אישור התשלום."
        )
        return

    try:
        # ניקח את התמונה באיכות הגבוהה ביותר
        photo = message.photo[-1]
        file = await photo.get_file()

        # כאן הייתה הבעיה  עכשיו נשתמש בפונקציה פשוטה שמחזירה bytearray
        file_bytearray = await file.download_as_bytearray()
        file_bytes = bytes(file_bytearray)

        api_result = await call_api_upload_proof(
            order_id=order_id,
            file_bytes=file_bytes,
        )

    except httpx.HTTPStatusError as e:
        logger.error("Error uploading payment proof to API: %s", e)
        await message.reply_text("❌ שגיאה בשליחת צילום האישור לשרת.")
        return
    except Exception:
        logger.exception("Unexpected error in photo_handler")
        await message.reply_text("❌ שגיאה בלתי צפויה בטיפול בתמונה.")
        return

    if not api_result.get("ok"):
        await message.reply_text("❌ השרת לא אישר את שמירת צילום האישור.")
        return

    await message.reply_text(
        "📸 קיבלתי את צילום האישור!\n"
        f"הזמנה {order_id} עודכנה למצב waiting_verification.\n"
        "אימות התשלום יתבצע ידנית על בסיס הרשומה במערכת."
    )


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

    # כל תמונה  תטופל כצילום אישור עבור ההזמנה האחרונה
    application.add_handler(MessageHandler(filters.PHOTO, photo_handler))

    application.run_polling()


if __name__ == "__main__":
    main()
