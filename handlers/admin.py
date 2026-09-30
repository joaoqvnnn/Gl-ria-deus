"""
Módulo ADMIN — Painel principal, dashboard, comandos básicos.
"""
import logging
import asyncio
from telegram import Update, ForceReply
from telegram.constants import ParseMode
from telegram.ext import ContextTypes

from config import ADMIN_IDS
from database import db
from keyboards import menus
from texts import cache

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════
# HELPERS
# ═══════════════════════════════════════════════
def is_admin(user_id: int) -> bool:
    return user_id in ADMIN_IDS


async def _edit_or_send(query, text: str, kb=None):
    try:
        await query.edit_message_text(text, reply_markup=kb, parse_mode=ParseMode.HTML)
    except Exception:
        await query.message.reply_text(text, reply_markup=kb, parse_mode=ParseMode.HTML)


def _dashboard_text(stats: dict) -> str:
    manut = "🔴 Em manutenção" if stats["manutencao"] else "🟢 Online"
    return (
        "🛠️ <b>PAINEL ADMINISTRADOR</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━━━\n\n"

        f"⚙️ <b>Status do Bot:</b> {manut}\n\n"

        "📊 <b>Visão Geral:</b>\n"
        f"├ 👥 Usuários: <b>{stats['total_users']}</b>\n"
        f"├ 🚫 Banidos: <b>{stats['total_banned']}</b>\n"
        f"├ 📦 Produtos ativos: <b>{stats['total_produtos']}</b>\n"
        f"└ 🛒 Carrinhos abandonados: <b>{stats['carrinhos_abandonados']}</b>\n\n"

        "💰 <b>Movimentação Financeira:</b>\n"
        f"├ Saldo em circulação: <b>R$ {stats['saldo_circulacao']:.2f}</b>\n"
        f"├ Receita total: <b>R$ {stats['receita_total']:.2f}</b>\n"
        f"├ Receita hoje: <b>R$ {stats['receita_hoje']:.2f}</b>\n"
        f"├ Receita 7 dias: <b>R$ {stats['receita_semana']:.2f}</b>\n"
        f"└ Receita do mês: <b>R$ {stats['receita_mes']:.2f}</b>\n\n"

        "🛒 <b>Vendas:</b>\n"
        f"├ Total de pedidos: <b>{stats['total_vendas']}</b>\n"
        f"└ Vendas hoje: <b>{stats['vendas_hoje']}</b>"
    )


# ═══════════════════════════════════════════════
# /admin — ABRIR PAINEL
# ═══════════════════════════════════════════════
async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if not is_admin(user.id):
        return

    try:
        stats = await db.admin_stats()
        await update.message.reply_text(
            _dashboard_text(stats),
            reply_markup=menus.admin_dashboard_kb(),
            parse_mode=ParseMode.HTML,
        )
    except Exception as e:
        logger.exception("Erro abrindo painel: %s", e)
        await update.message.reply_text(f"❌ Erro ao abrir painel: {e}")


async def admin_home_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Volta ao dashboard."""
    query = update.callback_query
    await query.answer()
    if not is_admin(update.effective_user.id):
        return

    try:
        stats = await db.admin_stats()
        await _edit_or_send(query, _dashboard_text(stats), menus.admin_dashboard_kb())
    except Exception as e:
        logger.exception("Erro no dashboard: %s", e)


# ═══════════════════════════════════════════════
# USUÁRIOS — LEGACY (compatibilidade)
# ═══════════════════════════════════════════════
async def admin_users_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Redireciona pra versão v2 (admin8)."""
    query = update.callback_query
    await query.answer()
    if not is_admin(update.effective_user.id):
        return

    try:
        from handlers import admin8
        await admin8.admin_users_v2_cb(update, context)
    except Exception as e:
        logger.exception("Erro redirecionando users: %s", e)


