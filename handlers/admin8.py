"""
Módulo ADMIN — USUÁRIOS (v2 — completo, com filtros, histórico, ban temp).
"""
import logging
import io
from telegram import Update, ForceReply, InputFile
from telegram.constants import ParseMode
from telegram.ext import ContextTypes

from config import ADMIN_IDS
from database import db
from keyboards import menus

logger = logging.getLogger(__name__)

USERS_PAGE_SIZE = 8
_ZERO = "\u200b"


def is_admin(user_id: int) -> bool:
    return user_id in ADMIN_IDS


async def _edit_or_send(query, text: str, kb=None):
    try:
        await query.edit_message_text(text, reply_markup=kb, parse_mode=ParseMode.HTML)
    except Exception:
        await query.message.reply_text(text, reply_markup=kb, parse_mode=ParseMode.HTML)


async def _delete_prompt(context, id_key, chat_key):
    pid = context.user_data.pop(id_key, None)
    chat = context.user_data.pop(chat_key, None)
    if pid and chat:
        try:
            await context.bot.delete_message(chat_id=chat, message_id=pid)
        except Exception:
            pass


async def _edit_prompt_error(context, id_key, chat_key, text, kb=None):
    pid = context.user_data.get(id_key)
    chat = context.user_data.get(chat_key)
    if pid and chat:
        try:
            await context.bot.edit_message_text(
                chat_id=chat, message_id=pid,
                text=text, reply_markup=kb, parse_mode=ParseMode.HTML,
            )
        except Exception:
            pass


# ═══════════════════════════════════════════════
# LISTA
# ═══════════════════════════════════════════════
async def admin_users_v2_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not is_admin(update.effective_user.id):
        return
    await _render_users(query, filtro="todos", page=0)


async def admin_users_page_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not is_admin(update.effective_user.id):
        return
    try:
        _, _, filtro, page = query.data.split(":")
        page = int(page)
    except (ValueError, IndexError):
        return
    await _render_users(query, filtro=filtro, page=page)


async def admin_users_filtro_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not is_admin(update.effective_user.id):
        return
    try:
        filtro = query.data.split(":")[2]
    except IndexError:
        filtro = "todos"
    await _render_users(query, filtro=filtro, page=0)


