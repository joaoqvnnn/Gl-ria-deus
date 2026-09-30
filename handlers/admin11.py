"""
Módulo ADMIN — ESTATÍSTICAS (v2 — completo).
"""
import logging
import io
from datetime import datetime
from telegram import Update, InputFile
from telegram.constants import ParseMode
from telegram.ext import ContextTypes

from config import ADMIN_IDS
from database import db
from keyboards import menus

logger = logging.getLogger(__name__)

PERIODO_LABEL = {
    "hoje": "Hoje",
    "7d": "Últimos 7 dias",
    "30d": "Últimos 30 dias",
    "mes": "Este mês",
    "mes_passado": "Mês passado",
    "tudo": "Todo o período",
}


def is_admin(user_id: int) -> bool:
    return user_id in ADMIN_IDS


async def _edit_or_send(query, text: str, kb=None):
    try:
        await query.edit_message_text(text, reply_markup=kb, parse_mode=ParseMode.HTML)
    except Exception:
        await query.message.reply_text(text, reply_markup=kb, parse_mode=ParseMode.HTML)


def _barra(valor: float, maximo: float, largura: int = 12) -> str:
    """Desenha uma barra em texto."""
    if maximo <= 0:
        return "░" * largura
    pct = min(valor / maximo, 1.0)
    cheio = int(pct * largura)
    return "█" * cheio + "░" * (largura - cheio)


def _seta_pct(pct: float) -> str:
    if pct > 5:
        return f"📈 +{pct:.1f}%"
    if pct < -5:
        return f"📉 {pct:.1f}%"
    return f"➖ {pct:+.1f}%"


# ═══════════════════════════════════════════════
# DASHBOARD
# ═══════════════════════════════════════════════
async def admin_stats_v2_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not is_admin(update.effective_user.id):
        return
    await _render_stats(query, periodo="30d")


async def admin_stats_v2_filtro_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not is_admin(update.effective_user.id):
        return
    try:
        periodo = query.data.split(":")[2]
    except IndexError:
        periodo = "30d"
    await _render_stats(query, periodo=periodo)


async def _render_stats(query, periodo: str = "30d"):
    s = await db.admin_stats_v2(periodo)
    saldos = await db.admin_stats_saldos()

    label = PERIODO_LABEL.get(periodo, periodo)

    texto = (
        "📊 <b>Estatísticas do Bot</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"📅 Período: <b>{label}</b>\n\n"
        "🛒 <b>Vendas:</b>\n"
        f"├ Pedidos: <b>{s['vendas_qtd']}</b>\n"
        f"├ Itens vendidos: <b>{s['vendas_itens']}</b>\n"
        f"├ Receita: <b>R$ {s['vendas_receita']:.2f}</b>\n"
        f"└ Ticket médio: <b>R$ {s['ticket_medio']:.2f}</b>\n\n"
        "💠 <b>Recargas:</b>\n"
        f"├ Pedidos: <b>{s['recargas_qtd']}</b>\n"
        f"└ Valor total: <b>R$ {s['recargas_valor']:.2f}</b>\n\n"
        "💸 <b>Saques:</b>\n"
        f"├ Processados: <b>{s['saques_qtd']}</b>\n"
        f"└ Valor total: <b>R$ {s['saques_valor']:.2f}</b>\n\n"
        "👥 <b>Usuários:</b>\n"
        f"└ Novos no período: <b>{s['novos_users']}</b>\n\n"
        "💰 <b>Saldos em circulação:</b>\n"
        f"├ Bot: <b>R$ {saldos['bot']:.2f}</b>\n"
        f"├ Web: <b>R$ {saldos['web']:.2f}</b>\n"
        f"├ Saques pendentes: <b>R$ {saldos['saques_pendentes']:.2f}</b>\n"
        f"└ Gifts livres: <b>R$ {saldos['gifts_livres']:.2f}</b>\n\n"
        "👇 Escolha um filtro ou detalhamento:"
    )

    kb = menus.admin_stats_v2_kb(periodo)
    await _edit_or_send(query, texto, kb)


