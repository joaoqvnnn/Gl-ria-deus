"""
Ações Diretas — botões que executam ações no bot SEM precisar de /start.
Funciona de qualquer lugar: canal, grupo, privado, forwarded.

Também processa o botão "🔍 Ver Compra" (só comprador ou admin).
"""
from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import ContextTypes

from config import ADMIN_IDS
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
      direct:view_purchase:<owner_id>:<purchase_id>
    """
    query = update.callback_query
    user = update.effective_user
    parts = query.data.split(":")
    action = parts[1] if len(parts) > 1 else ""

    # ═══════════════════════════════════════════════
    # 🔍 VER COMPRA — antes do gate (admin não precisa estar no canal)
    # ═══════════════════════════════════════════════
    if action == "view_purchase" and len(parts) >= 4:
        try:
            owner_id    = int(parts[2])
            purchase_id = parts[3]
        except (ValueError, IndexError):
            await query.answer("Dados inválidos.", show_alert=True)
            return

        # Só o comprador ou o admin podem abrir
        if user.id != owner_id and user.id not in ADMIN_IDS:
            await query.answer(
                "🔒 Esse botão é só para o comprador ou o admin.",
                show_alert=True,
            )
            return

        purchase = await db.get_purchase(purchase_id)
        if not purchase:
            await query.answer("Compra não encontrada.", show_alert=True)
            return

        product = await db.get_product(purchase["product_id"])
        activate_url = (product or {}).get("activate_url") or "https://t.me/"

        await query.answer()
        await context.bot.send_message(
            chat_id=query.message.chat_id,
            text=messages.delivery_text(
                purchase,
                purchase["email"],
                purchase["password"],
                masked=True,
            ),
            reply_markup=menus.delivery_keyboard(purchase["id"], activate_url),
            parse_mode=ParseMode.HTML,
        )
        return

    # ═══════════════════════════════════════════════
    # 🔐 GATE — todos os outros exigem estar no canal
    # ═══════════════════════════════════════════════
    if not await is_member(context, user.id):
        await query.answer(
            "⚠️ Entre no canal obrigatório primeiro para continuar.",
            show_alert=True,
        )
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

    # ═══════════════════════════════════════════════
    # 🎯 ABRIR PRODUTO
    # ═══════════════════════════════════════════════
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

        # Registra visualização (carrinho abandonado)
        await db.save_cart_view(user.id, pid)

        await query.answer()
        try:
            await query.edit_message_text(
                messages.product_text(u, product),
                reply_markup=menus.product_keyboard(pid),
                parse_mode=ParseMode.HTML,
            )
        except Exception:
            await context.bot.send_message(
                chat_id=query.message.chat_id,
                text=messages.product_text(u, product),
                reply_markup=menus.product_keyboard(pid),
                parse_mode=ParseMode.HTML,
            )
        return

    # ═══════════════════════════════════════════════
    # 🛍 ABRIR CATÁLOGO
    # ═══════════════════════════════════════════════
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

    # ═══════════════════════════════════════════════
    # 🎁 ABRIR FLUXO DE GIFT CARD
    # ═══════════════════════════════════════════════
    if action == "gift":
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

    # ═══════════════════════════════════════════════
    # 💠 ABRIR RECARGA
    # ═══════════════════════════════════════════════
    if action == "topup":
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

    # ═══════════════════════════════════════════════
    # ✅ EQUIVALENTE AO /start (menu principal)
    # ═══════════════════════════════════════════════
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

    # ═══════════════════════════════════════════════
    # Fallback
    # ═══════════════════════════════════════════════
    await query.answer()
