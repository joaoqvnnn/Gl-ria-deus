from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from config import CHANNEL_LINK, SUPPORT_LINK


# ────────────────────────────────────────────────
# 🔐 1. GATE DE ENTRADA
# ────────────────────────────────────────────────
def gate_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("➡️ ENTRAR NO CANAL", url=CHANNEL_LINK)]
    ])


# ────────────────────────────────────────────────
# 🏠 2. BOAS-VINDAS / MENU PRINCIPAL
# ────────────────────────────────────────────────
def main_menu_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🛍 Comprar Produtos", callback_data="menu:catalog")],
        [InlineKeyboardButton("🛒 Abrir Loja", callback_data="menu:store")],
        [
            InlineKeyboardButton("👤 Meu Perfil", callback_data="menu:profile"),
            InlineKeyboardButton("💠 Recarregar Saldo", callback_data="menu:topup"),
        ],
        [
            InlineKeyboardButton("👥 Afiliados", callback_data="menu:affiliates"),
            InlineKeyboardButton("🏆 Top Compradores", callback_data="menu:top"),
        ],
        [InlineKeyboardButton("📩 Atendimento", url=SUPPORT_LINK)],
        [
            InlineKeyboardButton("🤖 Sobre o Bot", callback_data="menu:about"),
            InlineKeyboardButton("🔎 Pesquisar Serviços", callback_data="menu:search"),
        ],
    ])


# ────────────────────────────────────────────────
# 📦 3. CATÁLOGO DE PRODUTOS
# ────────────────────────────────────────────────
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


# ────────────────────────────────────────────────
# 🎯 4. TELA DO PRODUTO
# ────────────────────────────────────────────────
def product_keyboard(pid: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🛒 COMPRAR", callback_data=f"buy:{pid}")],
        [InlineKeyboardButton("🛒 Comprar mais de um", callback_data=f"buymulti:{pid}")],
        [InlineKeyboardButton("⬅️ VOLTAR", callback_data="menu:catalog")],
    ])


# ────────────────────────────────────────────────
# 👤 8. MEU PERFIL
# ────────────────────────────────────────────────
def profile_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📜 Histórico de Compras", callback_data="soon:historico")],
        [InlineKeyboardButton("🎁 Resgatar Gift Card", callback_data="soon:gift")],
        [InlineKeyboardButton("✏️ Alterar dados", callback_data="soon:alterar")],
        [InlineKeyboardButton("⬅️ VOLTAR", callback_data="menu:home")],
    ])


# ────────────────────────────────────────────────
# 🔙 BOTÃO VOLTAR GENÉRICO
# ────────────────────────────────────────────────
def back_to_menu_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("⬅️ VOLTAR", callback_data="menu:home")]
    ])


# ────────────────────────────────────────────────
# 💸 5. SALDO INSUFICIENTE
# ────────────────────────────────────────────────
def insufficient_keyboard(product_id: int, quantity: int, total: float) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(
            f"💠 Gerar PIX de R$ {total:.2f}",
            callback_data=f"pix:gen:{product_id}:{quantity}",
        )],
        [InlineKeyboardButton("❌ Cancelar", callback_data="pix:new_cancel")],
    ])


# ────────────────────────────────────────────────
# 💠 6. QR CODE (PIX)
# ────────────────────────────────────────────────
def pix_keyboard(pix_id: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📋 Copiar PIX", callback_data=f"pix:copy:{pix_id}")],
        [InlineKeyboardButton("⏰ AGUARDANDO PAGAMENTO", callback_data=f"pix:check:{pix_id}")],
        [InlineKeyboardButton("❌ Cancelar", callback_data=f"pix:cancel:{pix_id}")],
    ])


# ────────────────────────────────────────────────
# 🛒 7. COMPRAR MAIS DE UM
# ────────────────────────────────────────────────
def multi_confirm_keyboard(product_id: int, qty: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ Confirmar Compra", callback_data=f"multi:confirm:{product_id}:{qty}")],
        [InlineKeyboardButton("❌ Cancelar", callback_data="multi:cancel")],
    ])


# ────────────────────────────────────────────────
# ✅ 9. ENTREGA DO PRODUTO
# ────────────────────────────────────────────────
def delivery_keyboard(purchase_id: str, activate_url: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🔓 VER PRODUTO", callback_data=f"delivery:reveal:{purchase_id}")],
        [InlineKeyboardButton("🔗 CLIQUE AQUI PARA ATIVAR", url=activate_url or "https://t.me/")],
    ])


def delivery_revealed_keyboard(purchase_id: str, activate_url: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🔗 CLIQUE AQUI PARA ATIVAR", url=activate_url or "https://t.me/")],
    ])
