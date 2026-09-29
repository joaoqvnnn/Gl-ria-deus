from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import ContextTypes

from database import db
from keyboards import menus
from texts import messages


PAGE_SIZE = 1  # 1 compra por página (formato "1/2")


async def history_router(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Roteia: hist:all:N | hist:active:N | hist:noop"""
    query = update.callback_query

    parts = query.data.split(":")
    action = parts[1] if len(parts) > 1 else "all"

    if action == "noop":
        await query.answer()
        return

    only_active = (action == "active")
    page = int(parts[2]) if len(parts) > 2 and parts[2].isdigit() else 0

    await query.answer()
    user = update.effective_user
    u = await db.get_or_create_user(user.id, user.username, user.first_name)

    purchases = await db.list_purchases(user.id, only_active=only_active)

    # ─── Vazio (todas)
    if not purchases and not only_active:
        await query.edit_message_text(
            messages.history_empty_text(),
            reply_markup=menus.history_empty_keyboard(),
            parse_mode=ParseMode.HTML,
        )
        return

    # ─── Vazio (apenas ativas)
    if not purchases and only_active:
        await query.edit_message_text(
            messages.history_active_empty_text(),
            reply_markup=menus.history_active_empty_keyboard(),
            parse_mode=ParseMode.HTML,
        )
        return

    total = len(purchases)
    pages = max((total + PAGE_SIZE - 1) // PAGE_SIZE, 1)
    page = min(max(page, 0), pages - 1)

    start = page * PAGE_SIZE
    purchase = purchases[start]

    product = await db.get_product(purchase["product_id"])
    activate_url = (product or {}).get("activate_url") or "https://t.me/"

    text = messages.history_item_text(purchase, start + 1, total, page + 1, pages)
    kb = menus.history_item_keyboard(
        purchase["id"], activate_url, page, pages, only_active
    )

    await query.edit_message_text(text, reply_markup=kb, parse_mode=ParseMode.HTML)
