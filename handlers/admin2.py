import logging
import asyncio
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

    try:
        compras = await db.admin_list_purchases(limit=10)
        total = await db.admin_count_purchases()

        if not compras:
            texto = (
                "🛒 <b>Vendas</b>\n"
                "━━━━━━━━━━━━━━━━━━━━━━━\n\n"
                "<i>Nenhuma venda registrada ainda.</i>"
            )
        else:
            texto = (
                "🛒 <b>Vendas Realizadas</b>\n"
                "━━━━━━━━━━━━━━━━━━━━━━━\n\n"
                f"📊 Total de pedidos: <b>{total}</b>\n"
                f"📋 Mostrando: <b>{len(compras)}</b> mais recentes\n\n"
                "👉 Toque em um pedido para ver detalhes:"
            )
        await _edit_or_send(query, texto, menus.admin_purchases_kb(compras))
    except Exception as e:
        logger.exception("Erro listando vendas: %s", e)
        await _edit_or_send(query, f"❌ Erro: {e}", menus.admin_back_kb())


async def admin_purchase_search_prompt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not is_admin(update.effective_user.id):
        return

    context.user_data["admin_purchase_search"] = True

    try:
        await query.edit_message_text(
            "🔍 <b>Buscar Pedido</b>\n\n"
            "Use o campo abaixo para enviar o <b>ID da compra</b>, "
            "<b>user_id</b> ou <b>nome do produto</b>:",
            parse_mode=ParseMode.HTML,
        )
    except Exception:
        pass

    try:
        await context.bot.send_message(
            chat_id=query.message.chat_id,
            text="👇 <b>Digite aqui:</b>",
            reply_markup=ForceReply(selective=True),
            parse_mode=ParseMode.HTML,
        )
    except Exception as e:
        logger.exception("Erro ForceReply busca pedido: %s", e)


async def admin_purchase_search_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.user_data.get("admin_purchase_search"):
        return
    if not is_admin(update.effective_user.id):
        return

    term = (update.message.text or "").strip()
    context.user_data.pop("admin_purchase_search", None)

    if not term:
        await update.message.reply_text("❌ Termo vazio. Tente novamente.")
        return

    try:
        compras = await db.admin_search_purchases(term)
    except Exception as e:
        logger.exception("Erro na busca de pedidos: %s", e)
        await update.message.reply_text(f"❌ Erro na busca: {e}")
        return

    if not compras:
        await update.message.reply_text(
            f"❌ Nenhum pedido encontrado com <code>{term}</code>.",
            reply_markup=menus.admin_back_kb(),
            parse_mode=ParseMode.HTML,
        )
        return

    texto = (
        "🔍 <b>Resultado da Busca</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"🎯 Termo: <code>{term}</code>\n"
        f"📋 Encontrados: <b>{len(compras)}</b>"
    )
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

    try:
        purchase_id = query.data.split(":", 2)[2]
        p = await db.get_purchase(purchase_id)
        if not p:
            await _edit_or_send(query, "❌ Pedido não encontrado.", menus.admin_back_kb())
            return

        status = p.get("status") or "active"
        status_label = "🟢 Ativo" if status != "cancelled" else "🔴 Cancelado"

        texto = (
            "🛒 <b>Detalhes do Pedido</b>\n"
            "━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"🎫 ID: <code>{p['id']}</code>\n"
            f"👤 Usuário: <code>{p['user_id']}</code>\n"
            f"⚜️ Produto: <b>{p['product_name']}</b>\n"
            f"📦 Quantidade: <b>{p['quantity']}</b>\n"
            f"💰 Total: <b>R$ {float(p['total']):.2f}</b>\n\n"
            f"📧 Email: <code>{p.get('email') or '—'}</code>\n"
            f"🔐 Senha: <code>{p.get('password') or '—'}</code>\n\n"
            f"🕐 Comprado: <b>{str(p.get('created_at') or '')[:16]}</b>\n"
            f"📆 Vence: <b>{str(p.get('expires_at') or '')[:10]}</b>\n"
            f"📡 Status: {status_label}"
        )

        await _edit_or_send(
            query, texto,
            menus.admin_purchase_kb(purchase_id, cancelled=(status == "cancelled")),
        )
    except Exception as e:
        logger.exception("Erro mostrando pedido: %s", e)