# ═══════════════════════════════════════════════
# COMPARATIVO MÊS
# ═══════════════════════════════════════════════
async def admin_stats_v2_comp_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not is_admin(update.effective_user.id):
        return

    c = await db.admin_stats_comparativo()
    a = c["atual"]
    p = c["anterior"]

    texto = (
        "📊 <b>Comparativo — Este mês vs Mês passado</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "💰 <b>Receita:</b>\n"
        f"├ Este mês: <b>R$ {a['vendas_receita']:.2f}</b>\n"
        f"├ Mês passado: <b>R$ {p['vendas_receita']:.2f}</b>\n"
        f"└ {_seta_pct(c['pct_receita'])}\n\n"
        "🛒 <b>Vendas (qtd):</b>\n"
        f"├ Este mês: <b>{a['vendas_qtd']}</b>\n"
        f"├ Mês passado: <b>{p['vendas_qtd']}</b>\n"
        f"└ {_seta_pct(c['pct_vendas'])}\n\n"
        "👥 <b>Novos usuários:</b>\n"
        f"├ Este mês: <b>{a['novos_users']}</b>\n"
        f"├ Mês passado: <b>{p['novos_users']}</b>\n"
        f"└ {_seta_pct(c['pct_users'])}\n\n"
        "💠 <b>Recargas (R$):</b>\n"
        f"├ Este mês: <b>R$ {a['recargas_valor']:.2f}</b>\n"
        f"├ Mês passado: <b>R$ {p['recargas_valor']:.2f}</b>\n"
        f"└ {_seta_pct(c['pct_recargas'])}"
    )

    kb = menus.InlineKeyboardMarkup([
        [menus.InlineKeyboardButton("⬅️ Voltar", callback_data="admin:stats")],
    ])
    await _edit_or_send(query, texto, kb)


# ═══════════════════════════════════════════════
# VENDAS POR DIA (gráfico em barras)
# ═══════════════════════════════════════════════
async def admin_stats_v2_dia_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not is_admin(update.effective_user.id):
        return

    dias = await db.admin_stats_por_dia(7)

    if not dias:
        texto = "📅 <b>Vendas por dia</b>\n\n<i>Sem vendas nos últimos 7 dias.</i>"
    else:
        max_receita = max(float(d["receita"]) for d in dias) or 1
        linhas = ["📅 <b>Vendas por dia (7d)</b>\n━━━━━━━━━━━━━━━━━━━━━━━\n"]

        for d in dias:
            dia = str(d["dia"])[5:]  # MM-DD
            receita = float(d["receita"])
            barra = _barra(receita, max_receita, largura=10)
            linhas.append(
                f"<code>{dia}</code> {barra}\n"
                f"    💰 R$ {receita:.2f} · {d['vendas']} venda(s)\n"
            )

        total_receita = sum(float(d["receita"]) for d in dias)
        total_vendas = sum(int(d["vendas"]) for d in dias)
        linhas.append(
            f"\n📊 <b>Total:</b> {total_vendas} venda(s) · R$ {total_receita:.2f}"
        )
        texto = "\n".join(linhas)

    kb = menus.InlineKeyboardMarkup([
        [menus.InlineKeyboardButton("⬅️ Voltar", callback_data="admin:stats")],
    ])
    await _edit_or_send(query, texto, kb)


# ═══════════════════════════════════════════════
# TOP PRODUTOS
# ═══════════════════════════════════════════════
async def admin_stats_v2_prod_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not is_admin(update.effective_user.id):
        return

    produtos = await db.admin_top_produtos_v2("30d", limit=10)

    if not produtos:
        texto = "🏆 <b>Top produtos</b>\n\n<i>Sem vendas ainda.</i>"
    else:
        max_rec = max(float(p["receita"]) for p in produtos) or 1
        linhas = ["🏆 <b>Top 10 Produtos (30d)</b>\n━━━━━━━━━━━━━━━━━━━━━━━\n"]
        medals = ["🥇", "🥈", "🥉"]

        for i, p in enumerate(produtos):
            pos = medals[i] if i < 3 else f"<b>{i+1}º</b>"
            rec = float(p["receita"])
            barra = _barra(rec, max_rec, largura=10)
            nome = (p["product_name"] or "?")[:30]
            linhas.append(
                f"{pos} <b>{nome}</b>\n"
                f"   {barra}\n"
                f"   💰 R$ {rec:.2f} · {p['qtd']} itens · {p['pedidos']} pedidos\n"
            )
        texto = "\n".join(linhas)

    kb = menus.InlineKeyboardMarkup([
        [menus.InlineKeyboardButton("⬅️ Voltar", callback_data="admin:stats")],
    ])
    await _edit_or_send(query, texto, kb)


