from telegram import Update, BufferedInputFile
from telegram.constants import ParseMode
from telegram.ext import ContextTypes

from config import BOT_HANDLE
from database import db
from keyboards import menus
from services import pdf_gen
from texts import messages


async def withdraw_history(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    user = update.effective_user
    u = await db.get_or_create_user(user.id, user.username, user.first_name)

    withdrawals = await db.list_withdrawals(user.id)

    pdf_bytes = pdf_gen.generate_withdraw_history_pdf(BOT_HANDLE, u, withdrawals)

    await context.bot.send_document(
        chat_id=query.message.chat_id,
        document=BufferedInputFile(pdf_bytes, filename="extrato-larizinha.pdf"),
        caption="📄 <b>Extrato do Bot</b>",
        parse_mode=ParseMode.HTML,
    )
