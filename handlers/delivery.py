from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import ContextTypes

from database import db
from keyboards import menus
from texts import messages


async def reveal_product(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    purchase_id = query.data.split(":", 2)[2]
    purchase = await db.get_purchase(purchase_id)
    if not purchase:
        await query.answer("Compra não encontrada.", show_alert=True)
        return

    product = await db.get_product(purchase["product_id"])

    await query.edit_message_text(
        text=messages.delivery_text(
            purchase, purchase["email"], purchase["password"], masked=False
        ),
        reply_markup=menus.delivery_revealed_keyboard(
            purchase["id"], (product or {}).get("activate_url") or "https://t.me/"
        ),
        parse_mode=ParseMode.HTML,
    )
