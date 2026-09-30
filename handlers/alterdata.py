import re
from telegram import Update
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
    context.user_data["_wa_prompt_id"] = query.message.message_id
    context.user_data["_wa_prompt_chat"] = query.message.chat_id

    try:
        await query.edit_message_text(
            messages.whatsapp_prompt_text(),
            reply_markup=menus.alter_data_cancel_keyboard(),
            parse_mode=ParseMode.HTML,
        )
    except Exception:
        pass


async def whatsapp_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not _state.is_set(context.user_data, "awaiting_whatsapp"):
        return

    text = (update.message.text or "").strip()

    # Apaga a mensagem que o usuário digitou
    try:
        await update.message.delete()
    except Exception:
        pass

    user = update.effective_user
    chat_id = update.effective_chat.id

    # Comando → cancela
    if text.startswith("/"):
        await _delete_prompt(context, "_wa_prompt_id", "_wa_prompt_chat")
        _state.clear_all(context.user_data)
        return

    u = await db.get_or_create_user(user.id, user.username, user.first_name)

    # ─── "remover" → sucesso
    if text.lower() == "remover":
        await db.set_whatsapp(user.id, None)
        await _delete_prompt(context, "_wa_prompt_id", "_wa_prompt_chat")
        _state.clear_all(context.user_data)

        try:
            await context.bot.send_message(
                chat_id=chat_id,
                text=messages.whatsapp_removed_text(),
                reply_markup=menus.back_to_menu_keyboard(),
                parse_mode=ParseMode.HTML,
            )
        except Exception:
            pass
        return

    # ─── Validação
    digits = re.sub(r"\D", "", text)
    if not (10 <= len(digits) <= 11):
        # Erro → EDITA o prompt com aviso (não apaga)
        await _edit_prompt_error(
            context,
            "_wa_prompt_id", "_wa_prompt_chat",
            messages.whatsapp_invalid_text() + "\n\n" + messages.whatsapp_prompt_text(),
            menus.alter_data_cancel_keyboard(),
        )
        return

    # ─── SUCESSO → apaga prompt + limpa state + envia msg nova
    await db.set_whatsapp(user.id, digits)
    await _delete_prompt(context, "_wa_prompt_id", "_wa_prompt_chat")
    _state.clear_all(context.user_data)

    try:
        await context.bot.send_message(
            chat_id=chat_id,
            text=messages.whatsapp_updated_text(digits),
            reply_markup=menus.back_to_menu_keyboard(),
            parse_mode=ParseMode.HTML,
        )
    except Exception:
        pass


# ═══════════════════════════════════════════════
# HELPERS
# ═══════════════════════════════════════════════
async def _delete_prompt(context, id_key: str, chat_key: str):
    pid = context.user_data.pop(id_key, None)
    chat = context.user_data.pop(chat_key, None)
    if pid and chat:
        try:
            await context.bot.delete_message(chat_id=chat, message_id=pid)
        except Exception:
            pass


async def _edit_prompt_error(context, id_key: str, chat_key: str, text: str, kb=None):
    pid = context.user_data.get(id_key)
    chat = context.user_data.get(chat_key)
    if pid and chat:
        try:
            await context.bot.edit_message_text(
                chat_id=chat,
                message_id=pid,
                text=text,
                reply_markup=kb,
                parse_mode=ParseMode.HTML,
            )
        except Exception:
            pass
