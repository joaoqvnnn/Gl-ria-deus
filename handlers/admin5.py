import logging
from telegram import Update, ForceReply, InputFile
from telegram.constants import ParseMode
from telegram.ext import ContextTypes

from config import ADMIN_IDS
from database import db
from keyboards import menus

logger = logging.getLogger(__name__)


def is_admin(user_id: int) -> bool:
    return user_id in ADMIN_IDS


async def _edit_or_send(query, text: str, kb=None):
    try:
        await query.edit_message_text(text, reply_markup=kb, parse_mode=ParseMode.HTML)
    except Exception:
        await query.message.reply_text(text, reply_markup=kb, parse_mode=ParseMode.HTML)


# ═══════════════════════════════════════════════
# CARRINHOS ABANDONADOS
# ═══════════════════════════════════════════════
async def admin_abandoned_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not is_admin(update.effective_user.id):
        return

    carrinhos = await db.admin_list_abandoned(10)
    total = await db.admin_count_abandoned()

    if not carrinhos:
        texto = (
            "🛍 <b>Carrinhos abandonados</b>\n"
            "━━━━━━━━━━━━━━━━━━━━\n\n"
            "<i>Nenhum carrinho abandonado no momento.</i>"
        )
    else:
        texto = (
            f"🛍 <b>Carrinhos abandonados</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━\n\n"
            f"⏳ Total pendente: <b>{total}</b>\n\n"
            "Toque em um carrinho pra ver ações:"
        )

    await _edit_or_send(query, texto, menus.admin_abandoned_kb(carrinhos))


async def admin_abandoned_item_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not is_admin(update.effective_user.id):
        return

    parts = query.data.split(":")
    user_id = int(parts[2])
    product_id = int(parts[3])

    u = await db.get_user(user_id)
    p = await db.get_product(product_id)

    if not u or not p:
        await _edit_or_send(query, "❌ Dados não encontrados.", menus.admin_back_kb())
        return

    nome = u.get("first_name") or u.get("username") or f"ID {user_id}"
    preco = float(p["price"])

    texto = (
        f"🛍 <b>Carrinho abandonado</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n\n"
        f"👤 Usuário: <b>{nome}</b>\n"
        f"🆔 ID: <code>{user_id}</code>\n"
        f"📦 Produto: <b>{p['name']}</b>\n"
        f"💰 Valor: <b>R$ {preco:.2f}</b>\n\n"
        "O que fazer?"
    )
    await _edit_or_send(query, texto, menus.admin_abandoned_item_kb(user_id, product_id))


async def admin_abandoned_send_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not is_admin(update.effective_user.id):
        return

    parts = query.data.split(":")
    user_id = int(parts[2])
    product_id = int(parts[3])

    p = await db.get_product(product_id)
    u = await db.get_user(user_id)

    if not p or not u:
        await _edit_or_send(query, "❌ Não encontrado.", menus.admin_back_kb())
        return

    nome = u.get("first_name") or "cliente"
    preco = float(p["price"])

    try:
        await context.bot.send_message(
            chat_id=user_id,
            text=(
                f"👋 Ei, <b>{nome}</b>, você esqueceu algo!\n\n"
                f"Notamos que você estava olhando <b>{p['name']}</b> "
                "mas não finalizou a compra.\n\n"
                f"💰 Valor: <b>R$ {preco:.2f}</b>\n\n"
                "🎁 Que tal finalizar agora?\n"
                "Seu produto está esperando por você!"
            ),
            reply_markup=menus.direct_product_two_keyboard(product_id),
            parse_mode=ParseMode.HTML,
        )
        await db.mark_cart_notified(user_id, product_id)
        await db.log_admin_action(
            update.effective_user.id, "abandoned_send", f"{user_id}/{product_id}"
        )

        await _edit_or_send(query, "✅ Lembrete enviado.", menus.admin_abandoned_item_kb(user_id, product_id))
    except Exception as e:
        await _edit_or_send(query, f"❌ Erro: {e}", menus.admin_back_kb())


async def admin_abandoned_del_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not is_admin(update.effective_user.id):
        return

    parts = query.data.split(":")
    user_id = int(parts[2])
    product_id = int(parts[3])

    await db.admin_clear_abandoned(user_id, product_id)
    await db.log_admin_action(
        update.effective_user.id, "abandoned_del", f"{user_id}/{product_id}"
    )

    await _edit_or_send(query, "🗑️ Removido da lista.", menus.admin_back_kb())


