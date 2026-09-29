from telegram import Update, ForceReply
from telegram.constants import ParseMode
from telegram.ext import ContextTypes

from database import db
from keyboards import menus
from texts import messages


async def search_open(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """EDITS + ForceReply para o usuário digitar 'procurar <termo>'."""
    query = update.callback_query
    await query.answer()

    context.user_data["awaiting_search"] = True

    try:
        await query.edit_message_text(
            messages.search_prompt_text(),
            reply_markup=menus.back_to_menu_keyboard(),
            parse_mode=ParseMode.HTML,
        )
    except Exception:
        pass

    await context.bot.send_message(
        chat_id=query.message.chat_id,
        text="Digite abaixo 👇",
        reply_markup=ForceReply(selective=True),
    )


async def search_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.user_data.get("awaiting_search"):
        return

    text = (update.message.text or "").strip()
    low = text.lower()

    if not low.startswith("procurar "):
        await update.message.reply_text(
            "❌ Use o formato: <code>procurar netflix</code>",
            parse_mode=ParseMode.HTML,
        )
        return

    term = text[len("procurar "):].strip()
    context.user_data.pop("awaiting_search", None)

    if not term:
        await update.message.reply_text(messages.search_prompt_text(), parse_mode=ParseMode.HTML)
        return

    results = await db.search_products(term)
    if not results:
        await update.message.reply_text(
            messages.search_no_results(term), parse_mode=ParseMode.HTML
        )
        return

    # Mostra um card por produto com botão "🛒 Comprar"
    await update.message.reply_text(
        messages.search_results_intro(term, len(results)),
        parse_mode=ParseMode.HTML,
    )

    for p in results[:5]:
        await update.message.reply_text(
            messages.search_product_card(p),
            reply_markup=menus.product_keyboard(p["id"]),
            parse_mode=ParseMode.HTML,
        )
