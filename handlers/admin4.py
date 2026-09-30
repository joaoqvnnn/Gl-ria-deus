"""
Módulo ADMIN — Produtos + Estoque (completo e real).

Funcionalidades:
  • Lista com paginação e resumo
  • Detalhe do produto com todas as métricas
  • Criar produto passo a passo
  • Editar cada campo individualmente
  • Clonar produto
  • Preço promocional (De/Por)
  • Categoria
  • Upload de imagem
  • Estoque: adicionar, importar .txt, ver, remover específica, limpar, exportar
  • Ativar/desativar/remover
"""
import io
import logging
from telegram import Update, ForceReply, InputFile
from telegram.constants import ParseMode
from telegram.ext import ContextTypes

from config import ADMIN_IDS
from database import db
from keyboards import menus

logger = logging.getLogger(__name__)

PAGE_SIZE = 8
_ZERO = "\u200b"


def is_admin(user_id: int) -> bool:
    return user_id in ADMIN_IDS


async def _edit_or_send(query, text: str, kb=None):
    try:
        await query.edit_message_text(text, reply_markup=kb, parse_mode=ParseMode.HTML)
    except Exception:
        await query.message.reply_text(text, reply_markup=kb, parse_mode=ParseMode.HTML)


async def _delete_prompt(context, id_key: str, chat_key: str):
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
# LISTA DE PRODUTOS (com paginação)
# ═══════════════════════════════════════════════
async def admin_products_v3_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not is_admin(update.effective_user.id):
        return
    await _show_products_page(query, context, page=0)


async def admin_products_page_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not is_admin(update.effective_user.id):
        return
    try:
        page = int(query.data.split(":")[2])
    except (IndexError, ValueError):
        page = 0
    await _show_products_page(query, context, page=page)


