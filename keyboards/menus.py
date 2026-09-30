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
    try:
        from texts import cache
        return cache.get_button(key, default)
    except Exception:
        return default


def _copy_button(text: str, label: str = "📋 Copiar PIX", fallback_data: str = "") -> InlineKeyboardButton:
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
# MÓDULO 3 — PERFIL, HISTÓRICO, RECARGA
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


def history_item_keyboard(purchase_id, activate_url, page, pages, only_active):
    rows = [[InlineKeyboardButton("🔗 CLIQUE AQUI PARA ATIVAR", url=activate_url or "https://t.me/")]]

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
# MÓDULO 4 — AFILIADOS, SAQUES, TOP
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
        [InlineKeyboardButton("🛒 Comprar agora", callback_data=f"direct:product:{product_id}")],
    ])


def direct_product_two_keyboard(product_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🛒 Comprar agora", callback_data=f"direct:product:{product_id}")],
        [InlineKeyboardButton("👀 Ver detalhes", callback_data=f"direct:product:{product_id}")],
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
                line.append(InlineKeyboardButton(b["text"], callback_data=b.get("action", "noop")))
        rows.append(line)
    return InlineKeyboardMarkup(rows)


# ═══════════════════════════════════════════════
# ADMIN — DASHBOARD
# ═══════════════════════════════════════════════

def admin_dashboard_kb() -> InlineKeyboardMarkup:
    """Painel admin principal — todos os botões em PT-BR."""
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
            InlineKeyboardButton("🛒 Carrinhos", callback_data="admin:abandoned"),
        ],
        [InlineKeyboardButton("📊 Estatísticas", callback_data="admin:stats")],
        [InlineKeyboardButton("📢 Transmissão", callback_data="admin:broadcast")],
        [InlineKeyboardButton("📝 Textos do Bot", callback_data="admin:texts")],
        [InlineKeyboardButton("🔘 Botões do Bot", callback_data="admin:buttons")],
        [InlineKeyboardButton("🖼️ Banner", callback_data="admin:banner")],
        [InlineKeyboardButton("⚙️ Configurações", callback_data="admin:config")],
        [
            InlineKeyboardButton("🛡 Sub-Admins", callback_data="admin:subadmins"),
            InlineKeyboardButton("📤 Exportar", callback_data="admin:export"),
        ],
        [InlineKeyboardButton("🔧 Extras", callback_data="admin:extras")],
        [InlineKeyboardButton("🔄 Atualizar Painel", callback_data="admin:home")],
    ])


def admin_back_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("⬅️ Voltar ao Painel", callback_data="admin:home")],
    ])


# ═══════════════════════════════════════════════
# ADMIN — USUÁRIOS (base — mantidas pra compat)
# ═══════════════════════════════════════════════

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


# ═══════════════════════════════════════════════
# ADMIN — BROADCAST (base)
# ═══════════════════════════════════════════════

def admin_broadcast_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📢 Todos os usuários", callback_data="admin:bc_all")],
        [InlineKeyboardButton("🛒 Apenas compradores", callback_data="admin:bc_buyers")],
        [InlineKeyboardButton("💤 Inativos (7d+)", callback_data="admin:bc_inactive")],
        [InlineKeyboardButton("⬅️ Voltar", callback_data="admin:home")],
    ])


# ═══════════════════════════════════════════════
# ADMIN — MANUTENÇÃO (base)
# ═══════════════════════════════════════════════

def admin_maintenance_kb(ativo: bool) -> InlineKeyboardMarkup:
    label = "🟢 Desligar manutenção" if ativo else "🔴 Ligar manutenção"
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(label, callback_data="admin:toggle_maintenance")],
        [InlineKeyboardButton("⬅️ Voltar", callback_data="admin:home")],
    ])


# ═══════════════════════════════════════════════
# ADMIN — VENDAS (base — mantidas pra compat)
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


# ═══════════════════════════════════════════════
# ADMIN — GIFT CARDS (base)
# ═══════════════════════════════════════════════

def admin_gifts_kb(gifts: list[dict]) -> InlineKeyboardMarkup:
    rows = []
    for g in gifts:
        if g.get("redeemed_by"):
            status_icon, info = "🔴", "resgatado"
        else:
            status_icon, info = "🟢", "livre"
        label = f"{status_icon} {g['code']} — {info}"
        rows.append([InlineKeyboardButton(label, callback_data=f"admin:gift:{g['code']}")])

    rows.append([InlineKeyboardButton("➕ Criar Gift Cards", callback_data="admin:gift_create")])
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


# ═══════════════════════════════════════════════
# ADMIN — SAQUES (base)
# ═══════════════════════════════════════════════

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


# ═══════════════════════════════════════════════
# ADMIN — AFILIADOS (base)
# ═══════════════════════════════════════════════

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
# ADMIN — ESTATÍSTICAS (base)
# ═══════════════════════════════════════════════

def admin_stats_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📅 Vendas por dia", callback_data="admin:stats_daily")],
        [InlineKeyboardButton("🏆 Top produtos", callback_data="admin:stats_products")],
        [InlineKeyboardButton("💎 Top compradores", callback_data="admin:stats_spenders")],
        [InlineKeyboardButton("⬅️ Voltar", callback_data="admin:home")],
    ])


# ═══════════════════════════════════════════════
# ADMIN — CONFIGURAÇÕES (base)
# ═══════════════════════════════════════════════

def admin_config_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🏪 Nome da loja", callback_data="admin:cfg:store_name")],
        [InlineKeyboardButton("📄 CNPJ", callback_data="admin:cfg:cnpj")],
        [InlineKeyboardButton("🕐 Horário de atendimento", callback_data="admin:cfg:horario")],
        [InlineKeyboardButton("📱 WhatsApp", callback_data="admin:cfg:whatsapp_link")],
        [InlineKeyboardButton("💬 Telegram", callback_data="admin:cfg:telegram_link")],
        [InlineKeyboardButton("🎁 Bônus de recarga (%)", callback_data="admin:cfg:bonus_rate")],
        [InlineKeyboardButton("💵 Recarga mínima (R$)", callback_data="admin:cfg:topup_min")],
        [InlineKeyboardButton("💸 Saque mínimo (R$)", callback_data="admin:cfg:withdraw_min")],
        [InlineKeyboardButton("🧲 Comissão de afiliado (%)", callback_data="admin:cfg:commission")],
        [InlineKeyboardButton("⬅️ Voltar", callback_data="admin:home")],
    ])


# ═══════════════════════════════════════════════
# ADMIN — TEXTOS (base)
# ═══════════════════════════════════════════════

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


# ═══════════════════════════════════════════════
# ADMIN — BOTÕES (base)
# ═══════════════════════════════════════════════

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


# ═══════════════════════════════════════════════
# ADMIN — BANNER (base)
# ═══════════════════════════════════════════════

def admin_banner_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🖼️ Enviar nova imagem", callback_data="admin:banner_new")],
        [InlineKeyboardButton("🗑️ Remover banner", callback_data="admin:banner_del")],
        [InlineKeyboardButton("⬅️ Voltar", callback_data="admin:home")],
    ])