async def _render_users(query, filtro: str = "todos", page: int = 0):
    total = await db.admin_users_v2_count(filtro)
    stats = await db.admin_users_v2_stats()

    total_pages = max((total + USERS_PAGE_SIZE - 1) // USERS_PAGE_SIZE, 1)
    page = min(max(page, 0), total_pages - 1)

    users = await db.admin_users_v2_list(
        filtro=filtro, limit=USERS_PAGE_SIZE, offset=page * USERS_PAGE_SIZE,
    )

    filtro_label = {
        "todos": "📋 Todos", "ativos": "🟢 Ativos", "banidos": "🚫 Banidos",
        "afiliados": "🤝 Afiliados", "com_saldo": "💰 Com saldo",
        "sem_saldo": "📭 Sem saldo", "inativos": "💤 Inativos 7d",
    }.get(filtro, filtro)

    texto = (
        "👥 <b>Gerenciar Usuários</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"📡 Filtro: <b>{filtro_label}</b>\n\n"
        "📊 <b>Resumo geral:</b>\n"
        f"├ 👥 Total: <b>{stats['total']}</b>\n"
        f"├ 🆕 Novos hoje: <b>{stats['novos_hoje']}</b>\n"
        f"├ 🚫 Banidos: <b>{stats['banidos']}</b>\n"
        f"├ 🤝 Afiliados: <b>{stats['afiliados']}</b>\n"
        f"└ 💰 Saldo em circulação: <b>R$ {stats['saldo_total']:.2f}</b>\n\n"
        f"📄 Página <b>{page + 1}/{total_pages}</b> · {total} user(s)\n\n"
        "🚫 Banido   🤝 Afiliado\n"
        "👉 Toque em um usuário:"
    )

    kb = menus.admin_users_v2_kb(users, page, total_pages, filtro)
    await _edit_or_send(query, texto, kb)


# ═══════════════════════════════════════════════
# DETALHE
# ═══════════════════════════════════════════════
async def admin_user_v2_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not is_admin(update.effective_user.id):
        return

    try:
        user_id = int(query.data.split(":")[2])
    except (IndexError, ValueError):
        return

    u = await db.get_user(user_id)
    if not u:
        await _edit_or_send(query, "❌ Usuário não encontrado.", menus.admin_back_kb())
        return

    stats = await db.user_stats(user_id)
    aff_stats = await db.affiliate_stats(user_id)
    compras_qtd = await db.admin_user_purchases_count(user_id)
    saques_qtd = await db.admin_user_withdrawals_count(user_id)

    banned = bool(u.get("banned"))
    is_aff = bool(u.get("is_affiliate"))
    tem_senha = bool(u.get("payout_password"))

    ban_icon = "🚫 Banido" if banned else "✅ Ativo"
    aff_icon = "🤝 Afiliado" if is_aff else "—"

    ban_line = ""
    if banned:
        motivo = u.get("ban_reason") if "ban_reason" in u.keys() else None
        ate = u.get("banned_until") if "banned_until" in u.keys() else None
        ban_line = "\n🚫 <b>Banimento:</b>\n"
        if motivo:
            ban_line += f"├ Motivo: <i>{motivo}</i>\n"
        if ate:
            ban_line += f"└ Até: <b>{str(ate)[:16]}</b>"
        else:
            ban_line += "└ <b>Permanente</b>"
        ban_line += "\n"

    texto = (
        f"👤 <b>Detalhes do Usuário</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"🆔 ID: <code>{u['user_id']}</code>\n"
        f"📛 Nome: <b>{u.get('first_name') or '—'}</b>\n"
        f"🔗 @{u.get('username') or '—'}\n"
        f"📊 Status: {ban_icon} · {aff_icon}\n"
        f"{ban_line}\n"
        "💰 <b>Saldos:</b>\n"
        f"├ Bot: <b>R$ {float(u.get('balance') or 0):.2f}</b>\n"
        f"└ Loja Web: <b>R$ {float(u.get('balance_web') or 0):.2f}</b>\n\n"
        f"📱 WhatsApp: <code>{u.get('whatsapp') or '—'}</code>\n"
        f"🔐 Senha de saque: <b>{'✅ Cadastrada' if tem_senha else '❌ Não'}</b>\n\n"
        "📈 <b>Movimentações:</b>\n"
        f"├ 🛒 Compras: <b>{stats['compras']}</b>\n"
        f"├ 💰 Gasto: <b>R$ {stats['gasto']:.2f}</b>\n"
        f"├ 💠 PIX inseridos: <b>R$ {stats['pix_inseridos']:.2f}</b>\n"
        f"└ 🎁 Gifts: <b>R$ {stats['gifts_valor']:.2f}</b>\n\n"
        "🤝 <b>Afiliado:</b>\n"
        f"├ 👥 Indicados: <b>{aff_stats['indicados']}</b>\n"
        f"├ 🪙 Ganho: <b>R$ {aff_stats['total_ganho']:.2f}</b>\n"
        f"├ 💸 Saques: <b>{saques_qtd}</b>\n"
        f"└ 📦 Pedidos: <b>{compras_qtd}</b>\n\n"
        f"📅 Cadastrado: <b>{str(u.get('created_at') or '')[:16]}</b>"
    )

    kb = menus.admin_user_v2_kb(user_id, banned, is_aff, tem_senha, "todos")
    await _edit_or_send(query, texto, kb)


# ═══════════════════════════════════════════════
# SALDO — Add / Rem / Set / Zero
# ═══════════════════════════════════════════════
async def admin_usr_add_prompt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await _saldo_prompt(update, context, "add")


async def admin_usr_rem_prompt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await _saldo_prompt(update, context, "rem")


async def admin_usr_set_prompt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await _saldo_prompt(update, context, "set")


async def _saldo_prompt(update, context, tipo: str):
    query = update.callback_query
    await query.answer()
    if not is_admin(update.effective_user.id):
        return

    try:
        user_id = int(query.data.split(":")[2])
    except (IndexError, ValueError):
        return

    u = await db.get_user(user_id)
    if not u:
        return

    labels = {
        "add": ("➕ <b>Adicionar Saldo</b>", "Envie o valor a SOMAR"),
        "rem": ("➖ <b>Remover Saldo</b>", "Envie o valor a SUBTRAIR"),
        "set": ("✏️ <b>Setar Saldo Exato</b>", "Envie o valor que ficará"),
    }
    titulo, instrucao = labels[tipo]

    context.user_data["admin_usr_saldo"] = {"user_id": user_id, "tipo": tipo}
    context.user_data["_usr_saldo_prompt_id"] = query.message.message_id
    context.user_data["_usr_saldo_prompt_chat"] = query.message.chat_id

    try:
        await query.edit_message_text(
            f"{titulo}\n"
            "━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"👤 User: <code>{user_id}</code>\n"
            f"💰 Saldo atual: <b>R$ {float(u.get('balance') or 0):.2f}</b>\n\n"
            f"📝 {instrucao} (ex: <code>10.50</code>)\n\n"
            "Envie <code>/cancelar</code> para sair.",
            reply_markup=ForceReply(selective=True),
            parse_mode=ParseMode.HTML,
        )
    except Exception:
        pass


async def admin_usr_saldo_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    info = context.user_data.get("admin_usr_saldo")
    if not info:
        return
    if not is_admin(update.effective_user.id):
        return

    texto = (update.message.text or "").strip().replace(",", ".")

    try:
        await update.message.delete()
    except Exception:
        pass

    if texto.startswith("/"):
        context.user_data.pop("admin_usr_saldo", None)
        await _delete_prompt(context, "_usr_saldo_prompt_id", "_usr_saldo_prompt_chat")
        return

    try:
        valor = float(texto)
        if valor < 0:
            raise ValueError
    except ValueError:
        await _edit_prompt_error(
            context,
            "_usr_saldo_prompt_id", "_usr_saldo_prompt_chat",
            "❌ Valor inválido.\n\nEnvie um número positivo (ex: <code>10.50</code>):",
            ForceReply(selective=True),
        )
        return

    user_id = info["user_id"]
    tipo = info["tipo"]

    if tipo == "add":
        await db.update_balance(user_id, valor)
        acao = f"➕ R$ {valor:.2f} adicionados"
    elif tipo == "rem":
        await db.update_balance(user_id, -valor)
        acao = f"➖ R$ {valor:.2f} removidos"
    else:
        await db.admin_set_balance_exact(user_id, valor)
        acao = f"✏️ Saldo setado para R$ {valor:.2f}"

    context.user_data.pop("admin_usr_saldo", None)
    await _delete_prompt(context, "_usr_saldo_prompt_id", "_usr_saldo_prompt_chat")

    u = await db.get_user(user_id)
    await db.log_admin_action(
        update.effective_user.id, f"usr_{tipo}_saldo", str(user_id), f"R$ {valor:.2f}"
    )

    # Notifica o user (opcional)
    try:
        emoji = {"add": "💰", "rem": "➖", "set": "✏️"}[tipo]
        await context.bot.send_message(
            chat_id=user_id,
            text=(
                f"{emoji} <b>Seu saldo foi atualizado</b>\n\n"
                f"💰 Novo saldo: <b>R$ {float(u.get('balance') or 0):.2f}</b>"
            ),
            parse_mode=ParseMode.HTML,
        )
    except Exception:
        pass

    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=(
            f"✅ <b>Saldo atualizado!</b>\n\n"
            f"👤 User: <code>{user_id}</code>\n"
            f"{acao}\n"
            f"💰 Novo saldo: <b>R$ {float(u.get('balance') or 0):.2f}</b>"
        ),
        reply_markup=menus.admin_back_kb(),
        parse_mode=ParseMode.HTML,
    )


