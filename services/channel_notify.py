"""
Notificações automáticas em canais.

Envia mensagens para:
- NOTIF_CHANNEL_ID (canal de compras)
- STOCK_CHANNEL_ID (canal de estoque)
"""
import logging
from datetime import datetime
from telegram import Bot, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.constants import ParseMode
from telegram.error import TelegramError

from config import NOTIF_CHANNEL_ID, STOCK_CHANNEL_ID, BOT_USERNAME

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════
# KEYBOARDS
# ═══════════════════════════════════════════════
def _kb_ver_produto(product_id: int) -> InlineKeyboardMarkup:
    """Botão que leva direto pra tela do produto."""
    return InlineKeyboardMarkup([[
        InlineKeyboardButton(
            "🛒 Ver Produto",
            url=f"https://t.me/{BOT_USERNAME}?start=prod_{product_id}",
        ),
    ]])


def _kb_novo_acesso(user_id: int, purchase_id: str) -> InlineKeyboardMarkup:
    """Botões da notificação 'NOVO ACESSO LIBERADO'."""
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(
            "🚀 Ir para o Bot",
            url=f"https://t.me/{BOT_USERNAME}?start=loja",
        )],
        [InlineKeyboardButton(
            "🔍 Ver Compra",
            callback_data=f"direct:view_purchase:{user_id}:{purchase_id}",
        )],
    ])


# ═══════════════════════════════════════════════
# NOTIFICAÇÕES
# ═══════════════════════════════════════════════
async def notify_new_access(
    bot: Bot,
    user: dict,
    product: dict,
    purchase: dict,
):
    """
    Envia "NOVO ACESSO LIBERADO" para o canal de compras.
    Chamado quando o usuário paga (compra ou recarga).
    """
    if not NOTIF_CHANNEL_ID or bot is None:
        return

    data_str = datetime.now().strftime("%d/%m/%Y, %H:%M")
    user_nome = user.get("first_name") or user.get("username") or f"ID {user['user_id']}"

    texto = (
        "💎 <b>NOVO ACESSO LIBERADO</b>\n"
        f"👤 Usuário: <b>{user_nome}</b>\n"
        f"📦 Plano: <b>{product['name']}</b>\n"
        "💵 Status: ✅ <b>Pago e ativo</b>\n"
        f"🕐 Data: <b>{data_str}</b>\n\n"
        "🚀 <b>Acesso liberado automaticamente!</b>"
    )

    try:
        await bot.send_message(
            chat_id=NOTIF_CHANNEL_ID,
            text=texto,
            reply_markup=_kb_novo_acesso(user["user_id"], purchase["id"]),
            parse_mode=ParseMode.HTML,
            disable_web_page_preview=True,
        )
    except TelegramError as e:
        logger.warning("Falha ao notificar novo acesso: %s", e)


async def notify_product_stock(
    bot: Bot,
    product: dict,
    stock_qty: int,
):
    """
    Envia "PRODUTO ABASTECIDO" para o canal de estoque.
    Chamado quando o admin abastece.
    """
    if not STOCK_CHANNEL_ID or bot is None:
        return

    texto = (
        "🟢 <b>Produto Abastecido!</b>\n"
        f"Nome: <b>{product['name']}</b>\n"
        f"Valor: <b>R$ {float(product['price']):.2f}</b>\n"
        f"Estoque: <b>{stock_qty}</b>"
    )

    try:
        await bot.send_message(
            chat_id=STOCK_CHANNEL_ID,
            text=texto,
            reply_markup=_kb_ver_produto(product["id"]),
            parse_mode=ParseMode.HTML,
            disable_web_page_preview=True,
        )
    except TelegramError as e:
        logger.warning("Falha ao notificar estoque: %s", e)


async def notify_topup(bot: Bot, user: dict, valor: float, bonus: float):
    """Notifica recarga no canal de compras."""
    if not NOTIF_CHANNEL_ID or bot is None:
        return

    data_str = datetime.now().strftime("%d/%m/%Y, %H:%M")
    user_nome = user.get("first_name") or user.get("username") or f"ID {user['user_id']}"
    bonus_txt = f"\n🎁 Bônus: <b>R$ {bonus:.2f}</b>" if bonus > 0 else ""

    texto = (
        "💎 <b>RECARGA CONFIRMADA</b>\n"
        f"👤 Usuário: <b>{user_nome}</b>\n"
        f"💰 Valor: <b>R$ {valor:.2f}</b>{bonus_txt}\n"
        "💵 Status: ✅ <b>Pago</b>\n"
        f"🕐 Data: <b>{data_str}</b>"
    )

    try:
        await bot.send_message(
            chat_id=NOTIF_CHANNEL_ID,
            text=texto,
            parse_mode=ParseMode.HTML,
            disable_web_page_preview=True,
        )
    except TelegramError as e:
        logger.warning("Falha ao notificar recarga: %s", e)