async def admin_refund_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not is_admin(update.effective_user.id):
        return

    try:
        purchase_id = query.data.split(":", 2)[2]
        p = await db.admin_cancel_purchase(purchase_id)

        if not p:
            await _edit_or_send(query, "❌ Pedido não encontrado.", menus.admin_back_kb())
            return

        await db.log_admin_action(
            update.effective_user.id, "refund", purchase_id, f"R$ {float(p['total']):.2f}",
        )

        # Notifica o usuário
        try:
            await context.bot.send_message(
                chat_id=p["user_id"],
                text=(
                    "💸 <b>Reembolso Recebido</b>\n"
                    "━━━━━━━━━━━━━━━━━━━━━━━\n\n"
                    f"⚜️ Produto: <b>{p['product_name']}</b>\n"
                    f"💰 Valor devolvido: <b>R$ {float(p['total']):.2f}</b>\n\n"
                    "O valor já está disponível no seu saldo! ✅"
                ),
                parse_mode=ParseMode.HTML,
            )
        except Exception:
            pass

        await _edit_or_send(
            query,
            f"✅ <b>Reembolso Realizado!</b>\n\n"
            f"💰 R$ {float(p['total']):.2f} devolvido ao usuário <code>{p['user_id']}</code>.",
            menus.admin_back_kb(),
        )
    except Exception as e:
        logger.exception("Erro reembolsando: %s", e)


async def admin_resend_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not is_admin(update.effective_user.id):
        return

    try:
        purchase_id = query.data.split(":", 2)[2]
        p = await db.get_purchase(purchase_id)
        if not p:
            return

        await context.bot.send_message(
            chat_id=p["user_id"],
            text=(
                "📤 <b>Suas Credenciais de Acesso</b>\n"
                "━━━━━━━━━━━━━━━━━━━━━━━\n\n"
                f"⚜️ Produto: <b>{p['product_name']}</b>\n"
                f"🎫 ID: <code>{p['id']}</code>\n"
                f"📧 Email: <code>{p.get('email') or '—'}</code>\n"
                f"🔐 Senha: <code>{p.get('password') or '—'}</code>"
            ),
            parse_mode=ParseMode.HTML,
        )

        await _edit_or_send(
            query, "✅ <b>Credenciais reenviadas!</b>", menus.admin_back_kb(),
        )
    except Exception as e:
        logger.exception("Erro reenviando credenciais: %s", e)
        await _edit_or_send(query, f"❌ Erro ao reenviar: {e}", menus.admin_back_kb())


# ═══════════════════════════════════════════════
# GIFT CARDS
# ═══════════════════════════════════════════════
async def admin_gifts_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not is_admin(update.effective_user.id):
        return

    try:
        gifts = await db.admin_list_gifts(limit=10)
        total = await db.admin_count_gifts()

        if not gifts:
            texto = (
                "🎁 <b>Gift Cards</b>\n"
                "━━━━━━━━━━━━━━━━━━━━━━━\n\n"
                "<i>Nenhum gift card criado ainda.</i>\n\n"
                "Toque em ➕ para criar os primeiros!"
            )
        else:
            texto = (
                "🎁 <b>Gift Cards</b>\n"
                "━━━━━━━━━━━━━━━━━━━━━━━\n\n"
                f"📊 Total: <b>{total}</b>\n"
                f"📋 Mostrando: <b>{len(gifts)}</b> mais recentes\n\n"
                "🟢 Livres  🔴 Resgatados\n\n"
                "👉 Toque em um pra ver detalhes:"
            )
        await _edit_or_send(query, texto, menus.admin_gifts_kb(gifts))
    except Exception as e:
        logger.exception("Erro listando gifts: %s", e)
        await _edit_or_send(query, f"❌ Erro: {e}", menus.admin_back_kb())