async def _show_products_page(query, context, page: int = 0):
    total = await db.admin_count_products_total()
    total_pages = max((total + PAGE_SIZE - 1) // PAGE_SIZE, 1)
    page = min(max(page, 0), total_pages - 1)
    offset = page * PAGE_SIZE

    produtos = await db.admin_all_products(limit=PAGE_SIZE, offset=offset)

    ativos = sum(1 for p in produtos if p.get("active"))
    estoque_total = sum(int(p.get("stock") or 0) for p in produtos)

    texto = (
        "📦 <b>Gerenciar Produtos</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"📊 <b>Resumo:</b>\n"
        f"├ Total de produtos: <b>{total}</b>\n"
        f"├ Ativos nesta página: <b>{ativos}</b>\n"
        f"└ Estoque nesta página: <b>{estoque_total}</b>\n\n"
        f"📄 Página <b>{page + 1}/{total_pages}</b>\n\n"
        "🟢 Ativo   🔴 Inativo   💸 Promoção\n"
        "👉 Toque em um produto para gerenciar:"
    )

    await _edit_or_send(query, texto, menus.admin_products_v3_kb(produtos, page, total_pages))


# ═══════════════════════════════════════════════
# DETALHE DO PRODUTO
# ═══════════════════════════════════════════════
async def admin_product_v3_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not is_admin(update.effective_user.id):
        return

    try:
        pid = int(query.data.split(":")[2])
    except (IndexError, ValueError):
        return

    p = await db.get_product(pid)
    if not p:
        await _edit_or_send(query, "❌ Produto não encontrado.", menus.admin_back_kb())
        return

    stats = await db.admin_stock_stats(pid)

    promo = p.get("promo_price")
    if promo:
        promo_line = f"├ 💸 Promoção: <b>R$ {float(promo):.2f}</b>\n"
    else:
        promo_line = "├ 💸 Promoção: <i>sem promoção</i>\n"

    cat = p.get("category") or "—"
    img = "✅" if p.get("image_url") else "❌"

    texto = (
        f"📦 <b>{p['name']}</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"📡 Status: <b>{'🟢 Ativo' if p.get('active') else '🔴 Inativo'}</b>\n\n"
        "💰 <b>Preço:</b>\n"
        f"├ Normal: <b>R$ {float(p['price']):.2f}</b>\n"
        f"{promo_line}"
        "\n"
        "📦 <b>Estoque:</b>\n"
        f"├ Total de contas: <b>{stats['total']}</b>\n"
        f"├ 🟢 Disponíveis: <b>{stats['disponiveis']}</b>\n"
        f"└ 🔴 Usadas: <b>{stats['usadas']}</b>\n\n"
        "📊 <b>Vendas:</b>\n"
        f"├ Vendidos: <b>{p.get('sold', 0)}</b>\n"
        f"└ Receita: <b>R$ {float(p['price']) * int(p.get('sold') or 0):.2f}</b>\n\n"
        "⚙️ <b>Config:</b>\n"
        f"├ 😀 Emoji: <b>{p.get('emoji') or '📦'}</b>\n"
        f"├ 🛡 Garantia: <b>{p.get('guarantee', 180)} dias</b>\n"
        f"├ 📁 Categoria: <b>{cat}</b>\n"
        f"├ 🖼 Imagem: {img}\n"
        f"└ 🔗 Link: <code>{(p.get('activate_url') or '')[:50]}</code>\n\n"
        f"📝 <b>Descrição:</b>\n<i>{(p.get('description') or '')[:250]}</i>"
    )

    kb = menus.admin_product_v3_kb(pid, bool(p.get("active")), bool(promo))
    await _edit_or_send(query, texto, kb)


# ═══════════════════════════════════════════════
# EDITAR CAMPO
# ═══════════════════════════════════════════════
_LABELS = {
    "name":         "📝 Nome do produto",
    "description":  "📄 Descrição",
    "price":        "💰 Preço (ex: 19.90)",
    "stock":        "📦 Estoque (número inteiro)",
    "emoji":        "😀 Emoji (ex: 🎬)",
    "guarantee":    "🛡 Garantia em dias",
    "activate_url": "🔗 Link de ativação (URL completa)",
    "category":     "📁 Categoria (ex: Filmes, IPTV, Música)",
}


async def admin_prod_edit_prompt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not is_admin(update.effective_user.id):
        return

    parts = query.data.split(":")
    try:
        pid = int(parts[2])
        campo = parts[3]
    except (IndexError, ValueError):
        return

    p = await db.get_product(pid)
    if not p:
        return

    context.user_data["admin_prod_edit"] = {"pid": pid, "campo": campo}
    context.user_data["_prod_edit_prompt_id"] = query.message.message_id
    context.user_data["_prod_edit_prompt_chat"] = query.message.chat_id

    valor_atual = str(p.get(campo) or "—")
    if campo == "description" and len(valor_atual) > 100:
        valor_atual = valor_atual[:100] + "..."
    if campo == "activate_url" and len(valor_atual) > 60:
        valor_atual = valor_atual[:60] + "..."

    try:
        await query.edit_message_text(
            f"✏️ <b>Editando: {_LABELS.get(campo, campo)}</b>\n\n"
            f"Valor atual: <code>{valor_atual}</code>\n\n"
            "Envie o novo valor (ou <code>/cancelar</code>):",
            reply_markup=menus.admin_back_kb(),
            parse_mode=ParseMode.HTML,
        )
    except Exception:
        pass


async def admin_prod_edit_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    info = context.user_data.get("admin_prod_edit")
    if not info:
        return
    if not is_admin(update.effective_user.id):
        return

    texto = (update.message.text or "").strip()

    try:
        await update.message.delete()
    except Exception:
        pass

    if texto.startswith("/"):
        await _delete_prompt(context, "_prod_edit_prompt_id", "_prod_edit_prompt_chat")
        context.user_data.pop("admin_prod_edit", None)
        return

    if not texto:
        await _edit_prompt_error(
            context,
            "_prod_edit_prompt_id", "_prod_edit_prompt_chat",
            "❌ Valor vazio.\n\nEnvie o novo valor:",
            menus.admin_back_kb(),
        )
        return

    pid = info["pid"]
    campo = info["campo"]

    try:
        if campo == "price":
            valor = float(texto.replace(",", "."))
            if valor <= 0:
                raise ValueError
        elif campo in ("stock", "guarantee"):
            valor = int(texto)
            if valor < 0:
                raise ValueError
        else:
            valor = texto
    except ValueError:
        await _edit_prompt_error(
            context,
            "_prod_edit_prompt_id", "_prod_edit_prompt_chat",
            f"❌ Valor inválido para <b>{_LABELS.get(campo, campo)}</b>.\n\n"
            "Tente novamente:",
            menus.admin_back_kb(),
        )
        return

    context.user_data.pop("admin_prod_edit", None)
    await _delete_prompt(context, "_prod_edit_prompt_id", "_prod_edit_prompt_chat")

    await db.admin_update_product(pid, **{campo: valor})
    await db.log_admin_action(
        update.effective_user.id, f"prod_edit_{campo}", str(pid), str(valor)[:60]
    )

    await _show_product_after_edit(update, context, pid)


async def _show_product_after_edit(update, context, pid: int):
    p = await db.get_product(pid)
    if not p:
        return
    stats = await db.admin_stock_stats(pid)
    promo = p.get("promo_price")

    promo_line = f"├ 💸 Promoção: <b>R$ {float(promo):.2f}</b>\n" if promo else "├ 💸 Promoção: <i>sem promoção</i>\n"

    texto = (
        f"📦 <b>{p['name']}</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"📡 Status: <b>{'🟢 Ativo' if p.get('active') else '🔴 Inativo'}</b>\n\n"
        "💰 <b>Preço:</b>\n"
        f"├ Normal: <b>R$ {float(p['price']):.2f}</b>\n"
        f"{promo_line}\n"
        "📦 <b>Estoque:</b>\n"
        f"├ Total: <b>{stats['total']}</b>\n"
        f"├ 🟢 Disponíveis: <b>{stats['disponiveis']}</b>\n"
        f"└ 🔴 Usadas: <b>{stats['usadas']}</b>\n\n"
        f"✅ <b>Produto atualizado!</b>"
    )

    kb = menus.admin_product_v3_kb(pid, bool(p.get("active")), bool(promo))
    try:
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=texto, reply_markup=kb, parse_mode=ParseMode.HTML,
        )
    except Exception:
        pass