# ═══════════════════════════════════════════════
# ADMIN — PRODUTOS v2 (base — mantidas pra compat)
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
# ADMIN — CARRINHOS (base — mantidas pra compat)
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
        [InlineKeyboardButton("📨 Enviar lembrete", callback_data=f"admin:abandoned_send:{user_id}:{product_id}")],
        [InlineKeyboardButton("🗑️ Remover da lista", callback_data=f"admin:abandoned_del:{user_id}:{product_id}")],
        [InlineKeyboardButton("⬅️ Voltar", callback_data="admin:abandoned")],
    ])


# ═══════════════════════════════════════════════
# ADMIN — SUB-ADMINS (base — mantidas pra compat)
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
        [InlineKeyboardButton("🎁 Gift Cards", callback_data=f"admin:sub_tog:{user_id}:gifts")],
        [InlineKeyboardButton("💸 Saques", callback_data=f"admin:sub_tog:{user_id}:withdrawals")],
        [InlineKeyboardButton("👥 Afiliados", callback_data=f"admin:sub_tog:{user_id}:affiliates")],
        [InlineKeyboardButton("📢 Transmissão", callback_data=f"admin:sub_tog:{user_id}:broadcast")],
        [InlineKeyboardButton("⚙️ Configurações", callback_data=f"admin:sub_tog:{user_id}:config")],
        [InlineKeyboardButton("✅ TODAS", callback_data=f"admin:sub_all:{user_id}")],
        [InlineKeyboardButton("⬅️ Voltar", callback_data=f"admin:sub:{user_id}")],
    ])


# ═══════════════════════════════════════════════
# ADMIN — EXPORTAR (base)
# ═══════════════════════════════════════════════

def admin_export_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("👥 Usuários (CSV)", callback_data="admin:export:users")],
        [InlineKeyboardButton("🛒 Vendas (CSV)", callback_data="admin:export:purchases")],
        [InlineKeyboardButton("💸 Saques (CSV)", callback_data="admin:export:withdrawals")],
        [InlineKeyboardButton("⬅️ Voltar", callback_data="admin:home")],
    ])


# ═══════════════════════════════════════════════
# ═══════════════════════════════════════════════
# ═══════════════════════════════════════════════
# MÓDULOS v2 (admin4-15)
# ═══════════════════════════════════════════════
# ═══════════════════════════════════════════════
# ═══════════════════════════════════════════════


# ═══════════════════════════════════════════════
# ADMIN 4 — PRODUTOS V3 + ESTOQUE
# ═══════════════════════════════════════════════

def admin_products_v3_kb(products: list[dict], page: int, total_pages: int) -> InlineKeyboardMarkup:
    rows = []
    for p in products:
        status = "🟢" if p.get("active") else "🔴"
        emoji = p.get("emoji") or "📦"
        promo = " 💸" if p.get("promo_price") else ""
        stock = int(p.get("stock") or 0)
        label = f"{status} {emoji} {p['name'][:28]} — R$ {float(p['price']):.2f}{promo} | 📦 {stock}"
        if len(label) > 64:
            label = label[:61] + "..."
        rows.append([InlineKeyboardButton(label, callback_data=f"admin:product:{p['id']}")])

    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton("◀️ Anterior", callback_data=f"admin:products_page:{page - 1}"))
    nav.append(InlineKeyboardButton(f"📄 {page + 1}/{total_pages}", callback_data="admin:noop"))
    if page < total_pages - 1:
        nav.append(InlineKeyboardButton("Próxima ▶️", callback_data=f"admin:products_page:{page + 1}"))
    if nav:
        rows.append(nav)

    rows.append([InlineKeyboardButton("🔍 Buscar produto", callback_data="admin:prod_search")])
    rows.append([InlineKeyboardButton("➕ Criar novo produto", callback_data="admin:new_product")])
    rows.append([InlineKeyboardButton("⬅️ Voltar ao Painel", callback_data="admin:home")])
    return InlineKeyboardMarkup(rows)


def admin_product_v3_kb(pid: int, active: bool, has_promo: bool) -> InlineKeyboardMarkup:
    toggle = "🔴 Desativar" if active else "🟢 Ativar"
    promo_label = "💸 Editar promoção" if has_promo else "💸 Criar promoção"

    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("✏️ Nome", callback_data=f"admin:prod_edit:{pid}:name"),
            InlineKeyboardButton("📄 Descrição", callback_data=f"admin:prod_edit:{pid}:description"),
        ],
        [
            InlineKeyboardButton("💰 Preço", callback_data=f"admin:prod_edit:{pid}:price"),
            InlineKeyboardButton("🛡 Garantia", callback_data=f"admin:prod_edit:{pid}:guarantee"),
        ],
        [
            InlineKeyboardButton("📦 Estoque", callback_data=f"admin:prod_edit:{pid}:stock"),
            InlineKeyboardButton("😀 Emoji", callback_data=f"admin:prod_edit:{pid}:emoji"),
        ],
        [
            InlineKeyboardButton("📁 Categoria", callback_data=f"admin:prod_edit:{pid}:category"),
            InlineKeyboardButton("🔗 Link", callback_data=f"admin:prod_edit:{pid}:activate_url"),
        ],
        [InlineKeyboardButton(promo_label, callback_data=f"admin:prod_promo:{pid}")],
        [InlineKeyboardButton("🖼 Imagem do produto", callback_data=f"admin:prod_img:{pid}")],
        [InlineKeyboardButton("📥 Gerenciar estoque", callback_data=f"admin:prod_stock:{pid}")],
        [InlineKeyboardButton("📋 Clonar produto", callback_data=f"admin:prod_clone:{pid}")],
        [InlineKeyboardButton(toggle, callback_data=f"admin:toggle_product:{pid}")],
        [InlineKeyboardButton("🗑️ Remover produto", callback_data=f"admin:prod_del:{pid}")],
        [InlineKeyboardButton("⬅️ Voltar", callback_data="admin:products")],
    ])


def admin_product_stock_v3_kb(pid: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📥 Adicionar contas (colar)", callback_data=f"admin:stock_add:{pid}")],
        [InlineKeyboardButton("📄 Importar arquivo .txt", callback_data=f"admin:stock_import:{pid}")],
        [
            InlineKeyboardButton("👀 Ver disponíveis", callback_data=f"admin:stock_view:{pid}"),
            InlineKeyboardButton("🔴 Ver usadas", callback_data=f"admin:stock_view_used:{pid}"),
        ],
        [InlineKeyboardButton("🗑️ Remover conta específica", callback_data=f"admin:stock_remove_prompt:{pid}")],
        [InlineKeyboardButton("🧹 Limpar não usadas", callback_data=f"admin:stock_clear:{pid}")],
        [InlineKeyboardButton("📤 Exportar .txt", callback_data=f"admin:stock_export:{pid}")],
        [InlineKeyboardButton("⬅️ Voltar", callback_data=f"admin:product:{pid}")],
    ])


def admin_confirm_kb(yes_data: str, no_data: str, yes_label: str = "✅ Confirmar") -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(yes_label, callback_data=yes_data)],
        [InlineKeyboardButton("❌ Cancelar", callback_data=no_data)],
    ])


# ═══════════════════════════════════════════════
# ADMIN 2 — VENDAS V2
# ═══════════════════════════════════════════════