async def admin_gift_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not is_admin(update.effective_user.id):
        return

    try:
        code = query.data.split(":", 2)[2]
        g = await db.get_gift(code)
        if not g:
            await _edit_or_send(query, "❌ Gift não encontrado.", menus.admin_back_kb())
            return

        tipo = g.get("tipo", "—")
        if tipo == "saldo":
            valor_txt = f"R$ {float(g.get('valor') or 0):.2f}"
        else:
            valor_txt = f"Produto ID {g.get('product_id')}"

        resgatado = "✅ Sim" if g.get("redeemed_by") else "❌ Não"

        texto = (
            "🎁 <b>Detalhes do Gift Card</b>\n"
            "━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"🔑 Código: <code>{g['code']}</code>\n"
            f"📦 Tipo: <b>{tipo}</b>\n"
            f"💰 Valor: <b>{valor_txt}</b>\n"
            f"👤 Resgatado: <b>{resgatado}</b>\n"
            f"🕐 Criado: <b>{str(g.get('created_at') or '')[:16]}</b>"
        )
        if g.get("redeemed_by"):
            texto += f"\n🎯 Resgatado por: <code>{g['redeemed_by']}</code>"
            texto += f"\n📅 Data: <b>{str(g.get('redeemed_at') or '')[:16]}</b>"

        await _edit_or_send(
            query, texto,
            menus.admin_gift_kb(code, redeemed=bool(g.get("redeemed_by"))),
        )
    except Exception as e:
        logger.exception("Erro mostrando gift: %s", e)


async def admin_gift_del_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not is_admin(update.effective_user.id):
        return

    try:
        code = query.data.split(":", 2)[2]
        await db.admin_delete_gift(code)
        await db.log_admin_action(update.effective_user.id, "gift_delete", code)

        await _edit_or_send(
            query,
            f"🗑️ <b>Gift Card Revogado</b>\n\n"
            f"🔑 Código: <code>{code}</code>\n"
            "Não poderá mais ser resgatado.",
            menus.admin_back_kb(),
        )
    except Exception as e:
        logger.exception("Erro revogando gift: %s", e)