async def admin_usr_zero_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not is_admin(update.effective_user.id):
        return

    try:
        user_id = int(query.data.split(":")[2])
    except (IndexError, ValueError):
        return

    u = await db.get_user(user_id)
    if not u:
        return

    texto = (
        "⚠️ <b>Zerar saldo?</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"👤 User: <code>{user_id}</code>\n"
        f"💰 Saldo atual: <b>R$ {float(u.get('balance') or 0):.2f}</b>\n\n"
        "Essa ação não pode ser desfeita."
    )

    kb = menus.InlineKeyboardMarkup([
        [menus.InlineKeyboardButton("🧹 Sim, zerar", callback_data=f"admin:usr_zero_yes:{user_id}")],
        [menus.InlineKeyboardButton("❌ Cancelar", callback_data=f"admin:user_v2:{user_id}")],
    ])
    await _edit_or_send(query, texto, kb)


async def admin_usr_zero_yes_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not is_admin(update.effective_user.id):
        return

    try:
        user_id = int(query.data.split(":")[2])
    except (IndexError, ValueError):
        return

    await db.admin_zero_balance(user_id)
    await db.log_admin_action(update.effective_user.id, "usr_zero_saldo", str(user_id))

    await query.answer("🧹 Saldo zerado!", show_alert=True)
    query.data = f"admin:user_v2:{user_id}"
    await admin_user_v2_cb(update, context)


