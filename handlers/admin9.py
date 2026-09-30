"""
Módulo ADMIN — GIFT CARDS v2 (completo).
"""
import io
import logging
from datetime import datetime
from telegram import Update, ForceReply, InputFile
from telegram.constants import ParseMode
from telegram.ext import ContextTypes

from config import ADMIN_IDS
from database import db
from keyboards import menus

logger = logging.getLogger(__name__)

GIFTS_PAGE_SIZE = 8


def is_admin(user_id: int) -> bool:
    return user_id in ADMIN_IDS


async def _edit_or_send(query, text: str, kb=None):
    try:
        await query.edit_message_text(text, reply_markup=kb, parse_mode=ParseMode.HTML)
    except Exception:
        try:
            await query.message.reply_text(text, reply_markup=kb, parse_mode=ParseMode.HTML)
        except Exception:
            pass


async def _delete_prompt(context, id_key, chat_key):
    pid = context.user_data.pop(id_key, None)
    chat = context.user_data.pop(chat_key, None)
    if pid and chat:
        try:
            await context.bot.delete_message(chat_id=chat, message_id=pid)
        except Exception:
            pass


async def _edit_prompt_error(context, id_key, chat_key, text, kb=None):
    pid = context.user_data.get(id_key)
    chat = context.user_data.get(chat_key)
    if pid and chat:
        try:
            await context.bot.edit_message_text(
                chat_id=chat, message_id=pid,
                text=text, reply_markup=kb, parse_mode=ParseMode.HTML,
            )
        except Exception:
            pass


# ═══════════════════════════════════════════════
# LISTA
# ═══════════════════════════════════════════════
async def admin_gifts_v2_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not is_admin(update.effective_user.id):
        return
    await _render_gifts(query, filtro="todos", page=0)


async def admin_gifts_page_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not is_admin(update.effective_user.id):
        return
    try:
        _, _, filtro, page = query.data.split(":")
        page = int(page)
    except (ValueError, IndexError):
        return
    await _render_gifts(query, filtro=filtro, page=page)


async def admin_gifts_filtro_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not is_admin(update.effective_user.id):
        return
    try:
        filtro = query.data.split(":")[2]
    except IndexError:
        filtro = "todos"
    await _render_gifts(query, filtro=filtro, page=0)


