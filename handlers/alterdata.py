import re
from telegram import Update, ForceReply
from telegram.constants import ParseMode
from telegram.ext import ContextTypes

from database import db
from keyboards import menus
from texts import messages


async def alter_open(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """EDITS a mensagem atual para o menu de Alterar Dados."""
    query = update.callback_query
    await query.answer()

    user = update.effective_user
    u = await db.get_or_create_user(user.id, user.username, user.first_name)

    await query.edit_message_text(
        messages.alter_data_text(u),
        reply_markup=menus.alter_data_keyboard(u),
        parse_mode=ParseMode.HTML,
    )


async def alter_whatsapp(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """EDITS para pedir o WhatsApp + envia ForceReply."""
    query = update.callback_query
    await query.answer()

    context.user_data["awaiting_whatsapp"] = True

    try:
        await query.edit_message_text(
            messages.whatsapp_prompt_text(),
            reply_markup=menus.alter_data_cancel_keyboard(),
            parse_mode=ParseMode.HTML,
        )
    except Exception:
        pass

    await context.bot.send_message(
        chat_id=query.message.chat_id,
        text="Digite abaixo 👇",
        reply_markup=ForceReply(selective=True),
    )


async def whatsapp_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.user_data.get("awaiting_whatsapp"):
        return

    text = (update.message.text or "").strip()
    user = update.effective_user
    u = await db.get_or_create_user(user.id, user.username, user.first_name)

    # Comando /start durante o fluxo → bloqueia
    if text.startswith("/start"):
        await update.message.reply_text(
            "⚠️ Você está no meio do cadastro de WhatsApp.\n"
            "Envie um número válido ou <code>remover</code>.",
            parse_mode=ParseMode.HTML,
        )
        return

    # Remover
    if text.lower() == "remover":
        await db.set_whatsapp(user.id, None)
        context.user_data.pop("awaiting_whatsapp", None)
        await update.message.reply_text(
            messages.whatsapp_removed_text(),
            parse_mode=ParseMode.HTML,
        )
        return

    # Validação: só dígitos, 10 ou 11 dígitos
    digits = re.sub(r"\D", "", text)
    if not (10 <= len(digits) <= 11):
        await update.message.reply_text(
            messages.whatsapp_invalid_text(),
            parse_mode=ParseMode.HTML,
        )
        return

    await db.set_whatsapp(user.id, digits)
    context.user_data.pop("awaiting_whatsapp", None)

    await update.message.reply_text(
        messages.whatsapp_updated_text(digits),
        parse_mode=ParseMode.HTML,
    )