# ═══════════════════════════════════════════════
# PROMOÇÃO (De/Por)
# ═══════════════════════════════════════════════
async def admin_prod_promo_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not is_admin(update.effective_user.id):
        return

    pid = int(query.data.split(":")[2])
    p = await db.get_product(pid)
    if not p:
        return

    promo = p.get("promo_price")
    promo_txt = f"R$ {float(promo):.2f}" if promo else "—"

    context.user_data["admin_prod_promo"] = pid
    context.user_data["_prod_promo_prompt_id"] = query.message.message_id
    context.user_data["_prod_promo_prompt_chat"] = query.message.chat_id

    try:
        await query.edit_message_text(
            f"💸 <b>Promoção — {p['name']}</b>\n"
            "━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"💰 Preço normal: <b>R$ {float(p['price']):.2f}</b>\n"
            f"💸 Promoção atual: <b>{promo_txt}</b>\n\n"
            "Envie o novo preço promocional (ex: <code>9.90</code>)\n\n"
            "💡 Envie <code>0</code> ou <code>remover</code> para remover a promoção.",
            reply_markup=menus.admin_back_kb(),
            parse_mode=ParseMode.HTML,
        )
    except Exception:
        pass


async def admin_prod_promo_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    pid = context.user_data.get("admin_prod_promo")
    if not pid:
        return
    if not is_admin(update.effective_user.id):
        return

    texto = (update.message.text or "").strip().lower()

    try:
        await update.message.delete()
    except Exception:
        pass

    if texto.startswith("/"):
        await _delete_prompt(context, "_prod_promo_prompt_id", "_prod_promo_prompt_chat")
        context.user_data.pop("admin_prod_promo", None)
        return

    if texto in ("0", "remover", "remova", "excluir"):
        await db.admin_update_product(pid, promo_price=None)
        context.user_data.pop("admin_prod_promo", None)
        await _delete_prompt(context, "_prod_promo_prompt_id", "_prod_promo_prompt_chat")
        await _show_product_after_edit(update, context, pid)
        return

    try:
        valor = float(texto.replace(",", ".").replace("r$", "").strip())
        if valor <= 0:
            raise ValueError
    except ValueError:
        await _edit_prompt_error(
            context,
            "_prod_promo_prompt_id", "_prod_promo_prompt_chat",
            "❌ Valor inválido.\n\nEnvie um número positivo (ex: <code>9.90</code>) "
            "ou <code>0</code> para remover.",
            menus.admin_back_kb(),
        )
        return

    await db.admin_update_product(pid, promo_price=valor)
    await db.log_admin_action(update.effective_user.id, "prod_promo", str(pid), f"R$ {valor:.2f}")

    context.user_data.pop("admin_prod_promo", None)
    await _delete_prompt(context, "_prod_promo_prompt_id", "_prod_promo_prompt_chat")
    await _show_product_after_edit(update, context, pid)


# ═══════════════════════════════════════════════
# CLONAR PRODUTO
# ═══════════════════════════════════════════════
async def admin_prod_clone_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not is_admin(update.effective_user.id):
        return

    pid = int(query.data.split(":")[2])
    new_pid = await db.admin_clone_product(pid)

    if not new_pid:
        await query.answer("❌ Produto não encontrado.", show_alert=True)
        return

    await db.log_admin_action(update.effective_user.id, "prod_clone", str(pid), f"novo={new_pid}")

    p = await db.get_product(pid)
    novo = await db.get_product(new_pid)

    texto = (
        "📋 <b>Produto Clonado!</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"📦 Original: <b>{p['name']}</b>\n"
        f"🆕 Novo: <b>{novo['name']}</b>\n\n"
        f"🆔 Novo ID: <code>{new_pid}</code>\n\n"
        "💡 <i>O estoque NÃO é copiado por segurança.</i>\n"
        "Adicione contas no novo produto quando quiser."
    )

    kb = menus.InlineKeyboardMarkup([
        [menus.InlineKeyboardButton("📦 Ver novo produto", callback_data=f"admin:product:{new_pid}")],
        [menus.InlineKeyboardButton("⬅️ Voltar", callback_data="admin:products")],
    ])
    await _edit_or_send(query, texto, kb)


