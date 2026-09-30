import logging
import threading
import asyncio
import os
import io
import smtplib

from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.utils import formataddr

from flask import Flask, request, jsonify, render_template, send_file
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
bot_app = None  # instância do PTB Application — usada para enviar mensagens


@flask_app.get("/")
def health():
    return "Larizinha Store Bot — OK"


# ═══════════════════════════════════════════════
# MINI APP — SENHA DE SAQUE
# ═══════════════════════════════════════════════
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


# ═══════════════════════════════════════════════
# API — SENHA / EMAIL / CHECAR
# ═══════════════════════════════════════════════
@flask_app.post("/api/salvar-senha/<int:user_id>")
def api_salvar_senha(user_id: int):
    data = request.get_json(silent=True) or {}
    pin = str(data.get("pin", "")).strip()

    if not pin.isdigit() or not (4 <= len(pin) <= 6):
        return jsonify(ok=False, error="Senha inválida (4 a 6 dígitos)."), 400

    if loop is None:
        return jsonify(ok=False, error="Servidor iniciando."), 503

    try:
        asyncio.run_coroutine_threadsafe(
            db.set_payout_password(user_id, pin), loop
        ).result(timeout=5)
    except Exception as e:
        logger.exception("Erro salvando senha: %s", e)
        return jsonify(ok=False, error="Erro interno."), 500

    return jsonify(ok=True)


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
# 📧 ENVIAR CÓDIGO POR E-MAIL
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
    </head>
    <body style="margin:0; padding:0; background-color:#f4f4f5; font-family:-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;">
      <table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0" style="background-color:#f4f4f5; padding:40px 16px;">
        <tr>
          <td align="center">
            <table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0" style="max-width:560px;">
              <tr>
                <td>
                  <table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0" style="background-color:#ffffff; border:1px solid #e5e7eb; border-radius:12px; overflow:hidden;">
                    <tr>
                      <td style="padding:48px 40px;">
                        <h1 style="margin:0 0 16px; font-size:24px; font-weight:700; color:#111827;">{titulo}</h1>
                        <p style="margin:0 0 24px; font-size:15px; line-height:1.6; color:#4b5563;">{subtitulo}</p>
                        <table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0">
                          <tr>
                            <td align="center">
                              <div style="display:inline-block; padding:20px 40px; background-color:#f9fafb; border:1px solid #e5e7eb; border-radius:8px;">
                                <span style="font-size:36px; font-weight:800; letter-spacing:12px; color:#111827; font-family:monospace;">{codigo}</span>
                              </div>
                            </td>
                          </tr>
                        </table>
                        <p style="margin:32px 0 0; font-size:14px; line-height:1.6; color:#6b7280;">
                          Este código expira em 5 minutos. Se você não solicitou, ignore este e-mail.
                        </p>
                      </td>
                    </tr>
                  </table>
                </td>
              </tr>
              <tr>
                <td style="padding-top:32px; text-align:center;">
                  <p style="margin:0; font-size:12px; color:#6b7280;">
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
        return jsonify(ok=False, error="Falha ao enviar e-mail."), 500


# ═══════════════════════════════════════════════
# LOJA VIRTUAL — páginas e APIs
# ═══════════════════════════════════════════════
@flask_app.get("/loja/<int:user_id>")
def loja_page(user_id: int):
    return render_template("loja.html", user_id=user_id)


@flask_app.get("/api/loja/usuario/<int:user_id>")
def api_loja_usuario(user_id):
    if loop is None:
        return jsonify(ok=False, error="Servidor iniciando."), 503
    try:
        u = asyncio.run_coroutine_threadsafe(
            db.get_or_create_user(user_id, None, None), loop
        ).result(timeout=5)
        return jsonify(ok=True, user={
            "user_id":      u["user_id"],
            "username":     u.get("username"),
            "first_name":   u.get("first_name"),
            "balance":      float(u.get("balance") or 0),
            "balance_web":  float(u.get("balance_web") or 0),
            "age_verified": int(u.get("age_verified") or 0),
        })
    except Exception as e:
        logger.exception(e)
        return jsonify(ok=False), 500