def admin_vendas_kb(vendas: list[dict], page: int, total_pages: int,
                    periodo: str, status: str) -> InlineKeyboardMarkup:
    rows = []

    for v in vendas:
        icon = "🟢" if (v.get("status") or "active") != "cancelled" else "🔴"
        nome = (v.get("product_name") or "?")[:22]
        label = f"{icon} {nome} — R$ {float(v.get('total') or 0):.2f}"
        if len(label) > 60:
            label = label[:57] + "..."
        rows.append([InlineKeyboardButton(
            label, callback_data=f"admin:venda:{v['id']}",
        )])

    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton(
            "◀️", callback_data=f"admin:vendas_page:{periodo}:{status}:{page - 1}",
        ))
    nav.append(InlineKeyboardButton(f"📄 {page + 1}/{total_pages}", callback_data="admin:noop"))
    if page < total_pages - 1:
        nav.append(InlineKeyboardButton(
            "▶️", callback_data=f"admin:vendas_page:{periodo}:{status}:{page + 1}",
        ))
    if nav:
        rows.append(nav)

    def chk(k, v):
        return "✅ " if k == v else ""

    rows.append([
        InlineKeyboardButton(f"{chk('hoje', periodo)}Hoje", callback_data=f"admin:vendas_filtro:hoje:{status}"),
        InlineKeyboardButton(f"{chk('7d', periodo)}7d",     callback_data=f"admin:vendas_filtro:7d:{status}"),
        InlineKeyboardButton(f"{chk('30d', periodo)}30d",   callback_data=f"admin:vendas_filtro:30d:{status}"),
    ])
    rows.append([
        InlineKeyboardButton(f"{chk('mes', periodo)}Mês",   callback_data=f"admin:vendas_filtro:mes:{status}"),
        InlineKeyboardButton(f"{chk('tudo', periodo)}Tudo", callback_data=f"admin:vendas_filtro:tudo:{status}"),
    ])

    rows.append([
        InlineKeyboardButton(f"{chk('todos', status)}Todos",         callback_data=f"admin:vendas_filtro:{periodo}:todos"),
        InlineKeyboardButton(f"{chk('ativos', status)}🟢 Ativos",     callback_data=f"admin:vendas_filtro:{periodo}:ativos"),
        InlineKeyboardButton(f"{chk('cancelados', status)}🔴 Cancel.", callback_data=f"admin:vendas_filtro:{periodo}:cancelados"),
    ])

    rows.append([
        InlineKeyboardButton("🔍 Buscar", callback_data="admin:purchase_search"),
        InlineKeyboardButton("📤 Exportar CSV", callback_data=f"admin:vendas_export:{periodo}:{status}"),
    ])

    rows.append([InlineKeyboardButton("⬅️ Voltar ao Painel", callback_data="admin:home")])
    return InlineKeyboardMarkup(rows)


def admin_venda_detalhe_kb(purchase_id: str, cancelado: bool, periodo: str, status: str) -> InlineKeyboardMarkup:
    rows = []

    if cancelado:
        rows.append([InlineKeyboardButton("🔄 Reativar pedido", callback_data=f"admin:venda_reactivate:{purchase_id}:{periodo}:{status}")])
    else:
        rows.append([InlineKeyboardButton("💰 Reembolsar", callback_data=f"admin:refund_prompt:{purchase_id}:{periodo}:{status}")])

    rows.append([InlineKeyboardButton("📤 Reenviar credenciais", callback_data=f"admin:venda_resend:{purchase_id}:{periodo}:{status}")])
    rows.append([InlineKeyboardButton("📧 Enviar msg pro usuário", callback_data=f"admin:venda_msg:{purchase_id}")])
    rows.append([InlineKeyboardButton("⬅️ Voltar", callback_data=f"admin:vendas_filtro:{periodo}:{status}")])
    return InlineKeyboardMarkup(rows)


# ═══════════════════════════════════════════════
# ADMIN 7 — SAQUES V2
# ═══════════════════════════════════════════════

def admin_saques_kb(wds: list[dict], page: int, total_pages: int,
                    status: str = "todos") -> InlineKeyboardMarkup:
    rows = []

    for w in wds:
        icon = {
            "pending": "🟡", "processed": "🟢", "rejected": "🔴",
        }.get(w.get("status"), "⚪")
        nome_curto = f"ID {w['user_id']}"
        label = f"{icon} {nome_curto} — R$ {float(w.get('amount') or 0):.2f}"
        if len(label) > 60:
            label = label[:57] + "..."
        rows.append([InlineKeyboardButton(label, callback_data=f"admin:saque:{w['id']}")])

    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton(
            "◀️", callback_data=f"admin:saques_page:{status}:{page - 1}",
        ))
    nav.append(InlineKeyboardButton(f"📄 {page + 1}/{total_pages}", callback_data="admin:noop"))
    if page < total_pages - 1:
        nav.append(InlineKeyboardButton(
            "▶️", callback_data=f"admin:saques_page:{status}:{page + 1}",
        ))
    if nav:
        rows.append(nav)

    def chk(k):
        return "✅ " if k == status else ""

    rows.append([
        InlineKeyboardButton(f"{chk('pending')}🟡 Pendentes", callback_data="admin:saques_filtro:pending"),
        InlineKeyboardButton(f"{chk('processed')}🟢 Processados", callback_data="admin:saques_filtro:processed"),
    ])
    rows.append([
        InlineKeyboardButton(f"{chk('rejected')}🔴 Rejeitados", callback_data="admin:saques_filtro:rejected"),
        InlineKeyboardButton(f"{chk('todos')}📋 Todos", callback_data="admin:saques_filtro:todos"),
    ])

    rows.append([
        InlineKeyboardButton("🔍 Buscar por user", callback_data="admin:saque_search"),
        InlineKeyboardButton("📤 Exportar CSV", callback_data=f"admin:saques_export:{status}"),
    ])

    rows.append([InlineKeyboardButton("⬅️ Voltar ao Painel", callback_data="admin:home")])
    return InlineKeyboardMarkup(rows)


def admin_saque_detalhe_kb(wid: str, status: str) -> InlineKeyboardMarkup:
    rows = []

    if status == "pending":
        rows.append([InlineKeyboardButton("✅ Aprovar saque", callback_data=f"admin:saque_ok:{wid}")])
        rows.append([InlineKeyboardButton("❌ Rejeitar com motivo", callback_data=f"admin:saque_no:{wid}")])
    elif status == "processed":
        rows.append([InlineKeyboardButton("📄 Enviar comprovante PDF", callback_data=f"admin:saque_pdf:{wid}")])
        rows.append([InlineKeyboardButton("📧 Avisar cliente", callback_data=f"admin:saque_notify:{wid}")])
    elif status == "rejected":
        rows.append([InlineKeyboardButton("📧 Avisar cliente novamente", callback_data=f"admin:saque_notify:{wid}")])

    rows.append([InlineKeyboardButton("⬅️ Voltar aos saques", callback_data="admin:withdrawals")])
    return InlineKeyboardMarkup(rows)


# ═══════════════════════════════════════════════
# ADMIN 8 — USUÁRIOS V2
# ═══════════════════════════════════════════════

