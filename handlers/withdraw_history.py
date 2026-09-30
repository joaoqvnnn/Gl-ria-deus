import io
from telegram import Update, InputFile
from telegram.constants import ParseMode
from telegram.ext import ContextTypes

from config import BOT_HANDLE
from database import db
from services import pdf_gen


async def withdraw_history(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Gera PDF do histórico de saques do usuário e envia como documento.
    """
    query = update.callback_query
    await query.answer()

    user = update.effective_user
    u = await db.get_or_create_user(user.id, user.username, user.first_name)

    withdrawals = await db.list_withdrawals(user.id)

    pdf_bytes = pdf_gen.generate_withdraw_history_pdf(BOT_HANDLE, u, withdrawals)

    # ─── Nome do arquivo com o username
    username = u.get("username") or u.get("first_name") or f"user{u['user_id']}"
    # limpa caracteres inválidos
    username = "".join(c for c in username if c.isalnum() or c in "_-")
    filename = f"extrato-{username}.pdf"

    await context.bot.send_document(
        chat_id=query.message.chat_id,
        document=InputFile(io.BytesIO(pdf_bytes), filename=filename),
    )
