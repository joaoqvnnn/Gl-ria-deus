from urllib.parse import quote
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo
from config import CHANNEL_LINK, SUPPORT_LINK, SUPPORT_MESSAGE, MINIAPP_BASE_URL


# ═══════════════════════════════════════════════
# HELPERS
# ═══════════════════════════════════════════════
def _support_url() -> str:
    if not SUPPORT_LINK:
        return "https://t.me/"
    return f"{SUPPORT_LINK}?text={quote(SUPPORT_MESSAGE)}"


def _btn(key: str, default: str) -> str:
    """Nome do botão lido do banco (com fallback)."""
    try:
        from texts import cache
        return cache.get_button(key, default)
    except Exception:
        return default


def _copy_button(text: str, label: str = "📋 Copiar PIX", fallback_data: str = "") -> InlineKeyboardButton:
    """Tenta usar CopyTextButton (PTB 21.2+). Se não der, usa callback."""
    try:
        from telegram import CopyTextButton
        return InlineKeyboardButton(label, copy_text=CopyTextButton(text=text))
    except Exception:
        return InlineKeyboardButton(label, callback_data=fallback_data)


# ═══════════════════════════════════════════════
# MÓDULO 1 — GATE, MENU, CATÁLOGO, PRODUTO
# ═══════════════════════════════════════════════

def gate_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("➡️ ENTRAR NO CANAL", url=CHANNEL_LINK)]
    ])


def main_menu_keyboard(user_id: int | None = None) -> InlineKeyboardMarkup:
    if user_id:
        loja_url = f"{MINIAPP_BASE_URL}/loja/{user_id}"
        loja_btn = InlineKeyboardButton(
            _btn("btn_store", "🛒 Abrir Loja"),
            web_app=WebAppInfo(url=loja_url),
        )
    else:
        loja_btn = InlineKeyboardButton(
            _btn("btn_store", "🛒 Abrir Loja"),
            callback_data="menu:store",
        )

    return InlineKeyboardMarkup([
        [InlineKeyboardButton(_btn("btn_catalog", "🛍 Comprar Produtos"), callback_data="menu:catalog")],
        [loja_btn],
        [
            InlineKeyboardButton(_btn("btn_profile", "👤 Meu Perfil"), callback_data="menu:profile"),
            InlineKeyboardButton(_btn("btn_topup", "💠 Recarregar Saldo"), callback_data="menu:topup"),
        ],
        [
            InlineKeyboardButton(_btn("btn_affiliates", "👥 Afiliados"), callback_data="menu:affiliates"),
            InlineKeyboardButton(_btn("btn_top", "🏆 Top Compradores"), callback_data="menu:top"),
        ],
        [InlineKeyboardButton(_btn("btn_support", "📩 Atendimento"), url=_support_url())],
        [
            InlineKeyboardButton(_btn("btn_about", "🤖 Sobre o Bot"), callback_data="menu:about"),
            InlineKeyboardButton(_btn("btn_search", "🔎 Pesquisar Serviços"), callback_data="menu:search"),
        ],
    ])


def catalog_keyboard(products: list[dict]) -> InlineKeyboardMarkup:
    rows = []
    for p in products:
        price = float(p["price"])
        label = f"{p['emoji']} {p['name']} — R$ {price:.2f}"
        if len(label) > 60:
            label = label[:57] + "..."
        rows.append([InlineKeyboardButton(label, callback_data=f"prod:{p['id']}")])
    rows.append([InlineKeyboardButton(_btn("btn_back", "⬅️ VOLTAR"), callback_data="menu:home")])
    return InlineKeyboardMarkup(rows)


def product_keyboard(pid: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(_btn("btn_buy", "🛒 COMPRAR"), callback_data=f"buy:{pid}")],
        [InlineKeyboardButton(_btn("btn_buymulti", "🛒 Comprar mais de um"), callback_data=f"buymulti:{pid}")],
        [InlineKeyboardButton(_btn("btn_back", "⬅️ VOLTAR"), callback_data="menu:catalog")],
    ])


def back_to_menu_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(_btn("btn_back", "⬅️ VOLTAR"), callback_data="menu:home")]
    ])


# ═══════════════════════════════════════════════
# MÓDULO 2 — COMPRA, PIX, MULTI, ENTREGA
# ═══════════════════════════════════════════════

