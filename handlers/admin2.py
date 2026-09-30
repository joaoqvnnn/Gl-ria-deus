import asyncio
import logging
from telegram import Update, ForceReply
from telegram.constants import ParseMode
from telegram.ext import ContextTypes

from config import ADMIN_IDS
from database import db
from keyboards import menus

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


# ═══════════════════════════════════════════════
# VENDAS
# ═══════════════════════════════════════════════
async def admin_purchases_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not is_admin(update.effective_user.id):
        return

    compras = await db.admin_list_purchases(limit=10)
    total = await db.admin_count_purchases()

    texto = (
        f"🛒 <b>Vendas</b> (mostrando 10 de {total})\n"
        f"━━━━━━━━━━━━━━━━━━━━\n\n"
        "Toque em uma venda pra ver detalhes:"
    )
    await _edit_or_send(query, texto, menus.admin_purchases_kb(compras))


async def admin_purchase_search_prompt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not is_admin(update.effective_user.id):
        return

    context.user_data["admin_purchase_search"] = True

    try:
        await query.edit_message_text(
            "🔍 <b>Buscar pedido</b>\n\n"
            "Envie o <b>ID da compra</b>, <b>user_id</b> ou <b>nome do produto</b>:",
            reply_markup=ForceReply(selective=True),
            parse_mode=ParseMode.HTML,
        )
    except Exception:
        pass


async def admin_purchase_search_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.user_data.get("admin_purchase_search"):
        return
    if not is_admin(update.effective_user.id):
        return

    term = (update.message.text or "").strip()
    context.user_data.pop("admin_purchase_search", None)

    if not term:
        await update.message.reply_text("❌ Termo vazio.")
        return

    compras = await db.admin_search_purchases(term)

    if not compras:
        await update.message.reply_text(
            f"❌ Nenhum pedido encontrado com <b>{term}</b>.",
            reply_markup=menus.admin_back_kb(),
            parse_mode=ParseMode.HTML,
        )
        return

    texto = f"🔍 <b>Busca: {term}</b>\n━━━━━━━━━━━━━━━━━━━━\n\nEncontrados: <b>{len(compras)}</b>"
    await update.message.reply_text(
        texto,
        reply_markup=menus.admin_purchases_kb(compras),
        parse_mode=ParseMode.HTML,
    )


async def admin_purchase_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not is_admin(update.effective_user.id):
        return

    purchase_id = query.data.split(":", 2)[2]
    p = await db.get_purchase(purchase_id)
    if not p:
        await _edit_or_send(query, "❌ Pedido não encontrado.", menus.admin_back_kb())
        return

    status = p.get("status") or "active"
    status_label = "🟢 Ativo" if status != "cancelled" else "🔴 Cancelado"

    texto = (
        f"🛒 <b>Pedido</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n\n"
        f"🎫 ID: <code>{p['id']}</code>\n"
        f"👤 User: <code>{p['user_id']}</code>\n"
        f"⚜️ Produto: <b>{p['product_name']}</b>\n"
        f"📦 Qtd: <b>{p['quantity']}</b>\n"
        f"💰 Total: <b>R$ {float(p['total']):.2f}</b>\n"
        f"📧 Email: <code>{p.get('email') or '—'}</code>\n"
        f"🔐 Senha: <code>{p.get('password') or '—'}</code>\n"
        f"🕐 Comprado: {str(p.get('created_at') or '')[:16]}\n"
        f"📆 Vence: {str(p.get('expires_at') or '')[:10]}\n"
        f"📡 Status: <b>{status_label}</b>"
    )

    await _edit_or_send(
        query, texto,
        menus.admin_purchase_kb(purchase_id, cancelled=(status == "cancelled")),
    )


async def admin_refund_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not is_admin(update.effective_user.id):
        return

    purchase_id = query.data.split(":", 2)[2]
    p = await db.admin_cancel_purchase(purchase_id)

    if not p:
        await _edit_or_send(query, "❌ Pedido não encontrado.", menus.admin_back_kb())
        return

    await db.log_admin_action(
        update.effective_user.id, "refund", purchase_id, f"R$ {float(p['total']):.2f}"
    )

    # Notifica o usuário
    try:
        await context.bot.send_message(
            chat_id=p["user_id"],
            text=(
                f"💸 <b>Reembolso recebido!</b>\n\n"
                f"⚜️ Produto: <b>{p['product_name']}</b>\n"
                f"💰 Valor devolvido: <b>R$ {float(p['total']):.2f}</b>\n\n"
                "O valor já está de volta no seu saldo. ✅"
            ),
            parse_mode=ParseMode.HTML,
        )
    except Exception:
        pass

    await _edit_or_send(
        query,
        f"✅ <b>Reembolso realizado!</b>\n\nR$ {float(p['total']):.2f} devolvido ao usuário.",
        menus.admin_back_kb(),
    )