# ═══════════════════════════════════════════════
# TOP COMPRADORES
# ═══════════════════════════════════════════════
async def admin_stats_v2_compradores_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not is_admin(update.effective_user.id):
        return

    tops = await db.admin_top_compradores_v2("30d", limit=10)

    if not tops:
        texto = "💎 <b>Top compradores</b>\n\n<i>Ninguém comprou ainda.</i>"
    else:
        max_t = max(float(t["total"]) for t in tops) or 1
        linhas = ["💎 <b>Top 10 Compradores (30d)</b>\n━━━━━━━━━━━━━━━━━━━━━━━\n"]
        medals = ["🥇", "🥈", "🥉"]

        for i, t in enumerate(tops):
            pos = medals[i] if i < 3 else f"<b>{i+1}º</b>"
            nome = (t.get("first_name") or t.get("username") or f"ID {t['user_id']}")[:28]
            total = float(t["total"])
            barra = _barra(total, max_t, largura=10)
            linhas.append(
                f"{pos} <b>{nome}</b>\n"
                f"   {barra}\n"
                f"   💰 R$ {total:.2f} · {t['compras']} compras\n"
            )
        texto = "\n".join(linhas)

    kb = menus.InlineKeyboardMarkup([
        [menus.InlineKeyboardButton("⬅️ Voltar", callback_data="admin:stats")],
    ])
    await _edit_or_send(query, texto, kb)


# ═══════════════════════════════════════════════
# TOP RECARGAS
# ═══════════════════════════════════════════════
async def admin_stats_v2_recargas_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not is_admin(update.effective_user.id):
        return

    tops = await db.admin_top_recargas_v2("30d", limit=10)

    if not tops:
        texto = "💠 <b>Top recargas</b>\n\n<i>Nenhuma recarga ainda.</i>"
    else:
        max_t = max(float(t["total"]) for t in tops) or 1
        linhas = ["💠 <b>Top 10 Recargas (30d)</b>\n━━━━━━━━━━━━━━━━━━━━━━━\n"]
        medals = ["🥇", "🥈", "🥉"]

        for i, t in enumerate(tops):
            pos = medals[i] if i < 3 else f"<b>{i+1}º</b>"
            nome = (t.get("first_name") or t.get("username") or f"ID {t['user_id']}")[:28]
            total = float(t["total"])
            barra = _barra(total, max_t, largura=10)
            linhas.append(
                f"{pos} <b>{nome}</b>\n"
                f"   {barra}\n"
                f"   💰 R$ {total:.2f} · {t['recargas']} recarga(s)\n"
            )
        texto = "\n".join(linhas)

    kb = menus.InlineKeyboardMarkup([
        [menus.InlineKeyboardButton("⬅️ Voltar", callback_data="admin:stats")],
    ])
    await _edit_or_send(query, texto, kb)


# ═══════════════════════════════════════════════
# TOP GIFTS
# ═══════════════════════════════════════════════
async def admin_stats_v2_gifts_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not is_admin(update.effective_user.id):
        return

    tops = await db.admin_top_gifts_v2(limit=10)

    if not tops:
        texto = "🎁 <b>Top gifts</b>\n\n<i>Nenhum gift resgatado ainda.</i>"
    else:
        max_t = max(float(t["total"]) for t in tops) or 1
        linhas = ["🎁 <b>Top 10 Gifts Resgatados</b>\n━━━━━━━━━━━━━━━━━━━━━━━\n"]
        medals = ["🥇", "🥈", "🥉"]

        for i, t in enumerate(tops):
            pos = medals[i] if i < 3 else f"<b>{i+1}º</b>"
            nome = (t.get("first_name") or t.get("username") or f"ID {t['user_id']}")[:28]
            total = float(t["total"])
            barra = _barra(total, max_t, largura=10)
            linhas.append(
                f"{pos} <b>{nome}</b>\n"
                f"   {barra}\n"
                f"   💰 R$ {total:.2f} · {t['gifts']} gift(s)\n"
            )
        texto = "\n".join(linhas)

    kb = menus.InlineKeyboardMarkup([
        [menus.InlineKeyboardButton("⬅️ Voltar", callback_data="admin:stats")],
    ])
    await _edit_or_send(query, texto, kb)