def admin_users_v2_kb(users: list[dict], page: int, total_pages: int,
                       filtro: str = "todos") -> InlineKeyboardMarkup:
    rows = []

    for u in users:
        nome = u.get("first_name") or u.get("username") or f"ID {u['user_id']}"
        icons = ""
        if u.get("banned"):
            icons += "🚫"
        if u.get("is_affiliate"):
            icons += "🤝"
        saldo = float(u.get("balance") or 0)
        label = f"{icons} {nome[:25]} — R$ {saldo:.2f}"
        if len(label) > 60:
            label = label[:57] + "..."
        rows.append([InlineKeyboardButton(label, callback_data=f"admin:user_v2:{u['user_id']}")])

    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton(
            "◀️", callback_data=f"admin:users_page:{filtro}:{page - 1}",
        ))
    nav.append(InlineKeyboardButton(f"📄 {page + 1}/{total_pages}", callback_data="admin:noop"))
    if page < total_pages - 1:
        nav.append(InlineKeyboardButton(
            "▶️", callback_data=f"admin:users_page:{filtro}:{page + 1}",
        ))
    if nav:
        rows.append(nav)

    def chk(k):
        return "✅ " if k == filtro else ""

    rows.append([
        InlineKeyboardButton(f"{chk('todos')}📋 Todos", callback_data="admin:users_filtro:todos"),
        InlineKeyboardButton(f"{chk('ativos')}🟢 Ativos", callback_data="admin:users_filtro:ativos"),
    ])
    rows.append([
        InlineKeyboardButton(f"{chk('banidos')}🚫 Banidos", callback_data="admin:users_filtro:banidos"),
        InlineKeyboardButton(f"{chk('afiliados')}🤝 Afiliados", callback_data="admin:users_filtro:afiliados"),
    ])
    rows.append([
        InlineKeyboardButton(f"{chk('com_saldo')}💰 Com saldo", callback_data="admin:users_filtro:com_saldo"),
        InlineKeyboardButton(f"{chk('sem_saldo')}📭 Sem saldo", callback_data="admin:users_filtro:sem_saldo"),
    ])
    rows.append([
        InlineKeyboardButton(f"{chk('inativos')}💤 Inativos 7d", callback_data="admin:users_filtro:inativos"),
    ])

    rows.append([
        InlineKeyboardButton("🔍 Buscar", callback_data="admin:user_search"),
        InlineKeyboardButton("📤 CSV", callback_data=f"admin:users_export:{filtro}"),
    ])

    rows.append([InlineKeyboardButton("⬅️ Voltar ao Painel", callback_data="admin:home")])
    return InlineKeyboardMarkup(rows)


def admin_user_v2_kb(user_id: int, banned: bool, is_aff: bool,
                      tem_senha: bool, filtro: str = "todos") -> InlineKeyboardMarkup:
    rows = []

    rows.append([
        InlineKeyboardButton("➕ Add saldo", callback_data=f"admin:usr_add:{user_id}"),
        InlineKeyboardButton("➖ Rem saldo", callback_data=f"admin:usr_rem:{user_id}"),
    ])
    rows.append([
        InlineKeyboardButton("✏️ Setar exato", callback_data=f"admin:usr_set:{user_id}"),
        InlineKeyboardButton("🧹 Zerar", callback_data=f"admin:usr_zero:{user_id}"),
    ])

    rows.append([InlineKeyboardButton("✉️ Enviar mensagem", callback_data=f"admin:usr_msg:{user_id}")])

    rows.append([
        InlineKeyboardButton("📜 Compras", callback_data=f"admin:usr_hist_compras:{user_id}"),
        InlineKeyboardButton("💸 Saques", callback_data=f"admin:usr_hist_saques:{user_id}"),
    ])

    if is_aff:
        rows.append([InlineKeyboardButton("🚫 Desativar afiliado", callback_data=f"admin:usr_aff_off:{user_id}")])
    else:
        rows.append([InlineKeyboardButton("🤝 Ativar afiliado", callback_data=f"admin:usr_aff_on:{user_id}")])

    if tem_senha:
        rows.append([InlineKeyboardButton("🔓 Resetar senha de saque", callback_data=f"admin:usr_reset_pin:{user_id}")])

    if banned:
        rows.append([InlineKeyboardButton("✅ Desbanir", callback_data=f"admin:usr_unban:{user_id}")])
    else:
        rows.append([InlineKeyboardButton("🚫 Banir", callback_data=f"admin:usr_ban:{user_id}")])

    rows.append([InlineKeyboardButton("⬅️ Voltar", callback_data=f"admin:users_filtro:{filtro}")])
    return InlineKeyboardMarkup(rows)


def admin_ban_options_kb(user_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🚫 1 dia", callback_data=f"admin:usr_ban_confirm:{user_id}:1")],
        [InlineKeyboardButton("🚫 7 dias", callback_data=f"admin:usr_ban_confirm:{user_id}:7")],
        [InlineKeyboardButton("🚫 30 dias", callback_data=f"admin:usr_ban_confirm:{user_id}:30")],
        [InlineKeyboardButton("🚫 Permanente", callback_data=f"admin:usr_ban_confirm:{user_id}:perm")],
        [InlineKeyboardButton("⬅️ Cancelar", callback_data=f"admin:user_v2:{user_id}")],
    ])


# ═══════════════════════════════════════════════
# ADMIN 9 — GIFT CARDS V2
# ═══════════════════════════════════════════════

def admin_gifts_v2_kb(gifts: list[dict], page: int, total_pages: int,
                       filtro: str = "todos") -> InlineKeyboardMarkup:
    from datetime import datetime
    rows = []

    for g in gifts:
        code = g["code"]
        tipo = g.get("tipo", "saldo")

        if g.get("redeemed_by"):
            icon = "🔴"
        elif g.get("expires_at"):
            try:
                exp_dt = datetime.strptime(str(g["expires_at"])[:19], "%Y-%m-%d %H:%M:%S")
                if exp_dt < datetime.now():
                    icon = "⚫"
                else:
                    icon = "🟢"
            except Exception:
                icon = "🟢"
        else:
            icon = "🟢"

        if tipo == "saldo":
            extra = f"R$ {float(g.get('valor') or 0):.2f}"
        elif tipo == "desconto":
            extra = f"{float(g.get('discount_pct') or 0):.0f}% off"
        else:
            extra = f"prod #{g.get('product_id')}"

        label = f"{icon} {code} — {extra}"
        if len(label) > 60:
            label = label[:57] + "..."
        rows.append([InlineKeyboardButton(label, callback_data=f"admin:gift_v2:{code}")])

    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton(
            "◀️", callback_data=f"admin:gifts_page:{filtro}:{page - 1}",
        ))
    nav.append(InlineKeyboardButton(f"📄 {page + 1}/{total_pages}", callback_data="admin:noop"))
    if page < total_pages - 1:
        nav.append(InlineKeyboardButton(
            "▶️", callback_data=f"admin:gifts_page:{filtro}:{page + 1}",
        ))
    if nav:
        rows.append(nav)

    def chk(k):
        return "✅ " if k == filtro else ""

    rows.append([
        InlineKeyboardButton(f"{chk('todos')}📋 Todos", callback_data="admin:gifts_filtro:todos"),
        InlineKeyboardButton(f"{chk('livres')}🟢 Livres", callback_data="admin:gifts_filtro:livres"),
    ])
    rows.append([
        InlineKeyboardButton(f"{chk('resgatados')}🔴 Resgatados", callback_data="admin:gifts_filtro:resgatados"),
        InlineKeyboardButton(f"{chk('expirados')}⚫ Expirados", callback_data="admin:gifts_filtro:expirados"),
    ])

    rows.append([
        InlineKeyboardButton("🔍 Buscar", callback_data="admin:gift_search"),
        InlineKeyboardButton("📤 Exportar CSV", callback_data=f"admin:gifts_export:{filtro}"),
    ])

    rows.append([
        InlineKeyboardButton("➕ Criar gifts", callback_data="admin:gift_create"),
        InlineKeyboardButton("📄 Exportar códigos", callback_data=f"admin:gifts_codes:{filtro}"),
    ])

    rows.append([InlineKeyboardButton("⬅️ Voltar ao Painel", callback_data="admin:home")])
    return InlineKeyboardMarkup(rows)


