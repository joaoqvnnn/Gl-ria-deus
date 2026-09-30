"""
Módulo ADMIN — SAQUES (v2 — completo, com motivo, PDF, filtros).
"""
import logging
from telegram import Update, ForceReply, InputFile
from telegram.constants import ParseMode
from telegram.ext import ContextTypes

from config import ADMIN_IDS, BOT_HANDLE, STORE_NAME
from database import db
from keyboards import menus
from services import pdf_gen

logger = logging.getLogger(__name__)

SAQUES_PAGE_SIZE = 8


def is_admin(user_id: int) -> bool:
    return user_id in ADMIN_IDS


async def _edit_or_send(query, text: str, kb=None):
    try:
        await query.edit_message_text(text, reply_markup=kb, parse_mode=ParseMode.HTML)
    except Exception:
        await query.message.reply_text(text, reply_markup=kb, parse_mode=ParseMode.HTML)


# ═══════════════════════════════════════════════
# LISTA
# ═══════════════════════════════════════════════
async def admin_saques_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not is_admin(update.effective_user.id):
        return
    await _render_saques(query, status="pending", page=0)


async def admin_saques_page_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not is_admin(update.effective_user.id):
        return
    try:
        _, _, status, page = query.data.split(":")
        page = int(page)
    except (ValueError, IndexError):
        return
    await _render_saques(query, status=status, page=page)


async def admin_saques_filtro_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not is_admin(update.effective_user.id):
        return
    try:
        status = query.data.split(":")[2]
    except IndexError:
        status = "todos"
    await _render_saques(query, status=status, page=0)


