from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import ContextTypes

from database import db
from keyboards import menus
from texts import messages


async def top_open(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await _render(query, "compras")


async def top_filter(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    filtro = query.data.split(":")[-1]
    await _render(query, filtro)


async def _render(query, filtro: str):
    if filtro == "compras":
        rows = await db.top_buyers(10)
    elif filtro == "recargas":
        rows = await db.top_by_topup(10)
    elif filtro == "gift":
        rows = await db.top_by_gift(10)
    elif filtro == "saldo":
        rows = await db.top_by_balance(10)
    else:
        rows = await db.top_buyers(10)

    await query.edit_message_text(
        messages.top_text(rows, filtro),
        reply_markup=menus.top_keyboard(filtro),
        parse_mode=ParseMode.HTML,
    )