def insufficient_keyboard(product_id: int, quantity: int, total: float) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(
            f"💠 Gerar PIX de R$ {total:.2f}",
            callback_data=f"pix:gen:{product_id}:{quantity}",
        )],
        [InlineKeyboardButton("❌ Cancelar", callback_data="pix:new_cancel")],
    ])


def pix_keyboard(pix_id: str, copia_cola: str = "") -> InlineKeyboardMarkup:
    copy_btn = _copy_button(copia_cola or "", "📋 Copiar PIX", f"pix:copy:{pix_id}")
    return InlineKeyboardMarkup([
        [copy_btn],
        [InlineKeyboardButton("⏰ AGUARDANDO PAGAMENTO", callback_data=f"pix:check:{pix_id}")],
        [InlineKeyboardButton("❌ Cancelar", callback_data=f"pix:cancel:{pix_id}")],
    ])


def multi_confirm_keyboard(product_id: int, qty: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(
            "✅ Confirmar Compra",
            callback_data=f"multi:confirm:{product_id}:{qty}",
        )],
        [InlineKeyboardButton("❌ Cancelar", callback_data="multi:cancel")],
    ])


def delivery_keyboard(purchase_id: str, activate_url: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🔓 VER PRODUTO", callback_data=f"delivery:reveal:{purchase_id}")],
        [InlineKeyboardButton("🔗 CLIQUE AQUI PARA ATIVAR", url=activate_url or "https://t.me/")],
    ])


def delivery_revealed_keyboard(purchase_id: str, activate_url: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🔗 CLIQUE AQUI PARA ATIVAR", url=activate_url or "https://t.me/")],
    ])


# ═══════════════════════════════════════════════
# MÓDULO 3 — PERFIL, HISTÓRICO, GIFT, DADOS, RECARGA
# ═══════════════════════════════════════════════

def profile_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📜 Histórico de Compras", callback_data="profile:history")],
        [InlineKeyboardButton("🎁 Resgatar Gift Card", callback_data="profile:gift")],
        [InlineKeyboardButton("✏️ Alterar dados", callback_data="profile:alter")],
        [InlineKeyboardButton(_btn("btn_back_to_profile", "⬅️ VOLTAR"), callback_data="menu:home")],
    ])


def history_empty_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🟢 Apenas Ativas", callback_data="hist:active:0")],
        [InlineKeyboardButton(_btn("btn_back_to_profile", "⬅️ VOLTAR"), callback_data="menu:profile")],
    ])


def history_active_empty_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📋 Ver Todas", callback_data="hist:all:0")],
        [InlineKeyboardButton(_btn("btn_back_to_profile", "⬅️ VOLTAR"), callback_data="menu:profile")],
    ])


def history_item_keyboard(
    purchase_id: str,
    activate_url: str,
    page: int,
    pages: int,
    only_active: bool,
) -> InlineKeyboardMarkup:
    rows = [
        [InlineKeyboardButton("🔗 CLIQUE AQUI PARA ATIVAR", url=activate_url or "https://t.me/")],
    ]

    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton(
            "<< Voltar",
            callback_data=f"hist:{'active' if only_active else 'all'}:{page - 1}",
        ))
    nav.append(InlineKeyboardButton(f"📄 {page + 1}/{pages}", callback_data="hist:noop"))
    if page < pages - 1:
        nav.append(InlineKeyboardButton(
            "Avançar >>",
            callback_data=f"hist:{'active' if only_active else 'all'}:{page + 1}",
        ))
    rows.append(nav)

    if only_active:
        rows.append([InlineKeyboardButton("📋 Ver Todas", callback_data="hist:all:0")])
    else:
        rows.append([InlineKeyboardButton("🟢 Apenas Ativas", callback_data="hist:active:0")])

    rows.append([InlineKeyboardButton(_btn("btn_back_to_profile", "⬅️ VOLTAR"), callback_data="menu:profile")])
    return InlineKeyboardMarkup(rows)


def gift_cancel_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(_btn("btn_gift_cancel", "❌ Cancelar"), callback_data="gift:cancel")],
    ])


def gift_success_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(_btn("btn_gift_use", "🎁 Usar"), callback_data="gift:use")],
    ])


