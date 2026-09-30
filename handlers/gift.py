from telegram import Update
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
    context.user_data["_gift_prompt_id"] = query.message.message_id
    context.user_data["_gift_prompt_chat"] = query.message.chat_id

    try:
        await query.edit_message_text(
            messages.gift_prompt_text(),
            reply_markup=menus.gift_cancel_keyboard(),
            parse_mode=ParseMode.HTML,
        )
    except Exception:
        pass


async def gift_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    await _delete_prompt(context, "_gift_prompt_id", "_gift_prompt_chat")
    _state.clear_all(context.user_data)
    context.user_data.pop("last_gift", None)

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

    # Apaga a mensagem que o usuário digitou
    try:
        await update.message.delete()
    except Exception:
        pass

    user = update.effective_user
    chat_id = update.effective_chat.id

    # Comando → cancela
    if not code or code.startswith("/"):
        await _delete_prompt(context, "_gift_prompt_id", "_gift_prompt_chat")
        _state.clear_all(context.user_data)
        return

    u = await db.get_or_create_user(user.id, user.username, user.first_name)
    gift = await db.get_gift(code)

    # ─── Inválido → EDITA o prompt mostrando erro (não apaga)
    if not gift:
        await _edit_prompt_error(
            context,
            "_gift_prompt_id", "_gift_prompt_chat",
            messages.gift_invalid_text() + "\n\n" + messages.gift_prompt_text(),
            menus.gift_cancel_keyboard(),
        )
        return

    # ─── Já resgatado → EDITA o prompt mostrando erro
    if gift.get("redeemed_by"):
        await _edit_prompt_error(
            context,
            "_gift_prompt_id", "_gift_prompt_chat",
            messages.gift_already_used_text() + "\n\n" + messages.gift_prompt_text(),
            menus.gift_cancel_keyboard(),
        )
        return

    # ─── SUCESSO → apaga prompt e limpa state
    await db.redeem_gift(code, user.id)
    await _delete_prompt(context, "_gift_prompt_id", "_gift_prompt_chat")
    _state.clear_all(context.user_data)

    # Gift de saldo
    if gift["tipo"] == "saldo":
        await db.update_balance(user.id, float(gift["valor"]))
        u2 = await db.get_user(user.id)

        try:
            await context.bot.send_message(
                chat_id=chat_id,
                text=messages.gift_success_text(
                    gift,
                    extra=f"\n💼 Saldo atual: <b>R$ {float(u2['balance']):.2f}</b>",
                ),
                reply_markup=menus.back_to_menu_keyboard(),
                parse_mode=ParseMode.HTML,
            )
        except Exception:
            pass
        return

    # Gift de produto
    context.user_data["last_gift"] = {
        "code": code,
        "product_id": gift.get("product_id"),
    }

    try:
        await context.bot.send_message(
            chat_id=chat_id,
            text=messages.gift_success_text(gift),
            reply_markup=menus.gift_success_keyboard(),
            parse_mode=ParseMode.HTML,
        )
    except Exception:
        pass


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


# ═══════════════════════════════════════════════
# HELPERS
# ═══════════════════════════════════════════════
async def _delete_prompt(context, id_key: str, chat_key: str):
    pid = context.user_data.pop(id_key, None)
    chat = context.user_data.pop(chat_key, None)
    if pid and chat:
        try:
            await context.bot.delete_message(chat_id=chat, message_id=pid)
        except Exception:
            pass


async def _edit_prompt_error(context, id_key: str, chat_key: str, text: str, kb=None):
    pid = context.user_data.get(id_key)
    chat = context.user_data.get(chat_key)
    if pid and chat:
        try:
            await context.bot.edit_message_text(
                chat_id=chat,
                message_id=pid,
                text=text,
                reply_markup=kb,
                parse_mode=ParseMode.HTML,
            )
        except Exception:
            pass
