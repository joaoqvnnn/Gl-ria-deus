from datetime import datetime


# ────────────────────────────────────────────────
# 🔐 1. GATE DE ENTRADA
# ────────────────────────────────────────────────
def gate_text() -> str:
    return (
        "❗ <b>Para utilizar nosso serviço é obrigatório que você entre no nosso grupo.</b>"
    )


# ────────────────────────────────────────────────
# 🏠 2. BOAS-VINDAS (MENU PRINCIPAL)
# ────────────────────────────────────────────────
def welcome_text(user: dict) -> str:
    return (
        "📡 <b>Bem-vindo à Larizinha Store!</b>\n"
        "✨ A sua central de streamings com entrega 100% automática.\n"
        "Pagou, recebeu. Sem filas, sem precisar falar com atendente, 24 horas por dia! ⚡\n\n"
        "🛡 <b>Segurança e Suporte:</b>\n"
        "Mais de 12.000 clientes já passaram por aqui.\n"
        "Participe da nossa comunidade e veja as referências\n\n"
        "● <b>Seus Dados:</b>\n"
        f"├ 👤 ID: <code>{user['user_id']}</code>\n"
        f"└ 💰 Saldo Atual: <b>R$ {float(user['balance']):.2f}</b>\n\n"
        "👇 <b>COMO COMEÇAR:</b>\n"
        "Clique no botão \"🛍 Comprar Produtos\" abaixo para ver nosso catálogo e escolher sua tela!"
    )


# ────────────────────────────────────────────────
# 📦 3. CATÁLOGO DE PRODUTOS
# ────────────────────────────────────────────────
def catalog_text(user: dict) -> str:
    return (
        "⚡ <b>Lari Contas | Catálogo de Serviços</b>\n"
        "────────────────────────\n"
        f"💰 | Saldo da Carteira: <b>R$ {float(user['balance']):.2f}</b>\n\n"
        "⬇️ Selecione uma categoria abaixo para ver nossos planos:"
    )


# ────────────────────────────────────────────────
# 🎯 4. TELA DO PRODUTO
# ────────────────────────────────────────────────
def product_text(user: dict, product: dict) -> str:
    price = float(product["price"])
    stock = int(product["stock"])
    sold = int(product.get("sold", 0))
    guarantee = int(product.get("guarantee", 180))

    return (
        "🔥 <b>OPORTUNIDADE EXCLUSIVA</b> 🔥\n"
        f"🚀 <b>{product['name']}</b>\n\n"
        "🟢 <b>DISPONÍVEL AGORA</b>\n"
        f"├ 💵 Preço: <b>R$ {price:.2f}</b>\n"
        f"├ 💰 Seu Saldo: <b>R$ {float(user['balance']):.2f}</b>\n"
        f"└ 📦 Estoque: <b>{stock}</b>\n\n"
        "📝 <b>Descrição:</b>\n"
        f"{product['description']}\n\n"
        "📊 <b>Estatísticas em tempo real:</b>\n"
        f"⚡️ Já foram vendidas {sold} unidades!\n"
        "👀 14 pessoas estão vendo isso agora.\n\n"
        f"🛡 Garantia: {guarantee} dias\n"
        "✅ Compra segura. Ao adquirir, concorda com /termos"
    )


# ────────────────────────────────────────────────
# 👤 8. MEU PERFIL
# ────────────────────────────────────────────────
def profile_text(user: dict) -> str:
    whatsapp = user.get("whatsapp") or "Não cadastrado"
    return (
        "👤 <b>Meu perfil</b>\n\n"
        "🔍 Veja aqui os detalhes da sua conta:\n\n"
        "- 👤 <b>Informações:</b>\n"
        f"🆔 ID da Carteira: <code>{user['user_id']}</code>\n"
        f"💰 Saldo Atual: <b>R$ {float(user['balance']):.2f}</b>\n"
        f"📲 Seu Whatsapp: {whatsapp}\n\n"
        "─── 📊 <b>Suas Movimentações:</b>\n"
        "ー 🛒 Compras Realizadas: 0\n"
        "ー 💰 Total Gasto Em Compras: R$ 0,00\n"
        "ー 💠 Pix Inseridos: R$ 0,00\n"
        "ー 🎁 Gifts Resgatados: R$ 0,00"
    )


# ────────────────────────────────────────────────
# 🤖 20. SOBRE O BOT
# ────────────────────────────────────────────────
def about_text() -> str:
    return (
        "🤖 <b>Sobre o Bot</b>\n\n"
        "Larizinha Store — central de streamings com entrega automática.\n"
        "Pagou, recebeu. 24h por dia.\n\n"
        "Para suporte, use o botão 📩 Atendimento."
    )


# ────────────────────────────────────────────────
# 🚧 MÓDULOS EM BREVE
# ────────────────────────────────────────────────
def soon_text(area: str) -> str:
    return f"🚧 <b>{area}</b>\n\nEsse módulo será liberado em breve."


