import logging
from telegram import Update
from telegram.constants import ChatMemberStatus, ParseMode
from telegram.error import TelegramError
from telegram.ext import ContextTypes

from config import CHANNEL_ID
from database import db
from handlers import _state
from keyboards import menus
from services import deeplink
from texts import messages

logger = logging.getLogger(__name__)

# Guarda a última mensagem de bloqueio por usuário: {user_id: (chat_id, message_id)}
GATE_MESSAGES: dict[int, tuple[int, int]] = {}

# Guarda o payload pendente por usuário (quando ele ainda não entrou no canal):
PENDING_PAYLOAD: dict[int, str] = {}


# ═══════════════════════════════════════════════
# VERIFICA SE O USUÁRIO ESTÁ NO CANAL
# ═══════════════════════════════════════════════
async def is_member(context: ContextTypes.DEFAULT_TYPE, user_id: int) -> bool:
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


# ═══════════════════════════════════════════════
# HELPERS
# ═══════════════════════════════════════════════
async def _show_welcome(
    context: ContextTypes.DEFAULT_TYPE,
    chat_id: int,
    user: dict,
    via_edit_message_id: int | None = None,
):
    text = messages.welcome_text(user)
    kb = menus.main_menu_keyboard(user_id=user["user_id"])

    if via_edit_message_id:
        try:
            await context.bot.edit_message_text(
                chat_id=chat_id,
                message_id=via_edit_message_id,
                text=text,
                reply_markup=kb,
                parse_mode=ParseMode.HTML,
            )
            return
        except TelegramError as e:
            logger.warning("Não consegui editar msg do gate: %s", e)

    await context.bot.send_message(
        chat_id=chat_id,
        text=text,
        reply_markup=kb,
        parse_mode=ParseMode.HTML,
    )


async def _handle_payload(
    context: ContextTypes.DEFAULT_TYPE,
    chat_id: int,
    user: dict,
    payload: str,
    via_edit_message_id: int | None = None,
):
    data = await deeplink.resolve_payload(payload)

    if data["type"] == "referral":
        referrer_id = data["referrer_id"]
        if referrer_id != user["user_id"]:
            await db.set_referred_by(user["user_id"], referrer_id)
            logger.info("Usuário %s indicado por %s", user["user_id"], referrer_id)

        await _show_welcome(context, chat_id, user, via_edit_message_id)
        return

    if data["type"] == "product":
        product = await db.get_product(data["product_id"])
        if product:
            text = messages.product_text(user, product)
            kb = menus.product_keyboard(product["id"])

            if via_edit_message_id:
                try:
                    await context.bot.edit_message_text(
                        chat_id=chat_id,
                        message_id=via_edit_message_id,
                        text=text,
                        reply_markup=kb,
                        parse_mode=ParseMode.HTML,
                    )
                    return
                except TelegramError:
                    pass

            await context.bot.send_message(
                chat_id=chat_id, text=text, reply_markup=kb, parse_mode=ParseMode.HTML
            )
            return

    if data["type"] == "catalog":
        products = await db.get_products()
        text = messages.catalog_text(user)
        kb = menus.catalog_keyboard(products)

        if via_edit_message_id:
            try:
                await context.bot.edit_message_text(
                    chat_id=chat_id,
                    message_id=via_edit_message_id,
                    text=text,
                    reply_markup=kb,
                    parse_mode=ParseMode.HTML,
                )
                return
            except TelegramError:
                pass

        await context.bot.send_message(
            chat_id=chat_id, text=text, reply_markup=kb, parse_mode=ParseMode.HTML
        )
        return

    await _show_welcome(context, chat_id, user, via_edit_message_id)


# ═══════════════════════════════════════════════
# /start
# ═══════════════════════════════════════════════
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # 🧹 SEMPRE limpa qualquer state preso antes de começar
    _state.clear_all(context.user_data)

    user = update.effective_user
    u = await db.get_or_create_user(user.id, user.username, user.first_name)

    payload = context.args[0] if context.args else ""

    if not await is_member(context, user.id):
        if payload:
            PENDING_PAYLOAD[user.id] = payload

        msg = await update.message.reply_text(
            messages.gate_text(),
            reply_markup=menus.gate_keyboard(),
            parse_mode=ParseMode.HTML,
        )
        GATE_MESSAGES[user.id] = (msg.chat_id, msg.message_id)
        return

    if payload:
        await _handle_payload(context, update.effective_chat.id, u, payload)
    else:
        await _show_welcome(context, update.effective_chat.id, u)


# ═══════════════════════════════════════════════
# DETECÇÃO DE ENTRADA NO CANAL
# ═══════════════════════════════════════════════
async def chat_member_update(update: Update, context: ContextTypes.DEFAULT_TYPE):
    cmu = update.chat_member
    if not cmu:
        return

    old_status = cmu.old_chat_member.status
    new_status = cmu.new_chat_member.status

    logger.info(
        "ChatMember recebido: user=%s old=%s new=%s chat=%s",
        cmu.from_user.id, old_status, new_status, cmu.chat.id,
    )

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
        logger.info("ChatMember: usuário %s entrou, sem gate guardado.", user_id)
        return

    chat_id, message_id = entry
    u = await db.get_or_create_user(
        user_id, cmu.from_user.username, cmu.from_user.first_name
    )

    payload = PENDING_PAYLOAD.pop(user_id, None)

    if payload:
        await _handle_payload(context, chat_id, u, payload, via_edit_message_id=message_id)
        return

    await _show_welcome(context, chat_id, u, via_edit_message_id=message_id)