async def admin_resend_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not is_admin(update.effective_user.id):
        return

    purchase_id = query.data.split(":", 2)[2]
    p = await db.get_purchase(purchase_id)
    if not p:
        return

    try:
        await context.bot.send_message(
            chat_id=p["user_id"],
            text=(
                f"📤 <b>Suas credenciais</b>\n\n"
                f"⚜️ Produto: <b>{p['product_name']}</b>\n"
                f"🎫 ID: <code>{p['id']}</code>\n"
                f"📧 Email: <code>{p.get('email') or '—'}</code>\n"
                f"🔐 Senha: <code>{p.get('password') or '—'}</code>"
            ),
            parse_mode=ParseMode.HTML,
        )
        await _edit_or_send(
            query, "✅ Credenciais reenviadas pro usuário.",
            menus.admin_back_kb(),
        )
    except Exception as e:
        await _edit_or_send(query, f"❌ Erro ao reenviar: {e}", menus.admin_back_kb())


# ═══════════════════════════════════════════════
# GIFT CARDS
# ═══════════════════════════════════════════════
async def admin_gifts_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not is_admin(update.effective_user.id):
        return

    gifts = await db.admin_list_gifts(limit=10)
    total = await db.admin_count_gifts()

    texto = (
        f"🎁 <b>Gift Cards</b> (mostrando 10 de {total})\n"
        f"━━━━━━━━━━━━━━━━━━━━\n\n"
        "Toque em um gift pra ver detalhes:"
    )
    await _edit_or_send(query, texto, menus.admin_gifts_kb(gifts))


async def admin_gift_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not is_admin(update.effective_user.id):
        return

    code = query.data.split(":", 2)[2]
    g = await db.get_gift(code)
    if not g:
        await _edit_or_send(query, "❌ Gift não encontrado.", menus.admin_back_kb())
        return

    tipo = g.get("tipo", "—")
    valor = f"R$ {float(g.get('valor') or 0):.2f}" if tipo == "saldo" else f"Produto ID {g.get('product_id')}"
    resgatado = "✅ Sim" if g.get("redeemed_by") else "❌ Não"

    texto = (
        f"🎁 <b>Gift Card</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n\n"
        f"🔑 Código: <code>{g['code']}</code>\n"
        f"📦 Tipo: <b>{tipo}</b>\n"
        f"💰 Valor: <b>{valor}</b>\n"
        f"👤 Resgatado: <b>{resgatado}</b>\n"
        f"🕐 Criado: {str(g.get('created_at') or '')[:16]}\n"
    )
    if g.get("redeemed_by"):
        texto += f"🎯 Resgatado por: <code>{g['redeemed_by']}</code>\n"
        texto += f"📅 Data: {str(g.get('redeemed_at') or '')[:16]}"

    await _edit_or_send(
        query, texto,
        menus.admin_gift_kb(code, redeemed=bool(g.get("redeemed_by"))),
    )


async def admin_gift_del_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not is_admin(update.effective_user.id):
        return

    code = query.data.split(":", 2)[2]
    await db.admin_delete_gift(code)
    await db.log_admin_action(update.effective_user.id, "gift_delete", code)

    await _edit_or_send(query, f"✅ Gift <code>{code}</code> revogado.", menus.admin_back_kb())


async def admin_gift_create_prompt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not is_admin(update.effective_user.id):
        return

    try:
        await query.edit_message_text(
            "➕ <b>Criar Gift Cards</b>\n\n"
            "Escolha o tipo:",
            reply_markup=menus.admin_gift_type_kb(),
            parse_mode=ParseMode.HTML,
        )
    except Exception:
        pass


async def admin_gift_tipo_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not is_admin(update.effective_user.id):
        return

    tipo = query.data.split(":")[2]  # saldo ou produto
    context.user_data["admin_gift_tipo"] = tipo

    if tipo == "saldo":
        try:
            await query.edit_message_text(
                "💰 <b>Gift de SALDO</b>\n\n"
                "Envie o <b>valor</b> que cada gift vai ter (ex: <code>5.00</code>):",
                reply_markup=ForceReply(selective=True),
                parse_mode=ParseMode.HTML,
            )
        except Exception:
            pass
    else:
        try:
            await query.edit_message_text(
                "🎁 <b>Gift de PRODUTO</b>\n\n"
                "Envie o <b>ID do produto</b> (ex: <code>1</code>):",
                reply_markup=ForceReply(selective=True),
                parse_mode=ParseMode.HTML,
            )
        except Exception:
            pass


