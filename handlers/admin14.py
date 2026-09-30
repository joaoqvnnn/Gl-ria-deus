"""
Módulo ADMIN — CARRINHOS ABANDONADOS v2 (completo).
"""
import io
import logging
import asyncio
from datetime import datetime
from telegram import Update, ForceReply, InputFile
from telegram.constants import ParseMode
from telegram.ext import ContextTypes

from config import ADMIN_IDS
from database import db
from keyboards import menus

logger = logging.getLogger(__name__)

CARTS_PAGE_SIZE = 8
TEMPLATE_DEFAULT = (
    "👋 Ei, <b>{nome}</b>, você esqueceu algo!\n\n"
    "Notamos que você estava olhando <b>{produto}</b> "
    "mas não finalizou a compra.\n\n"
    "💰 Valor: <b>R$ {preco}</b>\n\n"
    "🎁 Que tal finalizar agora?\n"
    "Seu produto está esperando por você!"
)


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
async def admin_carts_v2_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not is_admin(update.effective_user.id):
        return
    await _render_carts(query, tempo="todos", page=0)


async def admin_carts_page_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not is_admin(update.effective_user.id):
        return
    try:
        _, _, tempo, page = query.data.split(":")
        page = int(page)
    except (ValueError, IndexError):
        return
    await _render_carts(query, tempo=tempo, page=page)


async def admin_carts_filtro_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not is_admin(update.effective_user.id):
        return
    try:
        tempo = query.data.split(":")[2]
    except IndexError:
        tempo = "todos"
    await _render_carts(query, tempo=tempo, page=0)


