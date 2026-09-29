import logging
import threading
import asyncio
import os
import smtplib

from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.utils import formataddr

from flask import Flask, request, jsonify, render_template
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import (
    ApplicationBuilder,
    CallbackQueryHandler,
    ChatMemberHandler,
    CommandHandler,
    InlineQueryHandler,
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
    admin_stock,
    inline,
)

logging.basicConfig(
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger("larizinha-bot")


# ═══════════════════════════════════════════════
# FLASK
# ═══════════════════════════════════════════════
flask_app = Flask(__name__)
loop: asyncio.AbstractEventLoop | None = None


@flask_app.get("/")
def health():
    return "Larizinha Store Bot — OK"


# ─── Mini App: página HTML
@flask_app.get("/miniapp/senha/<int:user_id>")
def miniapp_senha(user_id: int):
    return render_template("miniapp_senha.html", user_id=user_id)


# ─── Mini App: salvar senha (rota antiga, mantida)
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


# ─── API: salvar senha (chamada pelo Web App)
@flask_app.post("/api/salvar-senha/<int:user_id>")
def api_salvar_senha(user_id: int):
    data = request.get_json(silent=True) or {}
    pin = str(data.get("pin", "")).strip()

    if not pin.isdigit() or not (4 <= len(pin) <= 6):
        return jsonify(ok=False, error="Senha inválida (4 a 6 dígitos)."), 400

    if loop is None:
        return jsonify(ok=False, error="Servidor iniciando. Tente novamente."), 503

    try:
        asyncio.run_coroutine_threadsafe(
            db.set_payout_password(user_id, pin), loop
        ).result(timeout=5)
    except Exception as e:
        logger.exception("Erro salvando senha: %s", e)
        return jsonify(ok=False, error="Erro interno ao salvar senha."), 500

    return jsonify(ok=True, message="Senha salva com sucesso.")


# ─── API: salvar email de recuperação
@flask_app.post("/api/salvar-email/<int:user_id>")
def api_salvar_email(user_id: int):
    data = request.get_json(silent=True) or {}
    email = str(data.get("email", "")).strip()

    if "@" not in email or "." not in email.split("@")[-1]:
        return jsonify(ok=False, error="E-mail inválido."), 400

    if loop is None:
        return jsonify(ok=False, error="Servidor iniciando."), 503

    try:
        async def _save():
            await db._db.execute(
                "UPDATE users SET whatsapp = COALESCE(whatsapp, ?) WHERE user_id = ?",
                (email, user_id),
            )
            await db._db.commit()

        asyncio.run_coroutine_threadsafe(_save(), loop).result(timeout=5)
    except Exception as e:
        logger.exception("Erro salvando email: %s", e)
        return jsonify(ok=False, error="Erro interno."), 500

    return jsonify(ok=True)


# ─── API: checar se já tem senha cadastrada
@flask_app.get("/api/checar-senha/<int:user_id>")
def api_checar_senha(user_id: int):
    if loop is None:
        return jsonify(ok=False, error="Servidor iniciando."), 503

    try:
        u = asyncio.run_coroutine_threadsafe(
            db.get_user(user_id), loop
        ).result(timeout=5)
        tem_senha = bool(u and u.get("payout_password"))
        return jsonify(ok=True, tem_senha=tem_senha)
    except Exception as e:
        logger.exception("Erro checando senha: %s", e)
        return jsonify(ok=False, error="Erro interno."), 500


# ═══════════════════════════════════════════════
# 📧 API: enviar código por e-mail (Gmail SMTP)
# ═══════════════════════════════════════════════
@flask_app.post("/api/enviar-codigo")
def api_enviar_codigo():
    data = request.get_json(silent=True) or {}
    email = str(data.get("email", "")).strip()
    codigo = str(data.get("codigo", "")).strip()
    tipo = str(data.get("tipo", "cadastro")).strip()

    if "@" not in email or not codigo:
        return jsonify(ok=False, error="Dados inválidos."), 400

    gmail_user = os.getenv("GMAIL_USER", "").strip()
    gmail_pass = os.getenv("GMAIL_APP_PASSWORD", "").strip()
    nome_loja = os.getenv("STORE_NAME", "Larizinha Store")

    if not gmail_user or not gmail_pass:
        logger.error("GMAIL_USER / GMAIL_APP_PASSWORD não configurados")
        return jsonify(ok=False, error="Servidor de e-mail não configurado."), 500

    eh_recuperacao = (tipo == "recuperacao")
    assunto = "Recuperação de senha" if eh_recuperacao else "Confirme seu e-mail"
    titulo = "Redefinição de senha" if eh_recuperacao else "Confirme seu e-mail"
    subtitulo = (
        "Recebemos uma solicitação para redefinir a senha da sua conta. "
        "Utilize o código abaixo para continuar:"
    ) if eh_recuperacao else (
        f"Recebemos seu cadastro na {nome_loja}. "
        "Para ativar sua conta, utilize o código de verificação abaixo:"
    )

    html = f"""
    <!DOCTYPE html>
    <html lang="pt-BR">
    <head>
      <meta charset="UTF-8">
      <meta name="viewport" content="width=device-width, initial-scale=1.0">
      <title>{titulo}</title>
      <style>
        @media (prefers-color-scheme: dark) {{
          .corpo-email {{ background-color:#000000 !important; }}
          .cartao-email {{ background-color:#111111 !important; border-color:#262626 !important; }}
          .texto-principal {{ color:#f5f5f5 !important; }}
          .texto-secundario {{ color:#a3a3a3 !important; }}
          .linha-divisoria {{ border-color:#262626 !important; }}
          .rodape-texto {{ color:#6b7280 !important; }}
          .codigo-box {{ background-color:#1a1a1a !important; border-color:#333333 !important; }}
          .codigo-texto {{ color:#ffffff !important; }}
        }}
      </style>
    </head>
    <body style="margin:0; padding:0; background-color:#f4f4f5; font-family:-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; -webkit-font-smoothing:antialiased;">
      <table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0" class="corpo-email" style="background-color:#f4f4f5; padding:40px 16px;">
        <tr>
          <td align="center">
            <table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0" style="max-width:560px;">
              <tr>
                <td>
                  <table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0" class="cartao-email" style="background-color:#ffffff; border:1px solid #e5e7eb; border-radius:12px; overflow:hidden;">
                    <tr>
                      <td style="padding:48px 40px;">
                        <h1 class="texto-principal" style="margin:0 0 16px; font-size:24px; font-weight:700; color:#111827; line-height:1.3;">{titulo}</h1>
                        <p class="texto-secundario" style="margin:0 0 24px; font-size:15px; line-height:1.6; color:#4b5563;">{subtitulo}</p>
                        <table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0">
                          <tr>
                            <td align="center">
                              <div class="codigo-box" style="display:inline-block; padding:20px 40px; background-color:#f9fafb; border:1px solid #e5e7eb; border-radius:8px;">
                                <span class="codigo-texto" style="font-size:36px; font-weight:800; letter-spacing:12px; color:#111827; font-family:monospace, 'Courier New', Courier;">{codigo}</span>
                              </div>
                            </td>
                          </tr>
                        </table>
                        <p class="texto-secundario" style="margin:32px 0 0; font-size:14px; line-height:1.6; color:#6b7280;">
                          Este código expira em 5 minutos. Se você não solicitou, ignore este e-mail.
                        </p>
                      </td>
                    </tr>
                    <tr>
                      <td class="linha-divisoria" style="border-top:1px solid #e5e7eb; padding:32px 40px; background-color:#f9fafb;">
                        <p class="texto-principal" style="margin:0 0 8px; font-size:15px; font-weight:600; color:#111827;">Ficou com alguma dúvida?</p>
                        <p class="texto-secundario" style="margin:0 0 16px; font-size:14px; line-height:1.6; color:#4b5563;">
                          Esta é uma mensagem automática. Pedimos que não responda este e-mail.
                        </p>
                        <p class="texto-secundario" style="margin:0; font-size:13px; line-height:1.6; color:#6b7280;">
                          Você está recebendo este e-mail porque se cadastrou na {nome_loja}.
                        </p>
                      </td>
                    </tr>
                  </table>
                </td>
              </tr>
              <tr>
                <td style="padding-top:32px;">
                  <p class="rodape-texto" style="margin:0; font-size:12px; color:#6b7280; line-height:1.5; text-align:center;">
                    <strong style="color:#374151;">{nome_loja}</strong>
                  </p>
                </td>
              </tr>
            </table>
          </td>
        </tr>
      </table>
    </body>
    </html>
    """

    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = assunto
        msg["From"] = formataddr((nome_loja, gmail_user))
        msg["To"] = email
        msg.attach(MIMEText(html, "html", "utf-8"))

        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(gmail_user, gmail_pass)
            server.sendmail(gmail_user, [email], msg.as_string())

        logger.info("Código enviado para %s (tipo=%s)", email, tipo)
        return jsonify(ok=True, message="E-mail enviado com sucesso")

    except smtplib.SMTPAuthenticationError:
        logger.exception("Falha de autenticação SMTP")
        return jsonify(ok=False, error="Falha na autenticação do servidor de e-mail."), 500
    except Exception as e:
        logger.exception("Erro enviando e-mail: %s", e)
        return jsonify(ok=False, error="Falha ao enviar e-mail. Tente novamente."), 500


def run_flask():
    flask_app.run(host="0.0.0.0", port=PORT, debug=False, use_reloader=False)


# ═══════════════════════════════════════════════
# POST INIT
# ═══════════════════════════════════════════════
async def post_init(app):
    global loop
    loop = asyncio.get_running_loop()

    await db.init_db()
    await db.seed_products()
    logger.info("Banco iniciado e produtos populados.")

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
    if update.effective_user.id not in ADMIN_IDS:
        return
    if not context.args:
        await update.message.reply_text("Uso: /pago <pix_id>")
        return

    pix_id = context.args[0]
    await db.mark_pix_paid(pix_id)
    await update.message.reply_text(f"✅ PIX {pix_id} marcado como pago.")


async def cancelar(update: Update, context):
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
    user_id = update.effective_user.id
    url = f"{MINIAPP_BASE_URL}/miniapp/senha/{user_id}"

    kb = InlineKeyboardMarkup([[
        InlineKeyboardButton(
            "🔐 Abrir Cadastro de Senha",
            web_app={"url": url},
        )
    ]])
    await update.message.reply_text(
        "🔐 Clique abaixo para cadastrar sua senha de saque:",
        reply_markup=kb,
    )


async def myid_command(update: Update, context):
    await update.message.reply_text(
        f"👤 Seu ID: <code>{update.effective_user.id}</code>\n"
        f"💬 Chat ID: <code>{update.effective_chat.id}</code>",
        parse_mode="HTML",
    )


# ═══════════════════════════════════════════════
# ROTEADOR DE TEXTO LIVRE
# ═══════════════════════════════════════════════
async def _text_router(update: Update, context):
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

    return


# ═══════════════════════════════════════════════
# MINI APP via botão
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
# BUILD APP
# ═══════════════════════════════════════════════
def build_app():
    app = ApplicationBuilder().token(BOT_TOKEN).post_init(post_init).build()

    # ─── COMANDOS
    app.add_handler(CommandHandler("start", start.start_command))
    app.add_handler(CommandHandler("pago", mark_paid))
    app.add_handler(CommandHandler("cancelar", cancelar))
    app.add_handler(CommandHandler("setsenha", setpin_command))
    app.add_handler(CommandHandler("myid", myid_command))
    app.add_handler(CommandHandler("notif", notif.notif_command))
    app.add_handler(CommandHandler("broadcast", notif.broadcast_command))
    app.add_handler(CommandHandler("addstock", admin_stock.addstock_command))
    app.add_handler(CommandHandler("stock", admin_stock.stock_command))

    # ─── GATE
    app.add_handler(
        ChatMemberHandler(
            start.chat_member_update,
            ChatMemberHandler.CHAT_MEMBER,
        )
    )

    # ─── INLINE
    app.add_handler(InlineQueryHandler(inline.inline_query))

    # ─── AÇÕES DIRETAS
    app.add_handler(
        CallbackQueryHandler(direct.direct_router, pattern=r"^direct:")
    )

    # ─── ENTREGA
    app.add_handler(
        CallbackQueryHandler(delivery.reveal_product, pattern=r"^delivery:reveal:")
    )

    # ─── PIX COMPRA
    app.add_handler(CallbackQueryHandler(buy.generate_pix,   pattern=r"^pix:gen:"))
    app.add_handler(CallbackQueryHandler(buy.copy_pix,       pattern=r"^pix:copy:"))
    app.add_handler(CallbackQueryHandler(buy.check_pix,      pattern=r"^pix:check:"))
    app.add_handler(CallbackQueryHandler(buy.cancel_pix,     pattern=r"^pix:cancel:"))
    app.add_handler(CallbackQueryHandler(buy.cancel_new_pix, pattern=r"^pix:new_cancel$"))

    # ─── PIX RECARGA
    app.add_handler(CallbackQueryHandler(topup.topup_copy,   pattern=r"^toppix:copy:"))
    app.add_handler(CallbackQueryHandler(topup.topup_check,  pattern=r"^toppix:check:"))
    app.add_handler(CallbackQueryHandler(topup.topup_cancel, pattern=r"^toppix:cancel:"))

    # ─── RECARGA
    app.add_handler(
        CallbackQueryHandler(topup.topup_pix_open, pattern=r"^topup:pix$")
    )

    # ─── COMPRA
    app.add_handler(CallbackQueryHandler(buy.buy_single,      pattern=r"^buy:"))
    app.add_handler(CallbackQueryHandler(multi.multi_start,   pattern=r"^buymulti:"))
    app.add_handler(CallbackQueryHandler(multi.multi_confirm, pattern=r"^multi:confirm:"))
    app.add_handler(CallbackQueryHandler(multi.multi_cancel,  pattern=r"^multi:cancel$"))

    # ─── HISTÓRICO
    app.add_handler(CallbackQueryHandler(history.history_router, pattern=r"^hist:"))
    app.add_handler(
        CallbackQueryHandler(history.history_router, pattern=r"^profile:history$")
    )

    # ─── GIFT
    app.add_handler(CallbackQueryHandler(gift.gift_open,   pattern=r"^profile:gift$"))
    app.add_handler(CallbackQueryHandler(gift.gift_cancel, pattern=r"^gift:cancel$"))
    app.add_handler(CallbackQueryHandler(gift.gift_use,    pattern=r"^gift:use$"))

    # ─── ALTERAR
    app.add_handler(
        CallbackQueryHandler(alterdata.alter_open,     pattern=r"^profile:alter$")
    )
    app.add_handler(
        CallbackQueryHandler(alterdata.alter_whatsapp, pattern=r"^alter:whatsapp$")
    )

    # ─── AFILIADOS
    app.add_handler(
        CallbackQueryHandler(affiliates.affiliates_open, pattern=r"^menu:affiliates$")
    )
    app.add_handler(
        CallbackQueryHandler(affiliates.affiliates_open, pattern=r"^aff:menu$")
    )
    app.add_handler(
        CallbackQueryHandler(affiliates.affiliates_join, pattern=r"^aff:join$")
    )

    # ─── HISTÓRICO SAQUE
    app.add_handler(
        CallbackQueryHandler(withdraw_history.withdraw_history, pattern=r"^aff:whist$")
    )

    # ─── SAQUES
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

    # ─── MINI APP
    app.add_handler(
        CallbackQueryHandler(_open_miniapp, pattern=r"^aff:setpin$")
    )

    # ─── TOP
    app.add_handler(CallbackQueryHandler(top.top_open,   pattern=r"^menu:top$"))
    app.add_handler(CallbackQueryHandler(top.top_filter, pattern=r"^top:"))

    # ─── PESQUISAR
    app.add_handler(
        CallbackQueryHandler(search.search_open, pattern=r"^menu:search$")
    )

    # ─── PRODUTO
    app.add_handler(
        CallbackQueryHandler(catalog.product_callback, pattern=r"^prod:")
    )

    # ─── MENU (fallback)
    app.add_handler(CallbackQueryHandler(menu.menu_router))

    # ─── TEXTO LIVRE
    app.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, _text_router)
    )

    return app


# ═══════════════════════════════════════════════
# BOOT
# ═══════════════════════════════════════════════
def main():
    threading.Thread(target=run_flask, daemon=True).start()
    logger.info("Servidor Flask rodando na porta %s", PORT)

    app = build_app()

    if WEBHOOK_URL:
        logger.info("Rodando via WEBHOOK em %s", WEBHOOK_URL)
        app.run_webhook(
            listen="0.0.0.0",
            port=PORT + 1,
            url_path=BOT_TOKEN,
            webhook_url=f"{WEBHOOK_URL}/{BOT_TOKEN}",
            drop_pending_updates=True,
        )
    else:
        logger.info("Rodando via POLLING")
        app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