def alter_data_keyboard(user: dict) -> InlineKeyboardMarkup:
    whats = user.get("whatsapp") or "Não cadastrado"
    label = f"📱 WhatsApp: {whats}"
    if len(label) > 60:
        label = label[:57] + "..."
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(label, callback_data="alter:whatsapp")],
        [InlineKeyboardButton(_btn("btn_back_to_profile", "⬅️ VOLTAR"), callback_data="menu:profile")],
    ])


def alter_data_cancel_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(_btn("btn_back_to_profile", "⬅️ VOLTAR"), callback_data="menu:profile")],
    ])


def topup_menu_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("💠 PIX RÁPIDO", callback_data="topup:pix")],
        [InlineKeyboardButton(_btn("btn_back", "⬅️ VOLTAR"), callback_data="menu:home")],
    ])


def topup_pix_keyboard(pix_id: str, copia_cola: str = "") -> InlineKeyboardMarkup:
    copy_btn = _copy_button(copia_cola or "", "📋 Copiar PIX", f"toppix:copy:{pix_id}")
    return InlineKeyboardMarkup([
        [copy_btn],
        [InlineKeyboardButton("⏰ AGUARDANDO PAGAMENTO", callback_data=f"toppix:check:{pix_id}")],
        [InlineKeyboardButton("❌ Cancelar", callback_data=f"toppix:cancel:{pix_id}")],
    ])


def topup_success_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🛒 Comprar", callback_data="menu:catalog")],
        [InlineKeyboardButton("👤 Meu Perfil", callback_data="menu:profile")],
    ])


# ═══════════════════════════════════════════════
# MÓDULO 4 — AFILIADOS, SAQUES, TOP, PESQUISA
# ═══════════════════════════════════════════════

def affiliates_inactive_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ Me Filiar", callback_data="aff:join")],
        [InlineKeyboardButton(_btn("btn_back", "⬅️ Voltar"), callback_data="menu:home")],
    ])


def affiliates_active_keyboard(user_id: int | None = None) -> InlineKeyboardMarkup:
    if user_id:
        senha_url = f"{MINIAPP_BASE_URL}/miniapp/senha/{user_id}"
        setpin_btn = InlineKeyboardButton(
            "🔐 Cadastrar Senha de Saque",
            web_app=WebAppInfo(url=senha_url),
        )
    else:
        setpin_btn = InlineKeyboardButton(
            "🔐 Cadastrar Senha de Saque",
            callback_data="aff:setpin",
        )

    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📜 Histórico de Saque", callback_data="aff:whist")],
        [InlineKeyboardButton("💸 Saques", callback_data="aff:withdraw")],
        [setpin_btn],
        [InlineKeyboardButton(_btn("btn_back", "⬅️ Voltar"), callback_data="menu:home")],
    ])


def withdraw_type_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📧 Email", callback_data="wd:type:email")],
        [InlineKeyboardButton("🆔 CPF", callback_data="wd:type:cpf")],
        [InlineKeyboardButton("📱 Telefone", callback_data="wd:type:phone")],
        [InlineKeyboardButton("🔑 Chave Aleatória", callback_data="wd:type:random")],
        [InlineKeyboardButton(_btn("btn_back", "⬅️ Voltar"), callback_data="aff:menu")],
    ])


def withdraw_confirm_key_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ Confirmar Chave PIX", callback_data="wd:confirm_key")],
        [InlineKeyboardButton("✏️ Editar Chave PIX", callback_data="wd:edit_key")],
        [InlineKeyboardButton("❌ Cancelar", callback_data="aff:menu")],
    ])


def withdraw_balance_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("💸 Sacar", callback_data="wd:sacar")],
        [InlineKeyboardButton(_btn("btn_back", "⬅️ Voltar"), callback_data="aff:menu")],
    ])


def withdraw_amount_cancel_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("❌ Cancelar", callback_data="aff:menu")],
    ])


def withdraw_success_keyboard(wid: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📄 PDF", callback_data="aff:whist")],
        [InlineKeyboardButton(_btn("btn_back", "⬅️ Voltar"), callback_data="aff:menu")],
    ])


def top_keyboard(current: str = "compras") -> InlineKeyboardMarkup:
    def check(key):
        return "✅ " if key == current else ""

    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton(f"{check('compras')}Compras",   callback_data="top:compras"),
            InlineKeyboardButton(f"{check('recargas')}Recargas", callback_data="top:recargas"),
        ],
        [
            InlineKeyboardButton(f"{check('gift')}Gift card",    callback_data="top:gift"),
            InlineKeyboardButton(f"{check('saldo')}Saldo",       callback_data="top:saldo"),
        ],
        [InlineKeyboardButton(_btn("btn_back", "⬅️ VOLTAR"), callback_data="menu:home")],
    ])