async def admin_user_search_prompt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Redireciona pra versão v2."""
    query = update.callback_query
    await query.answer()
    if not is_admin(update.effective_user.id):
        return

    try:
        from handlers import admin8
        await admin8.admin_user_search_prompt(update, context)
    except Exception as e:
        logger.exception("Erro redirecionando user_search: %s", e)


async def admin_search_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Redireciona pra versão v2."""
    if not is_admin(update.effective_user.id):
        return
    try:
        from handlers import admin8
        await admin8.admin_search_handler(update, context)
    except Exception as e:
        logger.exception("Erro redirecionando search: %s", e)


async def admin_user_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Redireciona pra versão v2."""
    query = update.callback_query
    await query.answer()
    if not is_admin(update.effective_user.id):
        return

    try:
        # Converte admin:user:<id> → admin:user_v2:<id>
        parts = query.data.split(":")
        if len(parts) >= 3:
            query.data = f"admin:user_v2:{parts[2]}"
        from handlers import admin8
        await admin8.admin_user_v2_cb(update, context)
    except Exception as e:
        logger.exception("Erro redirecionando user: %s", e)


# ═══════════════════════════════════════════════
# ADICIONAR / REMOVER SALDO — LEGACY
# ═══════════════════════════════════════════════
async def admin_add_balance_prompt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Redireciona pra admin8 (usr_add)."""
    query = update.callback_query
    await query.answer()
    if not is_admin(update.effective_user.id):
        return

    try:
        parts = query.data.split(":")
        if len(parts) >= 3:
            query.data = f"admin:usr_add:{parts[2]}"
        from handlers import admin8
        await admin8.admin_usr_add_prompt(update, context)
    except Exception as e:
        logger.exception("Erro redirecionando add_balance: %s", e)


async def admin_rem_balance_prompt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Redireciona pra admin8 (usr_rem)."""
    query = update.callback_query
    await query.answer()
    if not is_admin(update.effective_user.id):
        return

    try:
        parts = query.data.split(":")
        if len(parts) >= 3:
            query.data = f"admin:usr_rem:{parts[2]}"
        from handlers import admin8
        await admin8.admin_usr_rem_prompt(update, context)
    except Exception as e:
        logger.exception("Erro redirecionando rem_balance: %s", e)


async def admin_balance_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """LEGACY — não usado, mas mantido para não quebrar imports."""
    return


# ═══════════════════════════════════════════════
# BAN / UNBAN — LEGACY
# ═══════════════════════════════════════════════
async def admin_ban_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Redireciona pra admin8 (usr_ban)."""
    query = update.callback_query
    await query.answer()
    if not is_admin(update.effective_user.id):
        return

    try:
        parts = query.data.split(":")
        if len(parts) >= 3:
            query.data = f"admin:usr_ban:{parts[2]}"
        from handlers import admin8
        await admin8.admin_usr_ban_cb(update, context)
    except Exception as e:
        logger.exception("Erro redirecionando ban: %s", e)


async def admin_unban_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Redireciona pra admin8 (usr_unban)."""
    query = update.callback_query
    await query.answer()
    if not is_admin(update.effective_user.id):
        return

    try:
        parts = query.data.split(":")
        if len(parts) >= 3:
            query.data = f"admin:usr_unban:{parts[2]}"
        from handlers import admin8
        await admin8.admin_usr_unban_cb(update, context)
    except Exception as e:
        logger.exception("Erro redirecionando unban: %s", e)


# ═══════════════════════════════════════════════
# TRANSMISSÃO — LEGACY
# ═══════════════════════════════════════════════
async def admin_broadcast_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Redireciona pra admin10 (broadcast v2)."""
    query = update.callback_query
    await query.answer()
    if not is_admin(update.effective_user.id):
        return

    try:
        from handlers import admin10
        await admin10.admin_bc_v2_menu_cb(update, context)
    except Exception as e:
        logger.exception("Erro redirecionando broadcast: %s", e)


