import logging
from telegram.ext import (
    ApplicationBuilder,
    CallbackQueryHandler,
    ChatMemberHandler,
    CommandHandler,
    MessageHandler,
    filters,
)

from config import BOT_TOKEN, PORT, WEBHOOK_URL, ADMIN_IDS
from database import db
from handlers import start, menu, catalog, buy, multi, delivery

logging.basicConfig(
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger("larizinha-bot")


async def post_init(app):
    await db.init_db()
    await db.seed_products()
    logger.info("Banco iniciado e produtos populados.")


# ─── Comando admin p/ simular pagamento (teste)
async def mark_paid(update, context):
    if update.effective_user.id not in ADMIN_IDS:
        return
    if not context.args:
        await update.message.reply_text("Uso: /pago <pix_id>")
        return
    pix_id = context.args[0]
    await db.mark_pix_paid(pix_id)
    await update.message.reply_text(f"✅ PIX {pix_id} marcado como pago.")


async def cancelar(update, context):
    context.user_data.pop("awaiting_multi", None)
    await update.message.reply_text("❌ Operação cancelada.")


def build_app():
    app = ApplicationBuilder().token(BOT_TOKEN).post_init(post_init).build()

    # Comandos
    app.add_handler(CommandHandler("start", start.start_command))
    app.add_handler(CommandHandler("pago", mark_paid))
    app.add_handler(CommandHandler("cancelar", cancelar))

    # ChatMember (entrada no canal)
    app.add_handler(
        ChatMemberHandler(start.chat_member_update, ChatMemberHandler.CHAT_MEMBER)
    )

    # ─── Callbacks específicos (ordem importa!)

    # Entrega
    app.add_handler(CallbackQueryHandler(delivery.reveal_product, pattern=r"^delivery:reveal:"))

    # PIX
    app.add_handler(CallbackQueryHandler(buy.generate_pix,     pattern=r"^pix:gen:"))
    app.add_handler(CallbackQueryHandler(buy.copy_pix,         pattern=r"^pix:copy:"))
    app.add_handler(CallbackQueryHandler(buy.check_pix,        pattern=r"^pix:check:"))
    app.add_handler(CallbackQueryHandler(buy.cancel_pix,       pattern=r"^pix:cancel:"))
    app.add_handler(CallbackQueryHandler(buy.cancel_new_pix,   pattern=r"^pix:new_cancel$"))

    # Compra
    app.add_handler(CallbackQueryHandler(buy.buy_single,       pattern=r"^buy:"))

    # Comprar mais de um
    app.add_handler(CallbackQueryHandler(multi.multi_start,    pattern=r"^buymulti:"))
    app.add_handler(CallbackQueryHandler(multi.multi_confirm,  pattern=r"^multi:confirm:"))
    app.add_handler(CallbackQueryHandler(multi.multi_cancel,   pattern=r"^multi:cancel$"))

    # Produto
    app.add_handler(CallbackQueryHandler(catalog.product_callback, pattern=r"^prod:"))

    # Menu (fallback)
    app.add_handler(CallbackQueryHandler(menu.menu_router))

    # ─── Texto livre (para responder o ForceReply de quantidade)
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, multi.multi_qty_handler))

    return app


def main():
    app = build_app()
    if WEBHOOK_URL:
        logger.info("Rodando via WEBHOOK em %s", WEBHOOK_URL)
        app.run_webhook(
            listen="0.0.0.0",
            port=PORT,
            url_path=BOT_TOKEN,
            webhook_url=f"{WEBHOOK_URL}/{BOT_TOKEN}",
            drop_pending_updates=True,
        )
    else:
        logger.info("Rodando via POLLING (modo local)")
        app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
