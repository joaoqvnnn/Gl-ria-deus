"""
handlers/notif.py — Comandos admin para notificações customizadas.

Uso:
  /notif produto <id>           → manda "produto voltou" pro canal
  /notif estoque 1,3,5          → manda "bot abastecido" com produtos 1,3,5
  /notif cadastro               → convite de cadastro
  /notif gift                   → convite de gift card

  /broadcast
  <texto>
  ---
  [{"text":"Comprar agora","action":"direct:product:3"}]
  ---
  canal | estoque | todos | me
"""
import json
import logging
from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import ContextTypes

from config import ADMIN_IDS, NOTIF_CHANNEL_ID, STOCK_CHANNEL_ID
from database import db
from keyboards import menus
from services import notif_templates

logger = logging.getLogger(__name__)


def _is_admin(user_id: int) -> bool:
    return user_id in ADMIN_IDS


# ═══════════════════════════════════════════════
# /notif
# ═══════════════════════════════════════════════
async def notif_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not _is_admin(update.effective_user.id):
        return

    if not context.args:
        await update.message.reply_text(
            "📢 <b>Uso:</b>\n\n"
            "<code>/notif produto &lt;id&gt;</code> — produto voltou\n"
            "<code>/notif estoque 1,3,5</code> — bot abastecido\n"
            "<code>/notif cadastro</code> — convite cadastro\n"
            "<code>/notif gift</code> — convite gift card\n\n"
            "Ou use <code>/broadcast</code> para mensagem customizada.",
            parse_mode=ParseMode.HTML,
        )
        return

    tipo = context.args[0].lower()

    # ─── /notif produto <id>
    if tipo == "produto" and len(context.args) >= 2:
        try:
            pid = int(context.args[1])
        except ValueError:
            await update.message.reply_text("❌ ID inválido.")
            return

        product = await db.get_product(pid)
        if not product:
            await update.message.reply_text("❌ Produto não encontrado.")
            return

        text = notif_templates.template_produto_voltou(product)
        kb = menus.direct_product_keyboard(pid)

        destinos = _get_destinos()
        await _send_to_destinos(context, destinos, text, kb)
        await update.message.reply_text("✅ Notificação enviada.")
        return

    # ─── /notif estoque 1,3,5
    if tipo == "estoque" and len(context.args) >= 2:
        ids = [int(x) for x in context.args[1].split(",") if x.strip().isdigit()]
        if not ids:
            await update.message.reply_text("❌ IDs inválidos.")
            return

        produtos = []
        for pid in ids:
            p = await db.get_product(pid)
            if p:
                produtos.append(p)

        if not produtos:
            await update.message.reply_text("❌ Nenhum produto encontrado.")
            return

        text = notif_templates.template_bot_abastecido(produtos)
        kb = menus.direct_catalog_keyboard()

        destinos = _get_destinos()
        await _send_to_destinos(context, destinos, text, kb)
        await update.message.reply_text("✅ Notificação enviada.")
        return

    # ─── /notif cadastro
    if tipo == "cadastro":
        text = notif_templates.template_boas_vindas_cadastro()
        kb = menus.direct_start_keyboard()
        destinos = _get_destinos()
        await _send_to_destinos(context, destinos, text, kb)
        await update.message.reply_text("✅ Enviado.")
        return

    # ─── /notif gift
    if tipo == "gift":
        text = notif_templates.template_gift_card()
        kb = menus.direct_gift_keyboard()
        destinos = _get_destinos()
        await _send_to_destinos(context, destinos, text, kb)
        await update.message.reply_text("✅ Enviado.")
        return

    await update.message.reply_text("❌ Tipo desconhecido. Use /notif para ver ajuda.")


# ═══════════════════════════════════════════════
# /broadcast
# ═══════════════════════════════════════════════
async def broadcast_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Envia mensagem customizada com botões.

    Formato:
        /broadcast
        <texto>
        ---
        [{"text":"Comprar agora","action":"direct:product:3"}]
        ---
        canal|estoque|todos|me
    """
    if not _is_admin(update.effective_user.id):
        return

    raw = update.message.text or ""
    body = raw.replace("/broadcast", "", 1).strip()

    if not body:
        await update.message.reply_text(
            "📢 <b>Uso:</b>\n\n"
            "<code>/broadcast</code>\n"
            "<i>linha1: texto da mensagem</i>\n"
            "<code>---</code>\n"
            "<i>linha2: JSON dos botões</i>\n"
            "<code>---</code>\n"
            "<i>linha3: destino (canal | estoque | todos | me)</i>\n\n"
            "<b>Exemplo:</b>\n"
            "<code>/broadcast\n🔥 Promoção!\n---\n"
            '[{"text":"Comprar agora","action":"direct:product:3"}]\n---\ncanal</code>',
            parse_mode=ParseMode.HTML,
        )
        return

    try:
        texto, botoes_json, destino = [p.strip() for p in body.split("---", 2)]
        botoes = json.loads(botoes_json)
        kb = menus.direct_custom_keyboard(botoes)
    except Exception as e:
        await update.message.reply_text(f"❌ Erro no formato: {e}")
        return

    destino = destino.lower().strip()

    destinos = []
    if destino == "canal" and NOTIF_CHANNEL_ID:
        destinos = [NOTIF_CHANNEL_ID]
    elif destino == "estoque" and STOCK_CHANNEL_ID:
        destinos = [STOCK_CHANNEL_ID]
    elif destino == "todos":
        destinos = [x for x in [NOTIF_CHANNEL_ID, STOCK_CHANNEL_ID] if x]
    elif destino == "me":
        destinos = [update.effective_user.id]

    if not destinos:
        await update.message.reply_text("⚠️ Nenhum destino configurado.")
        return

    await _send_to_destinos(context, destinos, texto, kb)
    await update.message.reply_text("✅ Broadcast enviado.")


# ═══════════════════════════════════════════════
# HELPERS
# ═══════════════════════════════════════════════
def _get_destinos() -> list:
    """Retorna lista padrão: canal de compras + canal de estoque."""
    return [x for x in [NOTIF_CHANNEL_ID, STOCK_CHANNEL_ID] if x]


async def _send_to_destinos(context, destinos, text, kb):
    for dest in destinos:
        try:
            await context.bot.send_message(
                chat_id=dest,
                text=text,
                reply_markup=kb,
                parse_mode=ParseMode.HTML,
                disable_web_page_preview=True,
            )
        except Exception as e:
            logger.warning("Falha enviando para %s: %s", dest, e)