async def admin_bc_prompt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Redireciona 'admin:bc_*' antigos pra admin10."""
    query = update.callback_query
    await query.answer()
    if not is_admin(update.effective_user.id):
        return

    try:
        data = query.data
        # admin:bc_all → admin:bc_seg:todos
        # admin:bc_buyers → admin:bc_seg:compradores
        # admin:bc_inactive → admin:bc_seg:inativos
        if data == "admin:bc_all":
            query.data = "admin:bc_seg:todos"
        elif data == "admin:bc_buyers":
            query.data = "admin:bc_seg:compradores"
        elif data == "admin:bc_inactive":
            query.data = "admin:bc_seg:inativos"
        elif data == "admin:bc_media":
            query.data = "admin:bc_nova"

        from handlers import admin10
        if query.data.startswith("admin:bc_seg:"):
            await admin10.admin_bc_v2_segment_cb(update, context)
        else:
            await admin10.admin_bc_v2_nova_cb(update, context)
    except Exception as e:
        logger.exception("Erro redirecionando bc_prompt: %s", e)


# ═══════════════════════════════════════════════
# MANUTENÇÃO — LEGACY
# ═══════════════════════════════════════════════
async def admin_maintenance_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Redireciona pra admin15 (extras_maint)."""
    query = update.callback_query
    await query.answer()
    if not is_admin(update.effective_user.id):
        return

    try:
        from handlers import admin15
        await admin15.admin_extras_maint_cb(update, context)
    except Exception as e:
        logger.exception("Erro redirecionando maintenance: %s", e)


async def admin_toggle_maintenance_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Redireciona pra admin15."""
    query = update.callback_query
    await query.answer()
    if not is_admin(update.effective_user.id):
        return

    try:
        from handlers import admin15
        await admin15.admin_extras_maint_toggle_cb(update, context)
    except Exception as e:
        logger.exception("Erro redirecionando toggle_maintenance: %s", e)


# ═══════════════════════════════════════════════
# LOGS — LEGACY
# ═══════════════════════════════════════════════
async def admin_logs_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Redireciona pra admin15 (extras_logs)."""
    query = update.callback_query
    await query.answer()
    if not is_admin(update.effective_user.id):
        return

    try:
        from handlers import admin15
        await admin15.admin_extras_logs_cb(update, context)
    except Exception as e:
        logger.exception("Erro redirecionando logs: %s", e)


# ═══════════════════════════════════════════════
# RESTART — LEGACY
# ═══════════════════════════════════════════════
async def admin_restart_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Redireciona pra admin15 (restart soft)."""
    query = update.callback_query
    await query.answer()
    if not is_admin(update.effective_user.id):
        return

    try:
        from handlers import admin15
        await admin15.admin_extras_restart_soft_cb(update, context)
    except Exception as e:
        logger.exception("Erro redirecionando restart: %s", e)


# ═══════════════════════════════════════════════
# PRODUTOS — LEGACY
# ═══════════════════════════════════════════════
async def admin_products_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Redireciona pra admin4 (products v3)."""
    query = update.callback_query
    await query.answer()
    if not is_admin(update.effective_user.id):
        return

    try:
        from handlers import admin4
        await admin4.admin_products_v3_cb(update, context)
    except Exception as e:
        logger.exception("Erro redirecionando products: %s", e)


async def admin_toggle_product_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Redireciona pra admin4."""
    query = update.callback_query
    await query.answer()
    if not is_admin(update.effective_user.id):
        return

    try:
        from handlers import admin4
        await admin4.admin_toggle_product_cb(update, context)
    except Exception as e:
        logger.exception("Erro redirecionando toggle_product: %s", e)


# ═══════════════════════════════════════════════
# EDIT PRICE / STOCK — LEGACY (não usados)
# ═══════════════════════════════════════════════
async def admin_edit_price_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    return


async def admin_edit_stock_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    return