# ═══════════════════════════════════════════════
# IMAGEM DO PRODUTO
# ═══════════════════════════════════════════════
async def admin_prod_img_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not is_admin(update.effective_user.id):
        return

    pid = int(query.data.split(":")[2])
    p = await db.get_product(pid)
    if not p:
        return

    context.user_data["admin_prod_img"] = pid

    try:
        await query.edit_message_text(
            f"🖼 <b>Imagem do produto — {p['name']}</b>\n"
            "━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "📸 Envie a <b>foto</b> do produto agora.\n\n"
            "💡 Também aceito <b>URL</b> de imagem como texto.\n\n"
            "Envie <code>/cancelar</code> para sair.",
            reply_markup=menus.admin_back_kb(),
            parse_mode=ParseMode.HTML,
        )
    except Exception:
        pass


async def admin_prod_img_photo_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    pid = context.user_data.get("admin_prod_img")
    if not pid:
        return
    if not is_admin(update.effective_user.id):
        return

    file_id = None
    if update.message.photo:
        file_id = update.message.photo[-1].file_id
    elif update.message.document:
        file_id = update.message.document.file_id

    if not file_id:
        return

    context.user_data.pop("admin_prod_img", None)
    await db.admin_update_product(pid, image_url=file_id)
    await db.log_admin_action(update.effective_user.id, "prod_img", str(pid))
    await update.message.reply_text("✅ Imagem atualizada!")


async def admin_prod_img_text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    pid = context.user_data.get("admin_prod_img")
    if not pid:
        return
    if not is_admin(update.effective_user.id):
        return

    texto = (update.message.text or "").strip()

    try:
        await update.message.delete()
    except Exception:
        pass

    if texto.startswith("/"):
        context.user_data.pop("admin_prod_img", None)
        return

    if not (texto.startswith("http://") or texto.startswith("https://")):
        await update.message.reply_text(
            "❌ Envie uma foto ou uma URL que comece com http:// ou https://"
        )
        return

    context.user_data.pop("admin_prod_img", None)
    await db.admin_update_product(pid, image_url=texto)
    await db.log_admin_action(update.effective_user.id, "prod_img", str(pid))
    await update.message.reply_text("✅ URL da imagem atualizada!")


# ═══════════════════════════════════════════════
# CRIAR PRODUTO (WIZARD)
# ═══════════════════════════════════════════════
_STEPS = [
    ("name",         "📝 <b>Nome do produto</b>\n\nEnvie o nome (ex: <code>Netflix 4K</code>):"),
    ("description",  "📄 <b>Descrição</b>\n\nEnvie a descrição (pode ter várias linhas):"),
    ("price",        "💰 <b>Preço</b>\n\nEnvie em reais (ex: <code>19.90</code>):"),
    ("stock",        "📦 <b>Estoque inicial</b>\n\nEnvie a quantidade (ex: <code>10</code>):"),
    ("emoji",        "😀 <b>Emoji</b>\n\nUm emoji pro produto (ex: <code>🎬</code>):"),
    ("guarantee",    "🛡 <b>Garantia</b>\n\nEm dias (ex: <code>30</code>):"),
    ("category",     "📁 <b>Categoria</b>\n\nEx: <code>Filmes</code>, <code>IPTV</code>, <code>Música</code>:"),
    ("activate_url", "🔗 <b>Link de ativação</b>\n\nURL completa (ex: <code>https://t.me/</code>):"),
]


async def admin_new_product_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not is_admin(update.effective_user.id):
        return

    context.user_data["admin_new_prod"] = {"dados": {}, "step": 0}

    try:
        await query.edit_message_text(
            "➕ <b>Criar novo produto</b>\n"
            "━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"Passo <b>1/{len(_STEPS)}</b>\n\n"
            f"{_STEPS[0][1]}\n\n"
            "<i>Envie /cancelar para sair.</i>",
            parse_mode=ParseMode.HTML,
        )
    except Exception:
        pass


