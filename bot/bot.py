# -*- coding: utf-8 -*-
import os
import logging
import asyncio
from typing import Optional, Dict, Any, List

import httpx
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
)
from telegram.request import HTTPXRequest

logging.basicConfig(
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger("slh_bot")

BOT_TOKEN = os.getenv("BOT_TOKEN")
API_BASE = os.getenv("API_BASE", "http://127.0.0.1:8080")

logger.info("Starting bot with API_BASE=%s", API_BASE)


# ==========================
# HTTP helpers to SLH API
# ==========================

async def api_get(path: str) -> Any:
    url = f"{API_BASE}{path}"
    logger.info("GET %s", url)
    async with httpx.AsyncClient(timeout=15.0) as client:
        resp = await client.get(url)
    resp.raise_for_status()
    return resp.json()


async def api_post(path: str, payload: Dict[str, Any]) -> Any:
    url = f"{API_BASE}{path}"
    logger.info("POST %s %s", url, payload)
    async with httpx.AsyncClient(timeout=15.0) as client:
        resp = await client.post(url, json=payload)
    resp.raise_for_status()
    return resp.json()


# ==========================
# Helpers: user / shop / item
# ==========================

async def ensure_user(update: Update, context: ContextTypes.DEFAULT_TYPE) -> Dict[str, Any]:
    user_data = context.user_data.get("slh_user")
    if user_data:
        return user_data

    tg_user = update.effective_user
    payload = {
        "telegram_id": tg_user.id,
        "telegram_username": tg_user.username,
        "display_name": tg_user.full_name,
        "referral_code": None,
    }
    user = await api_post("/users/telegram-sync", payload)
    context.user_data["slh_user"] = user
    return user


async def ensure_shop_for_user(user: Dict[str, Any]) -> Dict[str, Any]:
    user_id = user["id"]
    shops: List[Dict[str, Any]] = await api_get(f"/users/{user_id}/shops")
    if shops:
        return shops[0]

    payload = {
        "owner_user_id": user_id,
        "title": "Sela Shop של המשתמש",
        "description": "חנות שנוצרה אוטומטית מהבוט",
        "shop_type": "basic",
    }
    shop = await api_post("/shops", payload)
    return shop


async def ensure_default_item_for_shop(shop: Dict[str, Any]) -> Dict[str, Any]:
    shop_id = shop["id"]
    items: List[Dict[str, Any]] = await api_get(f"/shops/{shop_id}/items")
    if items:
        return items[0]

    payload = {
        "name": "Love Card 39 NIS",
        "description": "כרטיס ניסוי שנוצר מהבוט",
        "image_url": None,
        "price_slh": "39.0",
        "price_bnb": None,
        "price_nis": 39,
        "metadata": {"rarity": "common", "level": 1},
    }
    item = await api_post(f"/shops/{shop_id}/items", payload)
    return item


# ==========================
# Handlers
# ==========================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    # אם הגיעו עם deep-link: /start shop_<ref>
    args = context.args or []
    if args and args[0].startswith("shop_"):
        referral_code = args[0].split("shop_", 1)[1]
        await show_shop_by_referral(update, context, referral_code)
        return

    try:
        user = await ensure_user(update, context)
    except Exception as e:
        logger.exception("Error syncing user: %s", e)
        await update.message.reply_text("❌ שגיאה בסנכרון משתמש עם ה-API.")
        return

    text = (
        f"היי {user.get('display_name') or update.effective_user.full_name}! 👋\n"
        "חיברתי אותך ל-SLH Shop Core.\n\n"
        "פקודות זמינות:\n"
        "/myshop  לראות/ליצור את החנות שלך\n"
        "/demo_order  ליצור הזמנת ניסיון ולקבל הוראות תשלום\n"
        "(אפשר גם להשתמש בלינקים עם /start shop_<referral_code> כדי להיכנס לחנות של מישהו אחר.)"
    )
    await update.message.reply_text(text)


async def myshop(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    try:
        user = await ensure_user(update, context)
        shop = await ensure_shop_for_user(user)
        item = await ensure_default_item_for_shop(shop)
    except Exception as e:
        logger.exception("Error in /myshop: %s", e)
        await update.message.reply_text("❌ שגיאה בטעינת/יצירת החנות שלך.")
        return

    referral_code = shop["referral_code"]
    bot_username = (await context.bot.get_me()).username
    deep_link = f"https://t.me/{bot_username}?start=shop_{referral_code}"

    text = (
        "🏪 החנות שלך:\n"
        f"שם: {shop['title']}\n"
        f"סטטוס: {shop['status']}\n"
        f"shop_id: {shop['id']}\n"
        f"referral_code: {referral_code}\n\n"
        "Deep-link לדוגמה:\n"
        f"{deep_link}\n\n"
        "(תחליף את YourBotUsername בשם האמיתי של הבוט שלך אם אתה מעתיק את הטקסט ידנית.)"
    )
    await update.message.reply_text(text)


async def demo_order(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    try:
        user = await ensure_user(update, context)
        shop = await ensure_shop_for_user(user)
        item = await ensure_default_item_for_shop(shop)

        payload = {
            "buyer_user_id": user["id"],
            "shop_id": shop["id"],
            "item_id": item["id"],
            "payment_method": "slh",
        }
        result = await api_post("/orders", payload)
        order = result["order"]
        pay = result["payment_instructions"]
    except Exception as e:
        logger.exception("Error in /demo_order: %s", e)
        await update.message.reply_text("❌ שגיאה ביצירת הזמנת ניסיון.")
        return

    text = (
        "✅ יצרתי עבורך הזמנת ניסיון.\n\n"
        f"🎴 פריט: {item['name']}\n"
        f"💰 סכום: {order['amount_slh']} {pay['symbol']}\n\n"
        "שלם לכתובת:\n"
        f"{pay['to_address']}\n"
        f"Chain ID: {pay['chain_id']}\n\n"
        "(בשלב זה זו רק סימולציה  אין אימות on-chain עדיין.)"
    )
    await update.message.reply_text(text)


async def show_shop_by_referral(
    update: Update, context: ContextTypes.DEFAULT_TYPE, referral_code: str
) -> None:
    try:
        shop = await api_get(f"/shops/by-referral/{referral_code}")
        items: List[Dict[str, Any]] = await api_get(f"/shops/{shop['id']}/items")
    except Exception as e:
        logger.exception("Error loading shop by referral: %s", e)
        await update.message.reply_text("❌ לא הצלחתי למצוא חנות לקוד הזה.")
        return

    lines = [
        "ברוך הבא לחנות 🏪",
        f"שם החנות: {shop['title']}",
        f"סטטוס: {shop['status']}",
        f"shop_id: {shop['id']}",
        f"referral_code: {shop['referral_code']}",
        "",
        "פריטים בחנות:",
    ]
    if not items:
        lines.append("(אין פריטים בחנות עדיין)")
    else:
        for idx, it in enumerate(items, start=1):
            lines.append(f"{idx}. {it['name']}  {it.get('price_slh') or ''}")

    lines.append("")
    lines.append("כרגע זו תצוגה בלבד. בהמשך נוסיף כפתורי קנייה שייצרו הזמנה עבורך.")

    await update.message.reply_text("\n".join(lines))


# ==========================
# Main
# ==========================

def main() -> None:
    if not BOT_TOKEN:
        raise RuntimeError("BOT_TOKEN environment variable is required")

    # מגדירים request ל-Telegram עם timeouts נדיבים כדי למנוע TimedOut על getMe/getUpdates
    tg_request = HTTPXRequest(
        connect_timeout=30.0,
        read_timeout=30.0,
        write_timeout=30.0,
        pool_timeout=30.0,
    )

    app = (
        Application.builder()
        .token(BOT_TOKEN)
        .request(tg_request)
        .build()
    )

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("myshop", myshop))
    app.add_handler(CommandHandler("demo_order", demo_order))

    logger.info("Starting polling...")
    app.run_polling()


if __name__ == "__main__":
    main()