# ═══════════════════════════════════════════════
# AÇÕES DIRETAS
# ═══════════════════════════════════════════════

def direct_product_keyboard(product_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(
            "🛒 Comprar agora",
            callback_data=f"direct:product:{product_id}",
        )],
    ])


def direct_product_two_keyboard(product_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(
            "🛒 Comprar agora",
            callback_data=f"direct:product:{product_id}",
        )],
        [InlineKeyboardButton(
            "👀 Ver detalhes",
            callback_data=f"direct:product:{product_id}",
        )],
    ])


def direct_catalog_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🛍 Ver promoção", callback_data="direct:catalog")],
    ])


def direct_gift_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🎁 Resgatar Gift Card", callback_data="direct:gift")],
    ])


def direct_topup_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("💠 Recarregar agora", callback_data="direct:topup")],
    ])


def direct_start_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ Me cadastrar", callback_data="direct:start")],
    ])


def direct_custom_keyboard(buttons: list[list[dict]]) -> InlineKeyboardMarkup:
    rows = []
    for row in buttons:
        line = []
        for b in row:
            if b.get("url"):
                line.append(InlineKeyboardButton(b["text"], url=b["url"]))
            else:
                line.append(InlineKeyboardButton(
                    b["text"],
                    callback_data=b.get("action", "noop"),
                ))
        rows.append(line)
    return InlineKeyboardMarkup(rows)


# ═══════════════════════════════════════════════
# ADMIN — MÓDULO 1 — DASHBOARD / USUÁRIOS
# ═══════════════════════════════════════════════

def admin_dashboard_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("👥 Usuários", callback_data="admin:users")],
        [InlineKeyboardButton("📦 Produtos", callback_data="admin:products")],
        [InlineKeyboardButton("🛒 Vendas", callback_data="admin:purchases")],
        [
            InlineKeyboardButton("🎁 Gift Cards", callback_data="admin:gifts"),
            InlineKeyboardButton("💸 Saques", callback_data="admin:withdrawals"),
        ],
        [
            InlineKeyboardButton("👥 Afiliados", callback_data="admin:affiliates"),
            InlineKeyboardButton("🛍 Carrinhos", callback_data="admin:abandoned"),
        ],
        [InlineKeyboardButton("📊 Estatísticas", callback_data="admin:stats")],
        [InlineKeyboardButton("📢 Broadcast", callback_data="admin:broadcast")],
        [InlineKeyboardButton("📝 Textos", callback_data="admin:texts")],
        [InlineKeyboardButton("🔘 Botões", callback_data="admin:buttons")],
        [InlineKeyboardButton("🖼️ Banner", callback_data="admin:banner")],
        [InlineKeyboardButton("⚙️ Configurações", callback_data="admin:config")],
        [
            InlineKeyboardButton("🛡 Sub-Admins", callback_data="admin:subadmins"),
            InlineKeyboardButton("📤 Exportar", callback_data="admin:export"),
        ],
        [
            InlineKeyboardButton("🚧 Manutenção", callback_data="admin:maintenance"),
            InlineKeyboardButton("📋 Logs", callback_data="admin:logs"),
        ],
        [InlineKeyboardButton("💾 Backup do banco", callback_data="admin:backup")],
        [InlineKeyboardButton("🔄 Atualizar", callback_data="admin:home")],
    ])


def admin_back_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("⬅️ Voltar ao Painel", callback_data="admin:home")],
    ])


def admin_users_kb(users: list[dict]) -> InlineKeyboardMarkup:
    rows = []
    for u in users:
        nome = u.get("first_name") or u.get("username") or f"ID {u['user_id']}"
        ban_icon = "🚫 " if u.get("banned") else ""
        label = f"{ban_icon}{nome} — R$ {float(u.get('balance') or 0):.2f}"
        if len(label) > 60:
            label = label[:57] + "..."
        rows.append([InlineKeyboardButton(label, callback_data=f"admin:user:{u['user_id']}")])

    rows.append([InlineKeyboardButton("🔍 Buscar usuário", callback_data="admin:user_search")])
    rows.append([InlineKeyboardButton("⬅️ Voltar", callback_data="admin:home")])
    return InlineKeyboardMarkup(rows)