async def admin_new_product_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    state = context.user_data.get("admin_new_prod")
    if not state:
        return
    if not is_admin(update.effective_user.id):
        return

    texto = update.message.text or update.message.caption or ""

    if texto.startswith("/"):
        context.user_data.pop("admin_new_prod", None)
        await update.message.reply_text("❌ Criação cancelada.")
        return

    texto = texto.strip()
    if not texto:
        await update.message.reply_text("❌ Valor vazio. Tente novamente.")
        return

    step = state["step"]
    campo = _STEPS[step][0]
    dados = state["dados"]

    try:
        if campo == "price":
            valor = float(texto.replace(",", "."))
            if valor <= 0:
                raise ValueError
        elif campo in ("stock", "guarantee"):
            valor = int(texto)
            if valor < 0:
                raise ValueError
        else:
            valor = texto
    except ValueError:
        await update.message.reply_text("❌ Valor inválido. Tente novamente.")
        return

    dados[campo] = valor
    step += 1

    if step < len(_STEPS):
        state["step"] = step
        state["dados"] = dados

        await update.message.reply_text(
            f"Passo <b>{step + 1}/{len(_STEPS)}</b>\n\n{_STEPS[step][1]}",
            reply_markup=ForceReply(selective=True),
            parse_mode=ParseMode.HTML,
        )
        return

    context.user_data.pop("admin_new_prod", None)

    try:
        pid = await db.admin_create_product(
            name=dados["name"],
            description=dados["description"],
            price=dados["price"],
            stock=dados["stock"],
            emoji=dados.get("emoji") or "📦",
            guarantee=dados.get("guarantee") or 180,
            activate_url=dados.get("activate_url") or "https://t.me/",
        )
        if dados.get("category"):
            await db.admin_update_product(pid, category=dados["category"])
    except Exception as e:
        logger.exception("Erro criando produto: %s", e)
        await update.message.reply_text(f"❌ Erro ao criar: {e}")
        return

    await db.log_admin_action(update.effective_user.id, "product_create", str(pid))

    kb = menus.InlineKeyboardMarkup([
        [menus.InlineKeyboardButton("📦 Ver produto", callback_data=f"admin:product:{pid}")],
        [menus.InlineKeyboardButton("⬅️ Voltar", callback_data="admin:products")],
    ])
    await update.message.reply_text(
        "✅ <b>Produto criado!</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"🆔 ID: <code>{pid}</code>\n"
        f"📝 Nome: <b>{dados['name']}</b>\n"
        f"💰 Preço: <b>R$ {dados['price']:.2f}</b>\n"
        f"📦 Estoque: <b>{dados['stock']}</b>",
        reply_markup=kb,
        parse_mode=ParseMode.HTML,
    )


# ═══════════════════════════════════════════════
# ESTOQUE — GERENCIAR
# ═══════════════════════════════════════════════
async def admin_prod_stock_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not is_admin(update.effective_user.id):
        return

    pid = int(query.data.split(":")[2])
    p = await db.get_product(pid)
    if not p:
        return

    stats = await db.admin_stock_stats(pid)

    texto = (
        f"📥 <b>Estoque — {p['name']}</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"📊 Total no banco: <b>{stats['total']}</b>\n"
        f"🟢 Disponíveis: <b>{stats['disponiveis']}</b>\n"
        f"🔴 Usadas: <b>{stats['usadas']}</b>\n\n"
        f"📦 Campo <code>stock</code> do produto: <b>{p['stock']}</b>\n\n"
        "Escolha uma ação:"
    )
    await _edit_or_send(query, texto, menus.admin_product_stock_v3_kb(pid))


async def admin_stock_add_prompt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not is_admin(update.effective_user.id):
        return

    pid = int(query.data.split(":")[2])
    context.user_data["admin_stock_add"] = pid

    try:
        await query.edit_message_text(
            "📥 <b>Adicionar contas ao estoque</b>\n"
            "━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "Envie uma ou mais contas, uma por linha:\n\n"
            "<code>email@exemplo.com:senha123\n"
            "conta2@x.com:abc456</code>\n\n"
            "💡 Aceito também separador <code>|</code>.\n\n"
            "Envie /cancelar para sair.",
            reply_markup=ForceReply(selective=True),
            parse_mode=ParseMode.HTML,
        )
    except Exception:
        pass


async def admin_stock_add_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    pid = context.user_data.get("admin_stock_add")
    if not pid:
        return
    if not is_admin(update.effective_user.id):
        return

    texto = update.message.text or ""

    if texto.startswith("/"):
        context.user_data.pop("admin_stock_add", None)
        await update.message.reply_text("❌ Cancelado.")
        return

    contas, invalidas = _parse_contas(texto)

    if not contas:
        await update.message.reply_text(
            "❌ Nenhuma conta válida.\n"
            "Use o formato: <code>email:senha</code> (uma por linha)",
            parse_mode=ParseMode.HTML,
        )
        return

    context.user_data.pop("admin_stock_add", None)

    qtd = await db.admin_add_stock_batch(pid, contas)
    await db.log_admin_action(update.effective_user.id, "stock_add", str(pid), f"qtd={qtd}")

    p = await db.get_product(pid)

    await update.message.reply_text(
        f"✅ <b>{qtd} contas adicionadas!</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"📦 Produto: <b>{p['name']}</b>\n"
        f"📊 Novo estoque: <b>{p['stock']}</b>\n"
        + (f"\n⚠️ {invalidas} linha(s) inválida(s) ignorada(s)." if invalidas else ""),
        reply_markup=menus.admin_back_kb(),
        parse_mode=ParseMode.HTML,
    )