# ═══════════════════════════════════════════════
# MENSAGEM DIRETA
# ═══════════════════════════════════════════════
async def admin_usr_msg_prompt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not is_admin(update.effective_user.id):
        return

    try:
        user_id = int(query.data.split(":")[2])
    except (IndexError, ValueError):
        return

    context.user_data["admin_usr_msg"] = user_id

    try:
        await query.edit_message_text(
            f"✉️ <b>Enviar mensagem</b>\n"
            "━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"👤 User: <code>{user_id}</code>\n\n"
            "Envie o texto (aceita HTML):\n\n"
            "Envie <code>/cancelar</code> para sair.",
            reply_markup=ForceReply(selective=True),
            parse_mode=ParseMode.HTML,
        )
    except Exception:
        pass


async def admin_usr_msg_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = context.user_data.get("admin_usr_msg")
    if not user_id:
        return
    if not is_admin(update.effective_user.id):
        return

    texto = (update.message.text or "").strip()

    try:
        await update.message.delete()
    except Exception:
        pass

    if texto.startswith("/"):
        context.user_data.pop("admin_usr_msg", None)
        return

    if not texto:
        return

    context.user_data.pop("admin_usr_msg", None)

    try:
        await context.bot.send_message(
            chat_id=user_id, text=texto, parse_mode=ParseMode.HTML,
        )
        await db.log_admin_action(update.effective_user.id, "usr_direct_msg", str(user_id))
        await update.message.reply_text(
            f"✅ Mensagem enviada para <code>{user_id}</code>.",
            reply_markup=menus.admin_back_kb(),
            parse_mode=ParseMode.HTML,
        )
    except Exception as e:
        await update.message.reply_text(f"❌ Erro: {e}")


# ═══════════════════════════════════════════════
# HISTÓRICOS
# ═══════════════════════════════════════════════
async def admin_usr_hist_compras_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not is_admin(update.effective_user.id):
        return

    try:
        user_id = int(query.data.split(":")[2])
    except (IndexError, ValueError):
        return

    compras = await db.admin_user_purchases_preview(user_id, limit=8)
    total = await db.admin_user_purchases_count(user_id)

    if not compras:
        texto = f"📜 <b>Compras do user {user_id}</b>\n\n<i>Nenhuma compra.</i>"
    else:
        linhas = [f"📜 <b>Compras ({total})</b> — últimas 8\n"]
        for c in compras:
            icon = "🟢" if (c.get("status") or "active") != "cancelled" else "🔴"
            linhas.append(
                f"{icon} <b>{c['product_name'][:30]}</b>\n"
                f"   💰 R$ {float(c['total']):.2f} · {str(c.get('created_at') or '')[:10]}\n"
            )
        texto = "\n".join(linhas)

    kb = menus.InlineKeyboardMarkup([
        [menus.InlineKeyboardButton("⬅️ Voltar", callback_data=f"admin:user_v2:{user_id}")],
    ])
    await _edit_or_send(query, texto, kb)


async def admin_usr_hist_saques_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not is_admin(update.effective_user.id):
        return

    try:
        user_id = int(query.data.split(":")[2])
    except (IndexError, ValueError):
        return

    saques = await db.admin_user_withdrawals_preview(user_id, limit=8)
    total = await db.admin_user_withdrawals_count(user_id)

    if not saques:
        texto = f"💸 <b>Saques do user {user_id}</b>\n\n<i>Nenhum saque.</i>"
    else:
        linhas = [f"💸 <b>Saques ({total})</b> — últimos 8\n"]
        for s in saques:
            icon = {"pending": "🟡", "processed": "🟢", "rejected": "🔴"}.get(s.get("status"), "⚪")
            linhas.append(
                f"{icon} R$ {float(s['amount']):.2f} · {str(s.get('created_at') or '')[:10]}\n"
                f"   🔑 <code>{(s.get('pix_key') or '—')[:30]}</code>\n"
            )
        texto = "\n".join(linhas)

    kb = menus.InlineKeyboardMarkup([
        [menus.InlineKeyboardButton("⬅️ Voltar", callback_data=f"admin:user_v2:{user_id}")],
    ])
    await _edit_or_send(query, texto, kb)


# ═══════════════════════════════════════════════
# AFILIADO
# ═══════════════════════════════════════════════
async def admin_usr_aff_on_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not is_admin(update.effective_user.id):
        return

    try:
        user_id = int(query.data.split(":")[2])
    except (IndexError, ValueError):
        return

    await db.admin_set_affiliate(user_id, True)
    await db.log_admin_action(update.effective_user.id, "usr_aff_on", str(user_id))
    await query.answer("✅ Afiliado ativado!", show_alert=True)
    query.data = f"admin:user_v2:{user_id}"
    await admin_user_v2_cb(update, context)


