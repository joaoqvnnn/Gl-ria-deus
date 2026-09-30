from telegram import Update, ForceReply
from telegram.constants import ParseMode
from telegram.ext import ContextTypes

from database import db
from handlers import _state
from keyboards import menus
from texts import messages


# Texto invisível pra trazer o ForceReply sem poluir
_ZERO = "\u200b"


# ═══════════════════════════════════════════════
# 🔎 ABRIR PESQUISA — edita + ForceReply
# ═══════════════════════════════════════════════
async def search_open(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    _state.set_state(context.user_data, "awaiting_search")

    # 1) Edita a mensagem atual com o prompt
    try:
        await query.edit_message_text(
            messages.search_prompt_text(),
            reply_markup=menus.back_to_menu_keyboard(),
            parse_mode=ParseMode.HTML,
        )
    except Exception:
        pass

    # 2) ForceReply numa nova mensagem (invisível)
    try:
        await context.bot.send_message(
            chat_id=query.message.chat_id,
            text=_ZERO,
            reply_markup=ForceReply(selective=True),
        )
    except Exception:
        pass


# ═══════════════════════════════════════════════
# 🔎 RECEBE O TERMO
# ═══════════════════════════════════════════════
async def search_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not _state.is_set(context.user_data, "awaiting_search"):
        return

    text = (update.message.text or "").strip()

    # Comando durante o fluxo → cancela
    if text.startswith("/"):
        _state.clear_all(context.user_data)
        await update.message.reply_text(
            "❌ Busca cancelada.",
            parse_mode=ParseMode.HTML,
        )
        return

    low = text.lower()

    # ─── Tem que começar com "procurar "
    if not low.startswith("procurar "):
        await update.message.reply_text(
            "❌ Use o formato: <code>procurar netflix</code>",
            parse_mode=ParseMode.HTML,
        )
        return

    term = text[len("procurar "):].strip()

    # Termo vazio → pede de novo (não limpa o state)
    if not term:
        await update.message.reply_text(
            messages.search_prompt_text(),
            parse_mode=ParseMode.HTML,
        )
        return

    # Termo válido → LIMPA o state
    _state.clear_all(context.user_data)

    results = await db.search_products(term)
    if not results:
        await update.message.reply_text(
            messages.search_no_results(term),
            parse_mode=ParseMode.HTML,
        )
        return

    # Intro
    await update.message.reply_text(
        messages.search_results_intro(term, len(results)),
        parse_mode=ParseMode.HTML,
    )

    # Cards (máx 5)
    for p in results[:5]:
        try:
            await update.message.reply_text(
                messages.search_product_card(p),
                reply_markup=menus.product_keyboard(p["id"]),
                parse_mode=ParseMode.HTML,
            )
        except Exception:
            continue
