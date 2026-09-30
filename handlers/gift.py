from telegram import Update, ForceReply
from telegram.constants import ParseMode
from telegram.ext import ContextTypes

from database import db
from handlers import _state
from keyboards import menus
from texts import messages


async def gift_open(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    _state.set_state(context.user_data, "awaiting_gift")

    # 1) Edita a mensagem com o prompt
    try:
        await query.edit_message_text(
            messages.gift_prompt_text(),
            reply_markup=menus.gift_cancel_keyboard(),
            parse_mode=ParseMode.HTML,
        )
    except Exception:
        pass

    # 2) Envia o ForceReply como NOVA mensagem (é isso que faz ele funcionar)
    try:
        await context.bot.send_message(
            chat_id=query.message.chat_id,
            text="Digite o código abaixo 👇",
            reply_markup=ForceReply(selective=True),
        )
    except Exception:
        pass


async def gift_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    _state.clear_all(context.user_data)

    u = await db.get_or_create_user(query.from_user.id, None, None)
    stats = await db.user_stats(u["user_id"])

    try:
        await query.edit_message_text(
            messages.profile_text(u, stats),
            reply_markup=menus.profile_keyboard(),
            parse_mode=ParseMode.HTML,
        )
    except Exception:
        pass


async def gift_code_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not _state.is_set(context.user_data, "awaiting_gift"):
        return

    code = (update.message.text or "").strip().upper()

    # /cancelar ou vazio → limpa
    if not code or code.startswith("/"):
        _state.clear_all(context.user_data)
        return

    user = update.effective_user
    u = await db.get_or_create_user(user.id, user.username, user.first_name)

    gift = await db.get_gift(code)

    # Inválido → LIMPA o state (senão trava)
    if not gift:
        _state.clear_all(context.user_data)
        await update.message.reply_text(
            messages.gift_invalid_text(),
            parse_mode=ParseMode.HTML,
        )
        return

    # Já usado → LIMPA
    if gift.get("redeemed_by"):
        _state.clear_all(context.user_data)
        await update.message.reply_text(
            messages.gift_already_used_text(),
            parse_mode=ParseMode.HTML,
        )
        return

    # Sucesso → LIMPA
    await db.redeem_gift(code, user.id)
    _state.clear_all(context.user_data)

    if gift["tipo"] == "saldo":
        await db.update_balance(user.id, float(gift["valor"]))
        u2 = await db.get_user(user.id)
        await update.message.reply_text(
            messages.gift_success_text(
                gift,
                extra=f"\n💼 Saldo atual: <b>R$ {float(u2['balance']):.2f}</b>",
            ),
            parse_mode=ParseMode.HTML,
        )
        return

    context.user_data["last_gift"] = {
        "code": code,
        "product_id": gift.get("product_id"),
    }

    await update.message.reply_text(
        messages.gift_success_text(gift),
        reply_markup=menus.gift_success_keyboard(),
        parse_mode=ParseMode.HTML,
    )


async def gift_use(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    last = context.user_data.get("last_gift")
    if not last or not last.get("product_id"):
        await query.answer("Produto do gift não encontrado.", show_alert=True)
        return

    pid = int(last["product_id"])
    user = update.effective_user
    u = await db.get_or_create_user(user.id, user.username, user.first_name)
    product = await db.get_product(pid)

    if not product:
        await query.answer("Produto não encontrado.", show_alert=True)
        return

    try:
        await query.edit_message_text(
            messages.product_text(u, product),
            reply_markup=menus.product_keyboard(pid),
            parse_mode=ParseMode.HTML,
        )
    except Exception:
        pass