async def admin_usr_aff_off_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not is_admin(update.effective_user.id):
        return

    try:
        user_id = int(query.data.split(":")[2])
    except (IndexError, ValueError):
        return

    await db.admin_set_affiliate(user_id, False)
    await db.log_admin_action(update.effective_user.id, "usr_aff_off", str(user_id))
    await query.answer("🚫 Afiliado desativado!", show_alert=True)
    query.data = f"admin:user_v2:{user_id}"
    await admin_user_v2_cb(update, context)


# ═══════════════════════════════════════════════
# RESETAR SENHA DE SAQUE
# ═══════════════════════════════════════════════
async def admin_usr_reset_pin_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not is_admin(update.effective_user.id):
        return

    try:
        user_id = int(query.data.split(":")[2])
    except (IndexError, ValueError):
        return

    await db.admin_reset_payout_password(user_id)
    await db.log_admin_action(update.effective_user.id, "usr_reset_pin", str(user_id))

    # Notifica o user
    try:
        await context.bot.send_message(
            chat_id=user_id,
            text=(
                "🔓 <b>Senha de saque resetada</b>\n\n"
                "Por segurança, sua senha foi removida.\n"
                "Cadastre uma nova no botão <b>🔐 Cadastrar Senha de Saque</b>."
            ),
            parse_mode=ParseMode.HTML,
        )
    except Exception:
        pass

    await query.answer("🔓 Senha resetada!", show_alert=True)
    query.data = f"admin:user_v2:{user_id}"
    await admin_user_v2_cb(update, context)


# ═══════════════════════════════════════════════
# BAN
# ═══════════════════════════════════════════════
async def admin_usr_ban_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not is_admin(update.effective_user.id):
        return

    try:
        user_id = int(query.data.split(":")[2])
    except (IndexError, ValueError):
        return

    u = await db.get_user(user_id)
    if not u:
        return

    texto = (
        "🚫 <b>Banir usuário</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"👤 <b>{u.get('first_name') or '—'}</b> · <code>{user_id}</code>\n\n"
        "Escolha a <b>duração</b> do banimento:"
    )
    kb = menus.admin_ban_options_kb(user_id)
    await _edit_or_send(query, texto, kb)


async def admin_usr_ban_confirm_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not is_admin(update.effective_user.id):
        return

    try:
        _, _, user_id_s, dur = query.data.split(":")
        user_id = int(user_id_s)
    except (ValueError, IndexError):
        return

    contexto = "1 dia" if dur == "1" else f"{dur} dias" if dur != "perm" else "permanente"

    context.user_data["admin_ban_user"] = {"user_id": user_id, "dur": dur}
    context.user_data["_ban_prompt_id"] = query.message.message_id
    context.user_data["_ban_prompt_chat"] = query.message.chat_id

    try:
        await query.edit_message_text(
            f"🚫 <b>Banimento {contexto}</b>\n"
            "━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"👤 User: <code>{user_id}</code>\n"
            f"⏰ Duração: <b>{contexto}</b>\n\n"
            "📝 <b>Escreva o motivo</b> do banimento (o user verá):\n\n"
            "Envie <code>/cancelar</code> para sair.",
            reply_markup=ForceReply(selective=True),
            parse_mode=ParseMode.HTML,
        )
    except Exception:
        pass