def admin_gift_v2_kb(code: str, redeemed: bool) -> InlineKeyboardMarkup:
    rows = []

    if not redeemed:
        rows.append([InlineKeyboardButton("🗑️ Revogar", callback_data=f"admin:gift_revoke:{code}")])

    rows.append([InlineKeyboardButton("📤 Exportar este código", callback_data=f"admin:gift_export_one:{code}")])
    rows.append([InlineKeyboardButton("⬅️ Voltar aos gifts", callback_data="admin:gifts")])
    return InlineKeyboardMarkup(rows)


def admin_gift_create_type_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("💰 Gift de saldo", callback_data="admin:gift_new:saldo")],
        [InlineKeyboardButton("🎁 Gift de produto", callback_data="admin:gift_new:produto")],
        [InlineKeyboardButton("💸 Gift de desconto %", callback_data="admin:gift_new:desconto")],
        [InlineKeyboardButton("⬅️ Voltar", callback_data="admin:gifts")],
    ])


def admin_gift_preview_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ Gerar agora", callback_data="admin:gift_confirm_create")],
        [InlineKeyboardButton("❌ Cancelar", callback_data="admin:gifts")],
    ])


# ═══════════════════════════════════════════════
# ADMIN 10 — TRANSMISSÃO V2
# ═══════════════════════════════════════════════

def admin_bc_v2_menu_kb(agendadas: int, rascunhos: int) -> InlineKeyboardMarkup:
    rows = [
        [InlineKeyboardButton("📢 Nova transmissão", callback_data="admin:bc_nova")],
    ]

    if agendadas > 0:
        rows.append([InlineKeyboardButton(
            f"📅 Agendadas ({agendadas})", callback_data="admin:bc_agendadas",
        )])

    if rascunhos > 0:
        rows.append([InlineKeyboardButton(
            f"📝 Rascunhos ({rascunhos})", callback_data="admin:bc_rascunhos",
        )])

    rows.append([InlineKeyboardButton("📊 Histórico", callback_data="admin:bc_historico")])
    rows.append([InlineKeyboardButton("⬅️ Voltar ao Painel", callback_data="admin:home")])
    return InlineKeyboardMarkup(rows)


def admin_bc_v2_segment_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📢 Todos os usuários", callback_data="admin:bc_seg:todos")],
        [InlineKeyboardButton("🛒 Apenas compradores", callback_data="admin:bc_seg:compradores")],
        [InlineKeyboardButton("💤 Inativos (7d+)", callback_data="admin:bc_seg:inativos")],
        [InlineKeyboardButton("📭 Sem saldo (0)", callback_data="admin:bc_seg:sem_saldo")],
        [InlineKeyboardButton("⬅️ Cancelar", callback_data="admin:broadcast")],
    ])


def admin_bc_v2_preview_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📤 Enviar agora", callback_data="admin:bc_send_now")],
        [InlineKeyboardButton("📅 Agendar", callback_data="admin:bc_schedule")],
        [InlineKeyboardButton("📝 Salvar rascunho", callback_data="admin:bc_save_draft")],
        [InlineKeyboardButton("❌ Cancelar", callback_data="admin:bc_cancel")],
    ])


def admin_bc_v2_schedule_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("5 min", callback_data="admin:bc_sch:5min"),
            InlineKeyboardButton("30 min", callback_data="admin:bc_sch:30min"),
        ],
        [
            InlineKeyboardButton("1 hora", callback_data="admin:bc_sch:1h"),
            InlineKeyboardButton("6 horas", callback_data="admin:bc_sch:6h"),
        ],
        [
            InlineKeyboardButton("1 dia", callback_data="admin:bc_sch:1d"),
            InlineKeyboardButton("✏️ Customizar", callback_data="admin:bc_sch:custom"),
        ],
        [InlineKeyboardButton("⬅️ Voltar", callback_data="admin:bc_preview_back")],
    ])


def admin_bc_v2_list_kb(items: list[dict], tipo: str = "agendada") -> InlineKeyboardMarkup:
    from datetime import datetime
    rows = []
    for item in items:
        bc_id = item["id"]
        seg = item.get("segmento") or "?"
        preview = (item.get("texto") or "")[:30]

        if tipo == "agendada":
            agend = item.get("agendado_para")
            quando = str(agend or "")[:16] if agend else "—"
            label = f"📅 {preview} — {quando}"
        elif tipo == "rascunho":
            criado = str(item.get("created_at") or "")[:10]
            label = f"📝 {preview} — {criado}"
        else:
            en = item.get("enviados", 0)
            fa = item.get("falhas", 0)
            label = f"✅ {preview} — {en}✓ {fa}✗"

        if len(label) > 60:
            label = label[:57] + "..."
        rows.append([InlineKeyboardButton(label, callback_data=f"admin:bc_view:{bc_id}")])

    rows.append([InlineKeyboardButton("⬅️ Voltar", callback_data="admin:broadcast")])
    return InlineKeyboardMarkup(rows)


def admin_bc_v2_view_kb(bc_id: str, status: str) -> InlineKeyboardMarkup:
    rows = []

    if status == "scheduled":
        rows.append([InlineKeyboardButton("📤 Enviar agora", callback_data=f"admin:bc_force_send:{bc_id}")])
        rows.append([InlineKeyboardButton("❌ Cancelar agendamento", callback_data=f"admin:bc_cancel_sched:{bc_id}")])
    elif status == "draft":
        rows.append([InlineKeyboardButton("📤 Enviar agora", callback_data=f"admin:bc_force_send:{bc_id}")])
        rows.append([InlineKeyboardButton("📅 Agendar", callback_data=f"admin:bc_sched_draft:{bc_id}")])
        rows.append([InlineKeyboardButton("🗑️ Apagar rascunho", callback_data=f"admin:bc_del:{bc_id}")])

    rows.append([InlineKeyboardButton("⬅️ Voltar", callback_data="admin:broadcast")])
    return InlineKeyboardMarkup(rows)


# ═══════════════════════════════════════════════
# ADMIN 11 — ESTATÍSTICAS V2
# ═══════════════════════════════════════════════

