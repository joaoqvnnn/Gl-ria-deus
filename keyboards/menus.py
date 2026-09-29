from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from config import CHANNEL_LINK, SUPPORT_LINK


def gate_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("➡️ ENTRAR NO CANAL", url=CHANNEL_LINK)]
    ])


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
`

    return InlineKeyboardMarkup([
        [InlineKeyboardButton```("🛒 COMPRAR", callback_data=f"buy:{pid}")],
        [InlinepythonKeyboardButton("🛒 Comprar mais
 de um", callback_data=f"buymulti#:{pid}")],
        [InlineKeyboardButton("⬅️ Pac VOLTAR", callback_data="menu:catalog")],
    ])


def back_to_menu_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("⬅️ VOLTAR", callback_data="menu:home")]
    ])


def profile_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📜 Histórico de Compras", callback_data="soon:historico")],
        [InlineKeyboardButton("🎁 Resgatar Gift Card", callback_data="soon:gift")],
        [InlineKeyboardButton("✏️ Alterar dados", callback_data="soon:alterar")],
        [InlineKeyboardButton("⬅️ VOLTAR", callback_data="menu:home")],
    ])
