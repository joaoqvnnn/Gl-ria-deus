import logging
from telegram import Update, ForceReply
from telegram.constants import ParseMode
from telegram.ext import ContextTypes

from config import ADMIN_IDS
from database import db
from keyboards import menus
from texts import cache

logger = logging.getLogger(__name__)


def is_admin(user_id: int) -> bool:
    return user_id in ADMIN_IDS


async def _edit_or_send(query, text: str, kb=None):
    try:
        await query.edit_message_text(text, reply_markup=kb, parse_mode=ParseMode.HTML)
    except Exception:
        await query.message.reply_text(text, reply_markup=kb, parse_mode=ParseMode.HTML)


# ═══════════════════════════════════════════════
# LISTA DE PRODUTOS (V2)
# ═══════════════════════════════════════════════
async def admin_products_v2_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not is_admin(update.effective_user.id):
        return

    produtos = await db.get_products()
    texto = (
        f"📦 <b>Produtos</b> ({len(produtos)})\n"
        f"━━━━━━━━━━━━━━━━━━━━\n\n"
        "Toque em um produto pra editar:"
    )
    await _edit_or_send(query, texto, menus.admin_products_kb_v2(produtos))


# ═══════════════════════════════════════════════
# DETALHE DO PRODUTO (V2 — completo)
# ═══════════════════════════════════════════════
async def admin_product_v2_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not is_admin(update.effective_user.id):
        return

    pid = int(query.data.split(":")[2])
    p = await db.get_product(pid)
    if not p:
        await _edit_or_send(query, "❌ Produto não encontrado.", menus.admin_back_kb())
        return

    contas = await db.admin_count_stock(pid)

    texto = (
        f"📦 <b>{p['name']}</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n\n"
        f"💰 Preço: <b>R$ {float(p['price']):.2f}</b>\n"
        f"📊 Estoque: <b>{p['stock']}</b> "
        f"(<i>{contas['disponiveis']} contas reais</i>)\n"
        f"💵 Vendidos: <b>{p.get('sold', 0)}</b>\n"
        f"😀 Emoji: <b>{p.get('emoji') or '📦'}</b>\n"
        f"🛡 Garantia: <b>{p.get('guarantee', 180)} dias</b>\n"
        f"🔗 Link: <code>{(p.get('activate_url') or '')[:50]}</code>\n"
        f"📡 Status: <b>{'🟢 Ativo' if p.get('active') else '🔴 Inativo'}</b>\n\n"
        f"📝 <b>Descrição:</b>\n<i>{(p.get('description') or '')[:200]}</i>"
    )
    await _edit_or_send(
        query, texto, menus.admin_product_kb_full(pid, bool(p.get("active")))
    )