def admin_user_kb(user_id: int, banned: bool = False) -> InlineKeyboardMarkup:
    rows = [
        [InlineKeyboardButton("➕ Adicionar saldo", callback_data=f"admin:add_balance:{user_id}")],
        [InlineKeyboardButton("➖ Remover saldo", callback_data=f"admin:rem_balance:{user_id}")],
        [InlineKeyboardButton("✉️ Enviar mensagem", callback_data=f"admin:msg_user:{user_id}")],
    ]
    if banned:
        rows.append([InlineKeyboardButton("✅ Desbanir", callback_data=f"admin:unban:{user_id}")])
    else:
        rows.append([InlineKeyboardButton("🚫 Banir", callback_data=f"admin:ban:{user_id}")])

    rows.append([InlineKeyboardButton("⬅️ Voltar", callback_data="admin:users")])
    return InlineKeyboardMarkup(rows)


def admin_broadcast_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📢 Todos", callback_data="admin:bc_all")],
        [InlineKeyboardButton("🛒 Só compradores", callback_data="admin:bc_buyers")],
        [InlineKeyboardButton("💤 Inativos (7d+)", callback_data="admin:bc_inactive")],
        [InlineKeyboardButton("⬅️ Voltar", callback_data="admin:home")],
    ])


def admin_maintenance_kb(ativo: bool) -> InlineKeyboardMarkup:
    label = "🟢 Desligar manutenção" if ativo else "🔴 Ligar manutenção"
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(label, callback_data="admin:toggle_maintenance")],
        [InlineKeyboardButton("⬅️ Voltar", callback_data="admin:home")],
    ])


# ═══════════════════════════════════════════════
# ADMIN — MÓDULO 2 — VENDAS / GIFTS / SAQUES / AFILIADOS
# ═══════════════════════════════════════════════

def admin_purchases_kb(purchases: list[dict]) -> InlineKeyboardMarkup:
    rows = []
    for p in purchases:
        status_icon = "🟢" if p.get("status") != "cancelled" else "🔴"
        label = f"{status_icon} {p['product_name'][:25]} — R$ {float(p['total']):.2f}"
        if len(label) > 60:
            label = label[:57] + "..."
        rows.append([InlineKeyboardButton(label, callback_data=f"admin:purchase:{p['id']}")])

    rows.append([InlineKeyboardButton("🔍 Buscar pedido", callback_data="admin:purchase_search")])
    rows.append([InlineKeyboardButton("⬅️ Voltar", callback_data="admin:home")])
    return InlineKeyboardMarkup(rows)


def admin_purchase_kb(purchase_id: str, cancelled: bool = False) -> InlineKeyboardMarkup:
    rows = []
    if not cancelled:
        rows.append([InlineKeyboardButton("💰 Reembolsar", callback_data=f"admin:refund:{purchase_id}")])
    rows.append([InlineKeyboardButton("📤 Reenviar credenciais", callback_data=f"admin:resend:{purchase_id}")])
    rows.append([InlineKeyboardButton("⬅️ Voltar", callback_data="admin:purchases")])
    return InlineKeyboardMarkup(rows)


def admin_gifts_kb(gifts: list[dict]) -> InlineKeyboardMarkup:
    rows = []
    for g in gifts:
        if g.get("redeemed_by"):
            status_icon, info = "🔴", "resgatado"
        else:
            status_icon, info = "🟢", "livre"
        label = f"{status_icon} {g['code']} — {info}"
        rows.append([InlineKeyboardButton(label, callback_data=f"admin:gift:{g['code']}")])

    rows.append([InlineKeyboardButton("➕ Criar gift cards", callback_data="admin:gift_create")])
    rows.append([InlineKeyboardButton("⬅️ Voltar", callback_data="admin:home")])
    return InlineKeyboardMarkup(rows)


def admin_gift_kb(code: str, redeemed: bool = False) -> InlineKeyboardMarkup:
    rows = []
    if not redeemed:
        rows.append([InlineKeyboardButton("🗑️ Revogar", callback_data=f"admin:gift_del:{code}")])
    rows.append([InlineKeyboardButton("⬅️ Voltar", callback_data="admin:gifts")])
    return InlineKeyboardMarkup(rows)


