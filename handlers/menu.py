from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    WebAppInfo,
)
from telegram.constants import ParseMode
from telegram.ext import ContextTypes

from config import MINIAPP_BASE_URL
from database import db
from keyboards import menus
from texts import messages
from handlers import profile as profile_handler


async def menu_router(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    data = query.data
    user = update.effective_user

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
        await profile_handler.show_profile(update, context)

    # ─── Recarregar Saldo
    elif data == "menu:topup":
        from handlers import topup as topup_handler
        await topup_handler.topup_open(update, context)

    # ─── Afiliados
    elif data == "menu:affiliates":
        from handlers import affiliates as aff_handler
        await aff_handler.affiliates_open(update, context)

    # ─── Top Compradores
    elif data == "menu:top":
        from handlers import top as top_handler
        await top_handler.top_open(update, context)

    # ─── Pesquisar Serviços
    elif data == "menu:search":
        from handlers import search as search_handler
        await search_handler.search_open(update, context)

    # ─── Abrir Loja (Web App dentro do Telegram)
    elif data == "menu:store":
        url = f"{MINIAPP_BASE_URL}/loja/{user.id}"
        kb = InlineKeyboardMarkup([[
            InlineKeyboardButton("🛒 Abrir Loja", web_app=WebAppInfo(url=url))
        ]])
        await query.edit_message_text(
            "🛒 <b>Clique abaixo para abrir a loja:</b>\n\n"
            "Você será redirecionado para uma experiência completa dentro do Telegram.",
            reply_markup=kb,
            parse_mode=ParseMode.HTML,
        )

    # ─── Sobre o Bot
    elif data == "menu:about":
        await query.edit_message_text(
            messages.about_text(),
            reply_markup=menus.back_to_menu_keyboard(),
            parse_mode=ParseMode.HTML,
        )

    # ─── Módulos "em breve"
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

    await query.answer()
