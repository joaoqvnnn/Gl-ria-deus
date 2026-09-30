"""
Módulo ADMIN — VENDAS v2 (completo) + GIFT CARDS + SAQUES (compat) + AFILIADOS (compat).
"""
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
        try:
            await query.message.reply_text(text, reply_markup=kb, parse_mode=ParseMode.HTML)
        except Exception:
            pass


# ═══════════════════════════════════════════════
# VENDAS v2
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
    await _edit_or_send(query, texto, kb)


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
        await _edit_or_send(query, "❌ Pedido não encontrado.", menus.admin_back_kb())
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
    await _edit_or_send(query, texto, kb)


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

    await _edit_or_send(query, texto, kb)


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
# GIFT CARDS — LEGACY (compat, redireciona pra admin9)
# ═══════════════════════════════════════════════
async def admin_gifts_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Redireciona pra admin9."""
    try:
        from handlers import admin9
        await admin9.admin_gifts_v2_cb(update, context)
    except Exception as e:
        logger.exception("Erro redirecionando gifts: %s", e)


async def admin_gift_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Redireciona 'admin:gift:X' → 'admin:gift_v2:X'."""
    query = update.callback_query
    try:
        code = query.data.split(":", 2)[2]
        query.data = f"admin:gift_v2:{code}"
        from handlers import admin9
        await admin9.admin_gift_v2_cb(update, context)
    except Exception as e:
        logger.exception("Erro redirecionando gift: %s", e)


async def admin_gift_del_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Redireciona pra revogar."""
    query = update.callback_query
    try:
        code = query.data.split(":", 2)[2]
        query.data = f"admin:gift_revoke:{code}"
        from handlers import admin9
        await admin9.admin_gift_revoke_cb(update, context)
    except Exception as e:
        logger.exception("Erro redirecionando gift_del: %s", e)


async def admin_gift_create_prompt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Redireciona pra admin9."""
    try:
        from handlers import admin9
        await admin9.admin_gift_create_cb(update, context)
    except Exception as e:
        logger.exception("Erro redirecionando gift_create: %s", e)


async def admin_gift_tipo_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Redireciona pra admin9 (novo tipo)."""
    query = update.callback_query
    try:
        tipo = query.data.split(":")[2]
        query.data = f"admin:gift_new:{tipo}"
        from handlers import admin9
        await admin9.admin_gift_new_cb(update, context)
    except Exception as e:
        logger.exception("Erro redirecionando gift_tipo: %s", e)


async def admin_gift_valor_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Redireciona pro wizard novo."""
    try:
        from handlers import admin9
        await admin9.admin_gift_wizard_handler(update, context)
    except Exception as e:
        logger.exception("Erro redirecionando gift_valor: %s", e)


async def admin_gift_qtd_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Redireciona pro wizard novo."""
    try:
        from handlers import admin9
        await admin9.admin_gift_wizard_handler(update, context)
    except Exception as e:
        logger.exception("Erro redirecionando gift_qtd: %s", e)


# ═══════════════════════════════════════════════
# SAQUES — LEGACY (compat, redireciona pra admin7)
# ═══════════════════════════════════════════════
async def admin_withdrawals_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        from handlers import admin7
        await admin7.admin_saques_cb(update, context)
    except Exception as e:
        logger.exception("Erro redirecionando withdrawals: %s", e)


async def admin_withdrawal_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    try:
        wid = query.data.split(":", 2)[2]
        query.data = f"admin:saque:{wid}"
        from handlers import admin7
        await admin7.admin_saque_detalhe_cb(update, context)
    except Exception as e:
        logger.exception("Erro redirecionando withdrawal: %s", e)


async def admin_wd_approve_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    try:
        wid = query.data.split(":", 2)[2]
        query.data = f"admin:saque_ok:{wid}"
        from handlers import admin7
        await admin7.admin_saque_ok_prompt_cb(update, context)
    except Exception as e:
        logger.exception("Erro redirecionando wd_approve: %s", e)


async def admin_wd_reject_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    try:
        wid = query.data.split(":", 2)[2]
        query.data = f"admin:saque_no:{wid}"
        from handlers import admin7
        await admin7.admin_saque_no_prompt_cb(update, context)
    except Exception as e:
        logger.exception("Erro redirecionando wd_reject: %s", e)


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