async def admin_gift_create_prompt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not is_admin(update.effective_user.id):
        return

    try:
        await query.edit_message_text(
            "➕ <b>Criar Gift Cards</b>\n"
            "━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "Escolha o <b>tipo</b> de gift que será criado:",
            reply_markup=menus.admin_gift_type_kb(),
            parse_mode=ParseMode.HTML,
        )
    except Exception as e:
        logger.exception("Erro abrindo criação de gift: %s", e)


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
                "💰 <b>Gift de Saldo</b>\n\n"
                "Use o campo abaixo para enviar o <b>valor</b> de cada gift "
                "(ex: <code>5.00</code>):",
                parse_mode=ParseMode.HTML,
            )
        except Exception:
            pass

        try:
            await context.bot.send_message(
                chat_id=query.message.chat_id,
                text="👇 <b>Digite o valor:</b>",
                reply_markup=ForceReply(selective=True),
                parse_mode=ParseMode.HTML,
            )
        except Exception:
            pass
    else:
        try:
            await query.edit_message_text(
                "🎁 <b>Gift de Produto</b>\n\n"
                "Use o campo abaixo para enviar o <b>ID do produto</b> "
                "(ex: <code>1</code>):",
                parse_mode=ParseMode.HTML,
            )
        except Exception:
            pass

        try:
            await context.bot.send_message(
                chat_id=query.message.chat_id,
                text="👇 <b>Digite o ID:</b>",
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
                await update.message.reply_text("❌ Produto não encontrado. Tente outro ID.")
                return
            context.user_data["admin_gift_produto"] = pid
            context.user_data["admin_gift_valor"] = 0
        except ValueError:
            await update.message.reply_text("❌ ID inválido.")
            return

    try:
        await update.message.reply_text(
            "🔢 <b>Quantos gift cards devo criar?</b>\n\n"
            "Use o campo abaixo (ex: <code>10</code>), máximo 200:",
            reply_markup=ForceReply(selective=True),
            parse_mode=ParseMode.HTML,
        )
    except Exception as e:
        logger.exception("Erro ForceReply quantidade: %s", e)


async def admin_gift_qtd_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.user_data.get("admin_gift_tipo"):
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

    try:
        codigos = await db.admin_create_gift_batch(
            code_base="LARI",
            quantidade=qtd,
            tipo=tipo,
            valor=valor,
            product_id=pid,
        )
    except Exception as e:
        logger.exception("Erro criando gifts: %s", e)
        await update.message.reply_text(f"❌ Erro: {e}")
        return

    await db.log_admin_action(
        update.effective_user.id, "gift_create", tipo, f"qtd={len(codigos)}",
    )

    lista = "\n".join(f"<code>{c}</code>" for c in codigos)

    await update.message.reply_text(
        f"✅ <b>{len(codigos)} Gift Cards Criados!</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"📦 Tipo: <b>{tipo}</b>\n"
        f"💰 Valor: <b>R$ {valor:.2f}</b>\n\n"
        "🔑 <b>Códigos:</b>\n"
        f"{lista}",
        reply_markup=menus.admin_back_kb(),
        parse_mode=ParseMode.HTML,
    )


# ═══════════════════════════════════════════════
# SAQUES — layout melhorado
# ═══════════════════════════════════════════════
async def admin_withdrawals_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not is_admin(update.effective_user.id):
        return

    try:
        wds = await db.admin_list_withdrawals(limit=10)
        pendentes = await db.admin_count_withdrawals("pending")

        if not wds:
            texto = (
                "💸 <b>Saques</b>\n"
                "━━━━━━━━━━━━━━━━━━━━━━━\n\n"
                "<i>Nenhum saque solicitado ainda.</i>"
            )
        else:
            # Separa por status
            linhas = [
                "💸 <b>Gerenciar Saques</b>",
                "━━━━━━━━━━━━━━━━━━━━━━━\n",
                f"⏳ Pendentes: <b>{pendentes}</b>\n",
                "👉 Toque em um saque para aprovar/rejeitar:\n",
            ]
            for w in wds:
                icon = {
                    "pending": "🟡",
                    "processed": "🟢",
                    "rejected": "🔴",
                }.get(w.get("status"), "⚪")

                # Pega nome do usuário
                u = await db.get_user(w["user_id"])
                nome = (u or {}).get("first_name") or (u or {}).get("username") or f"ID {w['user_id']}"

                # Mostra em NEGRITO conforme pedido
                linhas.append(
                    f"{icon} <b>{nome[:25]}</b> — <b>R$ {float(w['amount']):.2f}</b>"
                )
            texto = "\n".join(linhas)

        await _edit_or_send(query, texto, menus.admin_withdrawals_kb(wds))
    except Exception as e:
        logger.exception("Erro listando saques: %s", e)


async def admin_withdrawal_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not is_admin(update.effective_user.id):
        return

    try:
        wid = query.data.split(":", 2)[2]
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

        texto = (
            "💸 <b>Detalhes do Saque</b>\n"
            "━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"🎫 ID: <code>{w['id']}</code>\n\n"
            "👤 <b>Solicitante:</b>\n"
            f"├ Nome: <b>{nome}</b>\n"
            f"├ Username: @{username}\n"
            f"└ ID: <code>{w['user_id']}</code>\n\n"
            f"💰 Valor: <b>R$ {float(w['amount']):.2f}</b>\n"
            f"🔑 Chave: <code>{w.get('pix_key') or '—'}</code>\n"
            f"📦 Tipo: <b>{w.get('pix_key_type') or '—'}</b>\n\n"
            f"📅 Solicitado: <b>{str(w.get('created_at') or '')[:16]}</b>\n"
            f"📡 Status: <b>{status_icon}</b>"
        )

        await _edit_or_send(
            query, texto,
            menus.admin_withdrawal_kb(wid, w.get("status", "pending")),
        )
    except Exception as e:
        logger.exception("Erro mostrando saque: %s", e)


async def admin_wd_approve_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not is_admin(update.effective_user.id):
        return

    try:
        wid = query.data.split(":", 2)[2]
        w = await db.admin_approve_withdrawal(wid)

        if not w:
            await _edit_or_send(query, "❌ Saque não encontrado.", menus.admin_back_kb())
            return

        await db.log_admin_action(
            update.effective_user.id, "withdrawal_approve", wid,
            f"R$ {float(w['amount']):.2f}",
        )

        try:
            await context.bot.send_message(
                chat_id=w["user_id"],
                text=(
                    "✅ <b>Pagamento Realizado!</b>\n"
                    "━━━━━━━━━━━━━━━━━━━━━━━\n\n"
                    f"💰 Valor: <b>R$ {float(w['amount']):.2f}</b>\n"
                    f"🔑 Chave: <code>{w.get('pix_key') or '—'}</code>\n\n"
                    "Obrigado por confiar na nossa loja! 💙"
                ),
                parse_mode=ParseMode.HTML,
            )
        except Exception:
            pass

        await _edit_or_send(
            query,
            f"✅ <b>Saque Aprovado!</b>\n\n"
            f"💰 R$ {float(w['amount']):.2f}\n"
            f"🔑 Chave: <code>{w['pix_key']}</code>",
            menus.admin_back_kb(),
        )
    except Exception as e:
        logger.exception("Erro aprovando saque: %s", e)


async def admin_wd_reject_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not is_admin(update.effective_user.id):
        return

    try:
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
                    "❌ <b>Saque Rejeitado</b>\n\n"
                    f"💰 Valor: <b>R$ {float(w['amount']):.2f}</b>\n\n"
                    "O valor continua disponível no seu saldo.\n"
                    "Entre em contato com o suporte para mais informações."
                ),
                parse_mode=ParseMode.HTML,
            )
        except Exception:
            pass

        await _edit_or_send(
            query, "❌ <b>Saque Rejeitado.</b>", menus.admin_back_kb(),
        )
    except Exception as e:
        logger.exception("Erro rejeitando saque: %s", e)


