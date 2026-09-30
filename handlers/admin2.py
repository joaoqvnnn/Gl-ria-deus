import logging
import asyncio
from telegram import Update, ForceReply, InputFile
from telegram.constants import ParseMode
from telegram.ext import ContextTypes

from config import ADMIN_IDS
from database import db
from keyboards import menus

logger = logging.getLogger(__name__)

VENDAS_PAGE_SIZE = 8


def is_admin(user_id: int) -> bool:
    return user_id in ADMIN_IDS


async def _edit_or_send(query, text: str, kb=None):
    try:
        await query.edit_message_text(text, reply_markup=kb, parse_mode=ParseMode.HTML)
    except Exception:
        await query.message.reply_text(text, reply_markup=kb, parse_mode=ParseMode.HTML)


# ═══════════════════════════════════════════════
# VENDAS — v2 (com filtros e paginação)
# ═══════════════════════════════════════════════

async def admin_vendas_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not is_admin(update.effective_user.id):
        return
    await _render_vendas(query, periodo="tudo", status="todos", page=0)


async def admin_vendas_page_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not is_admin(update.effective_user.id):
        return
    try:
        _, _, periodo, status, page = query.data.split(":")
        page = int(page)
    except (ValueError, IndexError):
        return
    await _render_vendas(query, periodo=periodo, status=status, page=page)


async def admin_vendas_filtro_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not is_admin(update.effective_user.id):
        return
    try:
        _, _, periodo, status = query.data.split(":")
    except (ValueError, IndexError):
        return
    await _render_vendas(query, periodo=periodo, status=status, page=0)