# ═══════════════════════════════════════════════
# MENSAGEM DIRETA PRO USUÁRIO
# ═══════════════════════════════════════════════
async def admin_msg_user_prompt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not is_admin(update.effective_user.id):
        return

    user_id = int(query.data.split(":")[2])
    context.user_data["admin_msg_user"] = user_id

    try:
        await query.edit_message_text(
            f"✉️ <b>Enviar mensagem direta</b>\n\n"
            f"Usuário: <code>{user_id}</code>\n\n"
            "Envie o texto (pode usar HTML):",
            reply_markup=ForceReply(selective=True),
            parse_mode=ParseMode.HTML,
        )
    except Exception:
        pass


async def admin_msg_user_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = context.user_data.get("admin_msg_user")
    if not user_id:
        return
    if not is_admin(update.effective_user.id):
        return

    texto = update.message.text or update.message.caption or ""
    if not texto.strip():
        await update.message.reply_text("❌ Mensagem vazia.")
        return

    context.user_data.pop("admin_msg_user", None)

    try:
        await context.bot.send_message(
            chat_id=user_id,
            text=texto,
            parse_mode=ParseMode.HTML,
        )
        await db.log_admin_action(
            update.effective_user.id, "direct_msg", str(user_id)
        )
        await update.message.reply_text(
            f"✅ Mensagem enviada pra <code>{user_id}</code>.",
            reply_markup=menus.admin_back_kb(),
            parse_mode=ParseMode.HTML,
        )
    except Exception as e:
        await update.message.reply_text(f"❌ Erro: {e}", reply_markup=menus.admin_back_kb())


# ═══════════════════════════════════════════════
# BACKUP
# ═══════════════════════════════════════════════
async def admin_backup_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not is_admin(update.effective_user.id):
        return

    try:
        conteudo = await db.admin_backup_bytes()
        await context.bot.send_document(
            chat_id=query.message.chat_id,
            document=InputFile(conteudo, filename="backup-larizinha.db"),
            caption="💾 <b>Backup do banco</b>\n\nGuarde em local seguro.",
            parse_mode=ParseMode.HTML,
        )
        await db.log_admin_action(update.effective_user.id, "backup")
    except Exception as e:
        await _edit_or_send(query, f"❌ Erro ao gerar backup: {e}", menus.admin_back_kb())


# ═══════════════════════════════════════════════
# BROADCAST COM FOTO/VIDEO
# ═══════════════════════════════════════════════
async def admin_bc_media_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Recebe mídia (foto/vídeo) OU texto pra broadcast.
    Suporta legenda.
    """
    if not context.user_data.get("admin_bc"):
        return
    if not is_admin(update.effective_user.id):
        return

    tipo = context.user_data.get("admin_bc")

    # Pega texto (caption ou text)
    texto = update.message.caption or update.message.text or ""
    file_id = None
    tipo_midia = None

    if update.message.photo:
        file_id = update.message.photo[-1].file_id
        tipo_midia = "photo"
    elif update.message.video:
        file_id = update.message.video.file_id
        tipo_midia = "video"

    if not texto.strip() and not file_id:
        await update.message.reply_text("❌ Envie texto ou mídia.")
        return

    context.user_data.pop("admin_bc", None)

    # Pega lista de destinatários
    if tipo == "bc_all":
        ids = await db.all_user_ids()
    elif tipo == "bc_buyers":
        ids = await db.buyers_user_ids()
    elif tipo == "bc_inactive":
        ids = await db.inactive_user_ids(7)
    else:
        ids = []

    if not ids:
        await update.message.reply_text("⚠️ Nenhum destinatário.")
        return

    enviados = 0
    falhas = 0

    await update.message.reply_text(
        f"📢 Enviando pra <b>{len(ids)}</b> usuários...",
        parse_mode=ParseMode.HTML,
    )

    for uid in ids:
        try:
            if tipo_midia == "photo":
                await context.bot.send_photo(
                    chat_id=uid, photo=file_id, caption=texto,
                    parse_mode=ParseMode.HTML,
                )
            elif tipo_midia == "video":
                await context.bot.send_video(
                    chat_id=uid, video=file_id, caption=texto,
                    parse_mode=ParseMode.HTML,
                )
            else:
                await context.bot.send_message(
                    chat_id=uid, text=texto, parse_mode=ParseMode.HTML,
                )
            enviados += 1
        except Exception:
            falhas += 1
        await __import__("asyncio").sleep(0.05)

    await db.log_admin_action(
        update.effective_user.id, "broadcast_media", tipo,
        f"enviados={enviados} falhas={falhas}",
    )

    await update.message.reply_text(
        f"✅ <b>Broadcast concluído!</b>\n\n"
        f"📤 Enviados: <b>{enviados}</b>\n"
        f"❌ Falhas: <b>{falhas}</b>",
        reply_markup=menus.admin_back_kb(),
        parse_mode=ParseMode.HTML,
    )