async def admin_stock_import_prompt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not is_admin(update.effective_user.id):
        return

    pid = int(query.data.split(":")[2])
    context.user_data["admin_stock_import"] = pid

    try:
        await query.edit_message_text(
            "📄 <b>Importar contas via arquivo .txt</b>\n"
            "━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "Envie um arquivo <b>.txt</b> com uma conta por linha:\n\n"
            "<code>email@exemplo.com:senha123\n"
            "conta2@x.com:abc456</code>\n\n"
            "💡 Aceito também <code>|</code> como separador.\n\n"
            "Envie /cancelar para sair.",
            reply_markup=menus.admin_back_kb(),
            parse_mode=ParseMode.HTML,
        )
    except Exception:
        pass


async def admin_stock_import_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    pid = context.user_data.get("admin_stock_import")
    if not pid:
        return
    if not is_admin(update.effective_user.id):
        return

    doc = update.message.document
    if not doc:
        return

    try:
        file = await context.bot.get_file(doc.file_id)
        data = await file.download_as_bytearray()
        conteudo = data.decode("utf-8", errors="ignore")
    except Exception as e:
        logger.exception("Erro baixando arquivo: %s", e)
        await update.message.reply_text("❌ Falha ao baixar o arquivo.")
        return

    contas, invalidas = _parse_contas(conteudo)

    if not contas:
        await update.message.reply_text(
            "❌ Nenhuma conta válida no arquivo.\n"
            "Formato esperado: <code>email:senha</code> por linha.",
            parse_mode=ParseMode.HTML,
        )
        return

    context.user_data.pop("admin_stock_import", None)

    qtd = await db.admin_add_stock_batch(pid, contas)
    await db.log_admin_action(update.effective_user.id, "stock_import", str(pid), f"qtd={qtd}")

    p = await db.get_product(pid)

    await update.message.reply_text(
        f"✅ <b>{qtd} contas importadas!</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"📦 Produto: <b>{p['name']}</b>\n"
        f"📊 Novo estoque: <b>{p['stock']}</b>\n"
        + (f"\n⚠️ {invalidas} linha(s) inválida(s)." if invalidas else ""),
        reply_markup=menus.admin_back_kb(),
        parse_mode=ParseMode.HTML,
    )


async def admin_stock_view_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not is_admin(update.effective_user.id):
        return

    pid = int(query.data.split(":")[2])
    contas = await db.admin_list_stock(pid, only_available=True)

    if not contas:
        texto = "👀 <b>Contas disponíveis</b>\n\n<i>Nenhuma conta disponível.</i>"
    else:
        bloco = contas[:25]
        linhas = [f"👀 <b>Disponíveis ({len(contas)})</b>\n"]
        for c in bloco:
            email = c.get("email") or "—"
            senha = c.get("password") or "—"
            linhas.append(f"📧 <code>{email}</code>\n🔑 <code>{senha}</code>\n")
        if len(contas) > 25:
            linhas.append(f"\n<i>... e mais {len(contas) - 25} contas.</i>")
        texto = "\n".join(linhas)

    await _edit_or_send(query, texto, menus.admin_product_stock_v3_kb(pid))


async def admin_stock_view_used_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not is_admin(update.effective_user.id):
        return

    pid = int(query.data.split(":")[2])

    cur = await db._db.execute(
        "SELECT * FROM stock_items WHERE product_id = ? AND used = 1 ORDER BY id DESC LIMIT 25",
        (pid,),
    )
    rows = [dict(r) for r in await cur.fetchall()]

    cur = await db._db.execute(
        "SELECT COUNT(*) AS c FROM stock_items WHERE product_id = ? AND used = 1", (pid,)
    )
    total = int((await cur.fetchone())["c"])

    if not rows:
        texto = "🔴 <b>Contas usadas</b>\n\n<i>Nenhuma conta usada ainda.</i>"
    else:
        linhas = [f"🔴 <b>Usadas ({total})</b> — últimas 25\n"]
        for c in rows:
            linhas.append(f"📧 <code>{c.get('email') or '—'}</code>")
        texto = "\n".join(linhas)

    await _edit_or_send(query, texto, menus.admin_product_stock_v3_kb(pid))


async def admin_stock_remove_prompt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not is_admin(update.effective_user.id):
        return

    pid = int(query.data.split(":")[2])
    context.user_data["admin_stock_remove"] = pid

    try:
        await query.edit_message_text(
            "🗑️ <b>Remover conta específica</b>\n"
            "━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "Envie o <b>email</b> exato da conta não-usada que deseja remover.\n\n"
            "💡 Só remove contas disponíveis (used=0).\n\n"
            "Envie /cancelar para sair.",
            reply_markup=ForceReply(selective=True),
            parse_mode=ParseMode.HTML,
        )
    except Exception:
        pass


