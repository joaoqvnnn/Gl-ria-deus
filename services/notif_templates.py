"""
Templates prontos de mensagens de notificação.
Admin escolhe um tipo e preenche os dados.
"""


def template_produto_voltou(product: dict) -> str:
    """Para quando um produto volta ao estoque."""
    price = float(product["price"])
    return (
        "😍 <b>E o queridinho de vocês finalmente voltou!!!</b>\n\n"
        f"<b>{product['name']}</b>\n"
        f"✅ Apenas <b>R$ {price:.2f}</b>\n\n"
        "🗓 Duração: <b>30 Dias</b>\n"
        "🔒 Garantia: <b>30 Dias</b>\n"
        "🔒 Compra segura, liberação imediata\n"
        "🔗 Ativação via link, direto na sua conta\n\n"
        "⬇️ Clique abaixo e aproveite agora:"
    )


def template_bot_abastecido(produtos: list[dict]) -> str:
    """Para quando o admin abastece vários produtos."""
    linhas = [
        "✅ <b>BOT ABASTECIDO!</b>\n",
        "🔥 Acabamos de abastecer nosso bot e você já pode garantir o seu "
        "streaming favorito para o fim de semana.\n",
    ]
    for p in produtos:
        emoji = p.get("emoji") or "📱"
        linhas.append(f"{emoji} {p['name']} — <b>R$ {float(p['price']):.2f}</b>")

    linhas.append("")
    linhas.append("⚠️ <b>Poucas unidades disponíveis!</b>")
    linhas.append("⚠️ <b>Descontos disponíveis até acabar o estoque</b>")
    linhas.append("")
    linhas.append("🌟 Participe de nossa comunidade e fique por dentro de todas as promoções!")
    linhas.append("")
    linhas.append("📱 Clique abaixo:")
    return "\n".join(linhas)


def template_abandono(product: dict, user_name: str) -> str:
    """Carrinho abandonado."""
    price = float(product["price"])
    return (
        f"👋 Ei, <b>{user_name}</b>, você esqueceu algo!\n\n"
        f"Notamos que você estava olhando o produto <b>{product['name']}</b> "
        "mas não finalizou a compra.\n\n"
        f"💰 Valor: <b>R$ {price:.2f}</b>\n\n"
        "🎁 Que tal finalizar agora?\n"
        "Seu produto está esperando por você!\n\n"
        "Se tiver alguma dúvida, estamos aqui para ajudar!"
    )


def template_boas_vindas_cadastro() -> str:
    """Convite pra se cadastrar."""
    return (
        "👋 <b>Bem-vindo(a)!</b>\n\n"
        "Quer se cadastrar no nosso bot e ter acesso a todos os streamings "
        "com entrega automática?\n\n"
        "🎁 Cadastre-se agora e receba ofertas exclusivas!"
    )


def template_gift_card() -> str:
    """Convite pra resgatar gift card."""
    return (
        "🎁 <b>Resgate seu Gift Card!</b>\n\n"
        "Tem um código de presente? Resgate agora e use como quiser:\n"
        "💰 Saldo\n"
        "🎬 Produto\n\n"
        "Clique abaixo para começar:"
    )
