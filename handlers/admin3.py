"""
Módulo ADMIN — CONFIG / TEXTOS / BOTÕES (LEGACY — redireciona pra admin12).

Este arquivo é mantido apenas para compatibilidade com o `main.py`
que ainda registra alguns handlers antigos. Todos os callbacks
são redirecionados para a versão v2 (admin12).

Não usa mais nada próprio — o cache, banco e lógica ficam em admin12.
"""
import logging
from telegram import Update, ForceReply
from telegram.constants import ParseMode
from telegram.ext import ContextTypes

from config import ADMIN_IDS
from database import db
from keyboards import menus
from texts import cache

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


async def _delete_prompt(context, id_key, chat_key):
    pid = context.user_data.pop(id_key, None)
    chat = context.user_data.pop(chat_key, None)
    if pid and chat:
        try:
            await context.bot.delete_message(chat_id=chat, message_id=pid)
        except Exception:
            pass


# ═══════════════════════════════════════════════
# CONFIG — redireciona pra admin12
# ═══════════════════════════════════════════════
async def admin_config_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        from handlers import admin12
        await admin12.admin_cfg_v2_cb(update, context)
    except Exception as e:
        logger.exception("Erro redirecionando config: %s", e)


async def admin_cfg_edit_prompt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Redireciona 'admin:cfg:X' → 'admin:cfg2_edit:X'."""
    query = update.callback_query
    try:
        key = query.data.split(":", 2)[2]
        query.data = f"admin:cfg2_edit:{key}"
        from handlers import admin12
        await admin12.admin_cfg_v2_edit_cb(update, context)
    except Exception as e:
        logger.exception("Erro redirecionando cfg_edit: %s", e)


async def admin_cfg_edit_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Redireciona pro handler v2."""
    try:
        from handlers import admin12
        await admin12.admin_cfg_v2_edit_handler(update, context)
    except Exception as e:
        logger.exception("Erro redirecionando cfg_edit_handler: %s", e)


# ═══════════════════════════════════════════════
# TEXTOS — redireciona pra admin12
# ═══════════════════════════════════════════════
async def admin_texts_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        from handlers import admin12
        await admin12.admin_texts_v2_cb(update, context)
    except Exception as e:
        logger.exception("Erro redirecionando texts: %s", e)


async def admin_text_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Redireciona 'admin:text:X' → 'admin:text2_view:X'."""
    query = update.callback_query
    try:
        key = query.data.split(":", 2)[2]
        query.data = f"admin:text2_view:{key}"
        from handlers import admin12
        await admin12.admin_text_v2_view_cb(update, context)
    except Exception as e:
        logger.exception("Erro redirecionando text: %s", e)


async def admin_text_edit_prompt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Redireciona 'admin:text_edit:X' → 'admin:text2_edit:X'."""
    query = update.callback_query
    try:
        key = query.data.split(":", 2)[2]
        query.data = f"admin:text2_edit:{key}"
        from handlers import admin12
        await admin12.admin_text_v2_edit_cb(update, context)
    except Exception as e:
        logger.exception("Erro redirecionando text_edit: %s", e)


async def admin_text_edit_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Redireciona pro handler v2."""
    try:
        from handlers import admin12
        await admin12.admin_text_v2_edit_handler(update, context)
    except Exception as e:
        logger.exception("Erro redirecionando text_edit_handler: %s", e)


# ═══════════════════════════════════════════════
# BOTÕES — redireciona pra admin12
# ═══════════════════════════════════════════════
async def admin_buttons_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        from handlers import admin12
        await admin12.admin_buttons_v2_cb(update, context)
    except Exception as e:
        logger.exception("Erro redirecionando buttons: %s", e)


async def admin_button_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Redireciona 'admin:btn:X' → 'admin:btn2_view:X'."""
    query = update.callback_query
    try:
        key = query.data.split(":", 2)[2]
        query.data = f"admin:btn2_view:{key}"
        from handlers import admin12
        await admin12.admin_btn_v2_view_cb(update, context)
    except Exception as e:
        logger.exception("Erro redirecionando button: %s", e)


