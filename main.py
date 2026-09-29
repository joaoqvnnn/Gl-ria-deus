import logging
from telegram.ext import (
    ApplicationBuilder,
    CallbackQueryHandler,
    ChatMemberHandler,
    CommandHandler,
)

from config import BOT_TOKEN, PORT, WEBHOOK_URL
from database import db
from handlers import start, menu, catalog

logging.basicConfig(
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger("larizinha-bot")


async def post_init(app):
    await db.init_db()
    await db.seed_products()
    logger.info("Banco iniciado e produtos populados.")


def build_app():
    app = ApplicationBuilder().token(BOT_TOKEN).post_init(post_init).build()

    # Gate / Comandos
    app.add_handler(CommandHandler("start", start.start_command))

    # Detectar entrada no canal (precisa ser admin do canal!)
    app.add_handler(
        ChatMemberHandler(start.chat_member_update, ChatMemberHandler.CHAT_MEMBER)
    )

    # Produto (antes do menu genérico)
    app.add_handler(CallbackQueryHandler(catalog.product_callback, pattern=r"^prod:"))

    # Menu principal e demais botões
    app.add_handler(CallbackQueryHandler(menu.menu_router))

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