def admin_gift_type_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("💰 Gift de saldo", callback_data="admin:gift_tipo:saldo")],
        [InlineKeyboardButton("🎁 Gift de produto", callback_data="admin:gift_tipo:produto")],
        [InlineKeyboardButton("⬅️ Voltar", callback_data="admin:gifts")],
    ])


def admin_withdrawals_kb(wds: list[dict]) -> InlineKeyboardMarkup:
    rows = []
    for w in wds:
        icon = {
            "pending": "🟡",
            "processed": "🟢",
            "rejected": "🔴",
        }.get(w.get("status"), "⚪")
        label = f"{icon} R$ {float(w['amount']):.2f} — {w['pix_key_type'] or '—'}"
        if len(label) > 60:
            label = label[:57] + "..."
        rows.append([InlineKeyboardButton(label, callback_data=f"admin:wd:{w['id']}")])

    rows.append([InlineKeyboardButton("⬅️ Voltar", callback_data="admin:home")])
    return InlineKeyboardMarkup(rows)


def admin_withdrawal_kb(wid: str, status: str) -> InlineKeyboardMarkup:
    rows = []
    if status == "pending":
        rows.append([InlineKeyboardButton("✅ Aprovar", callback_data=f"admin:wd_ok:{wid}")])
        rows.append([InlineKeyboardButton("❌ Rejeitar", callback_data=f"admin:wd_no:{wid}")])
    rows.append([InlineKeyboardButton("⬅️ Voltar", callback_data="admin:withdrawals")])
    return InlineKeyboardMarkup(rows)


def admin_affiliates_kb(affiliates: list[dict]) -> InlineKeyboardMarkup:
    rows = []
    for a in affiliates:
        nome = a.get("first_name") or a.get("username") or f"ID {a['user_id']}"
        label = f"👤 {nome[:30]} — R$ {float(a.get('total_ganho') or 0):.2f}"
        if len(label) > 60:
            label = label[:57] + "..."
        rows.append([InlineKeyboardButton(label, callback_data=f"admin:aff:{a['user_id']}")])

    rows.append([InlineKeyboardButton("⬅️ Voltar", callback_data="admin:home")])
    return InlineKeyboardMarkup(rows)


def admin_affiliate_kb(user_id: int, ativo: bool) -> InlineKeyboardMarkup:
    rows = []
    if ativo:
        rows.append([InlineKeyboardButton("🚫 Desativar afiliado", callback_data=f"admin:aff_off:{user_id}")])
    else:
        rows.append([InlineKeyboardButton("✅ Ativar afiliado", callback_data=f"admin:aff_on:{user_id}")])
    rows.append([InlineKeyboardButton("⬅️ Voltar", callback_data="admin:affiliates")])
    return InlineKeyboardMarkup(rows)


# ═══════════════════════════════════════════════
# ADMIN — MÓDULO 3 — ESTATÍSTICAS / CONFIG / TEXTOS / BOTÕES / BANNER
# ═══════════════════════════════════════════════

def admin_stats_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📅 Vendas por dia", callback_data="admin:stats_daily")],
        [InlineKeyboardButton("🏆 Top produtos", callback_data="admin:stats_products")],
        [InlineKeyboardButton("💎 Top compradores", callback_data="admin:stats_spenders")],
        [InlineKeyboardButton("⬅️ Voltar", callback_data="admin:home")],
    ])


def admin_config_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🏪 Nome da loja", callback_data="admin:cfg:store_name")],
        [InlineKeyboardButton("📄 CNPJ", callback_data="admin:cfg:cnpj")],
        [InlineKeyboardButton("🕐 Horário", callback_data="admin:cfg:horario")],
        [InlineKeyboardButton("📱 WhatsApp", callback_data="admin:cfg:whatsapp_link")],
        [InlineKeyboardButton("💬 Telegram", callback_data="admin:cfg:telegram_link")],
        [InlineKeyboardButton("🎁 Bônus recarga (%)", callback_data="admin:cfg:bonus_rate")],
        [InlineKeyboardButton("💵 Recarga mínima", callback_data="admin:cfg:topup_min")],
        [InlineKeyboardButton("💸 Saque mínimo", callback_data="admin:cfg:withdraw_min")],
        [InlineKeyboardButton("🧲 Comissão afiliado (%)", callback_data="admin:cfg:commission")],
        [InlineKeyboardButton("⬅️ Voltar", callback_data="admin:home")],
    ])


