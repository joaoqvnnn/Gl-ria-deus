def gate_text() -> str:
    return (
        "❗ <b>Para utilizar nosso serviço é obrigatório que você entre no nosso grupo.</b>"
    )


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
        f"└ 💰 Saldo Atual: <b>R$ {user['balance']:.2f}</b>\n\n"
        "👇 <b>COMO COMEÇAR:</b>\n"
        "Clique no botão \"🛍 Comprar Produtos\" abaixo para ver nosso catálogo e escolher sua tela!"
    )


def catalog_text(user: dict) -> str:
    return (
        "⚡ <b>Lari Contas | Catálogo de Serviços</b>\n"
        "────────────────────────\n"
        f"💰 | Saldo da Carteira: <b>R$ {user['balance']:.2f}</b>\n\n"
        "⬇️ Selecione uma categoria abaixo para ver nossos planos:"
    )


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
        f"├ 💰 Seu Saldo: <b>R$ {user['balance']:.2f}</b>\n"
        f"└ 📦 Estoque: <b>{stock}</b>\n\n"
        "📝 <b>Descrição:</b>\n"
        f"{product['description']}\n\n"
        "📊 <b>Estatísticas em tempo real:</b>\n"
        f"⚡️ Já foram vendidas {sold} unidades!\n"
        "👀 14 pessoas estão vendo isso agora.\n\n"
        f"🛡 Garantia: {guarantee} dias\n"
        "✅ Compra segura. Ao adquirir, concorda com /termos"
    )


def about_text() -> str:
    return (
        "🤖 <b>Sobre o Bot</b>\n\n"
        "Larizinha Store — central de streamings com entrega automática.\n"
        "Pagou, recebeu. 24h por dia.\n\n"
        "Para suporte, use o botão 📩 Atendimento."
    )


def profile_text(user: dict) -> str:
    whatsapp = user.get("whatsapp") or "Não cadastrado"
    return (
        "👤 <b>Meu perfil</b>\n\n"
        "🔍 Veja aqui os detalhes da sua conta:\n\n"
        "- 👤 <b>Informações:</b>\n"
        f"🆔 ID da Carteira: <code>{user['user_id']}</code>\n"
        f"💰 Saldo Atual: <b>R$ {user['balance']:.2f}</b>\n"
        f"📲 Seu Whatsapp: {whatsapp}\n\n"
        "─── 📊 <b>Suas Movimentações:</b>\n"
        "ー 🛒 Compras Realizadas: 0\n"
        "ー 💰 Total Gasto Em Compras: R$ 0,00\n"
        "ー 💠 Pix Inseridos: R$ 0,00\n"
        "ー 🎁 Gifts Resgatados: R$ 0,00"
    )


def soon_text(area: str) -> str:
    return f"🚧 <b>{area}</b>\n\nEsse módulo será liberado em breve."
