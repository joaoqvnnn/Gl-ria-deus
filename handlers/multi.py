from telegram import Update, ForceReply
from telegram.constants import ParseMode
from telegram.ext import ContextTypes

from database import db
from handlers import _state
from keyboards import menus
from texts import messages
from handlers.buy import _process_purchase


# ═══════════════════════════════════════════════
# 🛒 COMPRAR MAIS DE UM — iniciar
# ═══════════════════════════════════════════════
async def multi_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Ao clicar em "🛒 Comprar mais de um" na tela do produto:
      - Seta o state awaiting_multi
      - ENVIA NOVA MENSAGEM com ForceReply
    """
    query = update.callback_query
    await query.answer()

    try:
        pid = int(query.data.split(":", 1)[1])
    except (IndexError, ValueError):
        return

    product = await db.get_product(pid)
    if not product:
        return

    # ⚠️ ORDEM IMPORTA:
    # 1) set_state() limpa TODOS os states (inclusive awaiting_multi se existir)
    # 2) depois guardamos o dict com o product_id
    _state.set_state(context.user_data, "awaiting_multi")
    context.user_data["awaiting_multi"] = {"product_id": pid}

    try:
        await context.bot.send_message(
            chat_id=query.message.chat_id,
            text=messages.multi_qty_text(product),
            reply_markup=ForceReply(selective=True),
            parse_mode=ParseMode.HTML,
        )
    except Exception:
        pass


# ═══════════════════════════════════════════════
# 🛒 COMPRAR MAIS DE UM — handler de texto (quantidade)
# ═══════════════════════════════════════════════
async def multi_qty_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Recebe a quantidade digitada (via ForceReply).
    - Se /cancelar → LIMPA state e envia msg
    - Se inválido → pede novamente (NÃO limpa)
    - Se válido → LIMPA state e envia o resultado
    """
    awaiting = context.user_data.get("awaiting_multi")
    if not awaiting:
        return

    text = (update.message.text or "").strip()
    user = update.effective_user

    # ─── /cancelar ou /start
    if text.startswith("/"):
        _state.clear_all(context.user_data)
        await update.message.reply_text(
            messages.multi_cancelled_text(),
            parse_mode=ParseMode.HTML,
        )
        return

    # ─── Parse int
    try:
        qty = int(text)
        if qty < 1:
            raise ValueError
    except ValueError:
        await update.message.reply_text(
            "❌ Digite um número válido maior que 0.",
            parse_mode=ParseMode.HTML,
        )
        return

    pid = awaiting.get("product_id")
    product = await db.get_product(pid) if pid else None
    u = await db.get_user(user.id)

    if not product or not u:
        _state.clear_all(context.user_data)
        return

    if qty > int(product["stock"]):
        await update.message.reply_text(
            f"❌ Estoque insuficiente. Disponível: <b>{product['stock']}</b>",
            parse_mode=ParseMode.HTML,
        )
        return

    _state.clear_all(context.user_data)

    # ─── ENVIA NOVA MENSAGEM com o resultado do pedido
    try:
        await update.message.reply_text(
            messages.multi_result_text(u, product, qty),
            reply_markup=menus.multi_confirm_keyboard(pid, qty),
            parse_mode=ParseMode.HTML,
        )
    except Exception:
        pass


# ═══════════════════════════════════════════════
# 🛒 COMPRAR MAIS DE UM — confirmar compra
# ═══════════════════════════════════════════════
async def multi_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Ao clicar em "✅ Confirmar Compra":
      - Verifica saldo
      - Se suficiente → processa compra (edita msg + entrega)
      - Se insuficiente → ENVIA NOVA MSG com aviso + botão PIX
    """
    query = update.callback_query
    await query.answer()
    user = update.effective_user

    # callback_data: multi:confirm:{pid}:{qty}
    try:
        _, _, pid_str, qty_str = query.data.split(":")
        pid = int(pid_str)
        qty = int(qty_str)
    except (ValueError, IndexError):
        return

    u = await db.get_or_create_user(user.id, user.username, user.first_name)
    product = await db.get_product(pid)
    if not product:
        return

    total = float(product["price"]) * qty
    balance = float(u["balance"])

    # ─── Saldo suficiente → processa
    if balance >= total:
        try:
            await query.edit_message_text(
                "⏳ <b>Processando compra...</b>",
                parse_mode=ParseMode.HTML,
            )
        except Exception:
            pass

        await _process_purchase(
            context, query.message.chat_id, u, product, quantity=qty
        )
        return

    # ─── Saldo insuficiente → NOVA MSG com aviso + botão PIX
    try:
        await context.bot.send_message(
            chat_id=query.message.chat_id,
            text=messages.insufficient_text(u, product, qty),
            reply_markup=menus.insufficient_keyboard(pid, qty, total),
            parse_mode=ParseMode.HTML,
        )
    except Exception:
        pass


# ═══════════════════════════════════════════════
# 🛒 COMPRAR MAIS DE UM — cancelar
# ═══════════════════════════════════════════════
async def multi_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Ao clicar em "❌ Cancelar":
      - Limpa state + carrinho abandonado
      - ENVIA NOVA MENSAGEM de cancelamento
    """
    query = update.callback_query
    await query.answer()
    user = update.effective_user

    _state.clear_all(context.user_data)

    # ─── Limpa carrinho abandonado
    try:
        await db.clear_cart_view(user.id, None)
    except Exception:
        pass

    try:
        await context.bot.send_message(
            chat_id=query.message.chat_id,
            text=messages.multi_cancelled_text(),
            parse_mode=ParseMode.HTML,
        )
    except Exception:
        pass
