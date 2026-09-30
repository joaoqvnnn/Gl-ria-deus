import asyncio
from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import ContextTypes

from config import WITHDRAW_MIN
from database import db
from handlers import _state
from keyboards import menus
from texts import messages


LABELS = {
    "email": "Email",
    "cpf": "CPF",
    "phone": "Telefone",
    "random": "Chave Aleatória",
}


async def withdraw_open(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    try:
        await query.edit_message_text(
            messages.withdraw_menu_text(),
            reply_markup=menus.withdraw_type_keyboard(),
            parse_mode=ParseMode.HTML,
        )
    except Exception:
        pass


async def withdraw_type(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    key_type = query.data.split(":")[-1]

    _state.set_state(context.user_data, "awaiting_wd_key")
    context.user_data["wd_type"] = key_type
    context.user_data["_wd_key_prompt_id"] = query.message.message_id
    context.user_data["_wd_key_prompt_chat"] = query.message.chat_id

    try:
        await query.edit_message_text(
            messages.withdraw_key_prompt(LABELS.get(key_type, key_type)),
            reply_markup=menus.withdraw_amount_cancel_keyboard(),
            parse_mode=ParseMode.HTML,
        )
    except Exception:
        pass


async def withdraw_key_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not _state.is_set(context.user_data, "awaiting_wd_key"):
        return

    text = (update.message.text or "").strip()

    # Apaga a mensagem que o usuário digitou
    try:
        await update.message.delete()
    except Exception:
        pass

    chat_id = update.effective_chat.id

    # Comando → cancela
    if text.startswith("/"):
        await _delete_prompt(context, "_wd_key_prompt_id", "_wd_key_prompt_chat")
        _state.clear_all(context.user_data)
        return

    if len(text) < 3:
        # Erro → edita o prompt com aviso
        key_type = context.user_data.get("wd_type", "random")
        await _edit_prompt_error(
            context,
            "_wd_key_prompt_id", "_wd_key_prompt_chat",
            "❌ Chave inválida.\n\n" + messages.withdraw_key_prompt(LABELS.get(key_type, key_type)),
            menus.withdraw_amount_cancel_keyboard(),
        )
        return

    key_type = context.user_data.get("wd_type", "random")
    user = update.effective_user

    await db.set_pix_key(
        user.id, key_type, text,
        name=user.first_name or "Usuário",
        bank="—",
    )

    # Salva o ID da msg do prompt pra apagar depois da confirmação
    prompt_id = context.user_data.get("_wd_key_prompt_id")
    prompt_chat = context.user_data.get("_wd_key_prompt_chat")

    _state.clear_all(context.user_data)
    # Recoloca os IDs (clear_all não limpa chaves extras, mas por segurança)
    context.user_data["_wd_key_prompt_id"] = prompt_id
    context.user_data["_wd_key_prompt_chat"] = prompt_chat

    u = await db.get_user(user.id)

    # EDITA o prompt mostrando a confirmação
    if prompt_id and prompt_chat:
        try:
            await context.bot.edit_message_text(
                chat_id=prompt_chat,
                message_id=prompt_id,
                text=messages.withdraw_confirm_key_text(u, key_type),
                reply_markup=menus.withdraw_confirm_key_keyboard(),
                parse_mode=ParseMode.HTML,
            )
        except Exception:
            pass
    else:
        # Fallback: manda msg nova
        try:
            await context.bot.send_message(
                chat_id=chat_id,
                text=messages.withdraw_confirm_key_text(u, key_type),
                reply_markup=menus.withdraw_confirm_key_keyboard(),
                parse_mode=ParseMode.HTML,
            )
        except Exception:
            pass


async def withdraw_confirm_key(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user = update.effective_user

    # 🧹 Apaga o prompt do cadastro (agora que confirmou)
    await _delete_prompt(context, "_wd_key_prompt_id", "_wd_key_prompt_chat")

    u = await db.get_user(user.id)
    if not u:
        return

    balance = float(u["balance"])

    # EDITA a msg atual (a de confirmação) mostrando o saldo
    try:
        await query.edit_message_text(
            messages.withdraw_confirm_balance_text(balance),
            reply_markup=menus.withdraw_balance_keyboard(),
            parse_mode=ParseMode.HTML,
        )
    except Exception:
        pass


async def withdraw_edit_key(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    await _delete_prompt(context, "_wd_key_prompt_id", "_wd_key_prompt_chat")

    try:
        await query.edit_message_text(
            messages.withdraw_menu_text(),
            reply_markup=menus.withdraw_type_keyboard(),
            parse_mode=ParseMode.HTML,
        )
    except Exception:
        pass


async def withdraw_sacar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user = update.effective_user

    u = await db.get_user(user.id)
    if not u:
        return

    balance = float(u["balance"])
    name = u.get("first_name") or "Usuário"

    _state.set_state(context.user_data, "awaiting_wd_amount")
    context.user_data["_wd_amount_prompt_id"] = query.message.message_id
    context.user_data["_wd_amount_prompt_chat"] = query.message.chat_id

    try:
        await query.edit_message_text(
            messages.withdraw_amount_prompt(name, balance),
            reply_markup=menus.withdraw_amount_cancel_keyboard(),
            parse_mode=ParseMode.HTML,
        )
    except Exception:
        pass


async def withdraw_amount_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not _state.is_set(context.user_data, "awaiting_wd_amount"):
        return

    text = (update.message.text or "").strip().replace(",", ".")

    # Apaga msg do usuário
    try:
        await update.message.delete()
    except Exception:
        pass

    user = update.effective_user
    chat_id = update.effective_chat.id

    if text.startswith("/"):
        await _delete_prompt(context, "_wd_amount_prompt_id", "_wd_amount_prompt_chat")
        _state.clear_all(context.user_data)
        return

    u = await db.get_user(user.id)
    if not u:
        _state.clear_all(context.user_data)
        return

    try:
        valor = float(text)
        if valor < WITHDRAW_MIN or valor > float(u["balance"]):
            raise ValueError
    except ValueError:
        # Erro → edita o prompt
        name = u.get("first_name") or "Usuário"
        await _edit_prompt_error(
            context,
            "_wd_amount_prompt_id", "_wd_amount_prompt_chat",
            messages.withdraw_invalid_amount() + "\n\n" + messages.withdraw_amount_prompt(name, float(u["balance"])),
            menus.withdraw_amount_cancel_keyboard(),
        )
        return

    if not u.get("payout_password"):
        await _delete_prompt(context, "_wd_amount_prompt_id", "_wd_amount_prompt_chat")
        _state.clear_all(context.user_data)
        try:
            await context.bot.send_message(
                chat_id=chat_id,
                text=messages.withdraw_no_pin(),
                reply_markup=menus.affiliates_active_keyboard(user_id=user.id),
                parse_mode=ParseMode.HTML,
            )
        except Exception:
            pass
        return

    # Salva valor e vai pra fase da senha
    prompt_id = context.user_data.pop("_wd_amount_prompt_id", None)
    prompt_chat = context.user_data.pop("_wd_amount_prompt_chat", None)

    _state.set_state(context.user_data, "awaiting_wd_pin")
    context.user_data["wd_amount"] = valor
    context.user_data["_wd_pin_prompt_id"] = prompt_id
    context.user_data["_wd_pin_prompt_chat"] = prompt_chat

    # Edita o prompt pra pedir a senha
    if prompt_id and prompt_chat:
        try:
            await context.bot.edit_message_text(
                chat_id=prompt_chat,
                message_id=prompt_id,
                text=messages.withdraw_password_prompt(),
                parse_mode=ParseMode.HTML,
            )
        except Exception:
            pass
    else:
        try:
            await context.bot.send_message(
                chat_id=chat_id,
                text=messages.withdraw_password_prompt(),
                parse_mode=ParseMode.HTML,
            )
        except Exception:
            pass


async def withdraw_pin_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not _state.is_set(context.user_data, "awaiting_wd_pin"):
        return

    pin = (update.message.text or "").strip()
    user = update.effective_user

    # Apaga msg do usuário (privacidade)
    try:
        await update.message.delete()
    except Exception:
        pass

    chat_id = update.effective_chat.id

    if pin.startswith("/"):
        await _delete_prompt(context, "_wd_pin_prompt_id", "_wd_pin_prompt_chat")
        _state.clear_all(context.user_data)
        return

    ok = await db.check_payout_password(user.id, pin)
    if not ok:
        # Erro → edita o prompt
        await _edit_prompt_error(
            context,
            "_wd_pin_prompt_id", "_wd_pin_prompt_chat",
            messages.withdraw_wrong_password() + "\n\n" + messages.withdraw_password_prompt(),
        )
        return

    valor = float(context.user_data.get("wd_amount", 0) or 0)

    # 🧹 Apaga o prompt da senha
    await _delete_prompt(context, "_wd_pin_prompt_id", "_wd_pin_prompt_chat")
    _state.clear_all(context.user_data)

    if valor <= 0:
        return

    u = await db.get_user(user.id)
    if not u:
        return

    try:
        await context.bot.send_message(
            chat_id=chat_id,
            text=messages.withdraw_processing(),
            parse_mode=ParseMode.HTML,
        )
    except Exception:
        pass

    await asyncio.sleep(2)

    wd = await db.create_withdrawal(
        user.id, valor,
        u.get("pix_key_type") or "random",
        u.get("pix_key") or "-",
    )
    await db.update_balance(user.id, -valor)
    await db.mark_withdrawal_processed(wd["id"])

    try:
        await context.bot.send_message(
            chat_id=chat_id,
            text=messages.withdraw_success_text(wd),
            reply_markup=menus.withdraw_success_keyboard(wd["id"]),
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
