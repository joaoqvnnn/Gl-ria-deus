import asyncio
from telegram import Update, ForceReply, InputMediaPhoto
from telegram.constants import ParseMode
from telegram.ext import ContextTypes

from config import TOPUP_MIN, TOPUP_BONUS_MIN, TOPUP_BONUS_RATE
from database import db
from keyboards import menus
from services import pix as pix_service
from services import qrcode_gen
from services import channel_notify
from texts import messages


async def topup_open(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(
        messages.topup_menu_text(),
        reply_markup=menus.topup_menu_keyboard(),
        parse_mode=ParseMode.HTML,
    )


async def topup_pix_open(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    context.user_data["awaiting_topup_value"] = True

    try:
        await query.edit_message_text(
            messages.topup_value_prompt_text(),
            reply_markup=menus.back_to_menu_keyboard(),
            parse_mode=ParseMode.HTML,
        )
    except Exception:
        pass

    await context.bot.send_message(
        chat_id=query.message.chat_id,
        text="Digite o valor abaixo 👇",
        reply_markup=ForceReply(selective=True),
    )


async def topup_value_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.user_data.get("awaiting_topup_value"):
        return

    text = (update.message.text or "").strip().replace(",", ".")
    user = update.effective_user
    u = await db.get_or_create_user(user.id, user.username, user.first_name)

    try:
        valor = float(text)
        if valor < TOPUP_MIN:
            raise ValueError
    except ValueError:
        await update.message.reply_text(
            messages.topup_invalid_value_text(),
            parse_mode=ParseMode.HTML,
        )
        return

    context.user_data.pop("awaiting_topup_value", None)

    bonus = valor * TOPUP_BONUS_RATE if valor >= TOPUP_BONUS_MIN else 0.0
    saldo_atual = float(u["balance"])
    saldo_futuro = saldo_atual + valor + bonus

    await context.bot.send_message(
        chat_id=update.message.chat_id,
        text=messages.generating_payment_text(),
        parse_mode=ParseMode.HTML,
    )

    pix_data = pix_service.gerar_pix(valor, "Recarga Larizinha")
    await db.create_pix(
        pix_data["id"], user.id, valor, "recarga", None, None, pix_data["copia_cola"]
    )

    context.user_data[f"bonus:{pix_data['id']}"] = bonus

    await asyncio.sleep(2)

    img = qrcode_gen.generate_pix_image(
        pix_code=pix_data["copia_cola"],
        valor=valor,
        id_recarga=pix_data["id"][:8],
        expira=pix_data["expira_em"],
        titulo="PIX - Recarga Larizinha",
        saldo_atual=saldo_atual,
        saldo_futuro=saldo_futuro,
        bonus=bonus,
    )

    await context.bot.send_photo(
        chat_id=update.message.chat_id,
        photo=img,
        caption=messages.topup_pix_caption(
            pix_data["id"], valor, bonus, saldo_atual, saldo_futuro, pix_data["expira_em"]
        ),
        reply_markup=menus.topup_pix_keyboard(pix_data["id"]),
        parse_mode=ParseMode.HTML,
    )


async def topup_copy(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    pix_id = query.data.split(":", 2)[2]
    pix = await db.get_pix(pix_id)
    if not pix:
        await query.answer("PIX não encontrado.", show_alert=True)
        return
    await query.answer(f"PIX Copia e Cola:\n\n{pix['copia_cola']}", show_alert=True)


async def topup_check(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    pix_id = query.data.split(":", 2)[2]
    pix = await db.get_pix(pix_id)
    if not pix:
        await query.answer("PIX não encontrado.", show_alert=True)
        return

    if pix["status"] != "paid":
        await context.bot.send_message(
            chat_id=query.message.chat_id,
            text=messages.not_paid_text(),
            parse_mode=ParseMode.HTML,
        )
        return

    valor = float(pix["valor"])
    green = qrcode_gen.generate_paid_image(
        pix_code=pix["copia_cola"],
        valor=valor,
        titulo="Recarga Confirmada",
    )
    try:
        await query.edit_message_media(
            media=InputMediaPhoto(
                media=green,
                caption=messages.paid_caption(),
                parse_mode=ParseMode.HTML,
            ),
            reply_markup=None,
        )
    except Exception:
        pass

    bonus = float(context.user_data.get(f"bonus:{pix_id}", 0.0))
    await db.update_balance(pix["user_id"], valor + bonus)
    u = await db.get_user(pix["user_id"])

    try:
        await channel_notify.notify_topup(context.bot, u, valor, bonus)
    except Exception:
        pass

    await context.bot.send_message(
        chat_id=query.message.chat_id,
        text=messages.topup_success_text(valor, bonus, float(u["balance"])),
        reply_markup=menus.topup_success_keyboard(),
        parse_mode=ParseMode.HTML,
    )


async def topup_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    pix_id = query.data.split(":", 2)[2]
    await db.cancel_pix(pix_id)

    try:
        await query.edit_message_caption(
            caption=messages.topup_cancelled_text(),
            parse_mode=ParseMode.HTML,
        )
    except Exception:
        pass