async def admin_gift_valor_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    tipo = context.user_data.get("admin_gift_tipo")
    if not tipo:
        return
    if not is_admin(update.effective_user.id):
        return

    text = (update.message.text or "").strip().replace(",", ".")

    if tipo == "saldo":
        try:
            valor = float(text)
            if valor <= 0:
                raise ValueError
        except ValueError:
            await update.message.reply_text("❌ Valor inválido.")
            return
        context.user_data["admin_gift_valor"] = valor
        context.user_data["admin_gift_produto"] = None
    else:
        try:
            pid = int(text)
            prod = await db.get_product(pid)
            if not prod:
                await update.message.reply_text("❌ Produto não encontrado.")
                return
            context.user_data["admin_gift_produto"] = pid
            context.user_data["admin_gift_valor"] = 0
        except ValueError:
            await update.message.reply_text("❌ ID inválido.")
            return

    await update.message.reply_text(
        "🔢 <b>Quantos gift cards quer criar?</b>\n\n"
        "Envie um número (ex: <code>10</code>):",
        reply_markup=ForceReply(selective=True),
        parse_mode=ParseMode.HTML,
    )


async def admin_gift_qtd_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.user_data.get("admin_gift_valor") and not context.user_data.get("admin_gift_produto"):
        return
    if not is_admin(update.effective_user.id):
        return

    text = (update.message.text or "").strip()
    try:
        qtd = int(text)
        if qtd <= 0 or qtd > 200:
            raise ValueError
    except ValueError:
        await update.message.reply_text("❌ Quantidade inválida (1 a 200).")
        return

    tipo = context.user_data.pop("admin_gift_tipo", "saldo")
    valor = context.user_data.pop("admin_gift_valor", 0)
    pid = context.user_data.pop("admin_gift_produto", None)

    codigos = await db.admin_create_gift_batch(
        code_base="LARI",
        quantidade=qtd,
        tipo=tipo,
        valor=valor,
        product_id=pid,
    )

    await db.log_admin_action(
        update.effective_user.id, "gift_create", tipo,
        f"qtd={len(codigos)}",
    )

    # Lista os códigos
    lista = "\n".join(f"<code>{c}</code>" for c in codigos)

    await update.message.reply_text(
        f"✅ <b>{len(codigos)} gift cards criados!</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n\n"
        f"{lista}",
        reply_markup=menus.admin_back_kb(),
        parse_mode=ParseMode.HTML,
    )


# ═══════════════════════════════════════════════
# SAQUES
# ═══════════════════════════════════════════════
async def admin_withdrawals_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not is_admin(update.effective_user.id):
        return

    wds = await db.admin_list_withdrawals(limit=10)
    pendentes = await db.admin_count_withdrawals("pending")

    texto = (
        f"💸 <b>Saques</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n\n"
        f"⏳ Pendentes: <b>{pendentes}</b>\n"
        f"📋 Últimos 10:"
    )
    await _edit_or_send(query, texto, menus.admin_withdrawals_kb(wds))


async def admin_withdrawal_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not is_admin(update.effective_user.id):
        return

    wid = query.data.split(":", 2)[2]
    w = await db.admin_get_withdrawal(wid)
    if not w:
        await _edit_or_send(query, "❌ Saque não encontrado.", menus.admin_back_kb())
        return

    u = await db.get_user(w["user_id"])
    nome = u.get("first_name") if u else "—"

    status_icon = {
        "pending": "⏳ Pendente",
        "processed": "✅ Processado",
        "rejected": "❌ Rejeitado",
    }.get(w.get("status"), "—")

    texto = (
        f"💸 <b>Saque</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n\n"
        f"🎫 ID: <code>{w['id']}</code>\n"
        f"👤 Usuário: <b>{nome}</b> (<code>{w['user_id']}</code>)\n"
        f"💰 Valor: <b>R$ {float(w['amount']):.2f}</b>\n"
        f"🔑 Chave: <code>{w.get('pix_key') or '—'}</code>\n"
        f"📦 Tipo: <b>{w.get('pix_key_type') or '—'}</b>\n"
        f"📅 Solicitado: {str(w.get('created_at') or '')[:16]}\n"
        f"📡 Status: <b>{status_icon}</b>"
    )

    await _edit_or_send(
        query, texto,
        menus.admin_withdrawal_kb(wid, w.get("status", "pending")),
    )


