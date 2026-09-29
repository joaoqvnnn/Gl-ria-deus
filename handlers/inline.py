"""
Pesquisa inline via @seubot procurar <termo>.

Retorna os produtos encontrados em formato de card (thumb + descrição).
Ao clicar, o bot envia a mensagem com o card + botão Comprar.
"""
import logging
from telegram import (
    Update,
    InlineQueryResultArticle,
    InlineQueryResultPhoto,
    InputTextMessageContent,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
)
from telegram.constants import ParseMode
from telegram.ext import ContextTypes

from config import BOT_USERNAME
from database import db

logger = logging.getLogger(__name__)


# ─── Fallback de thumb (usado se o produto não tiver imagem)
FALLBACK_THUMB = "https://i.imgur.com/8Q8Q8Q8.png"  # troque por uma URL sua


def _inline_product_card(product: dict) -> tuple[str, InlineKeyboardMarkup]:
    """Gera o texto e o teclado do card inline."""
    price = float(product["price"])
    texto = (
        f"🎯 <b>{product['name']}</b>\n"
        f"💵 <b>R$ {price:.2f}</b>\n"
        f"📝 {(product.get('description') or '')[:120]}\n\n"
        f'Para comprar, clique no botão "🛒 Comprar" abaixo ou abra o painel do serviço.'
    )
    kb = InlineKeyboardMarkup([[
        InlineKeyboardButton(
            "🛒 Comprar",
            url=f"https://t.me/{BOT_USERNAME}?start=prod_{product['id']}",
        ),
    ]])
    return texto, kb


async def inline_query(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Chamado quando o usuário digita @seubot no chat.
    Suporta:  @seubot procurar netflix
    """
    query = update.inline_query
    if not query:
        return

    raw = (query.query or "").strip().lower()
    term = raw.replace("procurar", "", 1).strip()

    if not term:
        # Mostra um hint
        hint = InlineQueryResultArticle(
            id="hint",
            title="🔎 Como procurar um serviço?",
            description="Digite: procurar <nome do serviço>",
            input_message_content=InputTextMessageContent(
                "🔎 <b>Como procurar um serviço?</b>\n"
                "Digite: <code>procurar &lt;nome do serviço&gt;</code>",
                parse_mode=ParseMode.HTML,
            ),
        )
        await query.answer([hint], cache_time=1, is_personal=True)
        return

    # Busca no banco
    try:
        results = await db.search_products(term)
    except Exception as e:
        logger.exception("Erro na busca inline: %s", e)
        results = []

    if not results:
        no_res = InlineQueryResultArticle(
            id="no_results",
            title=f"❌ Nenhum resultado para \"{term}\"",
            description="Tente outro termo",
            input_message_content=InputTextMessageContent(
                f"❌ <b>Nenhum serviço encontrado com \"{term}\"</b>",
                parse_mode=ParseMode.HTML,
            ),
        )
        await query.answer([no_res], cache_time=1, is_personal=True)
        return

    # Monta os cards
    inline_results = []
    for p in results[:20]:
        texto, kb = _inline_product_card(p)
        img = p.get("image_url") or FALLBACK_THUMB

        # Tenta Photo (mais bonito com imagem)
        inline_results.append(
            InlineQueryResultPhoto(
                id=str(p["id"]),
                photo_url=img,
                thumb_url=img,
                title=p["name"],
                description=(p.get("description") or "")[:120],
                caption=texto,
                parse_mode=ParseMode.HTML,
                reply_markup=kb,
            )
        )

    await query.answer(inline_results, cache_time=1, is_personal=True)