# ═══════════════════════════════════════════════
# CONVERSÃO
# ═══════════════════════════════════════════════
async def admin_stats_v2_conv_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not is_admin(update.effective_user.id):
        return

    c = await db.admin_stats_conversao()

    texto = (
        "📈 <b>Taxa de Conversão</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "🔍 <b>Funil:</b>\n"
        f"├ 👀 Viram produto: <b>{c['visualizou']}</b> users\n"
        f"├ 🛒 Compraram: <b>{c['comprou']}</b> users\n"
        f"└ 👥 Total: <b>{c['total_users']}</b> users\n\n"
        "📊 <b>Taxas:</b>\n"
        f"├ 🎯 Quem viu e comprou: <b>{c['taxa']:.1f}%</b>\n"
        f"└ 🎯 Geral (comprou/total): <b>{c['taxa_geral']:.1f}%</b>\n\n"
        "💡 <b>Dicas:</b>\n"
        "├ Taxa baixa? Melhore a descrição dos produtos\n"
        "├ Adicione mais fotos/imagens\n"
        "└ Use o carrinho abandonado pra recuperar clientes"
    )

    kb = menus.InlineKeyboardMarkup([
        [menus.InlineKeyboardButton("⬅️ Voltar", callback_data="admin:stats")],
    ])
    await _edit_or_send(query, texto, kb)


# ═══════════════════════════════════════════════
# SALDOS
# ═══════════════════════════════════════════════
async def admin_stats_v2_saldos_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not is_admin(update.effective_user.id):
        return

    saldos = await db.admin_stats_saldos()

    total = saldos["bot"] + saldos["web"]

    texto = (
        "💰 <b>Saldos em Circulação</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"├ 🤖 Bot: <b>R$ {saldos['bot']:.2f}</b>\n"
        f"├ 🌐 Web: <b>R$ {saldos['web']:.2f}</b>\n"
        f"└ 💵 Total: <b>R$ {total:.2f}</b>\n\n"
        "⏳ <b>Pendências:</b>\n"
        f"├ 💸 Saques pendentes: <b>R$ {saldos['saques_pendentes']:.2f}</b>\n"
        f"└ 🎁 Gifts livres: <b>R$ {saldos['gifts_livres']:.2f}</b>\n\n"
        "💡 <i>Saldos são valores que os usuários têm disponíveis "
        "e podem usar ou sacar.</i>"
    )

    kb = menus.InlineKeyboardMarkup([
        [menus.InlineKeyboardButton("⬅️ Voltar", callback_data="admin:stats")],
    ])
    await _edit_or_send(query, texto, kb)


# ═══════════════════════════════════════════════
# EXPORTAR RELATÓRIO
# ═══════════════════════════════════════════════
async def admin_stats_v2_export_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not is_admin(update.effective_user.id):
        return

    try:
        periodo = query.data.split(":")[2]
    except IndexError:
        periodo = "30d"

    try:
        csv_text = await db.admin_stats_export_csv(periodo)
        filename = f"relatorio-{periodo}-{datetime.now().strftime('%Y%m%d-%H%M')}.csv"

        await context.bot.send_document(
            chat_id=query.message.chat_id,
            document=InputFile(
                io.BytesIO(csv_text.encode("utf-8")),
                filename=filename,
            ),
            caption=(
                f"📤 <b>Relatório completo</b>\n"
                f"📅 Período: <b>{PERIODO_LABEL.get(periodo, periodo)}</b>"
            ),
            parse_mode=ParseMode.HTML,
        )
        await db.log_admin_action(update.effective_user.id, "stats_export", periodo)
    except Exception as e:
        logger.exception("Erro export stats: %s", e)
        await query.answer(f"❌ Erro: {e}", show_alert=True)
