"""
Carrinho Abandonado — envia mensagem automática após X minutos
que o usuário viu o produto e não comprou.

Roda em JobQueue a cada 60 segundos.
"""
import logging
from telegram.constants import ParseMode
from telegram.ext import ContextTypes

from config import ABANDONED_CART_MIN
from database import db
from keyboards import menus
from services import notif_templates

logger = logging.getLogger(__name__)


async def check_abandoned_carts(context: ContextTypes.DEFAULT_TYPE):
    """Job que roda a cada 60s verificando carrinhos abandonados."""
    try:
        carts = await db.list_abandoned_carts(minutes=ABANDONED_CART_MIN)
    except Exception as e:
        logger.exception("Erro buscando carrinhos abandonados: %s", e)
        return

    for c in carts:
        try:
            user_id = c["user_id"]
            product_id = c["product_id"]

            user = await db.get_user(user_id)
            product = await db.get_product(product_id)
            if not user or not product:
                await db.mark_cart_notified(user_id, product_id)
                continue

            name = user.get("first_name") or "cliente"

            text = notif_templates.template_abandono(product, name)

            await context.bot.send_message(
                chat_id=user_id,
                text=text,
                reply_markup=menus.direct_product_two_keyboard(product_id),
                parse_mode=ParseMode.HTML,
            )

            await db.mark_cart_notified(user_id, product_id)
            logger.info("Carrinho abandonado notificado: user=%s prod=%s", user_id, product_id)

        except Exception as e:
            logger.warning("Falha notificando carrinho user=%s: %s", c.get("user_id"), e)
            # marca como notificado pra não ficar tentando eternamente
            try:
                await db.mark_cart_notified(c["user_id"], c["product_id"])
            except Exception:
                pass
