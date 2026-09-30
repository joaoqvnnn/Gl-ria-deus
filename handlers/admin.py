import asyncio
import logging
from telegram import Update, ForceReply
from telegram.constants import ParseMode
from telegram.ext import ContextTypes

from config import ADMIN_IDS
from database import db
from keyboards import menus
from texts import cache, messages

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════
# HELPERS
# ═══════════════════════════════════════════════
def is_admin(user_id: int) -> bool:
    return user_id in ADMIN_IDS


async def _edit_or_send(query, text: str, kb=None):
    """Tenta editar; se falhar, envia nova."""
    try:
        await query.edit_message_text(text, reply_markup=kb, parse_mode=ParseMode.HTML)
    except Exception:
        await query.message.reply_text(text, reply_markup=kb, parse_mode=ParseMode.HTML)


# ═══════════════════════════════════════════════
# DASHBOARD
# ═══════════════════════════════════════════════
def _dashboard_text(stats: dict) -> str:
    manut = "🟢 Ligado" if not stats["manutencao"] else "🔴 Em manutenção"
    return (
        "🛠 <b>PAINEL ADMIN — Larizinha Store</b>\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"

        f"👥 <b>Usuários:</b> {stats['total_users']}\n"
        f"🚫 <b>Banidos:</b> {stats['total_banned']}\n"
        f"📦 <b>Produtos ativos:</b> {stats['total_produtos']}\n"
        f"🛒 <b>Carrinhos abandonados:</b> {stats['carrinhos_abandonados']}\n\n"

        "💰 <b>Saldo em circulação:</b>\n"
        f"<b>R$ {stats['saldo_circulacao']:.2f}</b>\n\n"

        "📊 <b>Vendas:</b>\n"
        f"├ Total: <b>{stats['total_vendas']}</b>\n"
        f"├ Receita total: <b>R$ {stats['receita_total']:.2f}</b>\n"
        f"├ Receita hoje: <b>R$ {stats['receita_hoje']:.2f}</b>\n"
        f"├ Receita 7d: <b>R$ {stats['receita_semana']:.2f}</b>\n"
        f"└ Receita mês: <b>R$ {stats['receita_mes']:.2f}</b>\n\n"

        f"⚙️ <b>Status:</b> {manut}"
    )


async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/admin — abre o painel."""
    user = update.effective_user
    if not is_admin(user.id):
        return

    stats = await db.admin_stats()
    await update.message.reply_text(
        _dashboard_text(stats),
        reply_markup=menus.admin_dashboard_kb(),
        parse_mode=ParseMode.HTML,
    )


async def admin_home_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Callback admin:home — volta ao dashboard."""
    query = update.callback_query
    await query.answer()
    user = update.effective_user
    if not is_admin(user.id):
        return

    stats = await db.admin_stats()
    await _edit_or_send(query, _dashboard_text(stats), menus.admin_dashboard_kb())


# ═══════════════════════════════════════════════
# USUÁRIOS
# ═══════════════════════════════════════════════
async def admin_users_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user = update.effective_user
    if not is_admin(user.id):
        return

    users = await db.list_users(limit=10)
    total = await db.count_users()

    texto = (
        f"👥 <b>Usuários</b> (mostrando 10 de {total})\n"
        f"━━━━━━━━━━━━━━━━━━━━\n\n"
        "Toque em um usuário pra ver detalhes:"
    )
    await _edit_or_send(query, texto, menus.admin_users_kb(users))