async def admin_usr_ban_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    info = context.user_data.get("admin_ban_user")
    if not info:
        return
    if not is_admin(update.effective_user.id):
        return

    motivo = (update.message.text or "").strip()

    try:
        await update.message.delete()
    except Exception:
        pass

    if motivo.startswith("/"):
        context.user_data.pop("admin_ban_user", None)
        await _delete_prompt(context, "_ban_prompt_id", "_ban_prompt_chat")
        return

    if not motivo:
        await _edit_prompt_error(
            context,
            "_ban_prompt_id", "_ban_prompt_chat",
            "❌ Motivo obrigatório.\n\nEscreva o motivo do banimento:",
            ForceReply(selective=True),
        )
        return

    user_id = info["user_id"]
    dur = info["dur"]

    if dur == "perm":
        dias = None
    else:
        dias = int(dur)

    await db.admin_ban_user_temporary(user_id, dias, motivo)
    context.user_data.pop("admin_ban_user", None)
    await _delete_prompt(context, "_ban_prompt_id", "_ban_prompt_chat")

    await db.log_admin_action(
        update.effective_user.id, "usr_ban", str(user_id),
        f"dur={dur} motivo={motivo[:50]}",
    )

    # Notifica o user
    dur_txt = "permanente" if dias is None else f"por {dias} dia(s)"
    try:
        await context.bot.send_message(
            chat_id=user_id,
            text=(
                "🚫 <b>Você foi banido</b>\n"
                "━━━━━━━━━━━━━━━━━━━━━━━\n\n"
                f"⏰ Duração: <b>{dur_txt}</b>\n\n"
                f"📝 <b>Motivo:</b>\n<i>{motivo}</i>\n\n"
                "Se acha que foi um erro, fale com o suporte."
            ),
            parse_mode=ParseMode.HTML,
        )
    except Exception:
        pass

    try:
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=f"🚫 <b>User {user_id} banido</b> ({dur_txt}).",
            reply_markup=menus.admin_back_kb(),
            parse_mode=ParseMode.HTML,
        )
    except Exception:
        pass


async def admin_usr_unban_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not is_admin(update.effective_user.id):
        return

    try:
        user_id = int(query.data.split(":")[2])
    except (IndexError, ValueError):
        return

    await db.admin_unban_user_full(user_id)
    await db.log_admin_action(update.effective_user.id, "usr_unban", str(user_id))

    try:
        await context.bot.send_message(
            chat_id=user_id,
            text="✅ <b>Você foi desbanido!</b>\n\nPode usar o bot novamente.",
            parse_mode=ParseMode.HTML,
        )
    except Exception:
        pass

    await query.answer("✅ Desbanido!", show_alert=True)
    query.data = f"admin:user_v2:{user_id}"
    await admin_user_v2_cb(update, context)


# ═══════════════════════════════════════════════
# EXPORTAR CSV
# ═══════════════════════════════════════════════
async def admin_users_export_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not is_admin(update.effective_user.id):
        return

    try:
        _, _, filtro = query.data.split(":")
    except ValueError:
        filtro = "todos"

    try:
        csv_text = await db.admin_users_v2_export_csv(filtro)
        if not csv_text or len(csv_text.splitlines()) <= 1:
            await query.answer("📭 Nenhum user neste filtro.", show_alert=True)
            return

        filename = f"usuarios-{filtro}.csv"
        await context.bot.send_document(
            chat_id=query.message.chat_id,
            document=InputFile(csv_text.encode("utf-8"), filename=filename),
            caption=(
                f"📤 <b>Usuários exportados</b>\n"
                f"📡 Filtro: <b>{filtro}</b>\n"
                f"📊 Total: <b>{len(csv_text.splitlines()) - 1}</b>"
            ),
            parse_mode=ParseMode.HTML,
        )
        await db.log_admin_action(update.effective_user.id, "users_export", filtro)
    except Exception as e:
        logger.exception("Erro export users: %s", e)
        await query.answer(f"❌ Erro: {e}", show_alert=True)


# ═══════════════════════════════════════════════
# BUSCA
# ═══════════════════════════════════════════════
async def admin_user_search_prompt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not is_admin(update.effective_user.id):
        return

    context.user_data["admin_await_search"] = True

    try:
        await query.edit_message_text(
            "🔍 <b>Buscar Usuário</b>\n\n"
            "Envie o <b>ID</b>, <b>nome</b> ou <b>@username</b>:",
            reply_markup=ForceReply(selective=True),
            parse_mode=ParseMode.HTML,
        )
    except Exception:
        pass


async def admin_search_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.user_data.get("admin_await_search"):
        return
    if not is_admin(update.effective_user.id):
        return

    term = (update.message.text or "").strip()

    try:
        await update.message.delete()
    except Exception:
        pass

    context.user_data.pop("admin_await_search", None)

    if not term:
        return

    try:
        usuarios = await db.search_users(term)
    except Exception as e:
        await update.message.reply_text(f"❌ Erro: {e}")
        return

    if not usuarios:
        await update.message.reply_text(
            f"❌ Nenhum user com <code>{term}</code>.",
            reply_markup=menus.admin_back_kb(),
            parse_mode=ParseMode.HTML,
        )
        return

    texto = f"🔍 <b>Resultados ({len(usuarios)}):</b>"
    kb = menus.admin_users_v2_kb(usuarios, 0, 1, "todos")
    await update.message.reply_text(texto, reply_markup=kb, parse_mode=ParseMode.HTML)