async def admin_stock_remove_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    pid = context.user_data.get("admin_stock_remove")
    if not pid:
        return
    if not is_admin(update.effective_user.id):
        return

    email = (update.message.text or "").strip()

    if email.startswith("/"):
        context.user_data.pop("admin_stock_remove", None)
        return

    if not email:
        await update.message.reply_text("❌ Email vazio.")
        return

    context.user_data.pop("admin_stock_remove", None)
    n = await db.admin_remove_stock_item(pid, email)

    await db.log_admin_action(update.effective_user.id, "stock_remove", str(pid), email)

    if n:
        await update.message.reply_text(
            f"✅ <b>{n} conta(s) removida(s).</b>\n📧 <code>{email}</code>",
            reply_markup=menus.admin_back_kb(),
            parse_mode=ParseMode.HTML,
        )
    else:
        await update.message.reply_text(
            f"❌ Nenhuma conta disponível com esse email:\n<code>{email}</code>",
            reply_markup=menus.admin_back_kb(),
            parse_mode=ParseMode.HTML,
        )


async def admin_stock_clear_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not is_admin(update.effective_user.id):
        return

    pid = int(query.data.split(":")[2])
    stats = await db.admin_stock_stats(pid)

    texto = (
        "⚠️ <b>Confirmação necessária</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"Você vai remover <b>{stats['disponiveis']}</b> conta(s) <b>NÃO USADA(S)</b>.\n\n"
        f"🔴 As <b>{stats['usadas']}</b> contas já usadas serão <b>mantidas</b>.\n\n"
        "Essa ação <b>não pode ser desfeita</b>."
    )

    kb = menus.admin_confirm_kb(
        yes_data=f"admin:stock_clear_yes:{pid}",
        no_data=f"admin:prod_stock:{pid}",
        yes_label="🧹 Sim, limpar",
    )
    await _edit_or_send(query, texto, kb)


async def admin_stock_clear_yes_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not is_admin(update.effective_user.id):
        return

    pid = int(query.data.split(":")[2])
    qtd = await db.admin_clear_stock(pid, apenas_nao_usadas=True)
    await db.log_admin_action(update.effective_user.id, "stock_clear", str(pid), f"qtd={qtd}")

    await _edit_or_send(
        query,
        f"🧹 <b>{qtd} conta(s) não usada(s) removida(s).</b>",
        menus.admin_product_stock_v3_kb(pid),
    )


async def admin_stock_export_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not is_admin(update.effective_user.id):
        return

    pid = int(query.data.split(":")[2])
    p = await db.get_product(pid)

    conteudo = await db.admin_export_stock(pid, only_available=True)

    if not conteudo:
        await query.answer("📭 Nenhuma conta disponível pra exportar.", show_alert=True)
        return

    filename = f"estoque-{pid}-{p['name'][:20].replace(' ', '_')}.txt"

    try:
        await context.bot.send_document(
            chat_id=query.message.chat_id,
            document=InputFile(io.BytesIO(conteudo.encode("utf-8")), filename=filename),
            caption=(
                f"📤 <b>Estoque exportado</b>\n\n"
                f"📦 Produto: <b>{p['name']}</b>\n"
                f"📊 Contas disponíveis: <b>{len(conteudo.splitlines())}</b>"
            ),
            parse_mode=ParseMode.HTML,
        )
    except Exception as e:
        logger.exception("Erro export: %s", e)


# ═══════════════════════════════════════════════
# ATIVAR / DESATIVAR / DELETAR
# ═══════════════════════════════════════════════
async def admin_toggle_product_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not is_admin(update.effective_user.id):
        return

    pid = int(query.data.split(":")[2])
    p = await db.get_product(pid)
    if not p:
        return

    novo = 0 if p.get("active") else 1
    await db.admin_update_product(pid, active=novo)
    await db.log_admin_action(
        update.effective_user.id, "toggle_product", str(pid), f"active={novo}"
    )
    await admin_product_v3_cb(update, context)


async def admin_prod_del_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not is_admin(update.effective_user.id):
        return

    pid = int(query.data.split(":")[2])
    p = await db.get_product(pid)
    if not p:
        return

    stats = await db.admin_stock_stats(pid)

    texto = (
        "🗑️ <b>Remover Produto</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"📦 <b>{p['name']}</b>\n\n"
        f"├ 💰 Preço: R$ {float(p['price']):.2f}\n"
        f"├ 📦 Estoque: {p['stock']}\n"
        f"├ 💵 Vendidos: {p.get('sold', 0)}\n"
        f"├ 📊 Contas no banco: {stats['total']}\n"
        f"└ 🔴 Contas usadas: {stats['usadas']}\n\n"
        "⚠️ <b>Escolha como remover:</b>\n\n"
        "🔒 <b>Desativar</b> — some do catálogo mas fica no admin\n"
        "❌ <b>Deletar de vez</b> — apaga produto + estoque (irreversível)"
    )

    kb = menus.InlineKeyboardMarkup([
        [menus.InlineKeyboardButton("🔒 Apenas desativar", callback_data=f"admin:prod_soft_del:{pid}")],
        [menus.InlineKeyboardButton("❌ Deletar de vez", callback_data=f"admin:prod_hard_del:{pid}")],
        [menus.InlineKeyboardButton("⬅️ Cancelar", callback_data=f"admin:product:{pid}")],
    ])
    await _edit_or_send(query, texto, kb)