async def _render_carts(query, tempo: str = "todos", page: int = 0):
    total = await db.admin_carts_v2_count(tempo)
    stats = await db.admin_carts_v2_stats()

    total_pages = max((total + CARTS_PAGE_SIZE - 1) // CARTS_PAGE_SIZE, 1)
    page = min(max(page, 0), total_pages - 1)

    carrinhos = await db.admin_carts_v2_list(
        tempo=tempo, limit=CARTS_PAGE_SIZE, offset=page * CARTS_PAGE_SIZE,
    )

    tempo_label = {
        "5min": "Últimos 5 min", "1h": "Última 1h",
        "24h": "Últimas 24h", "7d": "Últimos 7 dias", "todos": "Todo o período",
    }.get(tempo, tempo)

    texto = (
        "🛒 <b>Carrinhos Abandonados</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"📅 Filtro: <b>{tempo_label}</b>\n\n"
        "📊 <b>Resumo geral:</b>\n"
        f"├ ⏳ Aguardando: <b>{stats['total']}</b>\n"
        f"├ 📅 Hoje: <b>{stats['hoje']}</b>\n"
        f"├ 📊 Últimos 7d: <b>{stats['ultimos_7d']}</b>\n"
        f"├ 💰 Em risco: <b>R$ {stats['valor_risco']:.2f}</b>\n"
        f"└ ✅ Convertidos: <b>{stats['convertidos']}</b>\n\n"
        f"📄 Página <b>{page + 1}/{total_pages}</b> · {total} cart(s)\n\n"
        "👉 Toque em um carrinho para agir:"
    )

    kb = menus.admin_carts_v2_kb(carrinhos, page, total_pages, tempo)
    await _edit_or_send(query, texto, kb)


# ═══════════════════════════════════════════════
# DETALHE
# ═══════════════════════════════════════════════
async def admin_cart_v2_item_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not is_admin(update.effective_user.id):
        return

    try:
        _, _, u_id, p_id = query.data.split(":")
        user_id = int(u_id)
        product_id = int(p_id)
    except (ValueError, IndexError):
        return

    u = await db.get_user(user_id)
    p = await db.get_product(product_id)

    if not u or not p:
        await _edit_or_send(query, "❌ Dados não encontrados.", menus.admin_back_kb())
        return

    nome = u.get("first_name") or u.get("username") or f"ID {user_id}"
    preco = float(p["price"])

    cur = await db._db.execute(
        "SELECT viewed_at, reminders_sent FROM cart_views "
        "WHERE user_id = ? AND product_id = ?",
        (user_id, product_id),
    )
    cv = await cur.fetchone()
    viewed_at = str(cv["viewed_at"])[:16] if cv else "—"
    reminders = (cv["reminders_sent"] if cv else 0) or 0

    tempo_txt = "—"
    if cv:
        try:
            dt = datetime.strptime(str(cv["viewed_at"])[:19], "%Y-%m-%d %H:%M:%S")
            diff = datetime.now() - dt
            mins = int(diff.total_seconds() / 60)
            if mins < 60:
                tempo_txt = f"{mins} min"
            elif mins < 1440:
                tempo_txt = f"{mins // 60}h"
            else:
                tempo_txt = f"{mins // 1440}d"
        except Exception:
            pass

    texto = (
        "🛒 <b>Carrinho Abandonado</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "👤 <b>Cliente:</b>\n"
        f"├ Nome: <b>{nome[:35]}</b>\n"
        f"├ Username: @{u.get('username') or '—'}\n"
        f"└ ID: <code>{user_id}</code>\n\n"
        "📦 <b>Produto:</b>\n"
        f"├ Nome: <b>{p['name']}</b>\n"
        f"└ Preço: <b>R$ {preco:.2f}</b>\n\n"
        "⏰ <b>Timeline:</b>\n"
        f"├ Visto em: <b>{viewed_at}</b>\n"
        f"├ Há: <b>{tempo_txt}</b>\n"
        f"└ Lembretes enviados: <b>{reminders}</b>\n\n"
        "👇 O que fazer?"
    )

    kb = menus.admin_cart_v2_item_kb(user_id, product_id)
    await _edit_or_send(query, texto, kb)


# ═══════════════════════════════════════════════
# ENVIAR LEMBRETE
# ═══════════════════════════════════════════════
async def admin_cart_v2_send_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not is_admin(update.effective_user.id):
        return

    try:
        _, _, u_id, p_id = query.data.split(":")
        user_id = int(u_id)
        product_id = int(p_id)
    except (ValueError, IndexError):
        return

    ok = await _send_reminder(context.bot, user_id, product_id)
    if not ok:
        await query.answer("❌ Falha ao enviar.", show_alert=True)
        return

    await db.admin_carts_v2_increment_reminder(user_id, product_id)
    await db.log_admin_action(
        update.effective_user.id, "cart_send", f"{user_id}/{product_id}",
    )

    await query.answer("📨 Lembrete enviado!", show_alert=True)
    query.data = f"admin:cart2:{user_id}:{product_id}"
    await admin_cart_v2_item_cb(update, context)


async def _send_reminder(bot, user_id: int, product_id: int) -> bool:
    try:
        u = await db.get_user(user_id)
        p = await db.get_product(product_id)
        if not u or not p:
            return False

        nome = u.get("first_name") or "cliente"
        preco = float(p["price"])

        try:
            template = await db.get_config("cart_template", "")
        except Exception:
            template = ""

        if not template:
            template = TEMPLATE_DEFAULT

        texto = template.format(nome=nome, produto=p["name"], preco=f"{preco:.2f}")

        await bot.send_message(
            chat_id=user_id,
            text=texto,
            reply_markup=menus.direct_product_two_keyboard(product_id),
            parse_mode=ParseMode.HTML,
        )
        return True
    except Exception as e:
        logger.warning("Falha enviando lembrete: %s", e)
        return False


# ═══════════════════════════════════════════════
# MENSAGEM PERSONALIZADA
# ═══════════════════════════════════════════════
async def admin_cart_v2_msg_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not is_admin(update.effective_user.id):
        return

    try:
        _, _, u_id, p_id = query.data.split(":")
        user_id = int(u_id)
        product_id = int(p_id)
    except (ValueError, IndexError):
        return

    context.user_data["admin_cart_msg"] = {"user_id": user_id, "product_id": product_id}
    context.user_data["_cart_msg_prompt_id"] = query.message.message_id
    context.user_data["_cart_msg_prompt_chat"] = query.message.chat_id

    u = await db.get_user(user_id)
    p = await db.get_product(product_id)
    nome = (u or {}).get("first_name") or "cliente"
    prod_nome = (p or {}).get("name") or "?"

    try:
        await query.edit_message_text(
            "💬 <b>Mensagem personalizada</b>\n"
            "━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"👤 <b>{nome}</b>\n"
            f"📦 <b>{prod_nome}</b>\n\n"
            "Envie a mensagem.\n\n"
            "🔧 <b>Variáveis:</b>\n"
            "├ <code>{nome}</code> — nome do cliente\n"
            "├ <code>{produto}</code> — nome do produto\n"
            "└ <code>{preco}</code> — preço do produto\n\n"
            "Envie <code>/cancelar</code> para sair.",
            reply_markup=ForceReply(selective=True),
            parse_mode=ParseMode.HTML,
        )
    except Exception:
        pass


async def admin_cart_v2_msg_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    info = context.user_data.get("admin_cart_msg")
    if not info:
        return
    if not is_admin(update.effective_user.id):
        return

    texto = (update.message.text or "").strip()

    try:
        await update.message.delete()
    except Exception:
        pass

    if texto.startswith("/"):
        context.user_data.pop("admin_cart_msg", None)
        await _delete_prompt(context, "_cart_msg_prompt_id", "_cart_msg_prompt_chat")
        return

    if not texto:
        return

    user_id = info["user_id"]
    product_id = info["product_id"]

    u = await db.get_user(user_id)
    p = await db.get_product(product_id)
    nome = (u or {}).get("first_name") or "cliente"
    prod_nome = (p or {}).get("name") or "?"
    preco = float((p or {}).get("price") or 0)

    msg_final = (
        texto
        .replace("{nome}", nome)
        .replace("{produto}", prod_nome)
        .replace("{preco}", f"{preco:.2f}")
    )

    try:
        await context.bot.send_message(
            chat_id=user_id,
            text=msg_final,
            reply_markup=menus.direct_product_two_keyboard(product_id),
            parse_mode=ParseMode.HTML,
        )
        await db.admin_carts_v2_increment_reminder(user_id, product_id)
        await db.log_admin_action(
            update.effective_user.id, "cart_custom_msg", f"{user_id}/{product_id}",
        )
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="✅ <b>Mensagem enviada!</b>",
            reply_markup=menus.admin_back_kb(),
            parse_mode=ParseMode.HTML,
        )
    except Exception as e:
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=f"❌ Erro: {e}",
        )

    context.user_data.pop("admin_cart_msg", None)
    await _delete_prompt(context, "_cart_msg_prompt_id", "_cart_msg_prompt_chat")


