import asyncio
from telegram import Update, ForceReply
from telegram.constants import ParseMode
from telegram.ext import ContextTypes

from config import WITHDRAW_MIN
from database import db
from keyboards import menus
from texts import messages


LABELS = {
    "email": "Email",
    "cpf": "CPF",
    "phone": "Telefone",
    "random": "Chave Aleatória",
}


# ─── Abrir menu de saque
async def withdraw_open(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(
        messages.withdraw_menu_text(),
        reply_markup=menus.withdraw_type_keyboard(),
        parse_mode=ParseMode.HTML,
    )


# ─── Escolheu tipo de chave → ForceReply
async def withdraw_type(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    key_type = query.data.split(":")[-1]
    context.user_data["wd_type"] = key_type
    context.user_data["awaiting_wd_key"] = True

    try:
        await query.edit_message_text(
            messages.withdraw_key_prompt(LABELS[key_type]),
            reply_markup=menus.withdraw_amount_cancel_keyboard(),
            parse_mode=ParseMode.HTML,
        )
    except Exception:
        pass

    await context.bot.send_message(
        chat_id=query.message.chat_id,
        text="Digite abaixo 👇",
        reply_markup=ForceReply(selective=True),
    )


# ─── Recebeu a chave
async def withdraw_key_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.user_data.get("awaiting_wd_key"):
        return

    key = (update.message.text or "").strip()
    if len(key) < 3:
        await update.message.reply_text("❌ Chave inválida.", parse_mode=ParseMode.HTML)
        return

    key_type = context.user_data.get("wd_type", "random")
    user = update.effective_user

    await db.set_pix_key(
        user.id, key_type, key,
        name=user.first_name or "Usuário",
        bank="—",
    )
    context.user_data.pop("awaiting_wd_key", None)

    u = await db.get_user(user.id)
    await update.message.reply_text(
        messages.withdraw_confirm_key_text(u, key_type),
        reply_markup=menus.withdraw_confirm_key_keyboard(),
        parse_mode=ParseMode.HTML,
    )


# ─── Confirma a chave
async def withdraw_confirm_key(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user = update.effective_user

    u = await db.get_user(user.id)
    balance = float(u["balance"])

    await query.edit_message_text(
        messages.withdraw_confirm_balance_text(balance),
        reply_markup=menus.withdraw_balance_keyboard(),
        parse_mode=ParseMode.HTML,
    )


async def withdraw_edit_key(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(
        messages.withdraw_menu_text(),
        reply_markup=menus.withdraw_type_keyboard(),
        parse_mode=ParseMode.HTML,
    )


# ─── Clicou em "Sacar" → pede valor com saudação dinâmica
async def withdraw_sacar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user = update.effective_user

    u = await db.get_user(user.id)
    balance = float(u["balance"])
    name = u.get("first_name") or "Usuário"

    context.user_data["awaiting_wd_amount"] = True

    try:
        await query.edit_message_text(
            messages.withdraw_amount_prompt(name, balance),
            reply_markup=menus.withdraw_amount_cancel_keyboard(),
            parse_mode=ParseMode.HTML,
        )
    except Exception:
        pass

    await context.bot.send_message(
        chat_id=query.message.chat_id,
        text="Digite abaixo 👇",
        reply_markup=ForceReply(selective=True),
    )


# ─── Recebeu o valor → pede senha
async def withdraw_amount_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.user_data.get("awaiting_wd_amount"):
        return

    text = (update.message.text or "").strip().replace(",", ".")
    user = update.effective_user
    u = await db.get_user(user.id)

    try:
        valor = float(text)
        if valor < WITHDRAW_MIN or valor > float(u["balance"]):
            raise ValueError
    except ValueError:
        await update.message.reply_text(
            messages.withdraw_invalid_amount(), parse_mode=ParseMode.HTML
        )
        return

    # Verifica se tem senha
    if not u.get("payout_password"):
        context.user_data.pop("awaiting_wd_amount", None)
        await update.message.reply_text(
            messages.withdraw_no_pin(), parse_mode=ParseMode.HTML
        )
        return

    context.user_data["wd_amount"] = valor
    context.user_data.pop("awaiting_wd_amount", None)
    context.user_data["awaiting_wd_pin"] = True

    await update.message.reply_text(
        messages.withdraw_password_prompt(),
        reply_markup=ForceReply(selective=True),
        parse_mode=ParseMode.HTML,
    )


# ─── Recebeu a senha → processa
async def withdraw_pin_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.user_data.get("awaiting_wd_pin"):
        return

    pin = (update.message.text or "").strip()
    user = update.effective_user

    # Apaga a mensagem com a senha (privacidade)
    try:
        await update.message.delete()
    except Exception:
        pass

    ok = await db.check_payout_password(user.id, pin)
    if not ok:
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=messages.withdraw_wrong_password(),
            parse_mode=ParseMode.HTML,
        )
        return

    valor = float(context.user_data.pop("wd_amount", 0))
    context.user_data.pop("awaiting_wd_pin", None)

    u = await db.get_user(user.id)

    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=messages.withdraw_processing(),
        parse_mode=ParseMode.HTML,
    )
    await asyncio.sleep(2)

    # Cria o saque e deduz do saldo
    wd = await db.create_withdrawal(
        user.id, valor, u.get("pix_key_type") or "random", u.get("pix_key") or "-"
    )
    await db.update_balance(user.id, -valor)
    await db.mark_withdrawal_processed(wd["id"])

    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=messages.withdraw_success_text(wd),
        reply_markup=menus.withdraw_success_keyboard(wd["id"]),
        parse_mode=ParseMode.HTML,
    )