async def _render_vendas(query, periodo: str = "tudo", status: str = "todos", page: int = 0):
    total = await db.admin_vendas_count(periodo, status)
    stats = await db.admin_vendas_stats(periodo, status)
    total_pages = max((total + VENDAS_PAGE_SIZE - 1) // VENDAS_PAGE_SIZE, 1)
    page = min(max(page, 0), total_pages - 1)

    vendas = await db.admin_vendas_list(
        periodo=periodo, status=status,
        limit=VENDAS_PAGE_SIZE, offset=page * VENDAS_PAGE_SIZE,
    )

    periodo_label = {
        "hoje": "Hoje", "7d": "Últimos 7 dias", "30d": "Últimos 30 dias",
        "mes": "Este mês", "tudo": "Todo o período",
    }.get(periodo, periodo)

    status_label = {
        "todos": "Todos", "ativos": "🟢 Ativos", "cancelados": "🔴 Cancelados",
    }.get(status, status)

    texto = (
        "🛒 <b>Gerenciar Vendas</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"📅 Período: <b>{periodo_label}</b>\n"
        f"📡 Status: <b>{status_label}</b>\n\n"
        "📊 <b>Resumo:</b>\n"
        f"├ Pedidos: <b>{stats['total_pedidos']}</b>\n"
        f"├ Itens vendidos: <b>{stats['total_itens']}</b>\n"
        f"└ Receita: <b>R$ {stats['receita_total']:.2f}</b>\n\n"
        f"📄 Página <b>{page + 1}/{total_pages}</b>\n\n"
        "👉 Toque em um pedido para ver detalhes:"
    )

    kb = menus.admin_vendas_kb(vendas, page, total_pages, periodo, status)
    try:
        await query.edit_message_text(texto, reply_markup=kb, parse_mode=ParseMode.HTML)
    except Exception:
        await query.message.reply_text(texto, reply_markup=kb, parse_mode=ParseMode.HTML)


# ─── Detalhe do pedido
async def admin_venda_detalhe_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not is_admin(update.effective_user.id):
        return

    try:
        purchase_id = query.data.split(":", 2)[2]
    except (IndexError, ValueError):
        return

    p = await db.get_purchase(purchase_id)
    if not p:
        await query.edit_message_text("❌ Pedido não encontrado.")
        return

    u = await db.get_user(p["user_id"])
    nome = (u or {}).get("first_name") or (u or {}).get("username") or f"ID {p['user_id']}"

    cancelado = (p.get("status") or "active") == "cancelled"
    status_icon = "🔴 Cancelado" if cancelado else "🟢 Ativo"

    texto = (
        "🛒 <b>Detalhes do Pedido</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"🎫 ID: <code>{p['id']}</code>\n"
        f"📡 Status: {status_icon}\n\n"
        "👤 <b>Cliente:</b>\n"
        f"├ Nome: <b>{nome[:35]}</b>\n"
        f"└ ID: <code>{p['user_id']}</code>\n\n"
        "📦 <b>Produto:</b>\n"
        f"├ Serviço: <b>{p['product_name']}</b>\n"
        f"├ Quantidade: <b>{p['quantity']}</b>\n"
        f"└ Valor total: <b>R$ {float(p['total']):.2f}</b>\n\n"
        "🔐 <b>Credenciais entregues:</b>\n"
        f"├ 📧 <code>{p.get('email') or '—'}</code>\n"
        f"└ 🔑 <code>{p.get('password') or '—'}</code>\n\n"
        "📅 <b>Datas:</b>\n"
        f"├ Compra: <b>{str(p.get('created_at') or '')[:16]}</b>\n"
        f"└ Vence: <b>{str(p.get('expires_at') or '')[:10]}</b>"
    )

    kb = menus.admin_venda_detalhe_kb(purchase_id, cancelado, "tudo", "todos")
    try:
        await query.edit_message_text(texto, reply_markup=kb, parse_mode=ParseMode.HTML)
    except Exception:
        pass


# ─── Reembolso (com confirmação)
async def admin_refund_prompt_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not is_admin(update.effective_user.id):
        return

    parts = query.data.split(":")
    try:
        purchase_id = parts[2]
        periodo = parts[3] if len(parts) > 3 else "tudo"
        status = parts[4] if len(parts) > 4 else "todos"
    except (IndexError, ValueError):
        return

    p = await db.get_purchase(purchase_id)
    if not p:
        await query.answer("Não encontrado.", show_alert=True)
        return

    u = await db.get_user(p["user_id"])
    nome = (u or {}).get("first_name") or f"ID {p['user_id']}"

    texto = (
        "💰 <b>Confirmar Reembolso</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"👤 Cliente: <b>{nome[:30]}</b>\n"
        f"📦 Produto: <b>{p['product_name']}</b>\n"
        f"💵 Valor: <b>R$ {float(p['total']):.2f}</b>\n\n"
        "⚠️ Ao confirmar:\n"
        f"├ 💰 R$ {float(p['total']):.2f} voltam pro saldo do cliente\n"
        f"├ 📦 {p['quantity']} item(ns) voltam pro estoque\n"
        f"└ 📩 Cliente recebe notificação automática\n\n"
        "Tem certeza?"
    )

    kb = menus.InlineKeyboardMarkup([
        [menus.InlineKeyboardButton(
            "✅ Sim, reembolsar",
            callback_data=f"admin:refund_confirm:{purchase_id}:{periodo}:{status}",
        )],
        [menus.InlineKeyboardButton(
            "❌ Cancelar",
            callback_data=f"admin:venda:{purchase_id}",
        )],
    ])

    try:
        await query.edit_message_text(texto, reply_markup=kb, parse_mode=ParseMode.HTML)
    except Exception:
        pass


async def admin_refund_confirm_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not is_admin(update.effective_user.id):
        return

    parts = query.data.split(":")
    try:
        purchase_id = parts[2]
        periodo = parts[3] if len(parts) > 3 else "tudo"
        status = parts[4] if len(parts) > 4 else "todos"
    except (IndexError, ValueError):
        return

    p = await db.admin_cancel_purchase(purchase_id)
    if not p:
        await query.answer("❌ Pedido não encontrado.", show_alert=True)
        return

    await db.log_admin_action(
        update.effective_user.id, "refund", purchase_id,
        f"R$ {float(p['total']):.2f}",
    )

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

    try:
        await query.edit_message_text(
            f"✅ <b>Reembolso realizado!</b>\n\n"
            f"💰 R$ {float(p['total']):.2f} devolvido para <code>{p['user_id']}</code>.",
            reply_markup=menus.InlineKeyboardMarkup([
                [menus.InlineKeyboardButton(
                    "⬅️ Voltar às vendas",
                    callback_data=f"admin:vendas_filtro:{periodo}:{status}",
                )],
            ]),
            parse_mode=ParseMode.HTML,
        )
    except Exception:
        pass


# ─── Reativar pedido
async def admin_venda_reactivate_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not is_admin(update.effective_user.id):
        return

    parts = query.data.split(":")
    try:
        purchase_id = parts[2]
    except (IndexError, ValueError):
        return

    ok = await db.admin_mark_purchase_delivered(purchase_id)
    if not ok:
        await query.answer("Não encontrado.", show_alert=True)
        return

    await db.log_admin_action(update.effective_user.id, "purchase_reactivate", purchase_id)
    await query.answer("✅ Pedido reativado!", show_alert=True)

    query.data = f"admin:venda:{purchase_id}"
    await admin_venda_detalhe_cb(update, context)


# ─── Reenviar credenciais
async def admin_venda_resend_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not is_admin(update.effective_user.id):
        return

    parts = query.data.split(":")
    try:
        purchase_id = parts[2]
    except (IndexError, ValueError):
        return

    p = await db.get_purchase(purchase_id)
    if not p:
        return

    produto = await db.get_product(p["product_id"])
    activate_url = (produto or {}).get("activate_url") or "https://t.me/"

    try:
        await context.bot.send_message(
            chat_id=p["user_id"],
            text=(
                "📤 <b>Suas Credenciais de Acesso</b>\n"
                "━━━━━━━━━━━━━━━━━━━━━━━\n\n"
                f"⚜️ Produto: <b>{p['product_name']}</b>\n"
                f"🎫 ID: <code>{p['id']}</code>\n"
                f"📧 Email: <code>{p.get('email') or '—'}</code>\n"
                f"🔐 Senha: <code>{p.get('password') or '—'}</code>\n\n"
                "Use o botão abaixo para ativar:"
            ),
            reply_markup=menus.InlineKeyboardMarkup([
                [menus.InlineKeyboardButton("🔗 ATIVAR", url=activate_url)],
            ]),
            parse_mode=ParseMode.HTML,
        )
        await db.log_admin_action(update.effective_user.id, "purchase_resend", purchase_id)
        await query.answer("✅ Credenciais reenviadas!", show_alert=True)
    except Exception as e:
        await query.answer(f"❌ Falha: {e}", show_alert=True)


# ─── Enviar mensagem personalizada pro cliente
async def admin_venda_msg_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not is_admin(update.effective_user.id):
        return

    try:
        purchase_id = query.data.split(":", 2)[2]
    except (IndexError, ValueError):
        return

    p = await db.get_purchase(purchase_id)
    if not p:
        return

    context.user_data["admin_venda_msg"] = p["user_id"]

    try:
        await query.edit_message_text(
            f"📧 <b>Enviar mensagem pro cliente</b>\n"
            "━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"🆔 User ID: <code>{p['user_id']}</code>\n"
            f"📦 Pedido: <b>{p['product_name']}</b>\n\n"
            "Envie o texto da mensagem (aceita HTML):\n\n"
            "Envie <code>/cancelar</code> para sair.",
            parse_mode=ParseMode.HTML,
        )
    except Exception:
        pass


async def admin_venda_msg_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = context.user_data.get("admin_venda_msg")
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
        context.user_data.pop("admin_venda_msg", None)
        return

    if not texto:
        return

    context.user_data.pop("admin_venda_msg", None)

    try:
        await context.bot.send_message(
            chat_id=user_id, text=texto, parse_mode=ParseMode.HTML,
        )
        await db.log_admin_action(update.effective_user.id, "venda_direct_msg", str(user_id))
        await update.message.reply_text(
            f"✅ Mensagem enviada para <code>{user_id}</code>.",
            reply_markup=menus.admin_back_kb(),
            parse_mode=ParseMode.HTML,
        )
    except Exception as e:
        await update.message.reply_text(f"❌ Erro: {e}")


# ─── Exportar CSV
async def admin_vendas_export_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not is_admin(update.effective_user.id):
        return

    try:
        _, _, periodo, status = query.data.split(":")
    except (ValueError, IndexError):
        periodo, status = "tudo", "todos"

    try:
        csv_text = await db.admin_vendas_export_csv(periodo, status)
        if not csv_text or len(csv_text.splitlines()) <= 1:
            await query.answer("📭 Nenhuma venda neste filtro.", show_alert=True)
            return

        filename = f"vendas-{periodo}-{status}.csv"
        await context.bot.send_document(
            chat_id=query.message.chat_id,
            document=InputFile(
                csv_text.encode("utf-8"),
                filename=filename,
            ),
            caption=(
                f"📤 <b>Vendas exportadas</b>\n"
                f"📅 Período: <b>{periodo}</b>\n"
                f"📡 Status: <b>{status}</b>"
            ),
            parse_mode=ParseMode.HTML,
        )
        await db.log_admin_action(update.effective_user.id, "vendas_export", periodo, status)
    except Exception as e:
        logger.exception("Erro export vendas: %s", e)
        await query.answer(f"❌ Erro: {e}", show_alert=True)


# ─── Buscar pedido
async def admin_purchase_search_prompt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not is_admin(update.effective_user.id):
        return

    context.user_data["admin_purchase_search"] = True

    try:
        await query.edit_message_text(
            "🔍 <b>Buscar Pedido</b>\n\n"
            "Envie o <b>ID da compra</b>, <b>user_id</b> ou <b>nome do produto</b>:",
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
        return

    try:
        compras = await db.admin_search_purchases(term)
    except Exception as e:
        await update.message.reply_text(f"❌ Erro: {e}")
        return

    if not compras:
        await update.message.reply_text(
            f"❌ Nada encontrado com <code>{term}</code>.",
            reply_markup=menus.admin_back_kb(),
            parse_mode=ParseMode.HTML,
        )
        return

    texto = f"🔍 <b>Resultados ({len(compras)}):</b>"
    kb = menus.admin_vendas_kb(compras, 0, 1, "tudo", "todos")
    await update.message.reply_text(texto, reply_markup=kb, parse_mode=ParseMode.HTML)


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

    tipo = query.data.split(":")[2]
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

    if text.startswith("/"):
        context.user_data.pop("admin_gift_tipo", None)
        return

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

    if text.startswith("/"):
        for k in ("admin_gift_tipo", "admin_gift_valor", "admin_gift_produto"):
            context.user_data.pop(k, None)
        return

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
# SAQUES
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

                u = await db.get_user(w["user_id"])
                nome = (u or {}).get("first_name") or (u or {}).get("username") or f"ID {w['user_id']}"

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
# AFILIADOS
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