# ═══════════════════════════════════════════════
# DAR DESCONTO
# ═══════════════════════════════════════════════
async def admin_cart_v2_disc_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not is_admin(update.effective_user.id):
        return

    try:
        _, _, u_id, p_id = query.data.split(":")
        user_id = int(u_id)
        product_id = int(p_id)
    except (ValueError, IndexError):
        return

    p = await db.get_product(product_id)
    if not p:
        return

    preco = float(p["price"])

    texto = (
        "🎁 <b>Dar Desconto</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"📦 Produto: <b>{p['name']}</b>\n"
        f"💰 Preço: <b>R$ {preco:.2f}</b>\n\n"
        "Escolha o <b>percentual de desconto</b>:"
    )

    kb = menus.InlineKeyboardMarkup([
        [
            menus.InlineKeyboardButton("5%", callback_data=f"admin:cart2_disc_set:{user_id}:{product_id}:5"),
            menus.InlineKeyboardButton("10%", callback_data=f"admin:cart2_disc_set:{user_id}:{product_id}:10"),
        ],
        [
            menus.InlineKeyboardButton("15%", callback_data=f"admin:cart2_disc_set:{user_id}:{product_id}:15"),
            menus.InlineKeyboardButton("20%", callback_data=f"admin:cart2_disc_set:{user_id}:{product_id}:20"),
        ],
        [
            menus.InlineKeyboardButton("30%", callback_data=f"admin:cart2_disc_set:{user_id}:{product_id}:30"),
            menus.InlineKeyboardButton("50%", callback_data=f"admin:cart2_disc_set:{user_id}:{product_id}:50"),
        ],
        [menus.InlineKeyboardButton("⬅️ Voltar", callback_data=f"admin:cart2:{user_id}:{product_id}")],
    ])
    await _edit_or_send(query, texto, kb)


