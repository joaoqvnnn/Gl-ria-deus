"""
Módulo ADMIN — SUB-ADMINS (LEGACY — redireciona pra admin13).

Este arquivo é mantido apenas para compatibilidade com o `main.py`.
Todos os callbacks são redirecionados para a versão v2 (admin13).
"""
import logging
from telegram import Update, ForceReply
from telegram.constants import ParseMode
from telegram.ext import ContextTypes

from config import ADMIN_IDS
from database import db
from keyboards import menus

logger = logging.getLogger(__name__)


def is_master(user_id: int) -> bool:
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
# SUB-ADMINS — tudo redireciona pra admin13
# ═══════════════════════════════════════════════
async def admin_subadmins_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """admin:subadmins → admin13.admin_sub_v2_cb"""
    try:
        from handlers import admin13
        await admin13.admin_sub_v2_cb(update, context)
    except Exception as e:
        logger.exception("Erro redirecionando subadmins: %s", e)


async def admin_sub_add_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """admin:sub_add → admin13.admin_sub_v2_add_cb"""
    try:
        from handlers import admin13
        await admin13.admin_sub_v2_add_cb(update, context)
    except Exception as e:
        logger.exception("Erro redirecionando sub_add: %s", e)


async def admin_sub_add_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler do wizard — redireciona pra admin13."""
    try:
        from handlers import admin13
        await admin13.admin_sub_v2_add_handler(update, context)
    except Exception as e:
        logger.exception("Erro redirecionando sub_add_handler: %s", e)


async def admin_sub_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """admin:sub:<id> → admin13.admin_sub_v2_view_cb"""
    query = update.callback_query
    try:
        parts = query.data.split(":")
        if len(parts) >= 3:
            query.data = f"admin:sub2:{parts[2]}"
        from handlers import admin13
        await admin13.admin_sub_v2_view_cb(update, context)
    except Exception as e:
        logger.exception("Erro redirecionando sub: %s", e)


async def admin_sub_edit_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """admin:sub_edit:<id> → admin13.admin_sub_v2_perm_cb"""
    query = update.callback_query
    try:
        parts = query.data.split(":")
        if len(parts) >= 3:
            query.data = f"admin:sub2_perm:{parts[2]}"
        from handlers import admin13
        await admin13.admin_sub_v2_perm_cb(update, context)
    except Exception as e:
        logger.exception("Erro redirecionando sub_edit: %s", e)


async def admin_sub_toggle_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """admin:sub_tog:<id>:<area> → admin13.admin_sub_v2_tog_cb"""
    query = update.callback_query
    try:
        parts = query.data.split(":")
        if len(parts) >= 4:
            query.data = f"admin:sub2_tog:{parts[2]}:{parts[3]}"
        from handlers import admin13
        await admin13.admin_sub_v2_tog_cb(update, context)
    except Exception as e:
        logger.exception("Erro redirecionando sub_toggle: %s", e)


async def admin_sub_all_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """admin:sub_all:<id> → admin13.admin_sub_v2_all_cb"""
    query = update.callback_query
    try:
        parts = query.data.split(":")
        if len(parts) >= 3:
            query.data = f"admin:sub2_all:{parts[2]}"
        from handlers import admin13
        await admin13.admin_sub_v2_all_cb(update, context)
    except Exception as e:
        logger.exception("Erro redirecionando sub_all: %s", e)


async def admin_sub_del_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """admin:sub_del:<id> → admin13.admin_sub_v2_del_cb"""
    query = update.callback_query
    try:
        parts = query.data.split(":")
        if len(parts) >= 3:
            query.data = f"admin:sub2_del:{parts[2]}"
        from handlers import admin13
        await admin13.admin_sub_v2_del_cb(update, context)
    except Exception as e:
        logger.exception("Erro redirecionando sub_del: %s", e)


# ═══════════════════════════════════════════════
# EXPORTAR — redireciona pra admin6 admin6 (aqui mesmo tem a lógica)
# ═══════════════════════════════════════════════
async def admin_export_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """admin:export — menu de exportação."""
    query = update.callback_query
    await query.answer()
    if not is_master(update.effective_user.id):
        return

    texto = (
        "📤 <b>Exportar dados</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "Escolha o que exportar (formato CSV, abre no Excel):"
    )
    await _edit_or_send(query, texto, menus.admin_export_kb())


async def admin_export_run_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """admin:export:<tipo> — gera o CSV."""
    query = update.callback_query
    await query.answer()
    if not is_master(update.effective_user.id):
        return

    try:
        tipo = query.data.split(":")[2]
    except IndexError:
        return

    import io
    from telegram import InputFile

    try:
        if tipo == "users":
            conteudo = await db.admin_export_users_csv()
            nome_arquivo = "usuarios.csv"
        elif tipo == "purchases":
            conteudo = await db.admin_export_purchases_csv()
            nome_arquivo = "vendas.csv"
        elif tipo == "withdrawals":
            conteudo = await db.admin_export_withdrawals_csv()
            nome_arquivo = "saques.csv"
        else:
            return

        await context.bot.send_document(
            chat_id=query.message.chat_id,
            document=InputFile(
                io.BytesIO(conteudo.encode("utf-8")),
                filename=nome_arquivo,
            ),
            caption=f"📤 <b>{nome_arquivo}</b>",
            parse_mode=ParseMode.HTML,
        )
        await db.log_admin_action(
            update.effective_user.id, "export", tipo
        )
    except Exception as e:
        logger.exception("Erro exportando: %s", e)
        await _edit_or_send(query, f"❌ Erro: {e}", menus.admin_back_kb())


# ═══════════════════════════════════════════════
# CHECK PERM — helper (usado por outros handlers)
# ═══════════════════════════════════════════════
async def check_admin_perm(user_id: int, area: str) -> bool:
    """
    Helper pra ser usado nos outros handlers.
    Ex: if not await check_admin_perm(user_id, 'users'): return
    """
    ok, perms = await db.admin_is_admin_or_sub(user_id)
    if not ok:
        return False
    return db.sub_tem_permissao(perms, area)
