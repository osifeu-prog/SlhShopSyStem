import os
import logging
from typing import Dict, Any

import requests
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
)

# ==========================
# Config
# ==========================

BOT_TOKEN = os.getenv("BOT_TOKEN")
API_BASE = os.getenv("SLH_API_BASE", "http://127.0.0.1:8080")

logging.basicConfig(
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    level=logging.INFO,
)
log = logging.getLogger("slh_bot")

if not API_BASE:
    API_BASE = "http://127.0.0.1:8080"

# cache קטן: telegram_id -> user_id
USER_CACHE: Dict[int, str] = {}


# ==========================
# Helpers
# ==========================

def api_post(path: str, json: dict) -> dict:
    url = f"{API_BASE}{path}"
    log.info("POST %s %s", url, json)
    r = requests.post(url, json=json, timeout=15)
    r.raise_for_status()
    return r.json()


def api_get(path: str) -> Any:
    url = f"{API_BASE}{path}"
    log.info("GET %s", url)
    r = requests.get(url, timeout=15)
    r.raise_for_status()
    return r.json()


def ensure_user_id(telegram_user) -> str:
    """
    יוצר/מסנכרן User ב-API לפי נתוני טלגרם ומחזיר user_id.
    """
    tg_id = telegram_user.id
    if tg_id in USER_CACHE:
        return USER_CACHE[tg_id]

    payload = {
        "telegram_id": tg_id,
        "telegram_username": telegram_user.username,
        "display_name": telegram_user.full_name,
        "referral_code": None,
    }
    user = api_post("/users/telegram-sync", payload)
    user_id = user["id"]
    USER_CACHE[tg_id] = user_id
    return user_id


def ensure_shop_for_user(user_id: str) -> dict:
    """
    מחפש חנות למשתמש, ואם אין  יוצר אחת בסיסית.
    """
    shops = api_get(f"/users/{user_id}/shops")
    if shops:
        return shops[0]

    payload = {
        "owner_user_id": user_id,
        "title": "Sela Shop של המשתמש",
        "description": "חנות שנוצרה אוטומטית מהבוט",
        "shop_type": "basic",
    }
    shop = api_post("/shops", payload)
    return shop


def ensure_default_item(shop_id: str) -> dict:
    """
    בודק אם יש פריטים בחנות, ואם אין  יוצר Love Card 39 NIS.
    """
    items = api_get(f"/shops/{shop_id}/items")
    if items:
        return items[0]

    payload = {
        "name": "Love Card 39 NIS",
        "description": "כרטיס ניסוי שנוצר מהבוט",
        "image_url": None,
        "price_slh": "39.0",
        "price_bnb": None,
        "price_nis": 39,
        "metadata": {
            "rarity": "common",
            "level": 1,
        },
    }
    item = api_post(f"/shops/{shop_id}/items", payload)
    return item


async def handle_shop_visit(
    referral_code: str,
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    user_id: str,
) -> None:
    """
    טיפול בכניסה דרך /start shop_<referral_code>
    """
    chat = update.effective_chat

    try:
        shop = api_get(f"/shops/by-referral/{referral_code}")
    except Exception:
        log.exception("Failed to get shop by referral_code=%s", referral_code)
        await chat.send_message("❌ לא הצלחתי למצוא חנות לקוד הזה.")
        return

    try:
        items = api_get(f"/shops/{shop['id']}/items")
    except Exception:
        log.exception("Failed to get items for shop_id=%s", shop["id"])
        await chat.send_message("❌ לא הצלחתי לשלוף פריטים מהחנות.")
        return

    if items:
        lines = []
        for idx, item in enumerate(items, start=1):
            price = item.get("price_slh") or item.get("price_bnb") or "N/A"
            lines.append(f"{idx}. {item['name']}  {price}")
        items_text = "\n".join(lines)
    else:
        items_text = "אין עדיין פריטים בחנות הזו."

    text = (
        "ברוך הבא לחנות 🏪\n"
        f"שם החנות: {shop['title']}\n"
        f"סטטוס: {shop['status']}\n"
        f"shop_id: {shop['id']}\n"
        f"referral_code: {shop['referral_code']}\n\n"
        "פריטים בחנות:\n"
        f"{items_text}\n\n"
        "כרגע זו תצוגה בלבד. בהמשך נוסיף כפתורי קנייה שייצרו הזמנה עבורך."
    )
    await chat.send_message(text)