@flask_app.get("/api/loja/config")
def api_loja_config():
    defaults = {
        "store_name":    os.getenv("STORE_NAME", "Minha Loja"),
        "cnpj":          os.getenv("STORE_CNPJ", "00.000.000/0000-00"),
        "horario":       os.getenv("STORE_HOURS", "Seg a Sex, 09h às 18h"),
        "whatsapp_link": os.getenv("SUPPORT_WHATSAPP", "https://wa.me/"),
        "telegram_link": os.getenv("SUPPORT_LINK", "https://t.me/"),
    }
    if loop is not None:
        try:
            async def _get():
                cur = await db._db.execute("SELECT key, value FROM config")
                rows = await cur.fetchall()
                return {r["key"]: r["value"] for r in rows}
            cfg = asyncio.run_coroutine_threadsafe(_get(), loop).result(timeout=5)
            defaults.update({k: v for k, v in cfg.items() if v})
        except Exception:
            pass
    return jsonify(ok=True, config=defaults)


# ─── PIX (Mercado Pago) ───
@flask_app.post("/api/loja/pix")
def api_loja_pix():
    from services import mercadopago
    data = request.get_json(silent=True) or {}
    valor       = float(data.get("valor", 0))
    user_id     = int(data.get("user_id", 0))
    purchase_id = str(data.get("purchase_id", ""))
    tipo        = data.get("tipo", "recarga")
    itens       = data.get("itens") or []

    if valor <= 0 or not user_id or not purchase_id:
        return jsonify(ok=False, error="Dados inválidos."), 400

    try:
        pix = mercadopago.criar_pix(
            valor=valor,
            descricao=f"Pedido {purchase_id}",
            user_id=user_id,
            purchase_id=purchase_id,
        )

        # Salva PIX pendente no banco
        async def _save():
            await db._db.execute(
                "INSERT OR REPLACE INTO pix_pending "
                "(id, user_id, valor, tipo, product_id, quantity, copia_cola, status) "
                "VALUES (?, ?, ?, ?, NULL, NULL, ?, 'pending')",
                (str(pix["payment_id"]), user_id, valor, tipo, pix.get("qr_code_text")),
            )
            # Guarda o purchase_id e itens para o webhook reconstruir depois
            await db._db.execute(
                "CREATE TABLE IF NOT EXISTS pix_meta ("
                "  pix_id TEXT PRIMARY KEY,"
                "  purchase_id TEXT,"
                "  itens_json TEXT"
                ")"
            )
            import json as _json
            await db._db.execute(
                "INSERT OR REPLACE INTO pix_meta (pix_id, purchase_id, itens_json) VALUES (?, ?, ?)",
                (str(pix["payment_id"]), purchase_id, _json.dumps(itens)),
            )
            await db._db.commit()

        asyncio.run_coroutine_threadsafe(_save(), loop).result(timeout=5)

        return jsonify(ok=True, pix=pix)
    except Exception as e:
        logger.exception("Erro /api/loja/pix: %s", e)
        return jsonify(ok=False, error=str(e)), 500


@flask_app.get("/api/mercadopago/status/<int:payment_id>")
def api_mp_status(payment_id):
    from services import mercadopago
    try:
        p = mercadopago.consultar_pagamento(payment_id)
        return jsonify(ok=True, status=p.get("status"))
    except Exception as e:
        logger.exception(e)
        return jsonify(ok=False, error=str(e)), 500


@flask_app.post("/api/mercadopago/webhook")
def api_mp_webhook():
    from services import mercadopago
    data = request.get_json(silent=True) or {}
    payment_id = data.get("data", {}).get("id")
    if not payment_id:
        return jsonify(ok=False), 400

    try:
        p = mercadopago.consultar_pagamento(payment_id)
        if p.get("status") == "approved":
            asyncio.run_coroutine_threadsafe(
                _finalizar_pagamento_loja(payment_id), loop
            ).result(timeout=20)
    except Exception as e:
        logger.exception("Erro webhook MP: %s", e)

    return jsonify(ok=True), 200