async def _render_saques(query, status: str = "todos", page: int = 0):
    total = await db.admin_wd_count_v2(status)
    stats = await db.admin_wd_stats_v2()

    total_pages = max((total + SAQUES_PAGE_SIZE - 1) // SAQUES_PAGE_SIZE, 1)
    page = min(max(page, 0), total_pages - 1)

    wds = await db.admin_wd_list_v2(
        status=status, limit=SAQUES_PAGE_SIZE, offset=page * SAQUES_PAGE_SIZE,
    )

    status_label = {
        "pending": "🟡 Pendentes",
        "processed": "🟢 Processados",
        "rejected": "🔴 Rejeitados",
        "todos": "📋 Todos",
    }.get(status, status)

    texto = (
        "💸 <b>Gerenciar Saques</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"📡 Filtro: <b>{status_label}</b>\n\n"
        "📊 <b>Resumo geral:</b>\n"
        f"├ 🟡 Pendentes: <b>{stats['pendentes_qtd']}</b> — R$ {stats['pendentes_valor']:.2f}\n"
        f"├ 🟢 Processados: <b>{stats['processados_qtd']}</b> — R$ {stats['processados_valor']:.2f}\n"
        f"└ 🔴 Rejeitados: <b>{stats['rejeitados_qtd']}</b> — R$ {stats['rejeitados_valor']:.2f}\n\n"
        f"📄 Página <b>{page + 1}/{total_pages}</b> · {total} saque(s)\n\n"
        "👉 Toque em um saque para gerenciar:"
    )

    kb = menus.admin_saques_kb(wds, page, total_pages, status)
    await _edit_or_send(query, texto, kb)


# ═══════════════════════════════════════════════
# DETALHE
# ═══════════════════════════════════════════════
async def admin_saque_detalhe_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not is_admin(update.effective_user.id):
        return

    try:
        wid = query.data.split(":", 2)[2]
    except (IndexError, ValueError):
        return

    w = await db.admin_get_withdrawal(wid)
    if not w:
        await _edit_or_send(query, "❌ Saque não encontrado.", menus.admin_back_kb())
        return

    u = await db.get_user(w["user_id"])
    nome = (u or {}).get("first_name") or "—"
    username = (u or {}).get("username") or "—"

    status_icon = {
        "pending": "🟡 Pendente",
        "processed": "🟢 Processado",
        "rejected": "🔴 Rejeitado",
    }.get(w.get("status"), "—")

    motivo = w.get("reject_reason") if "reject_reason" in w.keys() else None

    texto = (
        "💸 <b>Detalhes do Saque</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"🎫 ID: <code>{w['id']}</code>\n"
        f"📡 Status: <b>{status_icon}</b>\n\n"
        "👤 <b>Solicitante:</b>\n"
        f"├ Nome: <b>{nome[:35]}</b>\n"
        f"├ Username: @{username}\n"
        f"└ ID: <code>{w['user_id']}</code>\n\n"
        "💰 <b>Saque:</b>\n"
        f"├ Valor: <b>R$ {float(w['amount']):.2f}</b>\n"
        f"├ Tipo de chave: <b>{w.get('pix_key_type') or '—'}</b>\n"
        f"└ Chave: <code>{w.get('pix_key') or '—'}</code>\n\n"
        "📅 <b>Datas:</b>\n"
        f"├ Solicitado: <b>{str(w.get('created_at') or '')[:16]}</b>\n"
        f"└ Processado: <b>{str(w.get('processed_at') or '—')[:16]}</b>"
    )

    if motivo:
        texto += f"\n\n📝 <b>Motivo da rejeição:</b>\n<i>{motivo}</i>"

    kb = menus.admin_saque_detalhe_kb(wid, w.get("status", "pending"))
    await _edit_or_send(query, texto, kb)


# ═══════════════════════════════════════════════
# APROVAR
# ═══════════════════════════════════════════════
async def admin_saque_ok_prompt_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not is_admin(update.effective_user.id):
        return

    wid = query.data.split(":", 2)[2]
    w = await db.admin_get_withdrawal(wid)
    if not w:
        await query.answer("Não encontrado.", show_alert=True)
        return

    u = await db.get_user(w["user_id"])
    nome = (u or {}).get("first_name") or f"ID {w['user_id']}"

    texto = (
        "✅ <b>Confirmar Aprovação de Saque</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"👤 Cliente: <b>{nome[:35]}</b>\n"
        f"💰 Valor: <b>R$ {float(w['amount']):.2f}</b>\n"
        f"🔑 Chave: <code>{w.get('pix_key') or '—'}</code>\n\n"
        "⚠️ Ao confirmar:\n"
        "├ ✅ Saque marcado como processado\n"
        "├ 💰 Valor debita do saldo do cliente\n"
        "└ 📩 Cliente recebe notificação\n\n"
        "Tem certeza?"
    )

    kb = menus.InlineKeyboardMarkup([
        [menus.InlineKeyboardButton("✅ Sim, aprovar", callback_data=f"admin:saque_ok_confirm:{wid}")],
        [menus.InlineKeyboardButton("❌ Cancelar", callback_data=f"admin:saque:{wid}")],
    ])
    await _edit_or_send(query, texto, kb)


async def admin_saque_ok_confirm_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not is_admin(update.effective_user.id):
        return

    wid = query.data.split(":", 2)[2]
    w = await db.admin_approve_withdrawal(wid)
    if not w:
        await query.answer("❌ Não encontrado.", show_alert=True)
        return

    await db.log_admin_action(
        update.effective_user.id, "withdrawal_approve", wid,
        f"R$ {float(w['amount']):.2f}",
    )

    # Notifica o cliente
    try:
        await context.bot.send_message(
            chat_id=w["user_id"],
            text=(
                "✅ <b>Pagamento Realizado!</b>\n"
                "━━━━━━━━━━━━━━━━━━━━━━━\n\n"
                f"💰 Valor: <b>R$ {float(w['amount']):.2f}</b>\n"
                f"🔑 Chave PIX: <code>{w.get('pix_key') or '—'}</code>\n"
                f"🎫 ID: <code>{w['id']}</code>\n\n"
                "Obrigado por confiar na nossa loja! 💙"
            ),
            parse_mode=ParseMode.HTML,
        )
    except Exception:
        pass

    await _edit_or_send(
        query,
        f"✅ <b>Saque aprovado!</b>\n\n"
        f"💰 R$ {float(w['amount']):.2f} para <code>{w['user_id']}</code>.",
        menus.admin_back_kb(),
    )


# ═══════════════════════════════════════════════
# REJEITAR (com motivo obrigatório)
# ═══════════════════════════════════════════════
async def admin_saque_no_prompt_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not is_admin(update.effective_user.id):
        return

    wid = query.data.split(":", 2)[2]
    w = await db.admin_get_withdrawal(wid)
    if not w:
        await query.answer("Não encontrado.", show_alert=True)
        return

    context.user_data["admin_saque_reject_wid"] = wid
    context.user_data["_saque_reject_prompt_id"] = query.message.message_id
    context.user_data["_saque_reject_prompt_chat"] = query.message.chat_id

    try:
        await query.edit_message_text(
            "❌ <b>Rejeitar Saque</b>\n"
            "━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"💰 Valor: <b>R$ {float(w['amount']):.2f}</b>\n"
            f"🔑 Chave: <code>{w.get('pix_key') or '—'}</code>\n\n"
            "📝 <b>Escreva o motivo da rejeição</b> abaixo.\n\n"
            "💡 <i>O cliente vai receber esse motivo por mensagem.</i>\n\n"
            "Envie <code>/cancelar</code> para sair.",
            reply_markup=ForceReply(selective=True),
            parse_mode=ParseMode.HTML,
        )
    except Exception:
        pass


async def admin_saque_no_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    wid = context.user_data.get("admin_saque_reject_wid")
    if not wid:
        return
    if not is_admin(update.effective_user.id):
        return

    motivo = (update.message.text or "").strip()

    # Apaga a msg do admin (privacidade do fluxo)
    try:
        await update.message.delete()
    except Exception:
        pass

    if motivo.startswith("/"):
        context.user_data.pop("admin_saque_reject_wid", None)
        return

    if not motivo:
        # Erro → edita o prompt pedindo de novo
        await _edit_prompt_error(
            context,
            "❌ Motivo vazio.\n\nEnvie o motivo da rejeição:",
        )
        return

    # Salva motivo + rejeita
    await db.admin_wd_set_reject_reason(wid, motivo)
    w = await db.admin_reject_withdrawal(wid)
    context.user_data.pop("admin_saque_reject_wid", None)

    if not w:
        await _delete_prompt(context)
        return

    await db.log_admin_action(
        update.effective_user.id, "withdrawal_reject", wid, motivo[:80],
    )

    # Notifica o cliente
    try:
        await context.bot.send_message(
            chat_id=w["user_id"],
            text=(
                "❌ <b>Saque Rejeitado</b>\n"
                "━━━━━━━━━━━━━━━━━━━━━━━\n\n"
                f"💰 Valor: <b>R$ {float(w['amount']):.2f}</b>\n\n"
                f"📝 <b>Motivo:</b>\n<i>{motivo}</i>\n\n"
                "O valor continua disponível no seu saldo.\n"
                "Entre em contato com o suporte se tiver dúvidas."
            ),
            parse_mode=ParseMode.HTML,
        )
    except Exception:
        pass

    await _delete_prompt(context)

    try:
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=f"❌ <b>Saque rejeitado.</b>\n\n📝 Motivo enviado: <i>{motivo[:80]}</i>",
            reply_markup=menus.admin_back_kb(),
            parse_mode=ParseMode.HTML,
        )
    except Exception:
        pass


