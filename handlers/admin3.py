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
# ESTATÍSTICAS
# ═══════════════════════════════════════════════
async def admin_stats_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not is_admin(update.effective_user.id):
        return

    stats = await db.admin_stats()
    ticket = await db.admin_ticket_medio()
    saldos = await db.admin_saldo_em_contas()
    carrinhos = await db.admin_carrinhos_pendentes()

    texto = (
        "📊 <b>Estatísticas</b>\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
        f"👥 Usuários: <b>{stats['total_users']}</b>\n"
        f"🚫 Banidos: <b>{stats['total_banned']}</b>\n"
        f"📦 Produtos ativos: <b>{stats['total_produtos']}</b>\n"
        f"🛒 Carrinhos abandonados: <b>{carrinhos}</b>\n\n"

        "💰 <b>Saldo em contas:</b>\n"
        f"├ Bot: <b>R$ {saldos['bot']:.2f}</b>\n"
        f"└ Web: <b>R$ {saldos['web']:.2f}</b>\n\n"

        "📈 <b>Vendas:</b>\n"
        f"├ Total: <b>{stats['total_vendas']}</b>\n"
        f"├ Receita: <b>R$ {stats['receita_total']:.2f}</b>\n"
        f"├ Hoje: <b>R$ {stats['receita_hoje']:.2f}</b>\n"
        f"├ 7 dias: <b>R$ {stats['receita_semana']:.2f}</b>\n"
        f"├ Mês: <b>R$ {stats['receita_mes']:.2f}</b>\n"
        f"└ Ticket médio: <b>R$ {ticket:.2f}</b>"
    )

    await _edit_or_send(query, texto, menus.admin_stats_kb())


async def admin_stats_daily_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not is_admin(update.effective_user.id):
        return

    dias = await db.admin_sales_by_day(7)

    if not dias:
        texto = "📅 <b>Vendas por dia</b>\n\n<i>Sem vendas nos últimos 7 dias.</i>"
    else:
        linhas = ["📅 <b>Vendas por dia (7d)</b>\n━━━━━━━━━━━━━━━━━━━━\n"]
        for d in dias:
            linhas.append(
                f"<code>{d['dia']}</code> — <b>{d['vendas']}</b> vendas — R$ {float(d['receita']):.2f}"
            )
        texto = "\n".join(linhas)

    await _edit_or_send(query, texto, menus.admin_stats_kb())


async def admin_stats_products_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not is_admin(update.effective_user.id):
        return

    produtos = await db.admin_top_products(10)

    if not produtos:
        texto = "🏆 <b>Top produtos</b>\n\n<i>Sem vendas ainda.</i>"
    else:
        linhas = ["🏆 <b>Top produtos</b>\n━━━━━━━━━━━━━━━━━━━━\n"]
        medals = ["🥇", "🥈", "🥉"]
        for i, p in enumerate(produtos):
            pos = medals[i] if i < 3 else f"{i+1}º"
            linhas.append(
                f"{pos} <b>{p['product_name'][:35]}</b>\n"
                f"    {p['qtd']} vendas — R$ {float(p['receita']):.2f}"
            )
        texto = "\n".join(linhas)

    await _edit_or_send(query, texto, menus.admin_stats_kb())


async def admin_stats_spenders_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not is_admin(update.effective_user.id):
        return

    tops = await db.admin_top_spenders(10)

    if not tops:
        texto = "💎 <b>Top compradores</b>\n\n<i>Ninguém comprou ainda.</i>"
    else:
        linhas = ["💎 <b>Top compradores</b>\n━━━━━━━━━━━━━━━━━━━━\n"]
        medals = ["🥇", "🥈", "🥉"]
        for i, u in enumerate(tops):
            pos = medals[i] if i < 3 else f"{i+1}º"
            nome = u.get("first_name") or u.get("username") or f"ID {u['user_id']}"
            linhas.append(
                f"{pos} <b>{nome[:30]}</b> — <code>{u['user_id']}</code>\n"
                f"    {u['compras']} compras — R$ {float(u['total']):.2f}"
            )
        texto = "\n".join(linhas)

    await _edit_or_send(query, texto, menus.admin_stats_kb())


# ═══════════════════════════════════════════════
# CONFIGURAÇÕES
# ═══════════════════════════════════════════════
async def admin_config_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not is_admin(update.effective_user.id):
        return

    cfg = await db.admin_load_config()

    def get(k, d):
        return cfg.get(k, d)

    texto = (
        "⚙️ <b>Configurações</b>\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
        f"🏪 Nome: <b>{get('store_name', 'Larizinha Store')}</b>\n"
        f"📄 CNPJ: <code>{get('cnpj', '—')}</code>\n"
        f"🕐 Horário: <b>{get('horario', '—')}</b>\n"
        f"📱 WhatsApp: <code>{get('whatsapp_link', '—')[:40]}</code>\n"
        f"💬 Telegram: <code>{get('telegram_link', '—')[:40]}</code>\n\n"
        f"🎁 Bônus recarga: <b>{get('bonus_rate', '10')}%</b>\n"
        f"💵 Recarga mínima: <b>R$ {get('topup_min', '4.00')}</b>\n"
        f"💸 Saque mínimo: <b>R$ {get('withdraw_min', '20.00')}</b>\n"
        f"🧲 Comissão afiliado: <b>{get('commission', '20')}%</b>\n\n"
        "Toque em um item pra editar:"
    )

    await _edit_or_send(query, texto, menus.admin_config_kb())