async def admin_cart_v2_disc_set_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not is_admin(update.effective_user.id):
        return

    try:
        _, _, u_id, p_id, pct = query.data.split(":")
        user_id = int(u_id)
        product_id = int(p_id)
        pct = float(pct)
    except (ValueError, IndexError):
        return

    p = await db.get_product(product_id)
    if not p:
        return

    preco = float(p["price"])
    valor_desc = preco * (pct / 100)
    preco_final = preco - valor_desc

    try:
        codigos = await db.admin_gift_create_full(
            code_base="CART",
            quantidade=1,
            tipo="saldo",
            valor=valor_desc,
            product_id=None,
            discount_pct=None,
            expires_days=7,
        )
        codigo = codigos[0] if codigos else "—"
    except Exception as e:
        logger.exception("Erro criando gift cupom: %s", e)
        codigo = "ERRO"

    u = await db.get_user(user_id)
    nome = (u or {}).get("first_name") or "cliente"

    try:
        await context.bot.send_message(
            chat_id=user_id,
            text=(
                f"🎁 <b>Cupom de desconto só pra você, {nome}!</b>\n"
                "━━━━━━━━━━━━━━━━━━━━━━━\n\n"
                f"📦 Produto: <b>{p['name']}</b>\n"
                f"💰 De: <s>R$ {preco:.2f}</s>\n"
                f"💸 Por: <b>R$ {preco_final:.2f}</b>\n"
                f"🎯 Desconto: <b>{pct:.0f}%</b> (R$ {valor_desc:.2f})\n\n"
                "🎫 <b>Seu cupom de saldo:</b>\n"
                f"<code>{codigo}</code>\n\n"
                "💡 Resgate no botão 🎁 Gift Card no seu perfil.\n"
                "⏰ Válido por 7 dias."
            ),
            reply_markup=menus.direct_product_two_keyboard(product_id),
            parse_mode=ParseMode.HTML,
        )
        await db.admin_carts_v2_increment_reminder(user_id, product_id)
        await db.log_admin_action(
            update.effective_user.id, "cart_discount",
            f"{user_id}/{product_id}", f"{pct:.0f}%",
        )

        await query.answer("🎁 Cupom enviado!", show_alert=True)
        query.data = f"admin:cart2:{user_id}:{product_id}"
        await admin_cart_v2_item_cb(update, context)
    except Exception as e:
        await query.answer(f"❌ Erro: {e}", show_alert=True)


# ═══════════════════════════════════════════════
# MARCAR CONVERTIDO / REMOVER
# ═══════════════════════════════════════════════
async def admin_cart_v2_conv_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not is_admin(update.effective_user.id):
        return

    try:
        _, _, u_id, p_id = query.data.split(":")
        user_id = int(u_id)
        product_id = int(p_id)
    except (ValueError, IndexError):
        return

    await db.admin_carts_v2_mark_converted(user_id, product_id)
    await db.log_admin_action(
        update.effective_user.id, "cart_converted", f"{user_id}/{product_id}",
    )

    await query.answer("✅ Marcado como convertido!", show_alert=True)
    query.data = "admin:abandoned"
    await admin_carts_v2_cb(update, context)


async def admin_cart_v2_del_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not is_admin(update.effective_user.id):
        return

    try:
        _, _, u_id, p_id = query.data.split(":")
        user_id = int(u_id)
        product_id = int(p_id)
    except (ValueError, IndexError):
        return

    await db.admin_clear_abandoned(user_id, product_id)
    await db.log_admin_action(
        update.effective_user.id, "cart_del", f"{user_id}/{product_id}",
    )

    await query.answer("🗑️ Removido!", show_alert=True)
    query.data = "admin:abandoned"
    await admin_carts_v2_cb(update, context)


# ═══════════════════════════════════════════════
# ENVIAR PRA TODOS
# ═══════════════════════════════════════════════
async def admin_carts_v2_send_all_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not is_admin(update.effective_user.id):
        return

    total = await db.admin_carts_v2_count("todos")

    texto = (
        "📨 <b>Enviar lembrete pra todos?</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"👥 Total de carrinhos: <b>{total}</b>\n\n"
        f"⚠️ Serão enviadas <b>{total}</b> mensagens. Continuar?"
    )

    kb = menus.InlineKeyboardMarkup([
        [menus.InlineKeyboardButton("✅ Sim, enviar", callback_data="admin:carts_send_all_yes")],
        [menus.InlineKeyboardButton("❌ Cancelar", callback_data="admin:abandoned")],
    ])
    await _edit_or_send(query, texto, kb)