async def _finalizar_pagamento_loja(payment_id):
    """Chamado quando o MP confirma o pagamento."""
    import json as _json

    pix = await db.get_pix(str(payment_id))
    if not pix:
        logger.warning("PIX não encontrado: %s", payment_id)
        return

    user = await db.get_user(pix["user_id"])
    if not user:
        return

    tipo  = pix.get("tipo", "recarga")
    valor = float(pix["valor"])

    # ─── RECARGA: credita balance_web
    if tipo == "recarga":
        await db._db.execute(
            "UPDATE users SET balance_web = balance_web + ? WHERE user_id = ?",
            (valor, user["user_id"]),
        )
        await db._db.commit()

        if bot_app:
            try:
                await bot_app.bot.send_message(
                    chat_id=user["user_id"],
                    text=f"✅ <b>Recarga no Web App confirmada!</b>\n\n💰 Valor: R$ {valor:.2f}",
                    parse_mode="HTML",
                )
            except Exception:
                pass

    # ─── COMPRA: cria purchase e manda credenciais
    elif tipo == "compra":
        # Recupera itens do pix_meta
        cur = await db._db.execute(
            "SELECT purchase_id, itens_json FROM pix_meta WHERE pix_id = ?",
            (str(payment_id),),
        )
        row = await cur.fetchone()
        itens = []
        purchase_id = None
        if row:
            purchase_id = row["purchase_id"]
            try:
                itens = _json.loads(row["itens_json"] or "[]")
            except Exception:
                itens = []

        if not itens:
            logger.warning("Compra sem itens: %s", payment_id)
            return

        primeiro = itens[0]
        product = await db.get_product(int(primeiro.get("id")))
        if not product:
            return

        qty = int(primeiro.get("qty", 1))
        items = await db.take_stock_items(product["id"], qty)
        first = items[0] if items else {"email": "N/A", "password": "N/A"}

        # Cria purchase (usando ID externo se tiver)
        if purchase_id:
            purchase = await db.create_purchase_with_id(
                purchase_id=purchase_id,
                user_id=user["user_id"],
                product_id=product["id"],
                product_name=product["name"],
                quantity=qty,
                total=valor,
                email=first["email"],
                password=first["password"],
            )
        else:
            purchase = await db.create_purchase(
                user_id=user["user_id"],
                product_id=product["id"],
                product_name=product["name"],
                quantity=qty,
                total=valor,
                email=first["email"],
                password=first["password"],
            )

        await db.decrement_stock(product["id"], qty)

        if bot_app:
            try:
                await bot_app.bot.send_message(
                    chat_id=user["user_id"],
                    text=(
                        f"✅ <b>Compra realizada no Web App!</b>\n\n"
                        f"⚜️ Serviço: <b>{product['name']}</b>\n"
                        f"💰 Total: <b>R$ {valor:.2f}</b>\n"
                        f"🎫 ID: <code>{purchase['id']}</code>"
                    ),
                    parse_mode="HTML",
                )
            except Exception:
                pass


@flask_app.post("/api/loja/comprar-saldo")
def api_loja_comprar_saldo():
    data = request.get_json(silent=True) or {}
    user_id = int(data.get("user_id", 0))
    itens   = data.get("itens", [])
    total   = float(data.get("total", 0))

    if not user_id or not itens or total <= 0:
        return jsonify(ok=False, error="Dados inválidos."), 400

    if loop is None:
        return jsonify(ok=False, error="Servidor iniciando."), 503

    try:
        result = asyncio.run_coroutine_threadsafe(
            _comprar_com_saldo_web(user_id, itens, total), loop
        ).result(timeout=20)
        return jsonify(**result)
    except Exception as e:
        logger.exception("Erro comprar-saldo: %s", e)
        return jsonify(ok=False, error=str(e)), 500


async def _comprar_com_saldo_web(user_id, itens, total):
    user = await db.get_user(user_id)
    if not user:
        return {"ok": False, "error": "Usuário não encontrado."}

    if float(user.get("balance_web") or 0) < total:
        return {"ok": False, "error": "Saldo insuficiente."}

    primeiro = itens[0]
    product = await db.get_product(int(primeiro["id"]))
    if not product:
        return {"ok": False, "error": "Produto inválido."}

    qty = int(primeiro.get("qty", 1))
    items = await db.take_stock_items(product["id"], qty)
    first = items[0] if items else {"email": "N/A", "password": "N/A"}

    purchase = await db.create_purchase(
        user_id=user_id,
        product_id=product["id"],
        product_name=product["name"],
        quantity=qty,
        total=total,
        email=first["email"],
        password=first["password"],
    )
    await db.decrement_stock(product["id"], qty)

    # Debita saldo só depois de garantir que deu certo
    await db._db.execute(
        "UPDATE users SET balance_web = balance_web - ? WHERE user_id = ?",
        (total, user_id),
    )
    await db._db.commit()

    if bot_app:
        try:
            await bot_app.bot.send_message(
                chat_id=user_id,
                text=(
                    f"✅ <b>Compra realizada no Web App!</b>\n\n"
                    f"⚜️ Serviço: <b>{product['name']}</b>\n"
                    f"💰 Total: <b>R$ {total:.2f}</b>\n"
                    f"🎫 ID: <code>{purchase['id']}</code>"
                ),
                parse_mode="HTML",
            )
        except Exception:
            pass

    novo = await db.get_user(user_id)
    return {
        "ok": True,
        "purchase_id": purchase["id"],
        "novo_saldo": float(novo.get("balance_web") or 0),
    }


