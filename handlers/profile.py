from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import ContextTypes

from database import db
from keyboards import menus
from texts import messages


async def show_profile(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Mostra o perfil (EDITA a mensagem atual)."""
    query = update.callback_query
    await query.answer()
    user = update.effective_user

    u = await db.get_or_create_user(user.id, user.username, user.first_name)
    stats = await db.user_stats(user.id)

    await query.edit_message_text(
        messages.profile_text(u, stats),
        reply_markup=menus.profile_keyboard(),
        parse_mode=ParseMode.HTML,
    )