async def admin_carts_v2_send_all_yes_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not is_admin(update.effective_user.id):
        return

    carrinhos = await db.admin_carts_v2_list(tempo="todos", limit=500, offset=0)
    total = len(carrinhos)

    if not total:
        await query.answer("📭 Nenhum carrinho pra enviar.", show_alert=True)
        return

    prog = None
    try:
        prog = await context.bot.send_message(
            chat_id=query.message.chat_id,
            text=f"⏳ <b>Enviando...</b> 0/{total}",
            parse_mode=ParseMode.HTML,
        )
    except Exception:
        pass

    enviados = 0
    falhas = 0

    for i, c in enumerate(carrinhos):
        try:
            ok = await _send_reminder(context.bot, c["user_id"], c["product_id"])
            if ok:
                enviados += 1
                await db.admin_carts_v2_increment_reminder(c["user_id"], c["product_id"])
            else:
                falhas += 1
        except Exception:
            falhas += 1

        if prog and (i + 1) % 20 == 0:
            try:
                await context.bot.edit_message_text(
                    chat_id=query.message.chat_id,
                    message_id=prog.message_id,
                    text=f"⏳ <b>Enviando...</b> {i + 1}/{total}",
                    parse_mode=ParseMode.HTML,
                )
            except Exception:
                pass

        await asyncio.sleep(0.05)

    await db.log_admin_action(
        update.effective_user.id, "cart_send_all",
        f"enviados={enviados} falhas={falhas}",
    )

    if prog:
        try:
            await context.bot.edit_message_text(
                chat_id=query.message.chat_id,
                message_id=prog.message_id,
                text=(
                    "✅ <b>Envio em massa concluído!</b>\n"
                    "━━━━━━━━━━━━━━━━━━━━━━━\n\n"
                    f"├ ✅ Enviados: <b>{enviados}</b>\n"
                    f"├ ❌ Falhas: <b>{falhas}</b>\n"
                    f"└ 📊 Total: <b>{total}</b>"
                ),
                reply_markup=menus.admin_back_kb(),
                parse_mode=ParseMode.HTML,
            )
        except Exception:
            pass


# ═══════════════════════════════════════════════
# EXPORTAR CSV
# ═══════════════════════════════════════════════
async def admin_carts_v2_export_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not is_admin(update.effective_user.id):
        return

    try:
        csv_text = await db.admin_carts_v2_export_csv()
        if not csv_text or len(csv_text.splitlines()) <= 1:
            await query.answer("📭 Nenhum carrinho.", show_alert=True)
            return

        filename = f"carrinhos-{datetime.now().strftime('%Y%m%d')}.csv"
        await context.bot.send_document(
            chat_id=query.message.chat_id,
            document=InputFile(csv_text.encode("utf-8"), filename=filename),
            caption="📤 <b>Carrinhos exportados</b>",
            parse_mode=ParseMode.HTML,
        )
        await db.log_admin_action(update.effective_user.id, "carts_export")
    except Exception as e:
        logger.exception("Erro export carts: %s", e)
        await query.answer(f"❌ Erro: {e}", show_alert=True)


# ═══════════════════════════════════════════════
# AUTOMAÇÃO
# ═══════════════════════════════════════════════
async def admin_carts_v2_auto_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not is_admin(update.effective_user.id):
        return

    try:
        ligado = (await db.get_config("cart_auto", "1")) == "1"
        minutos = int(await db.get_config("cart_minutes", "5"))
    except Exception:
        ligado, minutos = True, 5

    texto = (
        "⚙️ <b>Automação de Carrinhos</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"📡 Status: <b>{'🟢 LIGADO' if ligado else '🔴 DESLIGADO'}</b>\n"
        f"⏰ Tempo de espera: <b>{minutos} min</b>\n\n"
        "💡 Quando <b>LIGADO</b>, o bot envia automaticamente um lembrete "
        "para quem abandonou o carrinho após o tempo definido.\n\n"
        "Escolha uma opção:"
    )

    kb = menus.admin_cart_v2_auto_kb(ligado, minutos)
    await _edit_or_send(query, texto, kb)


async def admin_carts_v2_auto_toggle_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not is_admin(update.effective_user.id):
        return

    atual = await db.get_config("cart_auto", "1")
    novo = "0" if atual == "1" else "1"
    await db.set_config("cart_auto", novo)
    await db.log_admin_action(update.effective_user.id, "cart_auto_toggle", novo)

    await query.answer(f"{'🟢 Ligado' if novo == '1' else '🔴 Desligado'}", show_alert=True)
    await admin_carts_v2_auto_cb(update, context)