async def admin_user_search_prompt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Pede o termo de busca via ForceReply."""
    query = update.callback_query
    await query.answer()
    user = update.effective_user
    if not is_admin(user.id):
        return

    context.user_data["admin_await_search"] = True

    try:
        await query.edit_message_text(
            "🔍 <b>Buscar usuário</b>\n\n"
            "Envie o <b>ID</b>, <b>nome</b> ou <b>@username</b>:",
            reply_markup=ForceReply(selective=True),
            parse_mode=ParseMode.HTML,
        )
    except Exception:
        pass


async def admin_search_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Recebe o termo de busca (via ForceReply)."""
    if not context.user_data.get("admin_await_search"):
        return
    if not is_admin(update.effective_user.id):
        return

    term = (update.message.text or "").strip()
    context.user_data.pop("admin_await_search", None)

    if not term:
        await update.message.reply_text("❌ Termo vazio.")
        return

    usuarios = await db.search_users(term)

    if not usuarios:
        await update.message.reply_text(
            f"❌ Nenhum usuário encontrado com <b>{term}</b>.",
            reply_markup=menus.admin_back_kb(),
            parse_mode=ParseMode.HTML,
        )
        return

    texto = (
        f"🔍 <b>Busca: {term}</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n\n"
        f"Encontrados: <b>{len(usuarios)}</b>"
    )
    await update.message.reply_text(
        texto,
        reply_markup=menus.admin_users_kb(usuarios),
        parse_mode=ParseMode.HTML,
    )


async def admin_user_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """admin:user:<id> — mostra o perfil do usuário no admin."""
    query = update.callback_query
    await query.answer()
    user = update.effective_user
    if not is_admin(user.id):
        return

    try:
        target_id = int(query.data.split(":")[2])
    except (IndexError, ValueError):
        return

    u = await db.get_user(target_id)
    if not u:
        await _edit_or_send(query, "❌ Usuário não encontrado.", menus.admin_back_kb())
        return

    stats = await db.user_stats(target_id)
    banned = bool(u.get("banned"))

    texto = (
        f"👤 <b>Usuário</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n\n"
        f"🆔 ID: <code>{u['user_id']}</code>\n"
        f"📛 Nome: <b>{u.get('first_name') or '—'}</b>\n"
        f"🔗 Username: @{u.get('username') or '—'}\n"
        f"💰 Saldo: <b>R$ {float(u.get('balance') or 0):.2f}</b>\n"
        f"💠 Saldo Web: <b>R$ {float(u.get('balance_web') or 0):.2f}</b>\n"
        f"📱 WhatsApp: <code>{u.get('whatsapp') or '—'}</code>\n"
        f"🚫 Banido: <b>{'Sim' if banned else 'Não'}</b>\n\n"
        "📊 <b>Movimentações:</b>\n"
        f"├ 🛒 Compras: <b>{stats['compras']}</b>\n"
        f"├ 💰 Gasto: <b>R$ {stats['gasto']:.2f}</b>\n"
        f"├ 💠 Pix: <b>R$ {stats['pix_inseridos']:.2f}</b>\n"
        f"└ 🎁 Gifts: <b>R$ {stats['gifts_valor']:.2f}</b>"
    )

    await _edit_or_send(query, texto, menus.admin_user_kb(target_id, banned))


# ─── Adicionar saldo
async def admin_add_balance_prompt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not is_admin(update.effective_user.id):
        return

    target_id = int(query.data.split(":")[2])
    context.user_data["admin_balance"] = {"target": target_id, "tipo": "add"}

    try:
        await query.edit_message_text(
            f"➕ <b>Adicionar saldo</b>\n\n"
            f"Usuário: <code>{target_id}</code>\n\n"
            "Envie o valor (ex: <code>10.50</code>):",
            reply_markup=ForceReply(selective=True),
            parse_mode=ParseMode.HTML,
        )
    except Exception:
        pass


# ─── Remover saldo
async def admin_rem_balance_prompt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not is_admin(update.effective_user.id):
        return

    target_id = int(query.data.split(":")[2])
    context.user_data["admin_balance"] = {"target": target_id, "tipo": "rem"}

    try:
        await query.edit_message_text(
            f"➖ <b>Remover saldo</b>\n\n"
            f"Usuário: <code>{target_id}</code>\n\n"
            "Envie o valor (ex: <code>10.50</code>):",
            reply_markup=ForceReply(selective=True),
            parse_mode=ParseMode.HTML,
        )
    except Exception:
        pass