async def admin_wd_approve_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not is_admin(update.effective_user.id):
        return

    wid = query.data.split(":", 2)[2]
    w = await db.admin_approve_withdrawal(wid)

    if not w:
        await _edit_or_send(query, "❌ Saque não encontrado.", menus.admin_back_kb())
        return

    await db.log_admin_action(
        update.effective_user.id, "withdrawal_approve", wid, f"R$ {float(w['amount']):.2f}"
    )

    # Notifica o usuário
    try:
        await context.bot.send_message(
            chat_id=w["user_id"],
            text=(
                f"✅ <b>Pagamento realizado!</b>\n\n"
                f"💰 Valor: <b>R$ {float(w['amount']):.2f}</b>\n"
                f"🔑 Chave: <code>{w.get('pix_key') or '—'}</code>"
            ),
            parse_mode=ParseMode.HTML,
        )
    except Exception:
        pass

    await _edit_or_send(
        query,
        f"✅ <b>Saque aprovado!</b>\n\nR$ {float(w['amount']):.2f} pra <code>{w['pix_key']}</code>",
        menus.admin_back_kb(),
    )


async def admin_wd_reject_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not is_admin(update.effective_user.id):
        return

    wid = query.data.split(":", 2)[2]
    w = await db.admin_reject_withdrawal(wid)

    if not w:
        await _edit_or_send(query, "❌ Saque não encontrado.", menus.admin_back_kb())
        return

    await db.log_admin_action(update.effective_user.id, "withdrawal_reject", wid)

    try:
        await context.bot.send_message(
            chat_id=w["user_id"],
            text=(
                f"❌ <b>Saque rejeitado</b>\n\n"
                f"💰 Valor: R$ {float(w['amount']):.2f}\n"
                "O valor continua no seu saldo."
            ),
            parse_mode=ParseMode.HTML,
        )
    except Exception:
        pass

    await _edit_or_send(
        query, "❌ <b>Saque rejeitado.</b>", menus.admin_back_kb(),
    )


# ═══════════════════════════════════════════════
# AFILIADOS
# ═══════════════════════════════════════════════
async def admin_affiliates_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not is_admin(update.effective_user.id):
        return

    afiliados = await db.admin_top_affiliates(10)

    texto = (
        "👥 <b>Afiliados</b>\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
        "Top 10 por comissão gerada:"
    )
    await _edit_or_send(query, texto, menus.admin_affiliates_kb(afiliados))


async def admin_affiliate_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not is_admin(update.effective_user.id):
        return

    target_id = int(query.data.split(":")[2])
    u = await db.get_user(target_id)
    if not u:
        await _edit_or_send(query, "❌ Usuário não encontrado.", menus.admin_back_kb())
        return

    stats = await db.affiliate_stats(target_id)
    ativo = bool(u.get("is_affiliate"))

    texto = (
        f"👤 <b>Afiliado</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n\n"
        f"🆔 ID: <code>{target_id}</code>\n"
        f"📛 Nome: <b>{u.get('first_name') or '—'}</b>\n"
        f"⚙️ Status: <b>{'✅ Ativo' if ativo else '❌ Inativo'}</b>\n\n"
        f"👥 Indicações: <b>{stats['indicados']}</b>\n"
        f"🪙 Total ganho: <b>R$ {stats['total_ganho']:.2f}</b>\n"
        f"📊 Média: <b>R$ {stats['media']:.2f}</b>"
    )

    await _edit_or_send(query, texto, menus.admin_affiliate_kb(target_id, ativo))


async def admin_aff_on_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not is_admin(update.effective_user.id):
        return

    target_id = int(query.data.split(":")[2])
    await db.admin_set_affiliate(target_id, True)
    await db.log_admin_action(update.effective_user.id, "affiliate_on", str(target_id))

    await admin_affiliate_cb(update, context)


async def admin_aff_off_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not is_admin(update.effective_user.id):
        return

    target_id = int(query.data.split(":")[2])
    await db.admin_set_affiliate(target_id, False)
    await db.log_admin_action(update.effective_user.id, "affiliate_off", str(target_id))

    await admin_affiliate_cb(update, context)