async def admin_carts_v2_auto_min_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not is_admin(update.effective_user.id):
        return

    try:
        minutos = int(query.data.split(":")[2])
    except (ValueError, IndexError):
        return

    await db.set_config("cart_minutes", str(minutos))
    await db.log_admin_action(
        update.effective_user.id, "cart_minutes", str(minutos),
    )

    await query.answer(f"⏰ {minutos} min", show_alert=True)
    await admin_carts_v2_auto_cb(update, context)


# ═══════════════════════════════════════════════
# TEMPLATE
# ═══════════════════════════════════════════════
async def admin_carts_v2_template_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not is_admin(update.effective_user.id):
        return

    try:
        template = await db.get_config("cart_template", "")
    except Exception:
        template = ""

    if not template:
        template = TEMPLATE_DEFAULT

    context.user_data["admin_cart_template"] = True
    context.user_data["_tpl_prompt_id"] = query.message.message_id
    context.user_data["_tpl_prompt_chat"] = query.message.chat_id

    preview = template[:400] + ("\n\n<i>...</i>" if len(template) > 400 else "")

    texto = (
        "📝 <b>Template do Lembrete</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "📄 <b>Template atual:</b>\n"
        "╭─────────────────╮\n"
        f"{preview}\n"
        "╰─────────────────╯\n\n"
        "🔧 <b>Variáveis disponíveis:</b>\n"
        "├ <code>{nome}</code> — nome do cliente\n"
        "├ <code>{produto}</code> — nome do produto\n"
        "└ <code>{preco}</code> — preço\n\n"
        "Envie o <b>novo template</b> abaixo.\n\n"
        "💡 Envie <code>resetar</code> para voltar ao padrão."
    )

    try:
        await query.edit_message_text(
            texto,
            reply_markup=ForceReply(selective=True),
            parse_mode=ParseMode.HTML,
        )
    except Exception:
        pass


async def admin_carts_v2_template_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.user_data.get("admin_cart_template"):
        return
    if not is_admin(update.effective_user.id):
        return

    texto = update.message.text or ""

    try:
        await update.message.delete()
    except Exception:
        pass

    if texto.startswith("/"):
        context.user_data.pop("admin_cart_template", None)
        await _delete_prompt(context, "_tpl_prompt_id", "_tpl_prompt_chat")
        return

    if not texto.strip():
        return

    if texto.strip().lower() == "resetar":
        await db.set_config("cart_template", "")
        msg = "🔄 Template resetado para o padrão!"
    else:
        await db.set_config("cart_template", texto)
        msg = "✅ Template atualizado!"

    context.user_data.pop("admin_cart_template", None)
    await _delete_prompt(context, "_tpl_prompt_id", "_tpl_prompt_chat")

    await db.log_admin_action(update.effective_user.id, "cart_template")

    try:
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=msg,
            reply_markup=menus.admin_back_kb(),
            parse_mode=ParseMode.HTML,
        )
    except Exception:
        pass


# ═══════════════════════════════════════════════
# JOB — RODA NO BOT
# ═══════════════════════════════════════════════
async def check_abandoned_carts_v2(context: ContextTypes.DEFAULT_TYPE):
    try:
        ligado = (await db.get_config("cart_auto", "1")) == "1"
        if not ligado:
            return

        minutos = int(await db.get_config("cart_minutes", "5"))
    except Exception:
        minutos = 5

    try:
        carts = await db.list_abandoned_carts(minutes=minutos)
    except Exception as e:
        logger.exception("Erro buscando carrinhos: %s", e)
        return

    for c in carts:
        try:
            user_id = c["user_id"]
            product_id = c["product_id"]

            ok = await _send_reminder(context.bot, user_id, product_id)
            if ok:
                await db.admin_carts_v2_increment_reminder(user_id, product_id)
                logger.info("Carrinho notificado: %s/%s", user_id, product_id)

            await db.mark_cart_notified(user_id, product_id)
        except Exception as e:
            logger.warning("Falha cart user=%s: %s", c.get("user_id"), e)
            try:
                await db.mark_cart_notified(c["user_id"], c["product_id"])
            except Exception:
                pass
