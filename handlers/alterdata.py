import re
from telegram import Update, ForceReply
from telegram.constants import ParseMode
from telegram.ext import ContextTypes

from database import db
from handlers import _state
from keyboards import menus
from texts import messages


async def alter_open(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    user = update.effective_user
    u = await db.get_or_create_user(user.id, user.username, user.first_name)

    try:
        await query.edit_message_text(
            messages.alter_data_text(u),
            reply_markup=menus.alter_data_keyboard(u),
            parse_mode=ParseMode.HTML,
        )
    except Exception:
        pass


async def alter_whatsapp(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    _state.set_state(context.user_data, "awaiting_whatsapp")

    try:
        await query.edit_message_text(
            messages.whatsapp_prompt_text(),
            reply_markup=menus.alter_data_cancel_keyboard(),
            parse_mode=ParseMode.HTML,
        )
    except Exception:
        pass

    try:
        await context.bot.send_message(
            chat_id=query.message.chat_id,
            text="Digite abaixo 👇",
            reply_markup=ForceReply(selective=True),
        )
    except Exception:
        pass


async def whatsapp_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not _state.is_set(context.user_data, "awaiting_whatsapp"):
        return

    text = (update.message.text or "").strip()
    user = update.effective_user
    u = await db.get_or_create_user(user.id, user.username, user.first_name)

    if text.startswith("/start") or text.startswith("/cancelar"):
        _state.clear_all(context.user_data)
        await update.message.reply_text("❌ Operação cancelada.", parse_mode=ParseMode.HTML)
        return

    if text.lower() == "remover":
        await db.set_whatsapp(user.id, None)
        _state.clear_all(context.user_data)
        await update.message.reply_text(
            messages.whatsapp_removed_text(),
            parse_mode=ParseMode.HTML,
        )
        return

    digits = re.sub(r"\D", "", text)
    if not (10 <= len(digits) <= 11):
        await update.message.reply_text(
            messages.whatsapp_invalid_text(),
            parse_mode=ParseMode.HTML,
        )
        return

    await db.set_whatsapp(user.id, digits)
    _state.clear_all(context.user_data)

    await update.message.reply_text(
        messages.whatsapp_updated_text(digits),
        parse_mode=ParseMode.HTML,
    )