# ═══════════════════════════════════════════════
# EDITAR CAMPO DO PRODUTO
# ═══════════════════════════════════════════════
async def admin_prod_edit_prompt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not is_admin(update.effective_user.id):
        return

    # admin:prod_edit:<pid>:<campo>
    parts = query.data.split(":")
    pid = int(parts[2])
    campo = parts[3]

    p = await db.get_product(pid)
    if not p:
        return

    context.user_data["admin_prod_edit"] = {"pid": pid, "campo": campo}

    labels = {
        "name":         "📝 Nome do produto",
        "description":  "📄 Descrição",
        "price":        "💰 Preço (ex: 19.90)",
        "stock":        "📦 Estoque (número)",
        "emoji":        "😀 Emoji (ex: 🎨)",
        "guarantee":    "🛡 Garantia em dias",
        "activate_url": "🔗 Link de ativação (URL)",
    }

    valor_atual = str(p.get(campo) or "—")
    if campo == "description":
        valor_atual = valor_atual[:100] + "..." if len(valor_atual) > 100 else valor_atual

    try:
        await query.edit_message_text(
            f"✏️ <b>{labels.get(campo, campo)}</b>\n\n"
            f"Valor atual: <code>{valor_atual}</code>\n\n"
            "Envie o novo valor:",
            reply_markup=ForceReply(selective=True),
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

    pid = info["pid"]
    campo = info["campo"]
    texto = (update.message.text or "").strip()

    if not texto:
        await update.message.reply_text("❌ Valor vazio.")
        return

    # Validação por tipo
    try:
        if campo == "price":
            valor = float(texto.replace(",", "."))
            if valor <= 0:
                raise ValueError
        elif campo == "stock":
            valor = int(texto)
            if valor < 0:
                raise ValueError
        elif campo == "guarantee":
            valor = int(texto)
            if valor < 0:
                raise ValueError
        else:
            valor = texto
    except ValueError:
        await update.message.reply_text("❌ Valor inválido.")
        return

    context.user_data.pop("admin_prod_edit", None)

    await db.admin_update_product(pid, **{campo: valor})
    await db.log_admin_action(update.effective_user.id, f"prod_edit_{campo}", str(pid))

    await update.message.reply_text(
        f"✅ <b>Produto atualizado!</b>\n\n"
        f"<b>{campo}</b> = <code>{str(valor)[:100]}</code>",
        reply_markup=menus.admin_back_kb(),
        parse_mode=ParseMode.HTML,
    )


# ═══════════════════════════════════════════════
# GERENCIAR ESTOQUE
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

    contas = await db.admin_count_stock(pid)

    texto = (
        f"📥 <b>Estoque — {p['name']}</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n\n"
        f"📊 Total no banco: <b>{p['stock']}</b>\n"
        f"🟢 Disponíveis: <b>{contas['disponiveis']}</b>\n"
        f"🔴 Usadas: <b>{contas['usadas']}</b>\n\n"
        "Escolha uma ação:"
    )
    await _edit_or_send(query, texto, menus.admin_product_stock_kb(pid))


async def admin_stock_add_prompt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not is_admin(update.effective_user.id):
        return

    pid = int(query.data.split(":")[2])
    context.user_data["admin_stock_add"] = pid

    try:
        await query.edit_message_text(
            "📥 <b>Adicionar contas ao estoque</b>\n\n"
            "Envie uma ou mais contas no formato:\n"
            "<code>email@exemplo.com:senha123</code>\n\n"
            "Pode colar várias (uma por linha).\n"
            "Exemplo:\n"
            "<code>conta1@x.com:abc123\n"
            "conta2@x.com:def456</code>",
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
    linhas = [l.strip() for l in texto.split("\n") if l.strip()]

    contas = []
    invalidas = 0

    for linha in linhas:
        if ":" in linha:
            email, senha = linha.split(":", 1)
            email = email.strip()
            senha = senha.strip()
            if email and senha:
                contas.append((email, senha))
            else:
                invalidas += 1
        else:
            invalidas += 1

    if not contas:
        await update.message.reply_text(
            "❌ Nenhuma conta válida.\n"
            "Use o formato: <code>email:senha</code>",
            parse_mode=ParseMode.HTML,
        )
        return

    context.user_data.pop("admin_stock_add", None)

    qtd = await db.admin_add_stock_batch(pid, contas)
    await db.log_admin_action(
        update.effective_user.id, "stock_add", str(pid), f"qtd={qtd}"
    )

    p = await db.get_product(pid)

    await update.message.reply_text(
        f"✅ <b>{qtd} contas adicionadas!</b>\n\n"
        f"📦 Produto: <b>{p['name']}</b>\n"
        f"📊 Novo estoque: <b>{p['stock']}</b>\n"
        + (f"⚠️ {invalidas} linhas inválidas ignoradas." if invalidas else ""),
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
        # Lista em chunks de 20 pra não estourar o limite do Telegram
        bloco = contas[:20]
        linhas = [f"👀 <b>Contas disponíveis ({len(contas)})</b>\n"]
        for c in bloco:
            linhas.append(f"📧 <code>{c['email']}</code>")
        if len(contas) > 20:
            linhas.append(f"\n<i>... e mais {len(contas) - 20} contas.</i>")
        texto = "\n".join(linhas)

    await _edit_or_send(query, texto, menus.admin_product_stock_kb(pid))


async def admin_stock_clear_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not is_admin(update.effective_user.id):
        return

    pid = int(query.data.split(":")[2])
    qtd = await db.admin_clear_stock(pid, apenas_nao_usadas=True)
    await db.log_admin_action(update.effective_user.id, "stock_clear", str(pid), f"qtd={qtd}")

    await _edit_or_send(
        query,
        f"🗑️ <b>{qtd} contas não usadas removidas.</b>",
        menus.admin_product_stock_kb(pid),
    )


# ═══════════════════════════════════════════════
# CRIAR PRODUTO (FLUXO PASSO A PASSO)
# ═══════════════════════════════════════════════
_STEPS = [
    ("name",         "📝 <b>Nome do produto</b>\n\nEnvie o nome (ex: <code>Netflix 4K</code>):"),
    ("description",  "📄 <b>Descrição</b>\n\nEnvie a descrição do produto:"),
    ("price",        "💰 <b>Preço</b>\n\nEnvie o preço em reais (ex: <code>19.90</code>):"),
    ("stock",        "📦 <b>Estoque</b>\n\nEnvie a quantidade inicial (ex: <code>10</code>):"),
    ("emoji",        "😀 <b>Emoji</b>\n\nEnvie um emoji pro produto (ex: <code>🎬</code>):"),
    ("guarantee",    "🛡 <b>Garantia</b>\n\nEnvie em dias (ex: <code>30</code>):"),
    ("activate_url", "🔗 <b>Link de ativação</b>\n\nEnvie a URL (ex: <code>https://t.me/seubot</code>):"),
]


async def admin_new_product_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not is_admin(update.effective_user.id):
        return

    context.user_data["admin_new_prod"] = {"dados": {}, "step": 0}

    try:
        await query.edit_message_text(
            f"➕ <b>Criar novo produto</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━\n\n"
            f"Passo 1/{len(_STEPS)}\n\n{_STEPS[0][1]}",
            reply_markup=ForceReply(selective=True),
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

    texto = (update.message.text or "").strip()
    if not texto:
        await update.message.reply_text("❌ Valor vazio.")
        return

    step = state["step"]
    campo = _STEPS[step][0]
    dados = state["dados"]

    # Validação por tipo
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

    # Ainda tem passos
    if step < len(_STEPS):
        state["step"] = step
        state["dados"] = dados

        await update.message.reply_text(
            f"Passo {step + 1}/{len(_STEPS)}\n\n{_STEPS[step][1]}",
            reply_markup=ForceReply(selective=True),
            parse_mode=ParseMode.HTML,
        )
        return

    # Terminou — cria o produto
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
    except Exception as e:
        logger.exception("Erro criando produto: %s", e)
        await update.message.reply_text(f"❌ Erro ao criar: {e}")
        return

    await db.log_admin_action(update.effective_user.id, "product_create", str(pid))

    await update.message.reply_text(
        f"✅ <b>Produto criado!</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n\n"
        f"🆔 ID: <code>{pid}</code>\n"
        f"📝 Nome: <b>{dados['name']}</b>\n"
        f"💰 Preço: <b>R$ {dados['price']:.2f}</b>\n"
        f"📦 Estoque: <b>{dados['stock']}</b>",
        reply_markup=menus.admin_back_kb(),
        parse_mode=ParseMode.HTML,
    )


# ═══════════════════════════════════════════════
# REMOVER PRODUTO
# ═══════════════════════════════════════════════
async def admin_prod_del_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not is_admin(update.effective_user.id):
        return

    pid = int(query.data.split(":")[2])
    await db.admin_delete_product(pid)
    await db.log_admin_action(update.effective_user.id, "product_delete", str(pid))

    await _edit_or_send(
        query,
        "🗑️ <b>Produto removido.</b>\n\nEle foi desativado (não aparece mais no catálogo).",
        menus.admin_back_kb(),
    )