# ═══════════════════════════════════════════════
# AFILIADOS — layout melhorado
# ═══════════════════════════════════════════════
async def admin_affiliates_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not is_admin(update.effective_user.id):
        return

    try:
        afiliados = await db.admin_top_affiliates(10)

        if not afiliados:
            texto = (
                "👥 <b>Afiliados</b>\n"
                "━━━━━━━━━━━━━━━━━━━━━━━\n\n"
                "<i>Nenhum afiliado cadastrado ainda.</i>"
            )
        else:
            linhas = [
                "👥 <b>Programa de Afiliados</b>",
                "━━━━━━━━━━━━━━━━━━━━━━━\n",
                "🏆 <b>Top 10 por Comissão Gerada:</b>\n",
            ]
            medals = ["🥇", "🥈", "🥉"]
            for i, a in enumerate(afiliados):
                pos = medals[i] if i < 3 else f"{i+1}º"
                nome = a.get("first_name") or a.get("username") or f"ID {a['user_id']}"
                indicados = int(a.get("indicados") or 0)
                total = float(a.get("total_ganho") or 0)

                # Nome em negrito + dados organizados
                linhas.append(
                    f"{pos} <b>{nome[:28]}</b>\n"
                    f"    ├ 👥 {indicados} indicados\n"
                    f"    └ 💰 R$ {total:.2f}\n"
                )
            texto = "\n".join(linhas)

        await _edit_or_send(query, texto, menus.admin_affiliates_kb(afiliados))
    except Exception as e:
        logger.exception("Erro listando afiliados: %s", e)


async def admin_affiliate_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not is_admin(update.effective_user.id):
        return

    try:
        target_id = int(query.data.split(":")[2])
        u = await db.get_user(target_id)
        if not u:
            await _edit_or_send(query, "❌ Usuário não encontrado.", menus.admin_back_kb())
            return

        stats = await db.affiliate_stats(target_id)
        ativo = bool(u.get("is_affiliate"))

        texto = (
            "👤 <b>Detalhes do Afiliado</b>\n"
            "━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"🆔 ID: <code>{target_id}</code>\n"
            f"📛 Nome: <b>{u.get('first_name') or '—'}</b>\n"
            f"🔗 @{u.get('username') or '—'}\n"
            f"⚙️ Status: <b>{'✅ Ativo' if ativo else '❌ Inativo'}</b>\n\n"
            "📊 <b>Estatísticas:</b>\n"
            f"├ 👥 Indicações: <b>{stats['indicados']}</b>\n"
            f"├ 🪙 Total ganho: <b>R$ {stats['total_ganho']:.2f}</b>\n"
            f"└ 📊 Média: <b>R$ {stats['media']:.2f}</b>"
        )

        await _edit_or_send(query, texto, menus.admin_affiliate_kb(target_id, ativo))
    except Exception as e:
        logger.exception("Erro mostrando afiliado: %s", e)


async def admin_aff_on_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not is_admin(update.effective_user.id):
        return

    try:
        target_id = int(query.data.split(":")[2])
        await db.admin_set_affiliate(target_id, True)
        await db.log_admin_action(update.effective_user.id, "affiliate_on", str(target_id))
    except Exception as e:
        logger.exception("Erro ativando afiliado: %s", e)

    await admin_affiliate_cb(update, context)


async def admin_aff_off_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not is_admin(update.effective_user.id):
        return

    try:
        target_id = int(query.data.split(":")[2])
        await db.admin_set_affiliate(target_id, False)
        await db.log_admin_action(update.effective_user.id, "affiliate_off", str(target_id))
    except Exception as e:
        logger.exception("Erro desativando afiliado: %s", e)

    await admin_affiliate_cb(update, context)
