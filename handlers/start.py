
---

## 📄 11) `handlers/start.py`  — **GATE DE ENTRADA + BOAS-VINDAS**

```python
import logging
from telegram import Update
from telegram.constants import ChatMemberStatus, ParseMode
from telegram.error import TelegramError
from telegram.ext import ContextTypes

from config import CHANNEL_ID
from database import db
from keyboards import menus
from texts import messages

logger = logging.getLogger(__name__)

# Guarda a última mensagem de bloqueio por usuário: {user_id: (chat_id, message_id)}
GATE_MESSAGES: dict[int, tuple[int, int]] = {}


async def is_member(context: ContextTypes.DEFAULT_TYPE, user_id: int) -> bool:
    """Verifica se o usuário está no canal obrigatório."""
    try:
        member = await context.bot.get_chat_member(chat_id=CHANNEL_ID, user_id=user_id)
        return member.status in (
            ChatMemberStatus.MEMBER,
            ChatMemberStatus.ADMINISTRATOR,
            ChatMemberStatus.OWNER,
            ChatMemberStatus.RESTRICTED,
        )
    except TelegramError as e:
        logger.warning("Erro verificando membership: %s", e)
        return False


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Comando /start."""
    user = update.effective_user
    u = await db.get_or_create_user(user.id, user.username, user.first_name)

    # Verifica canal obrigatório
    if not await is_member(context, user.id):
        msg = await update.message.reply_text(
            messages.gate_text(),
            reply_markup=menus.gate_keyboard(),
            parse_mode=ParseMode.HTML,
        )
        GATE_MESSAGES[user.id] = (msg.chat_id, msg.message_id)
        return

    await update.message.reply_text(
        messages.welcome_text(u),
        reply_markup=menus.main_menu_keyboard(),
        parse_mode=ParseMode.HTML,
    )


async def chat_member_update(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Detecta quando o usuário entra no canal e EDITA a mensagem de bloqueio."""
    cmu = update.chat_member
    if not cmu:
        return

    old_status = cmu.old_chat_member.status
    new_status = cmu.new_chat_member.status

    entrou = (
        old_status in (ChatMemberStatus.LEFT, ChatMemberStatus.BANNED)
        and new_status in (
            ChatMemberStatus.MEMBER,
            ChatMemberStatus.ADMINISTRATOR,
            ChatMemberStatus.OWNER,
            ChatMemberStatus.RESTRICTED,
        )
    )
    if not entrou:
        return

    user_id = cmu.from_user.id
    entry = GATE_MESSAGES.pop(user_id, None)
    if not entry:
        return

    chat_id, message_id = entry
    u = await db.get_or_create_user(
        user_id, cmu.from_user.username, cmu.from_user.first_name
    )

    try:
        await context.bot.edit_message_text(
            chat_id=chat_id,
            message_id=message_id,
            text=messages.welcome_text(u),
            reply_markup=menus.main_menu_keyboard(),
            parse_mode=ParseMode.HTML,
        )
    except TelegramError as e:
        logger.warning("Não foi possível editar mensagem do gate: %s", e)