# ==========================
# Handlers
# ==========================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    chat = update.effective_chat

    # תמיד נסנכרן את המשתמש קודם
    try:
        user_id = ensure_user_id(user)
    except Exception:
        log.exception("Failed to sync user")
        await chat.send_message("❌ שגיאה בסנכרון משתמש עם ה-API.")
        return

    # אם יש ארגומנט ל-/start (deep-link)
    if context.args:
        arg0 = context.args[0]
        # מצפה לפורמט shop_<referral_code>
        if arg0.startswith("shop_"):
            referral_code = arg0[len("shop_") :]
            await handle_shop_visit(referral_code, update, context, user_id)
            return

    # אחרת /start רגיל
    text = (
        f"היי {user.full_name}! 👋\n"
        f"חיברתי אותך ל-SLH Shop Core.\n\n"
        f"פקודות זמינות:\n"
        f"/myshop  לראות/ליצור את החנות שלך\n"
        f"/demo_order  ליצור הזמנת ניסיון ולקבל הוראות תשלום\n"
        f"(אפשר גם להשתמש בלינקים עם /start shop_<referral_code> כדי להיכנס לחנות של מישהו אחר.)"
    )
    await chat.send_message(text)


async def myshop(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    chat = update.effective_chat

    try:
        user_id = ensure_user_id(user)
        shop = ensure_shop_for_user(user_id)
    except Exception:
        log.exception("Failed to get/create shop")
        await chat.send_message("❌ שגיאה בשליפת/יצירת החנות שלך.")
        return

    text = (
        "🏪 החנות שלך:\n"
        f"שם: {shop['title']}\n"
        f"סטטוס: {shop['status']}\n"
        f"shop_id: {shop['id']}\n"
        f"referral_code: {shop['referral_code']}\n\n"
        "Deep-link לדוגמה:\n"
        f"https://t.me/YourBotUsername?start=shop_{shop['referral_code']}\n\n"
        "(תחליף את YourBotUsername בשם האמיתי של הבוט שלך.)"
    )
    await chat.send_message(text)


async def demo_order(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    chat = update.effective_chat

    try:
        user_id = ensure_user_id(user)
        shop = ensure_shop_for_user(user_id)
        item = ensure_default_item(shop["id"])

        payload = {
            "buyer_user_id": user_id,
            "shop_id": shop["id"],
            "item_id": item["id"],
            "payment_method": "slh",
        }
        order_with_payment = api_post("/orders", payload)
        order = order_with_payment["order"]
        pay = order_with_payment["payment_instructions"]
    except Exception:
        log.exception("Failed to create demo order")
        await chat.send_message("❌ שגיאה ביצירת הזמנת ניסיון.")
        return

    text = (
        "✅ יצרתי עבורך הזמנת ניסיון.\n\n"
        f"🎴 פריט: {item['name']}\n"
        f"💰 סכום: {order['amount_slh']} {pay['symbol']}\n\n"
        f"שלם לכתובת:\n{pay['to_address']}\n"
        f"Chain ID: {pay['chain_id']}\n\n"
        "(בשלב זה זו רק סימולציה  אין אימות on-chain עדיין.)"
    )
    await chat.send_message(text)


# ==========================
# Main
# ==========================

async def on_startup(app):
    log.info("Bot started. API_BASE=%s", API_BASE)


def main() -> None:
    if not BOT_TOKEN:
        raise RuntimeError("Missing BOT_TOKEN env var")

    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("myshop", myshop))
    app.add_handler(CommandHandler("demo_order", demo_order))

    app.post_init = on_startup

    log.info("Starting polling...")
    app.run_polling()


if __name__ == "__main__":
    main()