# ─── Verificação +18 (IA) ───
@flask_app.post("/api/loja/verificar-idade")
def api_verificar_idade():
    from services import openai_service
    data = request.get_json(silent=True) or {}
    user_id = int(data.get("user_id", 0))
    front   = data.get("front", "")
    back    = data.get("back", "")

    if not user_id or not front or not back:
        return jsonify(ok=False, motivo="Dados incompletos."), 400

    try:
        result = openai_service.verificar_idade_por_rg(front, back)
        if result.get("aprovado"):
            async def _save():
                await db._db.execute(
                    "UPDATE users SET age_verified = 1 WHERE user_id = ?", (user_id,)
                )
                await db._db.commit()
            asyncio.run_coroutine_threadsafe(_save(), loop).result(timeout=5)
        return jsonify(ok=True, **result)
    except Exception as e:
        logger.exception(e)
        return jsonify(ok=False, motivo="Erro ao analisar documento."), 500


# ─── Chat IA ───
@flask_app.post("/api/loja/chat")
def api_loja_chat():
    from services import openai_service
    data = request.get_json(silent=True) or {}
    user_id = int(data.get("user_id", 0))
    msg     = str(data.get("message", "")).strip()

    if not msg:
        return jsonify(ok=False), 400

    contexto = ""
    if loop is not None:
        try:
            produtos = asyncio.run_coroutine_threadsafe(
                db.get_products(), loop
            ).result(timeout=5)
            contexto = "Produtos disponíveis:\n" + "\n".join(
                f"- {p['name']} — R$ {p['price']}" for p in produtos[:15]
            )
        except Exception:
            pass

    try:
        resposta = openai_service.chat_resposta(msg, contexto)
        return jsonify(ok=True, resposta=resposta)
    except Exception as e:
        logger.exception(e)
        return jsonify(ok=False, resposta="Erro no atendimento."), 500


# ─── Histórico de compras ───
@flask_app.get("/api/loja/historico/<int:user_id>")
def api_loja_historico(user_id):
    if loop is None:
        return jsonify(ok=False), 503
    try:
        compras = asyncio.run_coroutine_threadsafe(
            db.list_purchases(user_id), loop
        ).result(timeout=5)
        return jsonify(ok=True, compras=compras)
    except Exception as e:
        logger.exception(e)
        return jsonify(ok=False), 500


# ─── PDF do pedido ───
@flask_app.get("/api/loja/pedido/<purchase_id>/pdf")
def api_loja_pedido_pdf(purchase_id):
    from services import pdf_gen
    if loop is None:
        return "Servidor iniciando", 503
    try:
        purchase = asyncio.run_coroutine_threadsafe(
            db.get_purchase(purchase_id), loop
        ).result(timeout=5)
        if not purchase:
            return "Pedido não encontrado", 404

        pdf = pdf_gen.gerar_pdf_pedido(purchase)
        return send_file(
            io.BytesIO(pdf),
            mimetype="application/pdf",
            download_name=f"pedido-{purchase_id[:8]}.pdf",
        )
    except Exception as e:
        logger.exception(e)
        return str(e), 500


# ═══════════════════════════════════════════════
# RUN FLASK
# ═══════════════════════════════════════════════
def run_flask():
    flask_app.run(host="0.0.0.0", port=PORT, debug=False, use_reloader=False)


# ═══════════════════════════════════════════════
# POST INIT (PTB)
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
        logger.info("JobQueue: carrinho abandonado iniciado.")


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
        "awaiting_multi", "awaiting_gift", "awaiting_whatsapp",
        "awaiting_topup_value", "awaiting_wd_key", "awaiting_wd_amount",
        "awaiting_wd_pin", "awaiting_search",
    ):
        context.user_data.pop(k, None)
    await update.message.reply_text("❌ Operação cancelada.")


