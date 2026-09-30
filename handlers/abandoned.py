"""
handlers/abandoned.py — LEGACY.

Este arquivo existia antes e fazia o job do carrinho abandonado.
Agora essa lógica está no `admin14.check_abandoned_carts_v2`.

Mantido apenas para compatibilidade caso algum import antigo
ainda aponte pra cá.
"""
import logging
from telegram.ext import ContextTypes

logger = logging.getLogger(__name__)


async def check_abandoned_carts(context: ContextTypes.DEFAULT_TYPE):
    """Redireciona pro job novo (admin14)."""
    try:
        from handlers import admin14
        await admin14.check_abandoned_carts_v2(context)
    except Exception as e:
        logger.exception("Erro redirecionando check_abandoned_carts: %s", e)