def admin_stats_v2_kb(periodo: str = "30d") -> InlineKeyboardMarkup:
    def chk(k):
        return "✅ " if k == periodo else ""

    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton(f"{chk('hoje')}Hoje", callback_data="admin:stats2_f:hoje"),
            InlineKeyboardButton(f"{chk('7d')}7d", callback_data="admin:stats2_f:7d"),
            InlineKeyboardButton(f"{chk('30d')}30d", callback_data="admin:stats2_f:30d"),
        ],
        [
            InlineKeyboardButton(f"{chk('mes')}Este mês", callback_data="admin:stats2_f:mes"),
            InlineKeyboardButton(f"{chk('tudo')}Tudo", callback_data="admin:stats2_f:tudo"),
        ],
        [InlineKeyboardButton("📊 Comparativo mês", callback_data="admin:stats2_comp")],
        [InlineKeyboardButton("📅 Vendas por dia", callback_data="admin:stats2_dia")],
        [InlineKeyboardButton("🏆 Top produtos", callback_data="admin:stats2_prod")],
        [InlineKeyboardButton("💎 Top compradores", callback_data="admin:stats2_compradores")],
        [InlineKeyboardButton("💠 Top recargas", callback_data="admin:stats2_recargas")],
        [InlineKeyboardButton("🎁 Top gifts", callback_data="admin:stats2_gifts")],
        [InlineKeyboardButton("📈 Taxa de conversão", callback_data="admin:stats2_conv")],
        [InlineKeyboardButton("💰 Saldos", callback_data="admin:stats2_saldos")],
        [InlineKeyboardButton("📤 Exportar relatório", callback_data=f"admin:stats2_export:{periodo}")],
        [InlineKeyboardButton("⬅️ Voltar ao Painel", callback_data="admin:home")],
    ])


# ═══════════════════════════════════════════════
# ADMIN 12 — CONFIG/TEXTOS/BOTÕES V2
# ═══════════════════════════════════════════════

def admin_cfg_v2_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🏪 Nome da loja", callback_data="admin:cfg2_edit:store_name")],
        [InlineKeyboardButton("📄 CNPJ", callback_data="admin:cfg2_edit:cnpj")],
        [InlineKeyboardButton("🕐 Horário", callback_data="admin:cfg2_edit:horario")],
        [InlineKeyboardButton("📱 WhatsApp", callback_data="admin:cfg2_edit:whatsapp_link")],
        [InlineKeyboardButton("💬 Telegram", callback_data="admin:cfg2_edit:telegram_link")],
        [InlineKeyboardButton("🎁 Bônus recarga (%)", callback_data="admin:cfg2_edit:bonus_rate")],
        [InlineKeyboardButton("💵 Recarga mínima (R$)", callback_data="admin:cfg2_edit:topup_min")],
        [InlineKeyboardButton("💸 Saque mínimo (R$)", callback_data="admin:cfg2_edit:withdraw_min")],
        [InlineKeyboardButton("🧲 Comissão afiliado (%)", callback_data="admin:cfg2_edit:commission")],
        [InlineKeyboardButton("➕ Config custom", callback_data="admin:cfg2_add")],
        [InlineKeyboardButton("📤 Exportar tudo (JSON)", callback_data="admin:cfg2_export")],
        [InlineKeyboardButton("📥 Importar JSON", callback_data="admin:cfg2_import")],
        [InlineKeyboardButton("⬅️ Voltar ao Painel", callback_data="admin:home")],
    ])


def admin_cfg_v2_edit_kb(key: str) -> InlineKeyboardMarkup:
    rows = []
    if key in ("store_name", "cnpj", "horario", "whatsapp_link",
               "telegram_link", "bonus_rate", "topup_min",
               "withdraw_min", "commission"):
        rows.append([InlineKeyboardButton("🔄 Resetar padrão", callback_data=f"admin:cfg2_reset:{key}")])

    if key not in ("store_name", "cnpj", "horario", "whatsapp_link",
                   "telegram_link", "bonus_rate", "topup_min",
                   "withdraw_min", "commission", "maintenance"):
        rows.append([InlineKeyboardButton("🗑️ Remover", callback_data=f"admin:cfg2_del:{key}")])

    rows.append([InlineKeyboardButton("⬅️ Voltar", callback_data="admin:config")])
    return InlineKeyboardMarkup(rows)


def admin_texts_v2_kb(texts: list[dict]) -> InlineKeyboardMarkup:
    rows = []
    for t in texts[:15]:
        key = t["key"]
        if key.startswith("__"):
            continue
        preview = (t.get("value") or "")[:30].replace("\n", " ")
        label = f"📝 {key} — {preview}"
        if len(label) > 60:
            label = label[:57] + "..."
        rows.append([InlineKeyboardButton(label, callback_data=f"admin:text2_view:{key}")])

    rows.append([InlineKeyboardButton("🔍 Buscar texto", callback_data="admin:text2_search")])
    rows.append([InlineKeyboardButton("📤 Exportar", callback_data="admin:cfg2_export")])
    rows.append([InlineKeyboardButton("⬅️ Voltar ao Painel", callback_data="admin:home")])
    return InlineKeyboardMarkup(rows)


def admin_text_v2_view_kb(key: str) -> InlineKeyboardMarkup:
    rows = [
        [InlineKeyboardButton("✏️ Editar", callback_data=f"admin:text2_edit:{key}")],
    ]

    rows.append([InlineKeyboardButton("🔄 Resetar padrão", callback_data=f"admin:text2_reset:{key}")])
    rows.append([InlineKeyboardButton("⬅️ Voltar", callback_data="admin:texts")])
    return InlineKeyboardMarkup(rows)


def admin_buttons_v2_kb(buttons: list[dict]) -> InlineKeyboardMarkup:
    rows = []
    for b in buttons[:20]:
        key = b["key"]
        value = (b.get("value") or "")[:25]
        label = f"🔘 {key} = {value}"
        if len(label) > 60:
            label = label[:57] + "..."
        rows.append([InlineKeyboardButton(label, callback_data=f"admin:btn2_view:{key}")])

    rows.append([InlineKeyboardButton("🔍 Buscar botão", callback_data="admin:btn2_search")])
    rows.append([InlineKeyboardButton("📤 Exportar", callback_data="admin:cfg2_export")])
    rows.append([InlineKeyboardButton("⬅️ Voltar ao Painel", callback_data="admin:home")])
    return InlineKeyboardMarkup(rows)


def admin_button_v2_view_kb(key: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("✏️ Editar", callback_data=f"admin:btn2_edit:{key}")],
        [InlineKeyboardButton("🔄 Resetar padrão", callback_data=f"admin:btn2_reset:{key}")],
        [InlineKeyboardButton("⬅️ Voltar", callback_data="admin:buttons")],
    ])


# ═══════════════════════════════════════════════
# ADMIN 13 — SUB-ADMINS V2
# ═══════════════════════════════════════════════

