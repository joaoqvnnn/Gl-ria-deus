import asyncio
from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import ContextTypes

from database import db
from keyboards import menus
from services import pix as pix_service
from services import qrcode_gen
from texts import messages
from handlers.start import is_member


# ═══════════════════════════════════════════════
# 🛒 COMPRAR (compra única)
# ═══════════════════════════════════════════════
async def buy_single(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Ao clicar em "🛒 COMPRAR" na tela do produto:
      - Verifica canal obrigatório
      - Consulta saldo
      - Se saldo suficiente → processa compra direto (entrega)
      - Se saldo insuficiente → ENVIA NOVA MENSAGEM com aviso + botão PIX
        (a mensagem original do produto PERMANECE intacta)
    """
    query = update.callback_query
    await query.answer()
    user = update.effective_user

    # ─── Verifica canal obrigatório
    if not await is_member(context, user.id):
        await query.answer(
            "⚠️ Entre no canal obrigatório primeiro.",
            show_alert=True,
        )
        return

    # ─── Parse do ID do produto
    try:
        pid = int(query.data.split(":", 1)[1])
    except (IndexError, ValueError):
        return

    # ─── Puxa usuário e produto
    u = await db.get_or_create_user(user.id, user.username, user.first_name)
    product = await db.get_product(pid)
    if not product:
        await context.bot.send_message(
            chat_id=query.message.chat_id,
            text="❌ Produto não encontrado.",
        )
        return

    price = float(product["price"])
    balance = float(u["balance"])

    # ─── SALDO SUFICIENTE → processa compra direto (nova msg + entrega)
    if balance >= price:
        await _process_purchase(
            context, query.message.chat_id, u, product, quantity=1
        )
        return

    # ─── SALDO INSUFICIENTE → ENVIA NOVA MENSAGEM (produto original permanece)
    kb = menus.insufficient_keyboard(pid, 1, price)
    await context.bot.send_message(
        chat_id=query.message.chat_id,
        text=messages.insufficient_text(u, product, 1),
        reply_markup=kb,
        parse_mode=ParseMode.HTML,
    )


# ═══════════════════════════════════════════════
# 💠 GERAR PIX — EDITA a mensagem de saldo insuficiente
# ═══════════════════════════════════════════════
async def generate_pix(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Ao clicar em "💠 Gerar PIX de R$ X,XX" na mensagem de saldo insuficiente:
      1) EDITA a mensagem → "⏳ Gerando pagamento..."
      2) Aguarda 2 segundos
      3) ENVIA NOVA MENSAGEM com a Imagem Única do QR Code
    """
    query = update.callback_query
    await query.answer()
    user = update.effective_user

    # ─── callback_data: pix:gen:{product_id}:{qty}
    try:
        _, _, pid_str, qty_str = query.data.split(":")
        pid = int(pid_str)
        qty = int(qty_str)
    except (ValueError, IndexError):
        return

    # ─── 1) EDITA a mensagem de saldo insuficiente → "Gerando pagamento..."
    try:
        await query.edit_message_text(
            messages.generating_payment_text(),
            parse_mode=ParseMode.HTML,
        )
    except Exception:
        pass

    # ─── Puxa produto e calcula total
    product = await db.get_product(pid)
    if not product:
        return

    total = float(product["price"]) * qty

    # ─── Gera PIX
    pix_data = pix_service.gerar_pix(total, product["name"])
    await db.create_pix(
        pix_data["id"], user.id, total, "compra", pid, qty, pix_data["copia_cola"]
    )

    # ─── 2) Aguarda 2 segundos (tempo de processamento)
    await asyncio.sleep(2)

    # ─── 3) ENVIA NOVA MENSAGEM com a imagem única do QR Code
    img = qrcode_gen.generate_pix_image(
        pix_data["copia_cola"], total, pix_data["id"][:8], pix_data["expira_em"]
    )

    await context.bot.send_photo(
        chat_id=query.message.chat_id,
        photo=img,
        caption=messages.pix_caption(pix_data["id"], total, pix_data["expira_em"]),
        reply_markup=menus.pix_keyboard(pix_data["id"]),
        parse_mode=ParseMode.HTML,
    )


# ═══════════════════════════════════════════════
# 📋 COPIAR PIX (alerta com o copia e cola)
# ═══════════════════════════════════════════════
async def copy_pix(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    pix_id = query.data.split(":", 2)[2]
    pix = await db.get_pix(pix_id)
    if not pix:
        await query.answer("PIX não encontrado.", show_alert=True)
        return
    await query.answer(
        f"PIX Copia e Cola:\n\n{pix['copia_cola']}",
        show_alert=True,
    )


# ═══════════════════════════════════════════════
# ⏰ AGUARDANDO PAGAMENTO
# ═══════════════════════════════════════════════
async def check_pix(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Ao clicar em "⏰ AGUARDANDO PAGAMENTO":
      - Se NÃO pagou: ENVIA NOVA MENSAGEM de aviso
      - Se pagou:
          · EDITA a mensagem do QR Code atual → QR verde "PAGO"
          · Segue para a entrega
    """
    query = update.callback_query
    await query.answer()

    pix_id = query.data.split(":", 2)[2]
    pix = await db.get_pix(pix_id)
    if not pix:
        await query.answer("PIX não encontrado.", show_alert=True)
        return

    # ─── NÃO pagou → ENVIA NOVA MENSAGEM
    if pix["status"] != "paid":
        await context.bot.send_message(
            chat_id=query.message.chat_id,
            text=messages.not_paid_text(),
            parse_mode=ParseMode.HTML,
        )
        return

    # ─── PAGOU → EDITA a mensagem do QR Code atual → QR verde "PAGO"
    from telegram import InputMediaPhoto
    green_img = qrcode_gen.generate_paid_image(pix["copia_cola"])

    try:
        await query.edit_message_media(
            media=InputMediaPhoto(
                media=green_img,
                caption=messages.paid_caption(),
                parse_mode=ParseMode.HTML,
            ),
            reply_markup=None,
        )
    except Exception:
        pass

    # ─── Segue para a entrega
    await _finalize_pix_purchase(context, query.message.chat_id, pix)


# ═══════════════════════════════════════════════
# ❌ CANCELAR PIX (depois de gerado)
# ═══════════════════════════════════════════════
async def cancel_pix(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    pix_id = query.data.split(":", 2)[2]
    await db.cancel_pix(pix_id)
    try:
        await query.edit_message_caption(
            caption="❌ <b>PIX cancelado.</b>",
            parse_mode=ParseMode.HTML,
        )
    except Exception:
        pass


# ═══════════════════════════════════════════════
# ❌ CANCELAR (na tela de saldo insuficiente, antes de gerar PIX)
# ═══════════════════════════════════════════════
async def cancel_new_pix(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    try:
        await query.edit_message_text(
            "❌ <b>Compra cancelada.</b>",
            parse_mode=ParseMode.HTML,
        )
    except Exception:
        pass


# ═══════════════════════════════════════════════
# 🧠 Helpers internos
# ═══════════════════════════════════════════════
async def _finalize_pix_purchase(context, chat_id, pix):
    """
    Após confirmar pagamento do PIX de compra:
      - Credita o valor pago no saldo (para depois processar a compra)
      - Chama _process_purchase (deduz o total e entrega)
    """
    pid = pix["product_id"]
    qty = int(pix["quantity"] or 1)
    user = await db.get_user(pix["user_id"])
    product = await db.get_product(pid)

    if not user or not product:
        return

    # Credita o valor do PIX (o PIX foi pra completar o saldo)
    await db.update_balance(user["user_id"], +float(pix["valor"]))

    # Recarrega o user com saldo atualizado
    user = await db.get_user(pix["user_id"])

    # Processa a compra (deduz saldo, decrementa estoque, entrega)
    await _process_purchase(context, chat_id, user, product, quantity=qty)


async def _process_purchase(context, chat_id, user, product, quantity: int = 1):
    """
    Processa a compra:
      - Deduz saldo
      - Decrementa estoque
      - Retira itens do stock_items
      - Cria registro em purchases
      - Limpa carrinho abandonado
      - Envia mensagem de entrega com botões
    """
    total = float(product["price"]) * quantity

    # ─── Deduz saldo
    await db.update_balance(user["user_id"], -total)

    # ─── Estoque
    await db.decrement_stock(product["id"], quantity)
    items = await db.take_stock_items(product["id"], quantity)

    # ─── Item principal (fallback se não tiver estoque)
    first = items[0] if items else {
        "email": f"conta_{user['user_id']}@larizinha.com",
        "password": "senha_temporaria",
    }

    # ─── Cria registro de compra
    purchase = await db.create_purchase(
        user_id=user["user_id"],
        product_id=product["id"],
        product_name=product["name"],
        quantity=quantity,
        total=total,
        email=first["email"],
        password=first["password"],
    )

    # ─── Limpa carrinho abandonado (usuário comprou)
    try:
        await db.clear_cart_view(user["user_id"], product["id"])
    except Exception:
        pass

    # ─── Envia mensagem de entrega
    await context.bot.send_message(
        chat_id=chat_id,
        text=messages.delivery_text(
            purchase, first["email"], first["password"], masked=True
        ),
        reply_markup=menus.delivery_keyboard(
            purchase["id"], product.get("activate_url") or "https://t.me/"
        ),
        parse_mode=ParseMode.HTML,
    )