def admin_texts_kb(texts: list[dict]) -> InlineKeyboardMarkup:
    rows = []
    for t in texts:
        if t["key"].startswith("__"):
            continue
        label = t["key"]
        if len(label) > 40:
            label = label[:37] + "..."
        rows.append([InlineKeyboardButton(f"📝 {label}", callback_data=f"admin:text:{t['key']}")])

    rows.append([InlineKeyboardButton("⬅️ Voltar", callback_data="admin:home")])
    return InlineKeyboardMarkup(rows)


def admin_text_edit_kb(key: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("✏️ Editar", callback_data=f"admin:text_edit:{key}")],
        [InlineKeyboardButton("⬅️ Voltar", callback_data="admin:texts")],
    ])


def admin_buttons_kb(buttons: list[dict]) -> InlineKeyboardMarkup:
    rows = []
    for b in buttons:
        label = f"🔘 {b['key']} = {b['value'][:25]}"
        if len(label) > 60:
            label = label[:57] + "..."
        rows.append([InlineKeyboardButton(label, callback_data=f"admin:btn:{b['key']}")])

    rows.append([InlineKeyboardButton("⬅️ Voltar", callback_data="admin:home")])
    return InlineKeyboardMarkup(rows)


def admin_button_edit_kb(key: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("✏️ Editar", callback_data=f"admin:btn_edit:{key}")],
        [InlineKeyboardButton("⬅️ Voltar", callback_data="admin:buttons")],
    ])


def admin_banner_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🖼️ Enviar nova imagem", callback_data="admin:banner_new")],
        [InlineKeyboardButton("🗑️ Remover banner", callback_data="admin:banner_del")],
        [InlineKeyboardButton("⬅️ Voltar", callback_data="admin:home")],
    ])


# ═══════════════════════════════════════════════
# ADMIN — MÓDULO 4 — PRODUTOS COMPLETOS / ESTOQUE
# ═══════════════════════════════════════════════

def admin_products_kb_v2(products: list[dict]) -> InlineKeyboardMarkup:
    rows = []
    for p in products:
        status = "🟢" if p.get("active") else "🔴"
        label = f"{status} {p['name'][:32]} — R$ {float(p['price']):.2f}"
        if len(label) > 60:
            label = label[:57] + "..."
        rows.append([InlineKeyboardButton(label, callback_data=f"admin:product:{p['id']}")])

    rows.append([InlineKeyboardButton("➕ Criar novo produto", callback_data="admin:new_product")])
    rows.append([InlineKeyboardButton("⬅️ Voltar", callback_data="admin:home")])
    return InlineKeyboardMarkup(rows)


def admin_product_kb_full(pid: int, active: bool = True) -> InlineKeyboardMarkup:
    toggle = "🔴 Desativar" if active else "🟢 Ativar"

    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📝 Editar nome", callback_data=f"admin:prod_edit:{pid}:name")],
        [InlineKeyboardButton("📄 Editar descrição", callback_data=f"admin:prod_edit:{pid}:description")],
        [
            InlineKeyboardButton("💰 Preço", callback_data=f"admin:prod_edit:{pid}:price"),
            InlineKeyboardButton("📦 Estoque", callback_data=f"admin:prod_edit:{pid}:stock"),
        ],
        [
            InlineKeyboardButton("😀 Emoji", callback_data=f"admin:prod_edit:{pid}:emoji"),
            InlineKeyboardButton("🛡 Garantia", callback_data=f"admin:prod_edit:{pid}:guarantee"),
        ],
        [InlineKeyboardButton("🔗 Link de ativação", callback_data=f"admin:prod_edit:{pid}:activate_url")],
        [InlineKeyboardButton("📥 Gerenciar estoque", callback_data=f"admin:prod_stock:{pid}")],
        [InlineKeyboardButton(toggle, callback_data=f"admin:toggle_product:{pid}")],
        [InlineKeyboardButton("🗑️ Remover produto", callback_data=f"admin:prod_del:{pid}")],
        [InlineKeyboardButton("⬅️ Voltar", callback_data="admin:products")],
    ])


def admin_product_stock_kb(pid: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📥 Adicionar contas", callback_data=f"admin:stock_add:{pid}")],
        [InlineKeyboardButton("👀 Ver contas disponíveis", callback_data=f"admin:stock_view:{pid}")],
        [InlineKeyboardButton("🗑️ Limpar contas não usadas", callback_data=f"admin:stock_clear:{pid}")],
        [InlineKeyboardButton("⬅️ Voltar", callback_data=f"admin:product:{pid}")],
    ])


