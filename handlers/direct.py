"""
Ações Diretas — botões que executam ações no bot SEM precisar de /start.
Funciona de qualquer lugar: canal, grupo, privado, forwarded.
"""
from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import ContextTypes

from database import db
from keyboards import menus
from texts import messages
from handlers.start import is_member


async def direct_router(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Roteia callbacks que começam com 'direct:'.
    Formatos:
      direct:product:<id>
      direct:catalog
      direct:gift
      direct:topup
      direct:start
    """
    query = update.callback_query
    user = update.effective_user

    # Verifica canal obrigatório
    if not await is_member(context, user.id):
        await query.answer(
            "⚠️ Entre no canal obrigatório primeiro para continuar.",
            show_alert=True,
        )
        # Manda o Gate (nova msg, pois estamos fora do fluxo normal)
        msg = await context.bot.send_message(
            chat_id=query.message.chat_id,
            text=messages.gate_text(),
            reply_markup=menus.gate_keyboard(),
            parse_mode=ParseMode.HTML,
        )
        from handlers.start import GATE_MESSAGES
        GATE_MESSAGES[user.id] = (msg.chat_id, msg.message_id)
        return

    u = await db.get_or_create_user(user.id, user.username, user.first_name)
    parts = query.data.split(":")
    action = parts[1] if len(parts) > 1 else ""

    # ─── Abrir produto direto
    if action == "product" and len(parts) >= 3:
        try:
            pid = int(parts[2])
        except ValueError:
            await query.answer("Produto inválido.", show_alert=True)
            return

        product = await db.get_product(pid)
        if not product:
            await query.answer("Produto não encontrado.", show_alert=True)
            return

        # Registra visualização (para carrinho abandonado)
        await db.save_cart_view(user.id, pid)

        await query.answer()
        try:
            await query.edit_message_text(
                messages.product_text(u, product),
                reply_markup=menus.product_keyboard(pid),
                parse_mode=ParseMode.HTML,
            )
        except Exception:
            # Se não puder editar (mensagem antiga, forwarded, etc), envia nova
            await context.bot.send_message(
                chat_id=query.message.chat_id,
                text=messages.product_text(u, product),
                reply_markup=menus.product_keyboard(pid),
                parse_mode=ParseMode.HTML,
            )
        return

    # ─── Abrir catálogo
    if action == "catalog":
        products = await db.get_products()
        await query.answer()
        try:
            await query.edit_message_text(
                messages.catalog_text(u),
                reply_markup=menus.catalog_keyboard(products),
                parse_mode=ParseMode.HTML,
            )
        except Exception:
            await context.bot.send_message(
                chat_id=query.message.chat_id,
                text=messages.catalog_text(u),
                reply_markup=menus.catalog_keyboard(products),
                parse_mode=ParseMode.HTML,
            )
        return

    # ─── Abrir fluxo de gift card
    if action == "gift":
        from handlers import gift as gift_handler
        context.user_data["awaiting_gift"] = True

        await query.answer()
        try:
            await query.edit_message_text(
                messages.gift_prompt_text(),
                reply_markup=menus.gift_cancel_keyboard(),
                parse_mode=ParseMode.HTML,
            )
        except Exception:
            pass

        from telegram import ForceReply
        await context.bot.send_message(
            chat_id=query.message.chat_id,
            text="Digite o código abaixo 👇",
            reply_markup=ForceReply(selective=True),
        )
        return

    # ─── Abrir recarga
    if action == "topup":
        from handlers import topup as topup_handler
        await query.answer()
        try:
            await query.edit_message_text(
                messages.topup_menu_text(),
                reply_markup=menus.topup_menu_keyboard(),
                parse_mode=ParseMode.HTML,
            )
        except Exception:
            await context.bot.send_message(
                chat_id=query.message.chat_id,
                text=messages.topup_menu_text(),
                reply_markup=menus.topup_menu_keyboard(),
                parse_mode=ParseMode.HTML,
            )
        return

    # ─── Equivalente ao /start (menu principal)
    if action == "start":
        await query.answer()
        try:
            await query.edit_message_text(
                messages.welcome_text(u),
                reply_markup=menus.main_menu_keyboard(),
                parse_mode=ParseMode.HTML,
            )
        except Exception:
            await context.bot.send_message(
                chat_id=query.message.chat_id,
                text=messages.welcome_text(u),
                reply_markup=menus.main_menu_keyboard(),
                parse_mode=ParseMode.HTML,
            )
        return

    await query.answer()
