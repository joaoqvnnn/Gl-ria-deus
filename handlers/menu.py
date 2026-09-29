from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import ContextTypes

from database import db
from keyboards import menus
from texts import messages
from handlers.start import is_member


async def menu_router(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    data = query.data
    user = update.effective_user

    # Se não estiver no canal, bloqueia
    if not await is_member(context, user.id):
        await query.answer("⚠️ Entre no canal obrigatório primeiro.", show_alert=True)
        return

    u = await db.get_or_create_user(user.id, user.username, user.first_name)

    # ─── Voltar para o menu inicial
    if data == "menu:home":
        await query.edit_message_text(
            messages.welcome_text(u),
            reply_markup=menus.main_menu_keyboard(),
            parse_mode=ParseMode.HTML,
        )

    # ─── Catálogo
    elif data == "menu:catalog":
        products = await db.get_products()
        await query.edit_message_text(
            messages.catalog_text(u),
            reply_markup=menus.catalog_keyboard(products),
            parse_mode=ParseMode.HTML,
        )

    # ─── Meu Perfil
    elif data == "menu:profile":
        await query.edit_message_text(
            messages.profile_text(u),
            reply_markup=menus.profile_keyboard(),
            parse_mode=ParseMode.HTML,
        )

    # ─── Sobre o Bot
    elif data == "menu:about":
        await query.edit_message_text(
            messages.about_text(),
            reply_markup=menus.back_to_menu_keyboard(),
            parse_mode=ParseMode.HTML,
        )

    # ─── Módulos em breve
    elif data.startswith("soon:"):
        area = data.split(":", 1)[1]
        nomes = {
            "historico": "📜 Histórico de Compras",
            "gift": "🎁 Resgatar Gift Card",
            "alterar": "✏️ Alterar Dados",
        }
        await query.edit_message_text(
            messages.soon_text(nomes.get(area, area)),
            reply_markup=menus.back_to_menu_keyboard(),
            parse_mode=ParseMode.HTML,
        )

    elif data == "menu:store":
        await query.edit_message_text(
            messages.soon_text("🛒 Abrir Loja"),
            reply_markup=menus.back_to_menu_keyboard(),
            parse_mode=ParseMode.HTML,
        )

    elif data == "menu:topup":
        await query.edit_message_text(
            messages.soon_text("💠 Recarregar Saldo"),
            reply_markup=menus.back_to_menu_keyboard(),
            parse_mode=ParseMode.HTML,
        )

    elif data == "menu:affiliates":
        await query.edit_message_text(
            messages.soon_text("👥 Afiliados"),
            reply_markup=menus.back_to_menu_keyboard(),
            parse_mode=ParseMode.HTML,
        )

    elif data == "menu:top":
        await query.edit_message_text(
            messages.soon_text("🏆 Top Compradores"),
            reply_markup=menus.back_to_menu_keyboard(),
            parse_mode=ParseMode.HTML,
        )

    elif data == "menu:search":
        await query.edit_message_text(
            messages.soon_text("🔎 Pesquisar Serviços"),
            reply_markup=menus.back_to_menu_keyboard(),
            parse_mode=ParseMode.HTML,
        )

    await query.answer()