# ═══════════════════════════════════════════════
# COMPROVANTE PDF
# ═══════════════════════════════════════════════
async def admin_saque_pdf_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not is_admin(update.effective_user.id):
        return

    wid = query.data.split(":", 2)[2]
    w = await db.admin_get_withdrawal(wid)
    if not w:
        await query.answer("Não encontrado.", show_alert=True)
        return

    u = await db.get_user(w["user_id"])
    if not u:
        await query.answer("Usuário não encontrado.", show_alert=True)
        return

    try:
        pdf_bytes = pdf_gen.gerar_comprovante_saque(w, u, STORE_NAME)
        filename = f"comprovante-{wid[:8]}.pdf"

        # Envia pro admin
        await context.bot.send_document(
            chat_id=query.message.chat_id,
            document=InputFile(io.BytesIO(pdf_bytes), filename=filename),
            caption="📄 Comprovante gerado. Enviado pro cliente também.",
        )

        # Envia pro cliente
        try:
            await context.bot.send_document(
                chat_id=w["user_id"],
                document=InputFile(io.BytesIO(pdf_bytes), filename=filename),
                caption=(
                    "📄 <b>Comprovante de Saque</b>\n\n"
                    f"💰 Valor: <b>R$ {float(w['amount']):.2f}</b>\n"
                    "Guarde este documento em local seguro."
                ),
                parse_mode=ParseMode.HTML,
            )
        except Exception:
            pass

        await db.log_admin_action(update.effective_user.id, "withdrawal_pdf", wid)
    except Exception as e:
        logger.exception("Erro gerando PDF: %s", e)
        await query.answer(f"❌ Erro: {e}", show_alert=True)


