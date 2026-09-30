"""
Módulo ADMIN — LEGACY (carrinhos, mensagem direta, backup, broadcast mídia).

Este arquivo é mantido para compatibilidade com o `main.py`.
Tudo é redirecionado para os módulos v2 correspondentes.

O que fica de fato aqui:
  • admin_msg_user_prompt / admin_msg_user_handler — mensagem direta pro user
  • admin_bc_media_handler — legacy do broadcast (redireciona pra admin10)
"""
import logging
from telegram import Update, ForceReply
from telegram.constants import ParseMode
from telegram.ext import ContextTypes

from config import ADMIN_IDS
from database import db
from keyboards import menus

logger = logging.getLogger(__name__)


def is_admin(user_id: int) -> bool:
    return user_id in ADMIN_IDS


async def _edit_or_send(query, text: str, kb=None):
    try:
        await query.edit_message_text(text, reply_markup=kb, parse_mode=ParseMode.HTML)
    except Exception:
        try:
            await query.message.reply_text(text, reply_markup=kb, parse_mode=ParseMode.HTML)
        except Exception:
            pass


# ═══════════════════════════════════════════════
# CARRINHOS — redireciona pra admin14
# ═══════════════════════════════════════════════
async def admin_abandoned_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        from handlers import admin14
        await admin14.admin_carts_v2_cb(update, context)
    except Exception as e:
        logger.exception("Erro redirecionando abandoned: %s", e)


async def admin_abandoned_item_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        from handlers import admin14
        await admin14.admin_cart_v2_item_cb(update, context)
    except Exception as e:
        logger.exception("Erro redirecionando abandoned_item: %s", e)


async def admin_abandoned_send_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        from handlers import admin14
        await admin14.admin_cart_v2_send_cb(update, context)
    except Exception as e:
        logger.exception("Erro redirecionando abandoned_send: %s", e)


async def admin_abandoned_del_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        from handlers import admin14
        await admin14.admin_cart_v2_del_cb(update, context)
    except Exception as e:
        logger.exception("Erro redirecionando abandoned_del: %s", e)


# ═══════════════════════════════════════════════
# BACKUP — redireciona pra admin15
# ═══════════════════════════════════════════════
async def admin_backup_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        from handlers import admin15
        await admin15.admin_extras_backup_do_cb(update, context)
    except Exception as e:
        logger.exception("Erro redirecionando backup: %s", e)


# ═══════════════════════════════════════════════
# MENSAGEM DIRETA PRO USUÁRIO
# ═══════════════════════════════════════════════
async def admin_msg_user_prompt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not is_admin(update.effective_user.id):
        return

    try:
        user_id = int(query.data.split(":")[2])
    except (IndexError, ValueError):
        return

    context.user_data["admin_msg_user"] = user_id

    try:
        await query.edit_message_text(
            f"✉️ <b>Enviar mensagem direta</b>\n"
            "━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"👤 User: <code>{user_id}</code>\n\n"
            "Envie o texto (pode usar HTML):\n\n"
            "Envie <code>/cancelar</code> para sair.",
            reply_markup=ForceReply(selective=True),
            parse_mode=ParseMode.HTML,
        )
    except Exception:
        pass


async def admin_msg_user_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = context.user_data.get("admin_msg_user")
    if not user_id:
        return
    if not is_admin(update.effective_user.id):
        return

    texto = update.message.text or update.message.caption or ""

    try:
        await update.message.delete()
    except Exception:
        pass

    if texto.startswith("/"):
        context.user_data.pop("admin_msg_user", None)
        return

    if not texto.strip():
        await update.message.reply_text("❌ Mensagem vazia.")
        return

    context.user_data.pop("admin_msg_user", None)

    try:
        await context.bot.send_message(
            chat_id=user_id,
            text=texto,
            parse_mode=ParseMode.HTML,
        )
        await db.log_admin_action(
            update.effective_user.id, "direct_msg", str(user_id)
        )
        await update.message.reply_text(
            f"✅ Mensagem enviada para <code>{user_id}</code>.",
            reply_markup=menus.admin_back_kb(),
            parse_mode=ParseMode.HTML,
        )
    except Exception as e:
        await update.message.reply_text(
            f"❌ Erro: {e}",
            reply_markup=menus.admin_back_kb(),
        )


# ═══════════════════════════════════════════════
# BROADCAST MÍDIA — redireciona pra admin10
# ═══════════════════════════════════════════════
async def admin_bc_media_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Legacy — redireciona pra content handler do admin10."""
    try:
        from handlers import admin10
        await admin10.admin_bc_v2_content_handler(update, context)
    except Exception as e:
        logger.exception("Erro redirecionando bc_media: %s", e)
