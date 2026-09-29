"""
Comandos admin para gerenciar estoque e disparar notificações.

Uso:
  /addstock <product_id> <email> <senha>
     → Adiciona 1 item ao estoque, incrementa stock e notifica o canal.

  /addstock <product_id> <qty>
     → Adiciona qty itens genéricos (sem email/senha específicos).

  /stock <product_id>
     → Consulta estoque atual do produto.
"""
import logging
from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import ContextTypes

from config import ADMIN_IDS
from database import db
from services import channel_notify

logger = logging.getLogger(__name__)


def _is_admin(user_id: int) -> bool:
    return user_id in ADMIN_IDS


async def addstock_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not _is_admin(update.effective_user.id):
        return

    args = context.args or []

    # ─── /addstock <id> <email> <senha>
    if len(args) >= 3:
        try:
            pid = int(args[0])
        except ValueError:
            await update.message.reply_text("❌ ID inválido.")
            return

        email = args[1]
        senha = " ".join(args[2:])

        product = await db.get_product(pid)
        if not product:
            await update.message.reply_text("❌ Produto não encontrado.")
            return

        # Adiciona 1 item no estoque
        await db.add_stock_item(pid, email, senha)
        await db.increment_stock(pid, 1)

        # Notifica o canal automaticamente
        await channel_notify.notify_product_stock(
            context.bot, product, int(product["stock"]) + 1
        )

        await update.message.reply_text(
            f"✅ Estoque adicionado!\n"
            f"📦 Produto: <b>{product['name']}</b>\n"
            f"📧 Email: <code>{email}</code>\n"
            f"📊 Novo estoque: <b>{int(product['stock']) + 1}</b>",
            parse_mode=ParseMode.HTML,
        )
        return

    # ─── /addstock <id> <qty>
    if len(args) == 2:
        try:
            pid = int(args[0])
            qty = int(args[1])
        except ValueError:
            await update.message.reply_text("❌ Argumentos inválidos.")
            return

        product = await db.get_product(pid)
        if not product:
            await update.message.reply_text("❌ Produto não encontrado.")
            return

        # Adiciona qty itens genéricos
        for i in range(qty):
            await db.add_stock_item(
                pid,
                f"conta_{product['id']}_{i+1}@larizinha.com",
                "senha_auto",
            )
        await db.increment_stock(pid, qty)

        # Notifica o canal
        await channel_notify.notify_product_stock(
            context.bot, product, int(product["stock"]) + qty
        )

        await update.message.reply_text(
            f"✅ {qty} itens adicionados!\n"
            f"📦 Produto: <b>{product['name']}</b>\n"
            f"📊 Novo estoque: <b>{int(product['stock']) + qty}</b>",
            parse_mode=ParseMode.HTML,
        )
        return

    # ─── Ajuda
    await update.message.reply_text(
        "📦 <b>Como usar:</b>\n\n"
        "<code>/addstock &lt;id&gt; &lt;email&gt; &lt;senha&gt;</code>\n"
        "→ Adiciona 1 conta específica\n\n"
        "<code>/addstock &lt;id&gt; &lt;qty&gt;</code>\n"
        "→ Adiciona várias contas genéricas\n\n"
        "<code>/stock &lt;id&gt;</code>\n"
        "→ Consulta estoque do produto",
        parse_mode=ParseMode.HTML,
    )


async def stock_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not _is_admin(update.effective_user.id):
        return

    if not context.args:
        await update.message.reply_text("Uso: /stock <product_id>")
        return

    try:
        pid = int(context.args[0])
    except ValueError:
        await update.message.reply_text("❌ ID inválido.")
        return

    product = await db.get_product(pid)
    if not product:
        await update.message.reply_text("❌ Produto não encontrado.")
        return

    items = await db.list_available_stock(pid)

    texto = (
        f"📦 <b>{product['name']}</b>\n\n"
        f"📊 Estoque total: <b>{product['stock']}</b>\n"
        f"📧 Contas disponíveis: <b>{len(items)}</b>\n\n"
    )
    if items:
        texto += "<b>Primeiras contas:</b>\n"
        for it in items[:5]:
            texto += f"• <code>{it['email']}</code>\n"

    await update.message.reply_text(texto, parse_mode=ParseMode.HTML)