async def _render_gifts(query, filtro: str = "todos", page: int = 0):
    total = await db.admin_gifts_v2_count(filtro)
    stats = await db.admin_gifts_v2_stats()

    total_pages = max((total + GIFTS_PAGE_SIZE - 1) // GIFTS_PAGE_SIZE, 1)
    page = min(max(page, 0), total_pages - 1)

    gifts = await db.admin_gifts_v2_list(
        filtro=filtro, limit=GIFTS_PAGE_SIZE, offset=page * GIFTS_PAGE_SIZE,
    )

    filtro_label = {
        "todos": "📋 Todos", "livres": "🟢 Livres",
        "resgatados": "🔴 Resgatados", "expirados": "⚫ Expirados",
    }.get(filtro, filtro)

    texto = (
        "🎁 <b>Gerenciar Gift Cards</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"📡 Filtro: <b>{filtro_label}</b>\n\n"
        "📊 <b>Resumo geral:</b>\n"
        f"├ 📦 Total: <b>{stats['total']}</b>\n"
        f"├ 🟢 Livres: <b>{stats['livres']}</b>\n"
        f"├ 🔴 Resgatados: <b>{stats['resgatados']}</b>\n"
        f"├ ⚫ Expirados: <b>{stats['expirados']}</b>\n"
        f"└ 💰 Valor total emitido: <b>R$ {stats['valor_total']:.2f}</b>\n\n"
        f"📄 Página <b>{page + 1}/{total_pages}</b> · {total} gift(s)\n\n"
        "🟢 Livre   🔴 Resgatado   ⚫ Expirado\n\n"
        "👉 Toque em um gift:"
    )

    kb = menus.admin_gifts_v2_kb(gifts, page, total_pages, filtro)
    await _edit_or_send(query, texto, kb)


# ═══════════════════════════════════════════════
# DETALHE
# ═══════════════════════════════════════════════
async def admin_gift_v2_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not is_admin(update.effective_user.id):
        return

    try:
        code = query.data.split(":", 2)[2]
    except (IndexError, ValueError):
        return

    g = await db.get_gift(code)
    if not g:
        await _edit_or_send(query, "❌ Gift não encontrado.", menus.admin_back_kb())
        return

    tipo = g.get("tipo", "—")
    if tipo == "saldo":
        valor_txt = f"💰 R$ {float(g.get('valor') or 0):.2f}"
    elif tipo == "desconto":
        valor_txt = f"💸 {float(g.get('discount_pct') or 0):.0f}% de desconto"
    else:
        valor_txt = f"🎁 Produto ID {g.get('product_id')}"

    resgatado = "✅ Sim" if g.get("redeemed_by") else "❌ Não"

    exp_line = "—"
    exp_status = ""
    if "expires_at" in g.keys() and g.get("expires_at"):
        try:
            exp_dt = datetime.strptime(str(g["expires_at"])[:19], "%Y-%m-%d %H:%M:%S")
            exp_line = exp_dt.strftime("%d/%m/%Y %H:%M")
            if not g.get("redeemed_by"):
                if exp_dt < datetime.now():
                    exp_status = " <b>(EXPIRADO)</b>"
                else:
                    dias = (exp_dt - datetime.now()).days
                    exp_status = f" <i>({dias}d restantes)</i>"
        except Exception:
            exp_line = str(g["expires_at"])

    texto = (
        "🎁 <b>Detalhes do Gift Card</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"🔑 Código: <code>{g['code']}</code>\n"
        f"📦 Tipo: <b>{tipo}</b>\n"
        f"💰 Valor: <b>{valor_txt}</b>\n"
        f"👤 Resgatado: <b>{resgatado}</b>\n\n"
        f"⏰ Expira em: <b>{exp_line}</b>{exp_status}\n"
        f"🕐 Criado: <b>{str(g.get('created_at') or '')[:16]}</b>"
    )

    if g.get("redeemed_by"):
        u = await db.get_user(int(g["redeemed_by"]))
        nome = (u or {}).get("first_name") or (u or {}).get("username") or "—"
        texto += f"\n\n🎯 <b>Resgatado por:</b>\n"
        texto += f"├ Nome: <b>{nome}</b>\n"
        texto += f"├ ID: <code>{g['redeemed_by']}</code>\n"
        texto += f"└ Data: <b>{str(g.get('redeemed_at') or '')[:16]}</b>"

    kb = menus.admin_gift_v2_kb(code, bool(g.get("redeemed_by")))
    await _edit_or_send(query, texto, kb)


# ═══════════════════════════════════════════════
# REVOGAR
# ═══════════════════════════════════════════════
async def admin_gift_revoke_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not is_admin(update.effective_user.id):
        return

    code = query.data.split(":", 2)[2]
    g = await db.get_gift(code)
    if not g:
        return

    texto = (
        "🗑️ <b>Revogar Gift Card?</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"🔑 Código: <code>{code}</code>\n"
        f"💰 Valor: <b>R$ {float(g.get('valor') or 0):.2f}</b>\n\n"
        "⚠️ O código será <b>deletado permanentemente</b>."
    )

    kb = menus.InlineKeyboardMarkup([
        [menus.InlineKeyboardButton("🗑️ Sim, revogar", callback_data=f"admin:gift_revoke_yes:{code}")],
        [menus.InlineKeyboardButton("❌ Cancelar", callback_data=f"admin:gift_v2:{code}")],
    ])
    await _edit_or_send(query, texto, kb)


async def admin_gift_revoke_yes_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not is_admin(update.effective_user.id):
        return

    code = query.data.split(":", 2)[2]
    ok = await db.admin_gift_revoke(code)

    if not ok:
        await query.answer("❌ Não foi possível revogar (já resgatado?)", show_alert=True)
        return

    await db.log_admin_action(update.effective_user.id, "gift_revoke", code)

    await _edit_or_send(
        query,
        f"🗑️ <b>Gift revogado:</b>\n<code>{code}</code>",
        menus.admin_back_kb(),
    )


# ═══════════════════════════════════════════════
# EXPORTAR (um código / todos)
# ═══════════════════════════════════════════════
async def admin_gift_export_one_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not is_admin(update.effective_user.id):
        return

    code = query.data.split(":", 2)[2]
    g = await db.get_gift(code)
    if not g:
        return

    txt = f"{code}\nTipo: {g.get('tipo')}\nValor: R$ {float(g.get('valor') or 0):.2f}"
    if g.get("expires_at"):
        txt += f"\nExpira: {str(g['expires_at'])[:16]}"

    await context.bot.send_document(
        chat_id=query.message.chat_id,
        document=InputFile(io.BytesIO(txt.encode("utf-8")), filename=f"gift-{code}.txt"),
        caption=f"📤 Gift <code>{code}</code> exportado.",
        parse_mode=ParseMode.HTML,
    )


async def admin_gifts_codes_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not is_admin(update.effective_user.id):
        return

    try:
        _, _, filtro = query.data.split(":")
    except ValueError:
        filtro = "livres"

    txt = await db.admin_gifts_export_codes_txt(filtro)
    if not txt:
        await query.answer("📭 Nenhum código nesse filtro.", show_alert=True)
        return

    linhas = txt.splitlines()
    await context.bot.send_document(
        chat_id=query.message.chat_id,
        document=InputFile(
            io.BytesIO(txt.encode("utf-8")),
            filename=f"gifts-{filtro}.txt",
        ),
        caption=(
            f"📄 <b>Códigos exportados</b>\n"
            f"📡 Filtro: <b>{filtro}</b>\n"
            f"📊 Total: <b>{len(linhas)}</b>"
        ),
        parse_mode=ParseMode.HTML,
    )


# ═══════════════════════════════════════════════
# EXPORTAR CSV
# ═══════════════════════════════════════════════
async def admin_gifts_export_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not is_admin(update.effective_user.id):
        return

    try:
        _, _, filtro = query.data.split(":")
    except ValueError:
        filtro = "todos"

    try:
        csv_text = await db.admin_gifts_v2_export_csv(filtro)
        if not csv_text or len(csv_text.splitlines()) <= 1:
            await query.answer("📭 Nenhum gift neste filtro.", show_alert=True)
            return

        await context.bot.send_document(
            chat_id=query.message.chat_id,
            document=InputFile(
                csv_text.encode("utf-8"),
                filename=f"gifts-{filtro}.csv",
            ),
            caption=f"📤 <b>Gifts exportados</b>\n📡 Filtro: <b>{filtro}</b>",
            parse_mode=ParseMode.HTML,
        )
        await db.log_admin_action(update.effective_user.id, "gifts_export", filtro)
    except Exception as e:
        logger.exception("Erro export gifts: %s", e)
        await query.answer(f"❌ Erro: {e}", show_alert=True)


# ═══════════════════════════════════════════════
# BUSCAR
# ═══════════════════════════════════════════════
async def admin_gift_search_prompt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not is_admin(update.effective_user.id):
        return

    context.user_data["admin_gift_search"] = True

    try:
        await query.edit_message_text(
            "🔍 <b>Buscar Gift Card</b>\n\n"
            "Envie o <b>código</b> ou parte dele:",
            reply_markup=ForceReply(selective=True),
            parse_mode=ParseMode.HTML,
        )
    except Exception:
        pass


async def admin_gift_search_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.user_data.get("admin_gift_search"):
        return
    if not is_admin(update.effective_user.id):
        return

    term = (update.message.text or "").strip().upper()

    try:
        await update.message.delete()
    except Exception:
        pass

    context.user_data.pop("admin_gift_search", None)

    if not term:
        return

    resultados = await db.admin_gift_search(term)

    if not resultados:
        await update.message.reply_text(
            f"❌ Nenhum gift com <code>{term}</code>.",
            reply_markup=menus.admin_back_kb(),
            parse_mode=ParseMode.HTML,
        )
        return

    texto = f"🔍 <b>Resultados ({len(resultados)}):</b>"
    kb = menus.admin_gifts_v2_kb(resultados, 0, 1, "todos")
    await update.message.reply_text(texto, reply_markup=kb, parse_mode=ParseMode.HTML)


# ═══════════════════════════════════════════════
# CRIAR GIFT — fluxo passo a passo
# ═══════════════════════════════════════════════
async def admin_gift_create_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not is_admin(update.effective_user.id):
        return

    texto = (
        "➕ <b>Criar Gift Cards</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "Escolha o <b>tipo</b> de gift que será criado:"
    )
    await _edit_or_send(query, texto, menus.admin_gift_create_type_kb())


async def admin_gift_new_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not is_admin(update.effective_user.id):
        return

    tipo = query.data.split(":")[2]

    context.user_data["gift_wizard"] = {"tipo": tipo, "step": "valor"}
    context.user_data["_gift_prompt_id"] = query.message.message_id
    context.user_data["_gift_prompt_chat"] = query.message.chat_id

    if tipo == "saldo":
        texto = (
            "💰 <b>Gift de Saldo</b>\n"
            "━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "Passo <b>1/4</b> — Valor\n\n"
            "Envie o <b>valor</b> de cada gift (ex: <code>10.00</code>):\n\n"
            "Envie <code>/cancelar</code> para sair."
        )
    elif tipo == "produto":
        texto = (
            "🎁 <b>Gift de Produto</b>\n"
            "━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "Passo <b>1/4</b> — ID do produto\n\n"
            "Envie o <b>ID do produto</b> que será dado de presente (ex: <code>1</code>):\n\n"
            "Envie <code>/cancelar</code> para sair."
        )
    else:  # desconto
        texto = (
            "💸 <b>Gift de Desconto %</b>\n"
            "━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "Passo <b>1/4</b> — Percentual\n\n"
            "Envie o <b>percentual de desconto</b> (ex: <code>15</code> para 15%):\n\n"
            "Envie <code>/cancelar</code> para sair."
        )

    try:
        await query.edit_message_text(
            texto,
            reply_markup=ForceReply(selective=True),
            parse_mode=ParseMode.HTML,
        )
    except Exception:
        pass


async def admin_gift_wizard_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    wiz = context.user_data.get("gift_wizard")
    if not wiz:
        return
    if not is_admin(update.effective_user.id):
        return

    texto = (update.message.text or "").strip()

    try:
        await update.message.delete()
    except Exception:
        pass

    if texto.startswith("/"):
        context.user_data.pop("gift_wizard", None)
        await _delete_prompt(context, "_gift_prompt_id", "_gift_prompt_chat")
        return

    step = wiz.get("step")
    tipo = wiz.get("tipo")

    # ─── PASSO 1: valor/ID/percentual
    if step == "valor":
        if tipo == "saldo":
            try:
                v = float(texto.replace(",", "."))
                if v <= 0:
                    raise ValueError
            except ValueError:
                await _edit_prompt_error(
                    context, "_gift_prompt_id", "_gift_prompt_chat",
                    "❌ Valor inválido.\n\nEnvie um número positivo (ex: <code>10.00</code>):",
                    ForceReply(selective=True),
                )
                return
            wiz["valor"] = v
            wiz["product_id"] = None
            wiz["discount_pct"] = None

        elif tipo == "produto":
            try:
                pid = int(texto)
                prod = await db.get_product(pid)
                if not prod:
                    await _edit_prompt_error(
                        context, "_gift_prompt_id", "_gift_prompt_chat",
                        f"❌ Produto ID <code>{pid}</code> não encontrado.\n\n"
                        "Tente outro ID:",
                        ForceReply(selective=True),
                    )
                    return
            except ValueError:
                await _edit_prompt_error(
                    context, "_gift_prompt_id", "_gift_prompt_chat",
                    "❌ ID inválido.\n\nEnvie um número inteiro:",
                    ForceReply(selective=True),
                )
                return
            wiz["valor"] = 0
            wiz["product_id"] = pid
            wiz["discount_pct"] = None
            wiz["produto_nome"] = prod["name"]

        else:  # desconto
            try:
                pct = float(texto.replace(",", "."))
                if pct <= 0 or pct > 100:
                    raise ValueError
            except ValueError:
                await _edit_prompt_error(
                    context, "_gift_prompt_id", "_gift_prompt_chat",
                    "❌ Percentual inválido.\n\nEnvie entre 1 e 100:",
                    ForceReply(selective=True),
                )
                return
            wiz["valor"] = 0
            wiz["product_id"] = None
            wiz["discount_pct"] = pct

        wiz["step"] = "validade"
        await _edit_prompt_error(
            context, "_gift_prompt_id", "_gift_prompt_chat",
            "Passo <b>2/4</b> — Validade\n\n"
            "Em quantos <b>dias</b> o gift expira?\n\n"
            "💡 Envie <code>0</code> ou <code>sem</code> para <b>não expirar</b>.\n\n"
            "Exemplos: <code>7</code>, <code>30</code>, <code>90</code>",
            ForceReply(selective=True),
        )
        return

    # ─── PASSO 2: validade
    if step == "validade":
        if texto.lower() in ("0", "sem", "nunca", "no"):
            wiz["expires_days"] = None
        else:
            try:
                dias = int(texto)
                if dias <= 0:
                    raise ValueError
            except ValueError:
                await _edit_prompt_error(
                    context, "_gift_prompt_id", "_gift_prompt_chat",
                    "❌ Valor inválido.\n\nEnvie um número de dias (ex: <code>30</code>) "
                    "ou <code>0</code> para sem validade:",
                    ForceReply(selective=True),
                )
                return
            wiz["expires_days"] = dias

        wiz["step"] = "prefixo"
        await _edit_prompt_error(
            context, "_gift_prompt_id", "_gift_prompt_chat",
            "Passo <b>3/4</b> — Prefixo\n\n"
            "Qual o <b>prefixo</b> dos códigos?\n\n"
            "💡 Ex: <code>PROMO</code>, <code>LARI</code>, <code>BLACK</code>\n\n"
            "Os códigos ficarão: <code>PREFIXO-XXXXXX</code>",
            ForceReply(selective=True),
        )
        return

    # ─── PASSO 3: prefixo
    if step == "prefixo":
        prefixo = texto.upper().replace(" ", "").replace("-", "")
        if len(prefixo) < 2 or len(prefixo) > 12:
            await _edit_prompt_error(
                context, "_gift_prompt_id", "_gift_prompt_chat",
                "❌ Prefixo inválido (2 a 12 caracteres).\n\nTente novamente:",
                ForceReply(selective=True),
            )
            return

        wiz["prefixo"] = prefixo
        wiz["step"] = "quantidade"
        await _edit_prompt_error(
            context, "_gift_prompt_id", "_gift_prompt_chat",
            "Passo <b>4/4</b> — Quantidade\n\n"
            "Quantos códigos devo criar?\n\n"
            "💡 Máximo: <b>500</b>\n\n"
            "Exemplo: <code>10</code>",
            ForceReply(selective=True),
        )
        return

    # ─── PASSO 4: quantidade
    if step == "quantidade":
        try:
            qtd = int(texto)
            if qtd <= 0 or qtd > 500:
                raise ValueError
        except ValueError:
            await _edit_prompt_error(
                context, "_gift_prompt_id", "_gift_prompt_chat",
                "❌ Quantidade inválida (1 a 500).\n\nTente novamente:",
                ForceReply(selective=True),
            )
            return

        wiz["quantidade"] = qtd
        context.user_data.pop("gift_wizard", None)

        tipo_txt = {
            "saldo": "💰 Saldo",
            "produto": f"🎁 Produto: {wiz.get('produto_nome', '?')}",
            "desconto": f"💸 Desconto: {wiz['discount_pct']:.0f}%",
        }[tipo]

        val_txt = (
            f"R$ {wiz.get('valor', 0):.2f}"
            if tipo == "saldo"
            else "—"
        )
        exp_txt = (
            f"{wiz['expires_days']} dias"
            if wiz.get("expires_days")
            else "Sem validade"
        )

        preview = (
            "✅ <b>Confirmação</b>\n"
            "━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"📦 Tipo: <b>{tipo_txt}</b>\n"
            f"💰 Valor: <b>{val_txt}</b>\n"
            f"⏰ Validade: <b>{exp_txt}</b>\n"
            f"🏷️ Prefixo: <code>{wiz['prefixo']}</code>\n"
            f"🔢 Quantidade: <b>{wiz['quantidade']}</b>\n\n"
            "Confirma a criação?"
        )

        context.user_data["gift_preview_data"] = wiz

        await _edit_prompt_error(
            context, "_gift_prompt_id", "_gift_prompt_chat",
            preview,
            menus.admin_gift_preview_kb(),
        )
        return


async def admin_gift_confirm_create_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not is_admin(update.effective_user.id):
        return

    wiz = context.user_data.pop("gift_preview_data", None)
    if not wiz:
        await query.answer("Dados expirados, crie novamente.", show_alert=True)
        return

    await _delete_prompt(context, "_gift_prompt_id", "_gift_prompt_chat")

    try:
        codigos = await db.admin_gift_create_full(
            code_base=wiz["prefixo"],
            quantidade=wiz["quantidade"],
            tipo=wiz["tipo"],
            valor=wiz.get("valor", 0),
            product_id=wiz.get("product_id"),
            discount_pct=wiz.get("discount_pct"),
            expires_days=wiz.get("expires_days"),
        )
    except Exception as e:
        logger.exception("Erro criando gifts: %s", e)
        await query.message.reply_text(f"❌ Erro: {e}")
        return

    await db.log_admin_action(
        update.effective_user.id, "gift_create_batch",
        wiz["tipo"], f"qtd={len(codigos)} prefix={wiz['prefixo']}",
    )

    lista = "\n".join(f"<code>{c}</code>" for c in codigos[:30])
    extra = f"\n\n<i>... e mais {len(codigos) - 30} códigos.</i>" if len(codigos) > 30 else ""

    texto = (
        f"✅ <b>{len(codigos)} Gift Cards criados!</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"📦 Tipo: <b>{wiz['tipo']}</b>\n"
        f"🏷️ Prefixo: <code>{wiz['prefixo']}</code>\n\n"
        f"🔑 <b>Códigos:</b>\n{lista}{extra}"
    )

    try:
        await query.edit_message_text(texto, reply_markup=menus.admin_back_kb(), parse_mode=ParseMode.HTML)
    except Exception:
        await query.message.reply_text(texto, reply_markup=menus.admin_back_kb(), parse_mode=ParseMode.HTML)

    try:
        txt = "\n".join(codigos)
        await context.bot.send_document(
            chat_id=query.message.chat_id,
            document=InputFile(
                io.BytesIO(txt.encode("utf-8")),
                filename=f"gifts-{wiz['prefixo']}.txt",
            ),
            caption="📄 Arquivo com todos os códigos",
        )
    except Exception:
        pass
