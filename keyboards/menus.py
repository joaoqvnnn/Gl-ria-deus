from urllib.parse import quote
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo
from config import CHANNEL_LINK, SUPPORT_LINK, SUPPORT_MESSAGE, MINIAPP_BASE_URL


# ═══════════════════════════════════════════════
# HELPERS
# ═══════════════════════════════════════════════
def _support_url() -> str:
    """URL do suporte com mensagem pré-preenchida."""
    if not SUPPORT_LINK:
        return "https://t.me/"
    return f"{SUPPORT_LINK}?text={quote(SUPPORT_MESSAGE)}"


# ═══════════════════════════════════════════════
# MÓDULO 1 — GATE, MENU, CATÁLOGO, PRODUTO
# ═══════════════════════════════════════════════

def gate_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("➡️ ENTRAR NO CANAL", url=CHANNEL_LINK)]
    ])


def main_menu_keyboard(user_id: int | None = None) -> InlineKeyboardMarkup:
    """
    Menu principal.
    Se user_id for passado, o botão 'Abrir Loja' vira Web App (abre direto).
    """
    # Botão "Abrir Loja"
    if user_id:
        loja_url = f"{MINIAPP_BASE_URL}/loja/{user_id}"
        loja_btn = InlineKeyboardButton(
            "🛒 Abrir Loja",
            web_app=WebAppInfo(url=loja_url),
        )
    else:
        loja_btn = InlineKeyboardButton(
            "🛒 Abrir Loja",
            callback_data="menu:store",
        )

    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🛍 Comprar Produtos", callback_data="menu:catalog")],
        [loja_btn],
        [
            InlineKeyboardButton("👤 Meu Perfil", callback_data="menu:profile"),
            InlineKeyboardButton("💠 Recarregar Saldo", callback_data="menu:topup"),
        ],
        [
            InlineKeyboardButton("👥 Afiliados", callback_data="menu:affiliates"),
            InlineKeyboardButton("🏆 Top Compradores", callback_data="menu:top"),
        ],
        [InlineKeyboardButton("📩 Atendimento", url=_support_url())],
        [
            InlineKeyboardButton("🤖 Sobre o Bot", callback_data="menu:about"),
            InlineKeyboardButton("🔎 Pesquisar Serviços", callback_data="menu:search"),
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
    rows.append([InlineKeyboardButton("⬅️ VOLTAR", callback_data="menu:home")])
    return InlineKeyboardMarkup(rows)


def product_keyboard(pid: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🛒 COMPRAR", callback_data=f"buy:{pid}")],
        [InlineKeyboardButton("🛒 Comprar mais de um", callback_data=f"buymulti:{pid}")],
        [InlineKeyboardButton("⬅️ VOLTAR", callback_data="menu:catalog")],
    ])


def back_to_menu_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("⬅️ VOLTAR", callback_data="menu:home")]
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


def pix_keyboard(pix_id: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📋 Copiar PIX", callback_data=f"pix:copy:{pix_id}")],
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
        [InlineKeyboardButton("⬅️ VOLTAR", callback_data="menu:home")],
    ])


def history_empty_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🟢 Apenas Ativas", callback_data="hist:active:0")],
        [InlineKeyboardButton("⬅️ VOLTAR", callback_data="menu:profile")],
    ])


def history_active_empty_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📋 Ver Todas", callback_data="hist:all:0")],
        [InlineKeyboardButton("⬅️ VOLTAR", callback_data="menu:profile")],
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

    rows.append([InlineKeyboardButton("⬅️ VOLTAR", callback_data="menu:profile")])
    return InlineKeyboardMarkup(rows)


def gift_cancel_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("❌ Cancelar", callback_data="gift:cancel")],
    ])


def gift_success_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🎁 Usar", callback_data="gift:use")],
    ])


def alter_data_keyboard(user: dict) -> InlineKeyboardMarkup:
    whats = user.get("whatsapp") or "Não cadastrado"
    label = f"📱 WhatsApp: {whats}"
    if len(label) > 60:
        label = label[:57] + "..."
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(label, callback_data="alter:whatsapp")],
        [InlineKeyboardButton("⬅️ VOLTAR", callback_data="menu:profile")],
    ])


def alter_data_cancel_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("⬅️ VOLTAR", callback_data="menu:profile")],
    ])


def topup_menu_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("💠 PIX RÁPIDO", callback_data="topup:pix")],
        [InlineKeyboardButton("⬅️ VOLTAR", callback_data="menu:home")],
    ])


def topup_pix_keyboard(pix_id: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📋 Copiar PIX", callback_data=f"toppix:copy:{pix_id}")],
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
        [InlineKeyboardButton("⬅️ Voltar", callback_data="menu:home")],
    ])


def affiliates_active_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📜 Histórico de Saque", callback_data="aff:whist")],
        [InlineKeyboardButton("💸 Saques", callback_data="aff:withdraw")],
        [InlineKeyboardButton("🔐 Cadastrar Senha de Saque", callback_data="aff:setpin")],
        [InlineKeyboardButton("⬅️ Voltar", callback_data="menu:home")],
    ])


def withdraw_type_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📧 Email", callback_data="wd:type:email")],
        [InlineKeyboardButton("🆔 CPF", callback_data="wd:type:cpf")],
        [InlineKeyboardButton("📱 Telefone", callback_data="wd:type:phone")],
        [InlineKeyboardButton("🔑 Chave Aleatória", callback_data="wd:type:random")],
        [InlineKeyboardButton("⬅️ Voltar", callback_data="aff:menu")],
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
        [InlineKeyboardButton("⬅️ Voltar", callback_data="aff:menu")],
    ])


def withdraw_amount_cancel_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("❌ Cancelar", callback_data="aff:menu")],
    ])


def withdraw_success_keyboard(wid: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📄 PDF", callback_data="aff:whist")],
        [InlineKeyboardButton("⬅️ Voltar", callback_data="aff:menu")],
    ])


def top_keyboard(current: str = "compras") -> InlineKeyboardMarkup:
    def check(key):
        return "✅ " if key == current else ""

    return InlineKeyboardMarkup([
        [InlineKeyboardButton(f"{check('compras')}Compras",   callback_data="top:compras")],
        [InlineKeyboardButton(f"{check('recargas')}Recargas", callback_data="top:recargas")],
        [InlineKeyboardButton(f"{check('gift')}Gift card",    callback_data="top:gift")],
        [InlineKeyboardButton(f"{check('saldo')}Saldo",       callback_data="top:saldo")],
        [InlineKeyboardButton("⬅️ VOLTAR", callback_data="menu:home")],
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