def admin_sub_v2_kb(subs: list[dict], filtro: str = "todos") -> InlineKeyboardMarkup:
    from datetime import datetime
    rows = []

    for s in subs:
        nome = s.get("nome") or f"ID {s['user_id']}"

        if s.get("expires_at"):
            try:
                exp_dt = datetime.strptime(str(s["expires_at"])[:19], "%Y-%m-%d %H:%M:%S")
                if exp_dt < datetime.now():
                    icon = "⚫"
                else:
                    icon = "🟢"
            except Exception:
                icon = "🟢"
        else:
            icon = "🟢"

        perms = s.get("permissoes", "all")
        perms_short = "TUDO" if perms == "all" else f"{len(perms.split(','))} áreas"

        label = f"{icon} {nome[:22]} — {perms_short}"
        if len(label) > 60:
            label = label[:57] + "..."
        rows.append([InlineKeyboardButton(label, callback_data=f"admin:sub2:{s['user_id']}")])

    def chk(k):
        return "✅ " if k == filtro else ""

    rows.append([
        InlineKeyboardButton(f"{chk('todos')}📋 Todos", callback_data="admin:sub2_filtro:todos"),
        InlineKeyboardButton(f"{chk('ativos')}🟢 Ativos", callback_data="admin:sub2_filtro:ativos"),
        InlineKeyboardButton(f"{chk('expirados')}⚫ Expirados", callback_data="admin:sub2_filtro:expirados"),
    ])

    rows.append([InlineKeyboardButton("➕ Adicionar sub-admin", callback_data="admin:sub2_add")])
    rows.append([InlineKeyboardButton("📋 Logs globais", callback_data="admin:sub2_logs")])
    rows.append([InlineKeyboardButton("⬅️ Voltar ao Painel", callback_data="admin:home")])
    return InlineKeyboardMarkup(rows)


def admin_sub_v2_view_kb(user_id: int, has_exp: bool) -> InlineKeyboardMarkup:
    rows = [
        [InlineKeyboardButton("✏️ Editar permissões", callback_data=f"admin:sub2_perm:{user_id}")],
        [InlineKeyboardButton("📅 Mudar expiração", callback_data=f"admin:sub2_exp:{user_id}")],
        [InlineKeyboardButton("📜 Ver histórico dele", callback_data=f"admin:sub2_hist:{user_id}")],
    ]

    if has_exp:
        rows.append([InlineKeyboardButton("♾️ Tornar permanente", callback_data=f"admin:sub2_perm_forever:{user_id}")])

    rows.append([InlineKeyboardButton("🗑️ Remover", callback_data=f"admin:sub2_del:{user_id}")])
    rows.append([InlineKeyboardButton("⬅️ Voltar", callback_data="admin:subadmins")])
    return InlineKeyboardMarkup(rows)


def admin_sub_v2_perms_kb(user_id: int, perms: str) -> InlineKeyboardMarkup:
    ativas = perms.split(",") if perms and perms != "all" else []
    tudo = (perms == "all")

    def icon(area):
        if tudo:
            return "✅"
        return "✅" if area in ativas else "⬜"

    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton(f"{icon('users')} 👥 Usuários", callback_data=f"admin:sub2_tog:{user_id}:users"),
            InlineKeyboardButton(f"{icon('products')} 📦 Produtos", callback_data=f"admin:sub2_tog:{user_id}:products"),
        ],
        [
            InlineKeyboardButton(f"{icon('purchases')} 🛒 Vendas", callback_data=f"admin:sub2_tog:{user_id}:purchases"),
            InlineKeyboardButton(f"{icon('gifts')} 🎁 Gifts", callback_data=f"admin:sub2_tog:{user_id}:gifts"),
        ],
        [
            InlineKeyboardButton(f"{icon('withdrawals')} 💸 Saques", callback_data=f"admin:sub2_tog:{user_id}:withdrawals"),
            InlineKeyboardButton(f"{icon('affiliates')} 🤝 Afiliados", callback_data=f"admin:sub2_tog:{user_id}:affiliates"),
        ],
        [
            InlineKeyboardButton(f"{icon('broadcast')} 📢 Broadcast", callback_data=f"admin:sub2_tog:{user_id}:broadcast"),
            InlineKeyboardButton(f"{icon('config')} ⚙️ Config", callback_data=f"admin:sub2_tog:{user_id}:config"),
        ],
        [InlineKeyboardButton("✅ Dar TUDO", callback_data=f"admin:sub2_all:{user_id}")],
        [InlineKeyboardButton("❌ Remover tudo", callback_data=f"admin:sub2_none:{user_id}")],
        [InlineKeyboardButton("⬅️ Voltar", callback_data=f"admin:sub2:{user_id}")],
    ])


def admin_sub_v2_exp_kb(user_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("1 dia", callback_data=f"admin:sub2_exp_set:{user_id}:1"),
            InlineKeyboardButton("7 dias", callback_data=f"admin:sub2_exp_set:{user_id}:7"),
        ],
        [
            InlineKeyboardButton("30 dias", callback_data=f"admin:sub2_exp_set:{user_id}:30"),
            InlineKeyboardButton("90 dias", callback_data=f"admin:sub2_exp_set:{user_id}:90"),
        ],
        [InlineKeyboardButton("♾️ Permanente", callback_data=f"admin:sub2_exp_set:{user_id}:perm")],
        [InlineKeyboardButton("⬅️ Voltar", callback_data=f"admin:sub2:{user_id}")],
    ])


# ═══════════════════════════════════════════════
# ADMIN 14 — CARRINHOS ABANDONADOS V2
# ═══════════════════════════════════════════════

def admin_carts_v2_kb(carrinhos: list[dict], page: int, total_pages: int,
                       tempo: str = "todos") -> InlineKeyboardMarkup:
    rows = []

    for c in carrinhos:
        nome = c.get("first_name") or c.get("username") or f"ID {c['user_id']}"
        prod = (c.get("product_name") or "?")[:20]
        preco = float(c.get("product_price") or 0)
        lem = c.get("reminders_sent") or 0
        lem_icon = f" · {lem}📨" if lem > 0 else ""

        label = f"👤 {nome[:20]} — {prod}{lem_icon}"
        if len(label) > 60:
            label = label[:57] + "..."
        rows.append([InlineKeyboardButton(
            label,
            callback_data=f"admin:cart2:{c['user_id']}:{c['product_id']}",
        )])

    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton(
            "◀️", callback_data=f"admin:carts_page:{tempo}:{page - 1}",
        ))
    nav.append(InlineKeyboardButton(f"📄 {page + 1}/{total_pages}", callback_data="admin:noop"))
    if page < total_pages - 1:
        nav.append(InlineKeyboardButton(
            "▶️", callback_data=f"admin:carts_page:{tempo}:{page + 1}",
        ))
    if nav:
        rows.append(nav)

    def chk(k):
        return "✅ " if k == tempo else ""

    rows.append([
        InlineKeyboardButton(f"{chk('5min')}5min", callback_data="admin:carts_filtro:5min"),
        InlineKeyboardButton(f"{chk('1h')}1h", callback_data="admin:carts_filtro:1h"),
        InlineKeyboardButton(f"{chk('24h')}24h", callback_data="admin:carts_filtro:24h"),
    ])
    rows.append([
        InlineKeyboardButton(f"{chk('7d')}7d", callback_data="admin:carts_filtro:7d"),
        InlineKeyboardButton(f"{chk('todos')}Tudo", callback_data="admin:carts_filtro:todos"),
    ])

    rows.append([
        InlineKeyboardButton("📨 Enviar p/ todos", callback_data="admin:carts_send_all"),
        InlineKeyboardButton("📤 CSV", callback_data="admin:carts_export"),
    ])
    rows.append([
        InlineKeyboardButton("⚙️ Automação", callback_data="admin:carts_auto"),
        InlineKeyboardButton("📝 Template", callback_data="admin:carts_template"),
    ])

    rows.append([InlineKeyboardButton("⬅️ Voltar ao Painel", callback_data="admin:home")])
    return InlineKeyboardMarkup(rows)