async def setpin_command(update: Update, context):
    user_id = update.effective_user.id
    url = f"{MINIAPP_BASE_URL}/miniapp/senha/{user_id}"
    kb = InlineKeyboardMarkup([[
        InlineKeyboardButton("🔐 Abrir Cadastro de Senha", web_app={"url": url})
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
# BUILD APP (PTB)
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
        ChatMemberHandler(start.chat_member_update, ChatMemberHandler.CHAT_MEMBER)
    )

    # ─── INLINE
    app.add_handler(InlineQueryHandler(inline.inline_query))

    # ─── AÇÕES DIRETAS
    app.add_handler(CallbackQueryHandler(direct.direct_router, pattern=r"^direct:"))

    # ─── ENTREGA
    app.add_handler(CallbackQueryHandler(delivery.reveal_product, pattern=r"^delivery:reveal:"))

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
    app.add_handler(CallbackQueryHandler(topup.topup_pix_open, pattern=r"^topup:pix$"))

    # ─── COMPRA
    app.add_handler(CallbackQueryHandler(buy.buy_single,      pattern=r"^buy:"))
    app.add_handler(CallbackQueryHandler(multi.multi_start,   pattern=r"^buymulti:"))
    app.add_handler(CallbackQueryHandler(multi.multi_confirm, pattern=r"^multi:confirm:"))
    app.add_handler(CallbackQueryHandler(multi.multi_cancel,  pattern=r"^multi:cancel$"))

    # ─── HISTÓRICO
    app.add_handler(CallbackQueryHandler(history.history_router, pattern=r"^hist:"))
    app.add_handler(CallbackQueryHandler(history.history_router, pattern=r"^profile:history$"))

    # ─── GIFT
    app.add_handler(CallbackQueryHandler(gift.gift_open,   pattern=r"^profile:gift$"))
    app.add_handler(CallbackQueryHandler(gift.gift_cancel, pattern=r"^gift:cancel$"))
    app.add_handler(CallbackQueryHandler(gift.gift_use,    pattern=r"^gift:use$"))

    # ─── ALTERAR
    app.add_handler(CallbackQueryHandler(alterdata.alter_open,     pattern=r"^profile:alter$"))
    app.add_handler(CallbackQueryHandler(alterdata.alter_whatsapp, pattern=r"^alter:whatsapp$"))

    # ─── AFILIADOS
    app.add_handler(CallbackQueryHandler(affiliates.affiliates_open, pattern=r"^menu:affiliates$"))
    app.add_handler(CallbackQueryHandler(affiliates.affiliates_open, pattern=r"^aff:menu$"))
    app.add_handler(CallbackQueryHandler(affiliates.affiliates_join, pattern=r"^aff:join$"))

    # ─── HISTÓRICO SAQUE
    app.add_handler(CallbackQueryHandler(withdraw_history.withdraw_history, pattern=r"^aff:whist$"))

    # ─── SAQUES
    app.add_handler(CallbackQueryHandler(withdraw.withdraw_open,        pattern=r"^aff:withdraw$"))
    app.add_handler(CallbackQueryHandler(withdraw.withdraw_type,        pattern=r"^wd:type:"))
    app.add_handler(CallbackQueryHandler(withdraw.withdraw_confirm_key, pattern=r"^wd:confirm_key$"))
    app.add_handler(CallbackQueryHandler(withdraw.withdraw_edit_key,    pattern=r"^wd:edit_key$"))
    app.add_handler(CallbackQueryHandler(withdraw.withdraw_sacar,       pattern=r"^wd:sacar$"))

    # ─── MINI APP
    app.add_handler(CallbackQueryHandler(_open_miniapp, pattern=r"^aff:setpin$"))

    # ─── TOP
    app.add_handler(CallbackQueryHandler(top.top_open,   pattern=r"^menu:top$"))
    app.add_handler(CallbackQueryHandler(top.top_filter, pattern=r"^top:"))

    # ─── PESQUISAR
    app.add_handler(CallbackQueryHandler(search.search_open, pattern=r"^menu:search$"))

    # ─── PRODUTO
    app.add_handler(CallbackQueryHandler(catalog.product_callback, pattern=r"^prod:"))

    # ─── MENU (fallback)
    app.add_handler(CallbackQueryHandler(menu.menu_router))

    # ─── TEXTO LIVRE
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, _text_router))

    return app


# ═══════════════════════════════════════════════
# BOOT
# ═══════════════════════════════════════════════
def main():
    global bot_app

    threading.Thread(target=run_flask, daemon=True).start()
    logger.info("Servidor Flask rodando na porta %s", PORT)

    bot_app = build_app()

    if WEBHOOK_URL:
        logger.info("Rodando via WEBHOOK em %s", WEBHOOK_URL)
        bot_app.run_webhook(
            listen="0.0.0.0",
            port=PORT + 1,
            url_path=BOT_TOKEN,
            webhook_url=f"{WEBHOOK_URL}/{BOT_TOKEN}",
            drop_pending_updates=True,
        )
    else:
        logger.info("Rodando via POLLING")
        bot_app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
