import asyncio
from telegram import Update, ForceReply
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

# Texto invisível pra mandar o ForceReply sem poluir a tela
_ZERO = "\u200b"


# ═══════════════════════════════════════════════
# Abrir menu de saque
# ═══════════════════════════════════════════════
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


# ═══════════════════════════════════════════════
# Escolheu tipo de chave → pede a chave via ForceReply
# ═══════════════════════════════════════════════
async def withdraw_type(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    key_type = query.data.split(":")[-1]

    _state.set_state(context.user_data, "awaiting_wd_key")
    context.user_data["wd_type"] = key_type

    # 1) Edita a mensagem com o prompt
    try:
        await query.edit_message_text(
            messages.withdraw_key_prompt(LABELS.get(key_type, key_type)),
            reply_markup=menus.withdraw_amount_cancel_keyboard(),
            parse_mode=ParseMode.HTML,
        )
    except Exception:
        pass

    # 2) ForceReply numa nova mensagem (sem texto visível)
    try:
        await context.bot.send_message(
            chat_id=query.message.chat_id,
            text=_ZERO,
            reply_markup=ForceReply(selective=True),
        )
    except Exception:
        pass


# ═══════════════════════════════════════════════
# Recebeu a chave
# ═══════════════════════════════════════════════
async def withdraw_key_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not _state.is_set(context.user_data, "awaiting_wd_key"):
        return

    text = (update.message.text or "").strip()

    # Comando durante o fluxo → cancela
    if text.startswith("/"):
        _state.clear_all(context.user_data)
        await update.message.reply_text(
            "❌ Operação cancelada.",
            parse_mode=ParseMode.HTML,
        )
        return

    if len(text) < 3:
        await update.message.reply_text(
            "❌ Chave inválida. Tente novamente.",
            parse_mode=ParseMode.HTML,
        )
        return

    key_type = context.user_data.get("wd_type", "random")
    user = update.effective_user

    await db.set_pix_key(
        user.id, key_type, text,
        name=user.first_name or "Usuário",
        bank="—",
    )

    _state.clear_all(context.user_data)

    u = await db.get_user(user.id)

    try:
        await update.message.reply_text(
            messages.withdraw_confirm_key_text(u, key_type),
            reply_markup=menus.withdraw_confirm_key_keyboard(),
            parse_mode=ParseMode.HTML,
        )
    except Exception:
        pass


# ═══════════════════════════════════════════════
# Confirma a chave
# ═══════════════════════════════════════════════
async def withdraw_confirm_key(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user = update.effective_user

    u = await db.get_user(user.id)
    if not u:
        return

    balance = float(u["balance"])

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
    try:
        await query.edit_message_text(
            messages.withdraw_menu_text(),
            reply_markup=menus.withdraw_type_keyboard(),
            parse_mode=ParseMode.HTML,
        )
    except Exception:
        pass


# ═══════════════════════════════════════════════
# Clicou em "Sacar" → pede o valor
# ═══════════════════════════════════════════════
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

    try:
        await query.edit_message_text(
            messages.withdraw_amount_prompt(name, balance),
            reply_markup=menus.withdraw_amount_cancel_keyboard(),
            parse_mode=ParseMode.HTML,
        )
    except Exception:
        pass

    try:
        await context.bot.send_message(
            chat_id=query.message.chat_id,
            text=_ZERO,
            reply_markup=ForceReply(selective=True),
        )
    except Exception:
        pass


# ═══════════════════════════════════════════════
# Recebeu o valor → pede a senha
# ═══════════════════════════════════════════════
async def withdraw_amount_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not _state.is_set(context.user_data, "awaiting_wd_amount"):
        return

    text = (update.message.text or "").strip().replace(",", ".")
    user = update.effective_user
    u = await db.get_user(user.id)
    if not u:
        _state.clear_all(context.user_data)
        return

    if text.startswith("/"):
        _state.clear_all(context.user_data)
        await update.message.reply_text(
            "❌ Operação cancelada.",
            parse_mode=ParseMode.HTML,
        )
        return

    try:
        valor = float(text)
        if valor < WITHDRAW_MIN or valor > float(u["balance"]):
            raise ValueError
    except ValueError:
        await update.message.reply_text(
            messages.withdraw_invalid_amount(),
            parse_mode=ParseMode.HTML,
        )
        return

    # Verifica se tem senha cadastrada
    if not u.get("payout_password"):
        _state.clear_all(context.user_data)
        await update.message.reply_text(
            messages.withdraw_no_pin(),
            parse_mode=ParseMode.HTML,
        )
        return

    # Guarda o valor e transita pra fase da senha
    _state.set_state(context.user_data, "awaiting_wd_pin")
    context.user_data["wd_amount"] = valor

    try:
        await update.message.reply_text(
            messages.withdraw_password_prompt(),
            reply_markup=ForceReply(selective=True),
            parse_mode=ParseMode.HTML,
        )
    except Exception:
        pass


# ═══════════════════════════════════════════════
# Recebeu a senha → processa o saque
# ═══════════════════════════════════════════════
async def withdraw_pin_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not _state.is_set(context.user_data, "awaiting_wd_pin"):
        return

    pin = (update.message.text or "").strip()
    user = update.effective_user

    if pin.startswith("/"):
        _state.clear_all(context.user_data)
        await update.message.reply_text(
            "❌ Operação cancelada.",
            parse_mode=ParseMode.HTML,
        )
        return

    # Apaga a mensagem com a senha (privacidade)
    try:
        await update.message.delete()
    except Exception:
        pass

    ok = await db.check_payout_password(user.id, pin)
    if not ok:
        # NÃO limpa o state — deixa ele tentar de novo
        try:
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=messages.withdraw_wrong_password(),
                parse_mode=ParseMode.HTML,
            )
        except Exception:
            pass
        return

    valor = float(context.user_data.get("wd_amount", 0) or 0)
    _state.clear_all(context.user_data)

    if valor <= 0:
        return

    u = await db.get_user(user.id)
    if not u:
        return

    # Mensagem "processando"
    try:
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=messages.withdraw_processing(),
            parse_mode=ParseMode.HTML,
        )
    except Exception:
        pass

    await asyncio.sleep(2)

    # Cria o saque e debita o saldo
    wd = await db.create_withdrawal(
        user.id,
        valor,
        u.get("pix_key_type") or "random",
        u.get("pix_key") or "-",
    )
    await db.update_balance(user.id, -valor)
    await db.mark_withdrawal_processed(wd["id"])

    try:
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=messages.withdraw_success_text(wd),
            reply_markup=menus.withdraw_success_keyboard(wd["id"]),
            parse_mode=ParseMode.HTML,
        )
    except Exception:
        pass
