from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import ContextTypes

from database import db
from keyboards import menus
from texts import messages
from handlers.start import is_member


async def product_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Abre a tela de um produto (EDITA a mensagem atual).

    Regras:
      - Verifica canal obrigatório
      - Puxa saldo, nome, preço, estoque, vendas do banco
      - Salva visualização para o Carrinho Abandonado
    """
    query = update.callback_query
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
        await query.answer("Produto inválido.", show_alert=True)
        return

    # ─── Puxa usuário e produto do banco
    u = await db.get_or_create_user(user.id, user.username, user.first_name)
    product = await db.get_product(pid)

    if not product:
        await query.answer("Produto não encontrado.", show_alert=True)
        return

    # ─── Registra visualização (Carrinho Abandonado)
    try:
        await db.save_cart_view(user.id, pid)
    except Exception:
        pass

    # ─── Edita a mensagem atual com a tela do produto
    await query.edit_message_text(
        messages.product_text(u, product),
        reply_markup=menus.product_keyboard(pid),
        parse_mode=ParseMode.HTML,
    )
    await query.answer()
