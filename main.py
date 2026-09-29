import logging
import threading
import asyncio
from datetime import datetime, timedelta

from flask import Flask, request, jsonify, render_template
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import (
    ApplicationBuilder,
    CallbackQueryHandler,
    ChatMemberHandler,
    CommandHandler,
    MessageHandler,
    filters,
)

from config import (
    BOT_TOKEN,
    PORT,
    WEBHOOK_URL,
    MINIAPP_BASE_URL,
    ADMIN_IDS,
)
from database import db
from handlers import (
    start,
    menu,
    catalog,
    buy,
    multi,
    delivery,
    profile,
    history,
    gift,
    alterdata,
    topup,
    affiliates,
    withdraw,
    withdraw_history,
    top,
    search,
    direct,
    abandoned,
    notif,
)

logging.basicConfig(
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger("larizinha-bot")


# ═══════════════════════════════════════════════
# FLASK — Health Check + Mini App
# ═══════════════════════════════════════════════
flask_app = Flask(__name__)
loop: asyncio.AbstractEventLoop | None = None


@flask_app.get("/")
def health():
    return "Larizinha Store Bot — OK"


@flask_app.get("/miniapp/senha/<int:user_id>")
def miniapp_senha(user_id: int):
    return render_template("miniapp_senha.html", user_id=user_id)


@flask_app.post("/miniapp/senha/<int:user_id>")
def miniapp_senha_save(user_id: int):
    data = request.get_json(silent=True) or {}
    pin = str(data.get("pin", "")).strip()

    if not pin.isdigit() or len(pin) != 6:
        return jsonify(ok=False, error="Senha inválida (use 6 dígitos)."), 400

    if loop is None:
        return jsonify(ok=False, error="Servidor ainda inicializando."), 503

    try:
        asyncio.run_coroutine_threadsafe(
            db.set_payout_password(user_id, pin), loop
        ).result(timeout=5)
    except Exception as e:
        logger.exception("Erro salvando senha: %s", e)
        return jsonify(ok=False, error="Erro interno."), 500

    return jsonify(ok=True)


def run_flask():
    flask_app.run(host="0.0.0.0", port=PORT, debug=False, use_reloader=False)


# ═══════════════════════════════════════════════
# PTB — Post Init (DB + JobQueue)
# ═══════════════════════════════════════════════
async def post_init(app):
    global loop
    loop = asyncio.get_running_loop()

    await db.init_db()
    await db.seed_products()
    logger.info("Banco iniciado e produtos populados.")

    # ─── Job: Carrinho Abandonado (roda a cada 60s)
    if app.job_queue:
        app.job_queue.run_repeating(
            abandoned.check_abandoned_carts,
            interval=60,
            first=30,
            name="abandoned_carts",
        )
        logger.info("JobQueue: carrinho abandonado iniciado (interval=60s).")


# ═══════════════════════════════════════════════
# COMANDOS ADMIN
# ═══════════════════════════════════════════════
async def mark_paid(update: Update, context):
    """Simula pagamento de um PIX (só admin). Uso: /pago <pix_id>"""
    if update.effective_user.id not in ADMIN_IDS:
        return
    if not context.args:
        await update.message.reply_text("Uso: /pago <pix_id>")
        return

    pix_id = context.args[0]
    await db.mark_pix_paid(pix_id)
    await update.message.reply_text(f"✅ PIX {pix_id} marcado como pago.")


async def cancelar(update: Update, context):
    """Cancela qualquer fluxo que esteja aguardando input."""
    for k in (
        "awaiting_multi",
        "awaiting_gift",
        "awaiting_whatsapp",
        "awaiting_topup_value",
        "awaiting_wd_key",
        "awaiting_wd_amount",
        "awaiting_wd_pin",
        "awaiting_search",
    ):
        context.user_data.pop(k, None)
    await update.message.reply_text("❌ Operação cancelada.")


async def setpin_command(update: Update, context):
    """Abre o Mini App de cadastro de senha de saque."""
    user_id = update.effective_user.id
    url = f"{MINIAPP_BASE_URL}/miniapp/senha/{user_id}"

    kb = InlineKeyboardMarkup([[
        InlineKeyboardButton(
            "🔐 Abrir Cadastro de Senha",
            web_app={"url": url},  # WebAppInfo (dict funciona com PTB 21+)
        )
    ]])
    await update.message.reply_text(
        "🔐 Clique abaixo para cadastrar sua senha de saque:",
        reply_markup=kb,
    )


async def myid_command(update: Update, context):
    """Retorna o ID do usuário e do chat (útil pra pegar IDs de canais)."""
    await update.message.reply_text(
        f"👤 Seu ID: <code>{update.effective_user.id}</code>\n"
        f"💬 Chat ID: <code>{update.effective_chat.id}</code>",
        parse_mode="HTML",
    )


# ═══════════════════════════════════════════════
# TEXTO LIVRE — Roteador único (ForceReply)
# ═══════════════════════════════════════════════
async def _text_router(update: Update, context):
    """
    Encaminha a mensagem de texto para o handler correto conforme
    o estado do usuário (context.user_data).
    """
    ud = context.user_data

    if ud.get("awaiting_multi"):
        return await multi.multi_qty_handler(update, context)

    if ud.get("awaiting_gift"):
        return await gift.gift_code_handler(update, context)

    if ud.get("awaiting_whatsapp"):
        return await alterdata.whatsapp_handler(update, context)

    if ud.get("awaiting_topup_value"):
        return await topup.topup_value_handler(update, context)

    if ud.get("awaiting_wd_key"):
        return await withdraw.withdraw_key_handler(update, context)

    if ud.get("awaiting_wd_amount"):
        return await withdraw.withdraw_amount_handler(update, context)

    if ud.get("awaiting_wd_pin"):
        return await withdraw.withdraw_pin_handler(update, context)

    if ud.get("awaiting_search"):
        return await search.search_handler(update, context)

    # Nenhum fluxo ativo: silencia (evita poluir o chat)
    return


# ═══════════════════════════════════════════════
# MINI APP — Abrir via botão dentro do bot
# ═══════════════════════════════════════════════
async def _open_miniapp(update: Update, context):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    url = f"{MINIAPP_BASE_URL}/miniapp/senha/{user_id}"

    kb = InlineKeyboardMarkup([[
        InlineKeyboardButton("🔐 Abrir Cadastro de Senha", web_app={"url": url})
    ]])

    try:
        await query.edit_message_text(
            "🔐 Clique abaixo para cadastrar sua senha de saque:",
            reply_markup=kb,
        )
    except Exception:
        await context.bot.send_message(
            chat_id=query.message.chat_id,
            text="🔐 Abra o mini app:",
            reply_markup=kb,
        )


# ═══════════════════════════════════════════════
# BUILD APP (registro de handlers)
# ═══════════════════════════════════════════════
def build_app():
    app = ApplicationBuilder().token(BOT_TOKEN).post_init(post_init).build()

    # ─────────── COMANDOS ───────────
    app.add_handler(CommandHandler("start", start.start_command))
    app.add_handler(CommandHandler("pago", mark_paid))
    app.add_handler(CommandHandler("cancelar", cancelar))
    app.add_handler(CommandHandler("setsenha", setpin_command))
    app.add_handler(CommandHandler("myid", myid_command))
    app.add_handler(CommandHandler("notif", notif.notif_command))
    app.add_handler(CommandHandler("broadcast", notif.broadcast_command))

    # ─────────── CHATMEMBER (Gate) ───────────
    app.add_handler(
        ChatMemberHandler(
            start.chat_member_update,
            ChatMemberHandler.CHAT_MEMBER,
        )
    )

    # ═══════════════════════════════════════════
    # CALLBACKS — a ordem importa!
    # ═══════════════════════════════════════════

    # ─── Ações Diretas (botões de notificação/promoção)
    app.add_handler(
        CallbackQueryHandler(direct.direct_router, pattern=r"^direct:")
    )

    # ─── Entrega
    app.add_handler(
        CallbackQueryHandler(delivery.reveal_product, pattern=r"^delivery:reveal:")
    )

    # ─── PIX de compra
    app.add_handler(CallbackQueryHandler(buy.generate_pix,   pattern=r"^pix:gen:"))
    app.add_handler(CallbackQueryHandler(buy.copy_pix,       pattern=r"^pix:copy:"))
    app.add_handler(CallbackQueryHandler(buy.check_pix,      pattern=r"^pix:check:"))
    app.add_handler(CallbackQueryHandler(buy.cancel_pix,     pattern=r"^pix:cancel:"))
    app.add_handler(CallbackQueryHandler(buy.cancel_new_pix, pattern=r"^pix:new_cancel$"))

    # ─── PIX de recarga
    app.add_handler(CallbackQueryHandler(topup.topup_copy,    pattern=r"^toppix:copy:"))
    app.add_handler(CallbackQueryHandler(topup.topup_check,   pattern=r"^toppix:check:"))
    app.add_handler(CallbackQueryHandler(topup.topup_cancel,  pattern=r"^toppix:cancel:"))

    # ─── Recarga
    app.add_handler(
        CallbackQueryHandler(topup.topup_pix_open, pattern=r"^topup:pix$")
    )

    # ─── Compra
    app.add_handler(CallbackQueryHandler(buy.buy_single,     pattern=r"^buy:"))
    app.add_handler(CallbackQueryHandler(multi.multi_start,   pattern=r"^buymulti:"))
    app.add_handler(CallbackQueryHandler(multi.multi_confirm, pattern=r"^multi:confirm:"))
    app.add_handler(CallbackQueryHandler(multi.multi_cancel,  pattern=r"^multi:cancel$"))

    # ─── Histórico
    app.add_handler(CallbackQueryHandler(history.history_router, pattern=r"^hist:"))
    app.add_handler(
        CallbackQueryHandler(history.history_router, pattern=r"^profile:history$")
    )

    # ─── Gift Card
    app.add_handler(CallbackQueryHandler(gift.gift_open,   pattern=r"^profile:gift$"))
    app.add_handler(CallbackQueryHandler(gift.gift_cancel, pattern=r"^gift:cancel$"))
    app.add_handler(CallbackQueryHandler(gift.gift_use,    pattern=r"^gift:use$"))

    # ─── Alterar dados
    app.add_handler(
        CallbackQueryHandler(alterdata.alter_open,     pattern=r"^profile:alter$")
    )
    app.add_handler(
        CallbackQueryHandler(alterdata.alter_whatsapp, pattern=r"^alter:whatsapp$")
    )

    # ─── Afiliados
    app.add_handler(
        CallbackQueryHandler(affiliates.affiliates_open, pattern=r"^menu:affiliates$")
    )
    app.add_handler(
        CallbackQueryHandler(affiliates.affiliates_open, pattern=r"^aff:menu$")
    )
    app.add_handler(
        CallbackQueryHandler(affiliates.affiliates_join, pattern=r"^aff:join$")
    )

    # ─── Histórico de Saque (PDF)
    app.add_handler(
        CallbackQueryHandler(withdraw_history.withdraw_history, pattern=r"^aff:whist$")
    )

    # ─── Saques
    app.add_handler(
        CallbackQueryHandler(withdraw.withdraw_open,        pattern=r"^aff:withdraw$")
    )
    app.add_handler(
        CallbackQueryHandler(withdraw.withdraw_type,        pattern=r"^wd:type:")
    )
    app.add_handler(
        CallbackQueryHandler(withdraw.withdraw_confirm_key, pattern=r"^wd:confirm_key$")
    )
    app.add_handler(
        CallbackQueryHandler(withdraw.withdraw_edit_key,    pattern=r"^wd:edit_key$")
    )
    app.add_handler(
        CallbackQueryHandler(withdraw.withdraw_sacar,       pattern=r"^wd:sacar$")
    )

    # ─── Mini App (botão dentro do bot)
    app.add_handler(
        CallbackQueryHandler(_open_miniapp, pattern=r"^aff:setpin$")
    )

    # ─── Top Compradores
    app.add_handler(CallbackQueryHandler(top.top_open,   pattern=r"^menu:top$"))
    app.add_handler(CallbackQueryHandler(top.top_filter, pattern=r"^top:"))

    # ─── Pesquisar
    app.add_handler(
        CallbackQueryHandler(search.search_open, pattern=r"^menu:search$")
    )

    # ─── Produto (catálogo → produto)
    app.add_handler(
        CallbackQueryHandler(catalog.product_callback, pattern=r"^prod:")
    )

    # ─── Menu (fallback genérico)
    app.add_handler(CallbackQueryHandler(menu.menu_router))

    # ─────────── TEXTO LIVRE (ForceReply) ───────────
    app.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, _text_router)
    )

    return app


# ═══════════════════════════════════════════════
# BOOT
# ═══════════════════════════════════════════════
def main():
    # Sobe o Flask em thread separada (healthcheck + mini app)
    threading.Thread(target=run_flask, daemon=True).start()
    logger.info("Servidor Flask rodando na porta %s", PORT)

    app = build_app()

    if WEBHOOK_URL:
        logger.info("Rodando via WEBHOOK em %s", WEBHOOK_URL)
        app.run_webhook(
            listen="0.0.0.0",
            port=PORT + 1,  # porta interna diferente do Flask
            url_path=BOT_TOKEN,
            webhook_url=f"{WEBHOOK_URL}/{BOT_TOKEN}",
            drop_pending_updates=True,
        )
    else:
        logger.info("Rodando via POLLING")
        app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