async def admin_balance_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Recebe o valor pra add/rem saldo."""
    info = context.user_data.get("admin_balance")
    if not info:
        return
    if not is_admin(update.effective_user.id):
        return

    text = (update.message.text or "").strip().replace(",", ".")
    try:
        valor = float(text)
        if valor <= 0:
            raise ValueError
    except ValueError:
        await update.message.reply_text("❌ Valor inválido. Envie um número positivo.")
        return

    target = info["target"]
    tipo = info["tipo"]
    context.user_data.pop("admin_balance", None)

    u = await db.get_user(target)
    if not u:
        await update.message.reply_text("❌ Usuário não encontrado.")
        return

    delta = valor if tipo == "add" else -valor
    await db.update_balance(target, delta)

    u2 = await db.get_user(target)
    await db.log_admin_action(
        update.effective_user.id,
        f"{'add' if tipo == 'add' else 'rem'}_balance",
        str(target),
        f"R$ {valor:.2f}",
    )

    acao = "adicionado" if tipo == "add" else "removido"
    await update.message.reply_text(
        f"✅ <b>Saldo {acao}!</b>\n\n"
        f"Usuário: <code>{target}</code>\n"
        f"Valor: <b>R$ {valor:.2f}</b>\n"
        f"Saldo atual: <b>R$ {float(u2['balance']):.2f}</b>",
        reply_markup=menus.admin_back_kb(),
        parse_mode=ParseMode.HTML,
    )


# ─── Ban / Unban
async def admin_ban_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not is_admin(update.effective_user.id):
        return

    target_id = int(query.data.split(":")[2])
    await db.ban_user(target_id)
    await db.log_admin_action(update.effective_user.id, "ban", str(target_id))

    await admin_user_cb(update, context)


async def admin_unban_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not is_admin(update.effective_user.id):
        return

    target_id = int(query.data.split(":")[2])
    await db.unban_user(target_id)
    await db.log_admin_action(update.effective_user.id, "unban", str(target_id))

    await admin_user_cb(update, context)


# ═══════════════════════════════════════════════
# PRODUTOS
# ═══════════════════════════════════════════════
async def admin_products_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
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
    await _edit_or_send(query, texto, menus.admin_products_kb(produtos))


async def admin_product_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not is_admin(update.effective_user.id):
        return

    pid = int(query.data.split(":")[2])
    p = await db.get_product(pid)
    if not p:
        await _edit_or_send(query, "❌ Produto não encontrado.", menus.admin_back_kb())
        return

    texto = (
        f"📦 <b>{p['name']}</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n\n"
        f"💰 Preço: <b>R$ {float(p['price']):.2f}</b>\n"
        f"📊 Estoque: <b>{p['stock']}</b>\n"
        f"💵 Vendidos: <b>{p.get('sold', 0)}</b>\n"
        f"🛡 Garantia: <b>{p.get('guarantee', 180)} dias</b>\n"
        f"📡 Status: <b>{'🟢 Ativo' if p.get('active') else '🔴 Inativo'}</b>\n\n"
        f"📝 Descrição:\n<i>{(p.get('description') or '')[:200]}</i>"
    )
    await _edit_or_send(query, texto, menus.admin_product_kb(pid, bool(p.get("active"))))


async def admin_toggle_product_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not is_admin(update.effective_user.id):
        return

    pid = int(query.data.split(":")[2])
    p = await db.get_product(pid)
    if not p:
        return

    novo_status = 0 if p.get("active") else 1
    await db._db.execute("UPDATE products SET active = ? WHERE id = ?", (novo_status, pid))
    await db._db.commit()
    await db.log_admin_action(update.effective_user.id, "toggle_product", str(pid), f"active={novo_status}")

    await admin_product_cb(update, context)


async def admin_edit_price_prompt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not is_admin(update.effective_user.id):
        return

    pid = int(query.data.split(":")[2])
    p = await db.get_product(pid)
    if not p:
        return

    context.user_data["admin_edit_price"] = pid

    try:
        await query.edit_message_text(
            f"💰 <b>Editar preço</b>\n\n"
            f"Produto: <b>{p['name']}</b>\n"
            f"Preço atual: <b>R$ {float(p['price']):.2f}</b>\n\n"
            "Envie o novo preço (ex: <code>19.90</code>):",
            reply_markup=ForceReply(selective=True),
            parse_mode=ParseMode.HTML,
        )
    except Exception:
        pass


async def admin_edit_price_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    pid = context.user_data.get("admin_edit_price")
    if not pid:
        return
    if not is_admin(update.effective_user.id):
        return

    text = (update.message.text or "").strip().replace(",", ".")
    try:
        novo_preco = float(text)
        if novo_preco <= 0:
            raise ValueError
    except ValueError:
        await update.message.reply_text("❌ Preço inválido.")
        return

    context.user_data.pop("admin_edit_price", None)
    await db._db.execute("UPDATE products SET price = ? WHERE id = ?", (novo_preco, pid))
    await db._db.commit()
    await db.log_admin_action(update.effective_user.id, "edit_price", str(pid), f"R$ {novo_preco:.2f}")

    await update.message.reply_text(
        f"✅ <b>Preço atualizado!</b>\n\n"
        f"Novo preço: <b>R$ {novo_preco:.2f}</b>",
        reply_markup=menus.admin_back_kb(),
        parse_mode=ParseMode.HTML,
    )


async def admin_edit_stock_prompt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not is_admin(update.effective_user.id):
        return

    pid = int(query.data.split(":")[2])
    p = await db.get_product(pid)
    if not p:
        return

    context.user_data["admin_edit_stock"] = pid

    try:
        await query.edit_message_text(
            f"📦 <b>Editar estoque</b>\n\n"
            f"Produto: <b>{p['name']}</b>\n"
            f"Estoque atual: <b>{p['stock']}</b>\n\n"
            "Envie a nova quantidade (ex: <code>15</code>):",
            reply_markup=ForceReply(selective=True),
            parse_mode=ParseMode.HTML,
        )
    except Exception:
        pass


async def admin_edit_stock_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    pid = context.user_data.get("admin_edit_stock")
    if not pid:
        return
    if not is_admin(update.effective_user.id):
        return

    text = (update.message.text or "").strip()
    try:
        nova_qtd = int(text)
        if nova_qtd < 0:
            raise ValueError
    except ValueError:
        await update.message.reply_text("❌ Quantidade inválida.")
        return

    context.user_data.pop("admin_edit_stock", None)
    await db._db.execute("UPDATE products SET stock = ? WHERE id = ?", (nova_qtd, pid))
    await db._db.commit()
    await db.log_admin_action(update.effective_user.id, "edit_stock", str(pid), f"qty={nova_qtd}")

    await update.message.reply_text(
        f"✅ <b>Estoque atualizado!</b>\n\n"
        f"Nova quantidade: <b>{nova_qtd}</b>",
        reply_markup=menus.admin_back_kb(),
        parse_mode=ParseMode.HTML,
    )


# ═══════════════════════════════════════════════
# BROADCAST
# ═══════════════════════════════════════════════
async def admin_broadcast_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not is_admin(update.effective_user.id):
        return

    texto = (
        "📢 <b>Broadcast</b>\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
        "Escolha o público:"
    )
    await _edit_or_send(query, texto, menus.admin_broadcast_kb())


async def admin_bc_prompt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not is_admin(update.effective_user.id):
        return

    tipo = query.data.split(":")[1]  # bc_all, bc_buyers, bc_inactive
    context.user_data["admin_bc"] = tipo

    try:
        await query.edit_message_text(
            "📢 <b>Envie a mensagem</b>\n\n"
            "(pode usar HTML: <b>negrito</b>, <i>itálico</i>, emoji, links)",
            reply_markup=ForceReply(selective=True),
            parse_mode=ParseMode.HTML,
        )
    except Exception:
        pass


async def admin_bc_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    tipo = context.user_data.get("admin_bc")
    if not tipo:
        return
    if not is_admin(update.effective_user.id):
        return

    msg = update.message.text or update.message.caption or ""
    if not msg.strip():
        await update.message.reply_text("❌ Mensagem vazia.")
        return

    context.user_data.pop("admin_bc", None)

    if tipo == "bc_all":
        ids = await db.all_user_ids()
    elif tipo == "bc_buyers":
        ids = await db.buyers_user_ids()
    elif tipo == "bc_inactive":
        ids = await db.inactive_user_ids(7)
    else:
        ids = []

    if not ids:
        await update.message.reply_text("⚠️ Nenhum usuário nesse segmento.")
        return

    enviados = 0
    falhas = 0

    await update.message.reply_text(
        f"📢 Enviando para <b>{len(ids)}</b> usuários...",
        parse_mode=ParseMode.HTML,
    )

    for uid in ids:
        try:
            await context.bot.send_message(
                chat_id=uid, text=msg, parse_mode=ParseMode.HTML,
            )
            enviados += 1
        except Exception:
            falhas += 1

        # Throttle pra evitar flood
        await asyncio.sleep(0.05)

    await db.log_admin_action(
        update.effective_user.id, "broadcast", tipo,
        f"enviados={enviados} falhas={falhas}",
    )

    await update.message.reply_text(
        f"✅ <b>Broadcast concluído!</b>\n\n"
        f"📤 Enviados: <b>{enviados}</b>\n"
        f"❌ Falhas: <b>{falhas}</b>",
        reply_markup=menus.admin_back_kb(),
        parse_mode=ParseMode.HTML,
    )


# ═══════════════════════════════════════════════
# MANUTENÇÃO
# ═══════════════════════════════════════════════
async def admin_maintenance_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not is_admin(update.effective_user.id):
        return

    ativo = await db.get_maintenance()
    status = "🔴 LIGADO" if ativo else "🟢 DESLIGADO"
    texto = (
        "🚧 <b>Modo Manutenção</b>\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
        f"Status atual: <b>{status}</b>\n\n"
        "Quando <b>LIGADO</b>, o bot responde com uma mensagem de manutenção "
        "pra todos os usuários (exceto admins)."
    )
    await _edit_or_send(query, texto, menus.admin_maintenance_kb(ativo))


async def admin_toggle_maintenance_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not is_admin(update.effective_user.id):
        return

    ativo = await db.get_maintenance()
    novo = not ativo
    await db.set_maintenance(novo)
    await db.log_admin_action(
        update.effective_user.id, "toggle_maintenance", "global", f"novo={novo}",
    )

    await admin_maintenance_cb(update, context)


# ═══════════════════════════════════════════════
# LOGS
# ═══════════════════════════════════════════════
async def admin_logs_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not is_admin(update.effective_user.id):
        return

    logs = await db.list_admin_logs(20)

    if not logs:
        texto = "📋 <b>Logs</b>\n\n<i>Nenhuma ação registrada.</i>"
    else:
        linhas = ["📋 <b>Últimos 20 logs</b>\n━━━━━━━━━━━━━━━━━━━━\n"]
        for l in logs:
            data = str(l.get("created_at") or "")[:16]
            linhas.append(
                f"<code>{data}</code> — admin <code>{l['admin_id']}</code>\n"
                f"   <b>{l['action']}</b> → {l.get('target') or '—'} {l.get('details') or ''}"
            )
        texto = "\n".join(linhas)

    await _edit_or_send(query, texto, menus.admin_back_kb())
