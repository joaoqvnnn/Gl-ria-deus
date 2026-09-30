import asyncio
from telegram import Update, InputMediaPhoto, ForceReply
from telegram.constants import ParseMode
from telegram.ext import ContextTypes

from config import TOPUP_MIN, TOPUP_BONUS_MIN, TOPUP_BONUS_RATE
from database import db
from handlers import _state
from keyboards import menus
from services import pix as pix_service
from services import qrcode_gen
from services import channel_notify
from texts import messages


# ═══════════════════════════════════════════════
# 💠 MENU DE RECARGA
# ═══════════════════════════════════════════════
async def topup_open(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    try:
        await query.edit_message_text(
            messages.topup_menu_text(),
            reply_markup=menus.topup_menu_keyboard(),
            parse_mode=ParseMode.HTML,
        )
    except Exception:
        pass


# ═══════════════════════════════════════════════
# 💠 PIX RÁPIDO — abre o prompt + ForceReply
# ═══════════════════════════════════════════════
async def topup_pix_open(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    _state.set_state(context.user_data, "awaiting_topup_value")

    # 1) Edita a mensagem com o prompt do valor
    try:
        await query.edit_message_text(
            messages.topup_value_prompt_text(),
            reply_markup=menus.back_to_menu_keyboard(),
            parse_mode=ParseMode.HTML,
        )
    except Exception:
        pass

    # 2) Envia o ForceReply como NOVA mensagem (é o que faz ele funcionar)
    try:
        await context.bot.send_message(
            chat_id=query.message.chat_id,
            text="Digite abaixo 👇",
            reply_markup=ForceReply(selective=True),
        )
    except Exception:
        pass


# ═══════════════════════════════════════════════
# 💠 RECEBE O VALOR
# ═══════════════════════════════════════════════
async def topup_value_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not _state.is_set(context.user_data, "awaiting_topup_value"):
        return

    text = (update.message.text or "").strip().replace(",", ".")
    user = update.effective_user
    u = await db.get_or_create_user(user.id, user.username, user.first_name)

    # Comando durante o fluxo → cancela
    if text.startswith("/"):
        _state.clear_all(context.user_data)
        await update.message.reply_text(
            "❌ Operação cancelada.",
            parse_mode=ParseMode.HTML,
        )
        return

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

    _state.clear_all(context.user_data)

    bonus = valor * TOPUP_BONUS_RATE if valor >= TOPUP_BONUS_MIN else 0.0
    saldo_atual = float(u["balance"])
    saldo_futuro = saldo_atual + valor + bonus

    # ⏳ "Gerando pagamento..."
    try:
        await context.bot.send_message(
            chat_id=update.message.chat_id,
            text=messages.generating_payment_text(),
            parse_mode=ParseMode.HTML,
        )
    except Exception:
        pass

    # Gera PIX
    pix_data = pix_service.gerar_pix(valor, "Recarga Larizinha")
    await db.create_pix(
        pix_data["id"], user.id, valor, "recarga", None, None, pix_data["copia_cola"]
    )

    context.user_data[f"bonus:{pix_data['id']}"] = bonus

    await asyncio.sleep(2)

    # QR com valores embutidos
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

    try:
        await context.bot.send_photo(
            chat_id=update.message.chat_id,
            photo=img,
            caption=messages.topup_pix_caption(
                pix_data["id"], valor, bonus, saldo_atual, saldo_futuro, pix_data["expira_em"]
            ),
            reply_markup=menus.topup_pix_keyboard(
                pix_data["id"],
                copia_cola=pix_data["copia_cola"],
            ),
            parse_mode=ParseMode.HTML,
        )
    except Exception:
        pass


# ═══════════════════════════════════════════════
# 📋 COPIAR PIX (fallback — popup)
# ═══════════════════════════════════════════════
async def topup_copy(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    pix_id = query.data.split(":", 2)[2]
    pix = await db.get_pix(pix_id)
    if not pix:
        await query.answer("PIX não encontrado.", show_alert=True)
        return
    await query.answer(
        f"PIX Copia e Cola:\n\n{pix['copia_cola']}",
        show_alert=True,
    )


# ═══════════════════════════════════════════════
# ⏰ AGUARDANDO PAGAMENTO
# ═══════════════════════════════════════════════
async def topup_check(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    pix_id = query.data.split(":", 2)[2]
    pix = await db.get_pix(pix_id)
    if not pix:
        await query.answer("PIX não encontrado.", show_alert=True)
        return

    # ─── NÃO pagou
    if pix["status"] != "paid":
        try:
            await context.bot.send_message(
                chat_id=query.message.chat_id,
                text=messages.not_paid_text(),
                parse_mode=ParseMode.HTML,
            )
        except Exception:
            pass
        return

    # ─── PAGOU → EDITA o QR pra verde
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

    # ─── Credita saldo + bônus
    bonus = float(context.user_data.get(f"bonus:{pix_id}", 0.0))
    await db.update_balance(pix["user_id"], valor + bonus)
    u = await db.get_user(pix["user_id"])

    # ─── Notifica o canal
    try:
        await channel_notify.notify_topup(context.bot, u, valor, bonus)
    except Exception:
        pass

    # ─── Envia msg de sucesso
    try:
        await context.bot.send_message(
            chat_id=query.message.chat_id,
            text=messages.topup_success_text(valor, bonus, float(u["balance"])),
            reply_markup=menus.topup_success_keyboard(),
            parse_mode=ParseMode.HTML,
        )
    except Exception:
        pass


# ═══════════════════════════════════════════════
# ❌ CANCELAR (recarga) — DELETE + nova msg
# ═══════════════════════════════════════════════
async def topup_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    pix_id = query.data.split(":", 2)[2]
    await db.cancel_pix(pix_id)

    chat_id = query.message.chat_id

    # 1) Deleta a mensagem do QR Code
    try:
        await query.delete_message()
    except Exception:
        pass

    # 2) Envia nova msg de texto
    try:
        await context.bot.send_message(
            chat_id=chat_id,
            text=messages.topup_cancelled_text(),
            parse_mode=ParseMode.HTML,
        )
    except Exception:
        pass
