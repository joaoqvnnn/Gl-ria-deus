from telegram import Update, ForceReply
from telegram.constants import ParseMode
from telegram.ext import ContextTypes

from database import db
from keyboards import menus
from texts import messages


# ═══════════════════════════════════════════════
# 🎁 ABRIR RESGATE DE GIFT CARD
# ═══════════════════════════════════════════════
async def gift_open(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    context.user_data["awaiting_gift"] = True

    try:
        await query.edit_message_text(
            messages.gift_prompt_text(),
            reply_markup=ForceReply(selective=True),
            parse_mode=ParseMode.HTML,
        )
    except Exception:
        pass


# ═══════════════════════════════════════════════
# ❌ CANCELAR
# ═══════════════════════════════════════════════
async def gift_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    context.user_data.pop("awaiting_gift", None)
    context.user_data.pop("last_gift", None)

    u = await db.get_or_create_user(query.from_user.id, None, None)
    stats = await db.user_stats(u["user_id"])

    await query.edit_message_text(
        messages.profile_text(u, stats),
        reply_markup=menus.profile_keyboard(),
        parse_mode=ParseMode.HTML,
    )


# ═══════════════════════════════════════════════
# 🎁 RECEBE O CÓDIGO DO GIFT
# ═══════════════════════════════════════════════
async def gift_code_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.user_data.get("awaiting_gift"):
        return

    code = (update.message.text or "").strip().upper()
    user = update.effective_user
    u = await db.get_or_create_user(user.id, user.username, user.first_name)

    gift = await db.get_gift(code)

    # Inválido
    if not gift:
        await update.message.reply_text(
            messages.gift_invalid_text(),
            parse_mode=ParseMode.HTML,
        )
        return

    # Já resgatado
    if gift.get("redeemed_by"):
        await update.message.reply_text(
            messages.gift_already_used_text(),
            parse_mode=ParseMode.HTML,
        )
        return

    # Resgatar
    await db.redeem_gift(code, user.id)
    context.user_data.pop("awaiting_gift", None)

    # Gift de saldo
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

    # Gift de produto
    context.user_data["last_gift"] = {
        "code": code,
        "product_id": gift.get("product_id"),
    }

    await update.message.reply_text(
        messages.gift_success_text(gift),
        reply_markup=menus.gift_success_keyboard(),
        parse_mode=ParseMode.HTML,
    )


# ═══════════════════════════════════════════════
# 🎁 USAR GIFT (vai pro produto)
# ═══════════════════════════════════════════════
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

    await query.edit_message_text(
        messages.product_text(u, product),
        reply_markup=menus.product_keyboard(pid),
        parse_mode=ParseMode.HTML,
    )