async def admin_cfg_edit_prompt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not is_admin(update.effective_user.id):
        return

    chave = query.data.split(":")[2]  # admin:cfg:<chave>
    context.user_data["admin_cfg_edit"] = chave

    labels = {
        "store_name":    "🏪 Nome da loja",
        "cnpj":          "📄 CNPJ",
        "horario":       "🕐 Horário",
        "whatsapp_link": "📱 Link do WhatsApp",
        "telegram_link": "💬 Link do Telegram",
        "bonus_rate":    "🎁 Bônus recarga (%)",
        "topup_min":     "💵 Recarga mínima (R$)",
        "withdraw_min":  "💸 Saque mínimo (R$)",
        "commission":    "🧲 Comissão afiliado (%)",
    }

    try:
        await query.edit_message_text(
            f"✏️ <b>{labels.get(chave, chave)}</b>\n\n"
            "Envie o novo valor:",
            reply_markup=ForceReply(selective=True),
            parse_mode=ParseMode.HTML,
        )
    except Exception:
        pass


async def admin_cfg_edit_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chave = context.user_data.get("admin_cfg_edit")
    if not chave:
        return
    if not is_admin(update.effective_user.id):
        return

    valor = (update.message.text or "").strip()
    if not valor:
        await update.message.reply_text("❌ Valor vazio.")
        return

    context.user_data.pop("admin_cfg_edit", None)

    await db.admin_set_config(chave, valor)
    # Atualiza o cache imediatamente
    cache.set_config(chave, valor)
    await db.log_admin_action(update.effective_user.id, "config_edit", chave, valor)

    await update.message.reply_text(
        f"✅ <b>Configuração atualizada!</b>\n\n"
        f"<b>{chave}</b> = <code>{valor}</code>",
        reply_markup=menus.admin_back_kb(),
        parse_mode=ParseMode.HTML,
    )


# ═══════════════════════════════════════════════
# EDITAR TEXTOS
# ═══════════════════════════════════════════════
async def admin_texts_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not is_admin(update.effective_user.id):
        return

    textos = await db.admin_list_texts()

    texto = (
        f"📝 <b>Textos do Bot</b> ({len([t for t in textos if not t['key'].startswith('__')])})\n"
        f"━━━━━━━━━━━━━━━━━━━━\n\n"
        "Toque em um texto pra ver/editar:"
    )
    await _edit_or_send(query, texto, menus.admin_texts_kb(textos))


async def admin_text_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not is_admin(update.effective_user.id):
        return

    key = query.data.split(":", 2)[2]
    valor = await db.admin_get_text(key)
    if valor is None:
        await _edit_or_send(query, "❌ Texto não encontrado.", menus.admin_back_kb())
        return

    preview = valor[:800] + ("..." if len(valor) > 800 else "")

    texto = (
        f"📝 <b>{key}</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n\n"
        f"{preview}"
    )
    await _edit_or_send(query, texto, menus.admin_text_edit_kb(key))


async def admin_text_edit_prompt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not is_admin(update.effective_user.id):
        return

    key = query.data.split(":", 2)[2]
    context.user_data["admin_text_edit"] = key

    try:
        await query.edit_message_text(
            f"✏️ <b>Editando: {key}</b>\n\n"
            "Envie o novo texto.\n"
            "<i>Você pode usar HTML: &lt;b&gt;negrito&lt;/b&gt;, &lt;i&gt;itálico&lt;/i&gt;, emoji.</i>\n\n"
            "Variáveis disponíveis dependem do texto (ex: {balance}, {user_id}, {store_name}).",
            reply_markup=ForceReply(selective=True),
            parse_mode=ParseMode.HTML,
        )
    except Exception:
        pass


async def admin_text_edit_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    key = context.user_data.get("admin_text_edit")
    if not key:
        return
    if not is_admin(update.effective_user.id):
        return

    valor = update.message.text or update.message.caption or ""
    if not valor.strip():
        await update.message.reply_text("❌ Texto vazio.")
        return

    context.user_data.pop("admin_text_edit", None)

    await db.admin_update_text(key, valor)
    # Atualiza o cache em tempo real
    cache.set_text(key, valor)
    await db.log_admin_action(update.effective_user.id, "text_edit", key)

    await update.message.reply_text(
        f"✅ <b>Texto atualizado!</b>\n\n"
        f"<b>{key}</b> agora tem {len(valor)} caracteres.",
        reply_markup=menus.admin_back_kb(),
        parse_mode=ParseMode.HTML,
    )