async def admin_btn_edit_prompt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Redireciona 'admin:btn_edit:X' → 'admin:btn2_edit:X'."""
    query = update.callback_query
    try:
        key = query.data.split(":", 2)[2]
        query.data = f"admin:btn2_edit:{key}"
        from handlers import admin12
        await admin12.admin_btn_v2_edit_cb(update, context)
    except Exception as e:
        logger.exception("Erro redirecionando btn_edit: %s", e)


async def admin_btn_edit_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Redireciona pro handler v2."""
    try:
        from handlers import admin12
        await admin12.admin_btn_v2_edit_handler(update, context)
    except Exception as e:
        logger.exception("Erro redirecionando btn_edit_handler: %s", e)


# ═══════════════════════════════════════════════
# BANNER — mantido aqui (não tem v2)
# ═══════════════════════════════════════════════
async def admin_banner_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not is_admin(update.effective_user.id):
        return

    file_id = await db.admin_get_banner()

    texto = (
        "🖼️ <b>Banner do Menu Principal</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━━━\n\n"
    )
    if file_id:
        texto += "✅ Banner configurado."
    else:
        texto += "❌ Nenhum banner configurado."

    texto += "\n\nEscolha uma ação:"
    await _edit_or_send(query, texto, menus.admin_banner_kb())


async def admin_banner_new_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not is_admin(update.effective_user.id):
        return

    context.user_data["admin_banner_new"] = True

    try:
        await query.edit_message_text(
            "🖼️ <b>Enviar novo banner</b>\n\n"
            "Envie a imagem agora (foto ou arquivo PNG/JPG):",
            parse_mode=ParseMode.HTML,
        )
    except Exception:
        pass


async def admin_banner_photo_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.user_data.get("admin_banner_new"):
        return
    if not is_admin(update.effective_user.id):
        return

    file_id = None
    if update.message.photo:
        file_id = update.message.photo[-1].file_id
    elif update.message.document:
        file_id = update.message.document.file_id
    elif update.message.sticker:
        file_id = update.message.sticker.file_id

    if not file_id:
        await update.message.reply_text("❌ Envie uma imagem válida.")
        return

    context.user_data.pop("admin_banner_new", None)

    await db.admin_set_banner(file_id)
    cache.set_text("__banner__", file_id)
    await db.log_admin_action(update.effective_user.id, "banner_set")

    await update.message.reply_text(
        "✅ <b>Banner atualizado!</b>",
        reply_markup=menus.admin_back_kb(),
        parse_mode=ParseMode.HTML,
    )


async def admin_banner_del_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not is_admin(update.effective_user.id):
        return

    await db.admin_set_banner("")
    cache.set_text("__banner__", "")
    await db.log_admin_action(update.effective_user.id, "banner_del")

    await _edit_or_send(query, "✅ Banner removido.", menus.admin_back_kb())


# ═══════════════════════════════════════════════
# STATS — redireciona pra admin11
# ═══════════════════════════════════════════════
async def admin_stats_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        from handlers import admin11
        await admin11.admin_stats_v2_cb(update, context)
    except Exception as e:
        logger.exception("Erro redirecionando stats: %s", e)


async def admin_stats_daily_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        from handlers import admin11
        await admin11.admin_stats_v2_dia_cb(update, context)
    except Exception as e:
        logger.exception("Erro redirecionando stats_daily: %s", e)


async def admin_stats_products_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        from handlers import admin11
        await admin11.admin_stats_v2_prod_cb(update, context)
    except Exception as e:
        logger.exception("Erro redirecionando stats_products: %s", e)


async def admin_stats_spenders_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        from handlers import admin11
        await admin11.admin_stats_v2_compradores_cb(update, context)
    except Exception as e:
        logger.exception("Erro redirecionando stats_spenders: %s", e)