# ────────────────────────────────────────────────
# 💸 5. SALDO INSUFICIENTE
# ────────────────────────────────────────────────
def insufficient_text(user: dict, product: dict, quantity: int = 1) -> str:
    total = float(product["price"]) * quantity
    saldo = float(user["balance"])
    falta = max(total - saldo, 0)
    return (
        "❌ <b>Saldo insuficiente!</b>\n\n"
        f"💰 Seu saldo: <b>R$ {saldo:.2f}</b>\n"
        f"💵 Valor do produto: <b>R$ {total:.2f}</b>\n"
        f"📉 Faltam: <b>R$ {falta:.2f}</b>\n\n"
        f"💡 Deseja gerar um PIX no valor de <b>R$ {total:.2f}</b> para completar a compra?"
    )


# ────────────────────────────────────────────────
# ⏳ 6. GERANDO PAGAMENTO + QR CODE
# ────────────────────────────────────────────────
def generating_payment_text() -> str:
    return "⏳ <b>Gerando pagamento...</b>"


def pix_caption(pix_id: str, valor: float, expira: str) -> str:
    return (
        "💠 <b>PIX gerado com sucesso!</b>\n\n"
        f"💰 Valor: <b>R$ {valor:.2f}</b>\n"
        f"🎫 ID: <code>{pix_id}</code>\n"
        f"⏰ Expira em: <b>{expira}</b>\n\n"
        "Escaneie o QR Code ou use o botão <b>📋 Copiar PIX</b>."
    )


# ────────────────────────────────────────────────
# ⏰ 7. AGUARDANDO PAGAMENTO
# ────────────────────────────────────────────────
def not_paid_text() -> str:
    return (
        "⚠️ <b>Nosso sistema viu que você não realizou o pagamento</b>\n\n"
        "Se já pagou, aguarde alguns segundos e clique novamente em "
        "<b>⏰ AGUARDANDO PAGAMENTO</b>."
    )


def paid_caption() -> str:
    return "✅ <b>PAGAMENTO CONFIRMADO!</b>"


# ────────────────────────────────────────────────
# ✅ 9. ENTREGA DO PRODUTO
# ────────────────────────────────────────────────
def delivery_text(purchase: dict, email: str, password: str, masked: bool = True) -> str:
    created = purchase.get("created_at") or datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    expires = purchase.get("expires_at") or "-"

    try:
        created_fmt = datetime.strptime(str(created)[:19], "%Y-%m-%d %H:%M:%S").strftime("%d/%m/%Y")
    except Exception:
        created_fmt = str(created)

    try:
        expires_fmt = datetime.strptime(str(expires)[:19], "%Y-%m-%d %H:%M:%S").strftime("%d/%m/%Y")
    except Exception:
        expires_fmt = str(expires)

    email_show = "•" * 16 if masked else email
    pass_show = "•" * 16 if masked else password

    return (
        "✅ <b>Produto realizado com sucesso!</b>\n\n"
        f"⏰ Data da compra: <b>{created_fmt}</b>\n"
        f"📆 Vencimento: <b>{expires_fmt}</b>\n"
        f"💰 Valor: <b>R$ {float(purchase['total']):.2f}</b>\n"
        f"🎫 ID da compra: <code>{purchase['id']}</code>\n"
        f"⚜️ Serviço: <b>{purchase['product_name']}</b>\n"
        f"📧 Email: <code>{email_show}</code>\n"
        f"🔐 Senha: <code>{pass_show}</code>\n"
        "📃 Nota: Use o botão abaixo para ativar:"
    )


# ────────────────────────────────────────────────
# 🛒 7. COMPRAR MAIS DE UM
# ────────────────────────────────────────────────
def multi_qty_text(product: dict) -> str:
    return (
        "Quantos logins deseja comprar?\n\n"
        f"📦 Estoque disponível: <b>{product['stock']}</b>\n\n"
        "💡 Digite /cancelar a qualquer momento para sair."
    )


def multi_result_text(user: dict, product: dict, qty: int) -> str:
    unit = float(product["price"])
    total = unit * qty
    return (
        "🛒 <b>RESULTADO DO PEDIDO</b>\n"
        f"🚀 <b>{product['name']}</b>\n"
        f"📦 Quantidade: <b>{qty}</b>\n"
        f"💵 Preço unitário: <b>R$ {unit:.2f}</b>\n"
        f"💰 Total: <b>R$ {total:.2f}</b>\n"
        f"💰 Seu Saldo: <b>R$ {float(user['balance']):.2f}</b>"
    )


def multi_cancelled_text() -> str:
    return (
        "❌ <b>Compra cancelada!</b>\n\n"
        "Operação de compra múltipla foi cancelada."
    )