def admin_cart_v2_item_kb(user_id: int, product_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📨 Enviar lembrete", callback_data=f"admin:cart2_send:{user_id}:{product_id}")],
        [InlineKeyboardButton("💬 Mensagem personalizada", callback_data=f"admin:cart2_msg:{user_id}:{product_id}")],
        [InlineKeyboardButton("🎁 Dar desconto", callback_data=f"admin:cart2_disc:{user_id}:{product_id}")],
        [InlineKeyboardButton("✅ Marcar convertido", callback_data=f"admin:cart2_conv:{user_id}:{product_id}")],
        [InlineKeyboardButton("🗑️ Remover da lista", callback_data=f"admin:cart2_del:{user_id}:{product_id}")],
        [InlineKeyboardButton("⬅️ Voltar", callback_data="admin:abandoned")],
    ])


def admin_cart_v2_auto_kb(ligado: bool, minutos: int) -> InlineKeyboardMarkup:
    toggle_label = "🔴 Desligar" if ligado else "🟢 Ligar"
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(toggle_label, callback_data="admin:carts_auto_toggle")],
        [
            InlineKeyboardButton(f"{'✅ ' if minutos == 5 else ''}5 min", callback_data="admin:carts_auto_min:5"),
            InlineKeyboardButton(f"{'✅ ' if minutos == 15 else ''}15 min", callback_data="admin:carts_auto_min:15"),
        ],
        [
            InlineKeyboardButton(f"{'✅ ' if minutos == 30 else ''}30 min", callback_data="admin:carts_auto_min:30"),
            InlineKeyboardButton(f"{'✅ ' if minutos == 60 else ''}60 min", callback_data="admin:carts_auto_min:60"),
        ],
        [InlineKeyboardButton("⬅️ Voltar", callback_data="admin:abandoned")],
    ])


# ═══════════════════════════════════════════════
# ADMIN 15 — EXTRAS
# ═══════════════════════════════════════════════

def admin_extras_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("💾 Backup", callback_data="admin:extras_backup")],
        [InlineKeyboardButton("📋 Logs", callback_data="admin:extras_logs")],
        [InlineKeyboardButton("🚧 Manutenção", callback_data="admin:extras_maint")],
        [InlineKeyboardButton("🖥️ Status do Sistema", callback_data="admin:extras_system")],
        [
            InlineKeyboardButton("🔁 Restart soft", callback_data="admin:extras_restart_soft"),
            InlineKeyboardButton("⚡ Restart hard", callback_data="admin:extras_restart_hard"),
        ],
        [InlineKeyboardButton("🧹 Limpar sessões", callback_data="admin:extras_clear")],
        [InlineKeyboardButton("⬅️ Voltar ao Painel", callback_data="admin:home")],
    ])


def admin_extras_backup_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("💾 Fazer backup agora", callback_data="admin:extras_backup_do")],
        [InlineKeyboardButton("📂 Histórico de backups", callback_data="admin:extras_backup_hist")],
        [InlineKeyboardButton("⚙️ Backup automático", callback_data="admin:extras_backup_auto")],
        [InlineKeyboardButton("📥 Restaurar backup", callback_data="admin:extras_backup_restore")],
        [InlineKeyboardButton("⬅️ Voltar", callback_data="admin:extras")],
    ])


def admin_extras_backup_auto_kb(ligado: bool, horas: int) -> InlineKeyboardMarkup:
    toggle = "🔴 Desligar" if ligado else "🟢 Ligar"
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(toggle, callback_data="admin:extras_backup_auto_toggle")],
        [
            InlineKeyboardButton(f"{'✅ ' if horas == 6 else ''}6h", callback_data="admin:extras_backup_auto_h:6"),
            InlineKeyboardButton(f"{'✅ ' if horas == 12 else ''}12h", callback_data="admin:extras_backup_auto_h:12"),
            InlineKeyboardButton(f"{'✅ ' if horas == 24 else ''}24h", callback_data="admin:extras_backup_auto_h:24"),
        ],
        [InlineKeyboardButton("⬅️ Voltar", callback_data="admin:extras_backup")],
    ])


def admin_extras_logs_kb(admin_id=None, action=None, periodo="todos") -> InlineKeyboardMarkup:
    def chk(k, v):
        return "✅ " if k == v else ""

    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton(f"{chk(periodo, 'hoje')}Hoje", callback_data="admin:logs2_f:hoje"),
            InlineKeyboardButton(f"{chk(periodo, '7d')}7d", callback_data="admin:logs2_f:7d"),
            InlineKeyboardButton(f"{chk(periodo, '30d')}30d", callback_data="admin:logs2_f:30d"),
            InlineKeyboardButton(f"{chk(periodo, 'todos')}Tudo", callback_data="admin:logs2_f:todos"),
        ],
        [InlineKeyboardButton("🔍 Buscar por ação", callback_data="admin:logs2_search")],
        [InlineKeyboardButton("📊 Estatísticas", callback_data="admin:logs2_stats")],
        [InlineKeyboardButton("📤 Exportar CSV", callback_data="admin:logs2_export")],
        [InlineKeyboardButton("⬅️ Voltar", callback_data="admin:extras")],
    ])


def admin_extras_maint_kb(ativo: bool, agendada: str = "") -> InlineKeyboardMarkup:
    toggle = "🟢 Desligar" if ativo else "🔴 Ligar agora"
    rows = [
        [InlineKeyboardButton(toggle, callback_data="admin:extras_maint_toggle")],
        [InlineKeyboardButton("📝 Editar mensagem", callback_data="admin:extras_maint_msg")],
    ]
    if agendada:
        rows.append([InlineKeyboardButton("❌ Cancelar agendamento", callback_data="admin:extras_maint_sched_cancel")])
    else:
        rows.append([InlineKeyboardButton("📅 Agendar manutenção", callback_data="admin:extras_maint_sched")])

    rows.append([InlineKeyboardButton("⬅️ Voltar", callback_data="admin:extras")])
    return InlineKeyboardMarkup(rows)


def admin_extras_maint_sched_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("15 min", callback_data="admin:extras_maint_sched_set:15"),
            InlineKeyboardButton("30 min", callback_data="admin:extras_maint_sched_set:30"),
        ],
        [
            InlineKeyboardButton("1 hora", callback_data="admin:extras_maint_sched_set:60"),
            InlineKeyboardButton("6 horas", callback_data="admin:extras_maint_sched_set:360"),
        ],
        [InlineKeyboardButton("⬅️ Voltar", callback_data="admin:extras_maint")],
    ])
