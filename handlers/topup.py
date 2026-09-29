import asyncio
from telegram import Update, ForceReply, InputMediaPhoto
from telegram.constants import ParseMode
from telegram.ext import ContextTypes

from database import db
from keyboards import menus
from services import pix as pix_service
from services import qrcode_gen
from texts import messages


MIN_VALUE = 4.00
BONUS_MIN = 10.00
BONUS_RATE = 0.10


async def topup_open(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """EDITS para o menu de Recarregar Saldo."""
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(
        messages.topup_menu_text(),
        reply_markup=menus.topup_menu_keyboard(),
        parse_mode=ParseMode.HTML,
    )


async def topup_pix_open(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """EDITS para o prompt de valor + ForceReply."""
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
        if valor < MIN_VALUE:
            raise ValueError
    except ValueError:
        await update.message.reply_text(
            messages.topup_invalid_value_text(),
            parse_mode=ParseMode.HTML,
        )
        return

    context.user_data.pop("awaiting_topup_value", None)

    bonus = valor * BONUS_RATE if valor >= BONUS_MIN else 0.0
    saldo_atual = float(u["balance"])
    saldo_futuro = saldo_atual + valor + bonus

    # ⏳ Gerando pagamento (NOVA MENSAGEM, conforme fluxo)
    await context.bot.send_message(
        chat_id=update.message.chat_id,
        text=messages.generating_payment_text(),
        parse_mode=ParseMode.HTML,
    )

    # Gera PIX
    pix_data = pix_service.gerar_pix(valor, "Recarga Larizinha")
    await db.create_pix(
        pix_data["id"], user.id, valor, "recarga", None, None, pix_data["copia_cola"]
    )

    # guarda o bônus no user_data pra usar no check
    context.user_data[f"bonus:{pix_data['id']}"] = bonus

    await asyncio.sleep(2)

    # QR com valores embutidos
    img = qrcode_gen.generate_pix_image(
        pix_data["copia_cola"], valor, pix_data["id"][:8], pix_data["expira_em"]
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

    # NÃO pagou
    if pix["status"] != "paid":
        await context.bot.send_message(
            chat_id=query.message.chat_id,
            text=messages.not_paid_text(),
            parse_mode=ParseMode.HTML,
        )
        return

    # PAGOU → EDITA a mensagem do QR para verde
    green = qrcode_gen.generate_paid_image(pix["copia_cola"])
    try:
        await query.edit_message_media(
            media=InputMediaPhoto(
                media=green, caption=messages.paid_caption(), parse_mode=ParseMode.HTML
            ),
            reply_markup=None,
        )
    except Exception:
        pass

    # Credita saldo (+ bônus)
    bonus = float(context.user_data.get(f"bonus:{pix_id}", 0.0))
    await db.update_balance(pix["user_id"], float(pix["valor"]) + bonus)
    u = await db.get_user(pix["user_id"])

    await context.bot.send_message(
        chat_id=query.message.chat_id,
        text=messages.topup_success_text(float(pix["valor"]), bonus, float(u["balance"])),
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
            caption=messages.topup_cancelled_text(), parse_mode=ParseMode.HTML
        )
    except Exception:
        pass