async def admin_prod_soft_del_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not is_admin(update.effective_user.id):
        return

    pid = int(query.data.split(":")[2])
    await db.admin_delete_product(pid)
    await db.log_admin_action(update.effective_user.id, "product_soft_del", str(pid))

    await _edit_or_send(
        query,
        "🔒 <b>Produto desativado.</b>\n\n<i>Ele não aparece mais no catálogo, "
        "mas continua no painel admin.</i>",
        menus.admin_back_kb(),
    )


async def admin_prod_hard_del_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not is_admin(update.effective_user.id):
        return

    pid = int(query.data.split(":")[2])
    p = await db.get_product(pid)
    if not p:
        return

    stats = await db.admin_stock_stats(pid)

    texto = (
        "⚠️ <b>DELETAR DEFINITIVAMENTE</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"📦 <b>{p['name']}</b>\n\n"
        f"🗑 Serão apagados:\n"
        f"├ 1 produto\n"
        f"├ {stats['total']} contas do estoque\n"
        f"└ Todas as {stats['usadas']} contas usadas\n\n"
        "🚨 <b>Isso NÃO PODE SER DESFEITO!</b>\n\n"
        "Tem certeza absoluta?"
    )

    kb = menus.admin_confirm_kb(
        yes_data=f"admin:prod_hard_del_yes:{pid}",
        no_data=f"admin:product:{pid}",
        yes_label="🚨 SIM, DELETAR",
    )
    await _edit_or_send(query, texto, kb)


async def admin_prod_hard_del_yes_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not is_admin(update.effective_user.id):
        return

    pid = int(query.data.split(":")[2])
    p = await db.get_product(pid)

    await db.admin_really_delete_product(pid)
    await db.log_admin_action(update.effective_user.id, "product_hard_del", str(pid))

    await _edit_or_send(
        query,
        f"🗑️ <b>Produto deletado:</b> <code>{p['name'] if p else pid}</code>",
        menus.admin_back_kb(),
    )


# ═══════════════════════════════════════════════
# BUSCAR PRODUTO
# ═══════════════════════════════════════════════
async def admin_prod_search_prompt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not is_admin(update.effective_user.id):
        return

    context.user_data["admin_prod_search"] = True

    try:
        await query.edit_message_text(
            "🔍 <b>Buscar produto</b>\n\n"
            "Envie o <b>ID</b> ou parte do <b>nome</b>:",
            reply_markup=ForceReply(selective=True),
            parse_mode=ParseMode.HTML,
        )
    except Exception:
        pass


async def admin_prod_search_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.user_data.get("admin_prod_search"):
        return
    if not is_admin(update.effective_user.id):
        return

    term = (update.message.text or "").strip()
    context.user_data.pop("admin_prod_search", None)

    if not term:
        return

    if term.isdigit():
        p = await db.get_product(int(term))
        produtos = [p] if p else []
    else:
        produtos = await db.search_products(term)

    if not produtos:
        await update.message.reply_text(
            f"❌ Nada encontrado com <code>{term}</code>.",
            reply_markup=menus.admin_back_kb(),
            parse_mode=ParseMode.HTML,
        )
        return

    texto = f"🔍 <b>Resultados</b> ({len(produtos)}):"
    kb = menus.admin_products_v3_kb(produtos, 0, 1)
    await update.message.reply_text(texto, reply_markup=kb, parse_mode=ParseMode.HTML)


# ═══════════════════════════════════════════════
# HELPERS
# ═══════════════════════════════════════════════
def _parse_contas(texto: str) -> tuple[list[tuple[str, str]], int]:
    """
    Aceita linha por linha com separador ':' ou '|'.
    Retorna (contas_validas, num_invalidas).
    """
    contas = []
    invalidas = 0

    for linha in (texto or "").splitlines():
        linha = linha.strip()
        if not linha:
            continue

        if "|" in linha and ":" not in linha:
            sep = "|"
        elif ":" in linha:
            sep = ":"
        elif "|" in linha:
            sep = "|"
        else:
            if "@" in linha:
                contas.append((linha, "—"))
                continue
            invalidas += 1
            continue

        partes = linha.split(sep, 1)
        if len(partes) != 2:
            invalidas += 1
            continue

        email = partes[0].strip()
        senha = partes[1].strip()

        if email:
            contas.append((email, senha or "—"))
        else:
            invalidas += 1

    return contas, invalidas