# ═══════════════════════════════════════════════
# AVISAR CLIENTE
# ═══════════════════════════════════════════════
async def admin_saque_notify_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not is_admin(update.effective_user.id):
        return

    wid = query.data.split(":", 2)[2]
    w = await db.admin_get_withdrawal(wid)
    if not w:
        await query.answer("Não encontrado.", show_alert=True)
        return

    status = w.get("status", "pending")
    if status == "processed":
        msg = (
            "✅ <b>Seu saque foi processado!</b>\n\n"
            f"💰 Valor: <b>R$ {float(w['amount']):.2f}</b>\n"
            f"🔑 Chave: <code>{w.get('pix_key') or '—'}</code>\n\n"
            "Se não recebeu, entre em contato com o suporte."
        )
    elif status == "rejected":
        motivo = w.get("reject_reason") or "Não informado"
        msg = (
            "❌ <b>Saque rejeitado</b>\n\n"
            f"💰 Valor: <b>R$ {float(w['amount']):.2f}</b>\n\n"
            f"📝 <b>Motivo:</b>\n<i>{motivo}</i>"
        )
    else:
        msg = (
            "⏳ <b>Seu saque está em análise</b>\n\n"
            f"💰 Valor: <b>R$ {float(w['amount']):.2f}</b>\n\n"
            "Aguarde, em breve processaremos."
        )

    try:
        await context.bot.send_message(
            chat_id=w["user_id"], text=msg, parse_mode=ParseMode.HTML,
        )
        await query.answer("✅ Cliente notificado!", show_alert=True)
    except Exception as e:
        await query.answer(f"❌ Falha: {e}", show_alert=True)


# ═══════════════════════════════════════════════
# EXPORTAR CSV
# ═══════════════════════════════════════════════
async def admin_saques_export_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not is_admin(update.effective_user.id):
        return

    try:
        _, _, status = query.data.split(":")
    except ValueError:
        status = "todos"

    try:
        csv_text = await db.admin_wd_export_csv_v2(status)
        if not csv_text or len(csv_text.splitlines()) <= 1:
            await query.answer("📭 Nenhum saque neste filtro.", show_alert=True)
            return

        filename = f"saques-{status}.csv"
        await context.bot.send_document(
            chat_id=query.message.chat_id,
            document=InputFile(csv_text.encode("utf-8"), filename=filename),
            caption=(
                f"📤 <b>Saques exportados</b>\n"
                f"📡 Filtro: <b>{status}</b>"
            ),
            parse_mode=ParseMode.HTML,
        )
        await db.log_admin_action(update.effective_user.id, "saques_export", status)
    except Exception as e:
        logger.exception("Erro export saques: %s", e)
        await query.answer(f"❌ Erro: {e}", show_alert=True)


# ═══════════════════════════════════════════════
# BUSCAR POR USER_ID
# ═══════════════════════════════════════════════
async def admin_saque_search_prompt_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not is_admin(update.effective_user.id):
        return

    context.user_data["admin_saque_search"] = True

    try:
        await query.edit_message_text(
            "🔍 <b>Buscar saques por user</b>\n\n"
            "Envie o <b>user_id</b> (só números):",
            reply_markup=ForceReply(selective=True),
            parse_mode=ParseMode.HTML,
        )
    except Exception:
        pass


async def admin_saque_search_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.user_data.get("admin_saque_search"):
        return
    if not is_admin(update.effective_user.id):
        return

    term = (update.message.text or "").strip()

    try:
        await update.message.delete()
    except Exception:
        pass

    context.user_data.pop("admin_saque_search", None)

    if not term.isdigit():
        await update.message.reply_text(
            "❌ Envie apenas números (user_id).",
            reply_markup=menus.admin_back_kb(),
        )
        return

    user_id = int(term)
    wds = await db.admin_wd_search_by_user(user_id, limit=20)

    if not wds:
        await update.message.reply_text(
            f"❌ Nenhum saque encontrado para <code>{user_id}</code>.",
            reply_markup=menus.admin_back_kb(),
            parse_mode=ParseMode.HTML,
        )
        return

    texto = f"🔍 <b>Saques do user {user_id}</b> ({len(wds)}):"
    kb = menus.admin_saques_kb(wds, 0, 1, "todos")
    await update.message.reply_text(texto, reply_markup=kb, parse_mode=ParseMode.HTML)


# ═══════════════════════════════════════════════
# HELPERS
# ═══════════════════════════════════════════════
async def _delete_prompt(context):
    pid = context.user_data.pop("_saque_reject_prompt_id", None)
    chat = context.user_data.pop("_saque_reject_prompt_chat", None)
    if pid and chat:
        try:
            await context.bot.delete_message(chat_id=chat, message_id=pid)
        except Exception:
            pass


async def _edit_prompt_error(context, text: str):
    pid = context.user_data.get("_saque_reject_prompt_id")
    chat = context.user_data.get("_saque_reject_prompt_chat")
    if pid and chat:
        try:
            await context.bot.edit_message_text(
                chat_id=chat, message_id=pid,
                text=text, reply_markup=ForceReply(selective=True),
                parse_mode=ParseMode.HTML,
            )
        except Exception:
            pass


# import necessário no topo
import io
