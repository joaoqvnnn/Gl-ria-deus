from telegram import Update, ForceReply
from telegram.constants import ParseMode
from telegram.ext import ContextTypes

from database import db
from keyboards import menus
from texts import messages
from handlers.buy import _process_purchase


# ─── Callback: 🛒 Comprar mais de um → ENVIA NOVA MENSAGEM com ForceReply
async def multi_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user = update.effective_user

    try:
        pid = int(query.data.split(":", 1)[1])
    except (IndexError, ValueError):
        return

    product = await db.get_product(pid)
    if not product:
        return

    context.user_data["awaiting_multi"] = {"product_id": pid}

    await context.bot.send_message(
        chat_id=query.message.chat_id,
        text=messages.multi_qty_text(product),
        reply_markup=ForceReply(selective=True),
        parse_mode=ParseMode.HTML,
    )


# ─── Handler de texto (aguardando quantidade)
async def multi_qty_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    awaiting = context.user_data.get("awaiting_multi")
    if not awaiting:
        return

    text = (update.message.text or "").strip()
    user = update.effective_user

    # /cancelar
    if text.startswith("/cancelar"):
        context.user_data.pop("awaiting_multi", None)
        await update.message.reply_text(
            messages.multi_cancelled_text(),
            parse_mode=ParseMode.HTML,
        )
        return

    # Parse int
    try:
        qty = int(text)
        if qty < 1:
            raise ValueError
    except ValueError:
        await update.message.reply_text(
            "❌ Digite um número válido maior que 0.", parse_mode=ParseMode.HTML
        )
        return

    pid = awaiting["product_id"]
    product = await db.get_product(pid)
    u = await db.get_user(user.id)

    if not product:
        context.user_data.pop("awaiting_multi", None)
        return

    if qty > product["stock"]:
        await update.message.reply_text(
            f"❌ Estoque insuficiente. Disponível: <b>{product['stock']}</b>",
            parse_mode=ParseMode.HTML,
        )
        return

    context.user_data.pop("awaiting_multi", None)

    # ENVIA NOVA MENSAGEM com o resultado do pedido
    await update.message.reply_text(
        messages.multi_result_text(u, product, qty),
        reply_markup=menus.multi_confirm_keyboard(pid, qty),
        parse_mode=ParseMode.HTML,
    )


# ─── Confirmar Compra (múltipla)
async def multi_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user = update.effective_user

    # multi:confirm:{pid}:{qty}
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

    # Saldo suficiente
    if balance >= total:
        # Edita a mensagem de resultado → "Processando" e vai pra entrega
        try:
            await query.edit_message_text(
                "⏳ <b>Processando compra...</b>", parse_mode=ParseMode.HTML
            )
        except Exception:
            pass
        await _process_purchase(context, query.message.chat_id, u, product, quantity=qty)
        return

    # Saldo insuficiente → ENVIA NOVA MENSAGEM com aviso + PIX
    kb = menus.insufficient_keyboard(pid, qty, total)
    await context.bot.send_message(
        chat_id=query.message.chat_id,
        text=messages.insufficient_text(u, product, qty),
        reply_markup=kb,
        parse_mode=ParseMode.HTML,
    )


async def multi_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    context.user_data.pop("awaiting_multi", None)
    # ENVIA NOVA MENSAGEM (conforme fluxo)
    await context.bot.send_message(
        chat_id=query.message.chat_id,
        text=messages.multi_cancelled_text(),
        parse_mode=ParseMode.HTML,
    )