# ═══════════════════════════════════════════════
# ADMIN — MÓDULO 5 — CARRINHOS / MSG DIRETA / BACKUP
# ═══════════════════════════════════════════════

def admin_abandoned_kb(carrinhos: list[dict]) -> InlineKeyboardMarkup:
    rows = []
    for c in carrinhos:
        nome = c.get("first_name") or c.get("username") or f"ID {c['user_id']}"
        label = f"👤 {nome[:22]} — {c['product_name'][:20] if c.get('product_name') else '?'}"
        if len(label) > 60:
            label = label[:57] + "..."
        rows.append([InlineKeyboardButton(
            label,
            callback_data=f"admin:abandoned:{c['user_id']}:{c['product_id']}",
        )])

    rows.append([InlineKeyboardButton("⬅️ Voltar", callback_data="admin:home")])
    return InlineKeyboardMarkup(rows)


def admin_abandoned_item_kb(user_id: int, product_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("✉️ Enviar lembrete", callback_data=f"admin:abandoned_send:{user_id}:{product_id}")],
        [InlineKeyboardButton("🗑️ Remover da lista", callback_data=f"admin:abandoned_del:{user_id}:{product_id}")],
        [InlineKeyboardButton("⬅️ Voltar", callback_data="admin:abandoned")],
    ])


# ═══════════════════════════════════════════════
# ADMIN — MÓDULO 6 — SUB-ADMINS / EXPORT
# ═══════════════════════════════════════════════

def admin_subadmins_kb(subs: list[dict]) -> InlineKeyboardMarkup:
    rows = []
    for s in subs:
        nome = s.get("nome") or f"ID {s['user_id']}"
        label = f"👤 {nome[:25]} — {s.get('permissoes', 'all')}"
        if len(label) > 60:
            label = label[:57] + "..."
        rows.append([InlineKeyboardButton(label, callback_data=f"admin:sub:{s['user_id']}")])

    rows.append([InlineKeyboardButton("➕ Adicionar sub-admin", callback_data="admin:sub_add")])
    rows.append([InlineKeyboardButton("⬅️ Voltar", callback_data="admin:home")])
    return InlineKeyboardMarkup(rows)


def admin_subadmin_kb(user_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("✏️ Editar permissões", callback_data=f"admin:sub_edit:{user_id}")],
        [InlineKeyboardButton("🗑️ Remover sub-admin", callback_data=f"admin:sub_del:{user_id}")],
        [InlineKeyboardButton("⬅️ Voltar", callback_data="admin:subadmins")],
    ])


def admin_sub_permissoes_kb(user_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("👥 Usuários", callback_data=f"admin:sub_tog:{user_id}:users")],
        [InlineKeyboardButton("📦 Produtos", callback_data=f"admin:sub_tog:{user_id}:products")],
        [InlineKeyboardButton("🛒 Vendas", callback_data=f"admin:sub_tog:{user_id}:purchases")],
        [InlineKeyboardButton("🎁 Gifts", callback_data=f"admin:sub_tog:{user_id}:gifts")],
        [InlineKeyboardButton("💸 Saques", callback_data=f"admin:sub_tog:{user_id}:withdrawals")],
        [InlineKeyboardButton("👥 Afiliados", callback_data=f"admin:sub_tog:{user_id}:affiliates")],
        [InlineKeyboardButton("📢 Broadcast", callback_data=f"admin:sub_tog:{user_id}:broadcast")],
        [InlineKeyboardButton("⚙️ Config", callback_data=f"admin:sub_tog:{user_id}:config")],
        [InlineKeyboardButton("✅ TODAS", callback_data=f"admin:sub_all:{user_id}")],
        [InlineKeyboardButton("⬅️ Voltar", callback_data=f"admin:sub:{user_id}")],
    ])


def admin_export_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("👥 Usuários (CSV)", callback_data="admin:export:users")],
        [InlineKeyboardButton("🛒 Vendas (CSV)", callback_data="admin:export:purchases")],
        [InlineKeyboardButton("💸 Saques (CSV)", callback_data="admin:export:withdrawals")],
        [InlineKeyboardButton("⬅️ Voltar", callback_data="admin:home")],
    ])
