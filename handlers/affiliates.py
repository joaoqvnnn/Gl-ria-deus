import logging
from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import ContextTypes

from config import BOT_USERNAME
from database import db
from keyboards import menus
from texts import messages

logger = logging.getLogger(__name__)


def _link(user_id: int) -> str:
    return f"https://t.me/{BOT_USERNAME}?start={user_id}"


# ═══════════════════════════════════════════════
# 👥 ABRIR AFILIADOS
# ═══════════════════════════════════════════════
async def affiliates_open(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user = update.effective_user

    try:
        u = await db.get_or_create_user(user.id, user.username, user.first_name)

        if not u.get("is_affiliate"):
            await query.edit_message_text(
                messages.affiliates_inactive_text(),
                reply_markup=menus.affiliates_inactive_keyboard(),
                parse_mode=ParseMode.HTML,
            )
            return

        stats = await db.affiliate_stats(user.id)

        await query.edit_message_text(
            messages.affiliates_active_text(u, stats, _link(user.id)),
            reply_markup=menus.affiliates_active_keyboard(user_id=user.id),
            parse_mode=ParseMode.HTML,
        )
    except Exception as e:
        logger.exception("ERRO em affiliates_open: %s", e)
        try:
            await query.edit_message_text(
                "⚠️ Erro ao abrir Afiliados. Tente novamente.",
                parse_mode=ParseMode.HTML,
            )
        except Exception:
            pass


# ═══════════════════════════════════════════════
# ✅ ME FILIAR
# ═══════════════════════════════════════════════
async def affiliates_join(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user = update.effective_user

    try:
        await db.activate_affiliate(user.id)
        u = await db.get_user(user.id)
        stats = await db.affiliate_stats(user.id)

        await query.edit_message_text(
            messages.affiliates_active_text(u, stats, _link(user.id)),
            reply_markup=menus.affiliates_active_keyboard(user_id=user.id),
            parse_mode=ParseMode.HTML,
        )
    except Exception as e:
        logger.exception("ERRO em affiliates_join: %s", e)
        try:
            await query.edit_message_text(
                "⚠️ Erro ao se filiar. Tente novamente.",
                parse_mode=ParseMode.HTML,
            )
        except Exception:
            pass