# ═══════════════════════════════════════════════
# EDITAR BOTÕES
# ═══════════════════════════════════════════════
async def admin_buttons_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not is_admin(update.effective_user.id):
        return

    botoes = await db.admin_list_buttons()

    texto = (
        f"🔘 <b>Botões do Bot</b> ({len(botoes)})\n"
        f"━━━━━━━━━━━━━━━━━━━━\n\n"
        "Toque em um botão pra ver/editar:"
    )
    await _edit_or_send(query, texto, menus.admin_buttons_kb(botoes))


async def admin_button_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not is_admin(update.effective_user.id):
        return

    key = query.data.split(":", 2)[2]
    valor = await db.admin_get_button(key)
    if valor is None:
        await _edit_or_send(query, "❌ Botão não encontrado.", menus.admin_back_kb())
        return

    texto = (
        f"🔘 <b>Botão</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n\n"
        f"Chave: <code>{key}</code>\n"
        f"Valor: <b>{valor}</b>"
    )
    await _edit_or_send(query, texto, menus.admin_button_edit_kb(key))


async def admin_btn_edit_prompt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not is_admin(update.effective_user.id):
        return

    key = query.data.split(":", 2)[2]
    context.user_data["admin_btn_edit"] = key

    try:
        await query.edit_message_text(
            f"✏️ <b>Editando botão: {key}</b>\n\n"
            "Envie o novo texto do botão (com emoji se quiser):",
            reply_markup=ForceReply(selective=True),
            parse_mode=ParseMode.HTML,
        )
    except Exception:
        pass


async def admin_btn_edit_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    key = context.user_data.get("admin_btn_edit")
    if not key:
        return
    if not is_admin(update.effective_user.id):
        return

    valor = (update.message.text or "").strip()
    if not valor:
        await update.message.reply_text("❌ Texto vazio.")
        return

    context.user_data.pop("admin_btn_edit", None)

    await db.admin_update_button(key, valor)
    cache.set_button(key, valor)
    await db.log_admin_action(update.effective_user.id, "button_edit", key, valor)

    await update.message.reply_text(
        f"✅ <b>Botão atualizado!</b>\n\n"
        f"<b>{key}</b> agora é <b>{valor}</b>",
        reply_markup=menus.admin_back_kb(),
        parse_mode=ParseMode.HTML,
    )


# ═══════════════════════════════════════════════
# BANNER (imagem do welcome)
# ═══════════════════════════════════════════════
async def admin_banner_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not is_admin(update.effective_user.id):
        return

    file_id = await db.admin_get_banner()

    texto = (
        "🖼️ <b>Banner do Menu Principal</b>\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
    )
    if file_id:
        texto += "✅ Banner configurado."
    else:
        texto += "❌ Nenhum banner configurado."

    texto += "\n\nEscolha uma ação:"
    await _edit_or_send(query, texto, menus.admin_banner_kb())


async def admin_banner_new_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not is_admin(update.effective_user.id):
        return

    context.user_data["admin_banner_new"] = True

    try:
        await query.edit_message_text(
            "🖼️ <b>Enviar novo banner</b>\n\n"
            "Envie a imagem agora (foto ou arquivo PNG/JPG):",
            parse_mode=ParseMode.HTML,
        )
    except Exception:
        pass


async def admin_banner_photo_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Recebe a foto do banner quando admin_banner_new está ativo."""
    if not context.user_data.get("admin_banner_new"):
        return
    if not is_admin(update.effective_user.id):
        return

    # Aceita foto ou documento (imagem)
    file_id = None
    if update.message.photo:
        file_id = update.message.photo[-1].file_id
    elif update.message.document:
        file_id = update.message.document.file_id
    elif update.message.sticker:
        file_id = update.message.sticker.file_id

    if not file_id:
        await update.message.reply_text("❌ Envie uma imagem válida.")
        return

    context.user_data.pop("admin_banner_new", None)

    await db.admin_set_banner(file_id)
    cache.set_text("__banner__", file_id)
    await db.log_admin_action(update.effective_user.id, "banner_set")

    await update.message.reply_text(
        "✅ <b>Banner atualizado!</b>",
        reply_markup=menus.admin_back_kb(),
        parse_mode=ParseMode.HTML,
    )


async def admin_banner_del_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not is_admin(update.effective_user.id):
        return

    await db.admin_set_banner("")
    cache.set_text("__banner__", "")
    await db.log_admin_action(update.effective_user.id, "banner_del")

    await _edit_or_send(query, "✅ Banner removido.", menus.admin_back_kb())
