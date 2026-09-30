from datetime import datetime


# ═══════════════════════════════════════════════
# MÓDULO 1 — GATE, MENU, CATÁLOGO, PRODUTO
# ═══════════════════════════════════════════════

def gate_text() -> str:
    return "❗ <b>Para utilizar nosso serviço é obrigatório que você entre no nosso grupo.</b>"


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


def catalog_text(user: dict) -> str:
    return (
        "⚡ <b>Lari Contas | Catálogo de Serviços</b>\n"
        "────────────────────────\n"
        f"💰 | Saldo da Carteira: <b>R$ {float(user['balance']):.2f}</b>\n\n"
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


def about_text() -> str:
    return (
        "🤖 <b>Sobre o Bot</b>\n\n"
        "Larizinha Store — central de streamings com entrega automática.\n"
        "Pagou, recebeu. 24h por dia.\n\n"
        "Para suporte, use o botão 📩 Atendimento."
    )


def soon_text(area: str) -> str:
    return f"🚧 <b>{area}</b>\n\nEsse módulo será liberado em breve."


# ═══════════════════════════════════════════════
# MÓDULO 2 — COMPRA, PIX, ENTREGA, MULTI
# ═══════════════════════════════════════════════

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


def not_paid_text() -> str:
    return (
        "⚠️ <b>Nosso sistema viu que você não realizou o pagamento</b>\n\n"
        "Se já pagou, aguarde alguns segundos e clique novamente em "
        "<b>⏰ AGUARDANDO PAGAMENTO</b>."
    )


def paid_caption() -> str:
    return "✅ <b>PAGAMENTO CONFIRMADO!</b>"


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
    return "❌ <b>Compra cancelada!</b>\n\nOperação de compra múltipla foi cancelada."


# ═══════════════════════════════════════════════
# MÓDULO 3 — PERFIL, HISTÓRICO, GIFT, DADOS, RECARGA
# ═══════════════════════════════════════════════

def profile_text(user: dict, stats: dict | None = None) -> str:
    stats = stats or {}
    whatsapp = user.get("whatsapp") or "Não cadastrado"
    compras = stats.get("compras", 0)
    gasto = stats.get("gasto", 0.0)
    pix_in = stats.get("pix_inseridos", 0.0)
    gifts = stats.get("gifts_valor", 0.0)

    return (
        "👤 <b>Meu perfil</b>\n\n"
        "🔍 Veja aqui os detalhes da sua conta:\n\n"
        "- 👤 <b>Informações:</b>\n"
        f"🆔 ID da Carteira: <code>{user['user_id']}</code>\n"
        f"💰 Saldo Atual: <b>R$ {float(user['balance']):.2f}</b>\n"
        f"📲 Seu Whatsapp: <code>{whatsapp}</code>\n\n"
        "─── 📊 <b>Suas Movimentações:</b>\n"
        f"ー 🛒 Compras Realizadas: <b>{compras}</b>\n"
        f"ー 💰 Total Gasto Em Compras: <b>R$ {gasto:.2f}</b>\n"
        f"ー 💠 Pix Inseridos: <b>R$ {pix_in:.2f}</b>\n"
        f"ー 🎁 Gifts Resgatados: <b>R$ {gifts:.2f}</b>"
    )


def history_empty_text() -> str:
    return (
        "Você não tem compras no bot.\n"
        "Quando comprar alguma conta, as informações dela ficarão exibidas aqui."
    )


def history_active_empty_text() -> str:
    return "Você não tem compras ativas (não vencidas) no bot."


def _fmt_date(s) -> str:
    try:
        return datetime.strptime(str(s)[:19], "%Y-%m-%d %H:%M:%S").strftime("%d/%m/%Y")
    except Exception:
        return str(s)


def history_item_text(purchase: dict, idx: int, total: int, page: int, pages: int) -> str:
    return (
        f"📦 <b>Compras: {total}</b>\n\n"
        f"⏰ Data da compra: <b>{_fmt_date(purchase['created_at'])}</b>\n"
        f"📆 Vencimento: <b>{_fmt_date(purchase['expires_at'])}</b>\n"
        f"💰 Valor: <b>R$ {float(purchase['total']):.2f}</b>\n"
        f"🎫 ID da compra: <code>{purchase['id']}</code>\n"
        f"⚜️ Serviço: <b>{purchase['product_name']}</b>\n"
        f"📧 Email: <code>{purchase.get('email') or 'N/A'}</code>\n"
        f"🔐 Senha: <code>{purchase.get('password') or 'N/A'}</code>\n"
        "📃 Nota: Use o link abaixo para ativar:\n\n"
        f"<i>Página {page}/{pages}</i>"
    )


def gift_prompt_text() -> str:
    return (
        "🎁 <b>RESGATAR GIFT CARD</b>\n"
        "Digite o código do seu gift card abaixo:\n"
        "Exemplo: <code>ABC123XYZ456</code>"
    )


def gift_invalid_text() -> str:
    return "❌ <b>Gift não encontrado.</b>\n\nVerifique o código e tente novamente."


def gift_already_used_text() -> str:
    return "❌ <b>Este gift card já foi resgatado.</b>"


def gift_success_text(gift: dict, extra: str = "") -> str:
    if gift.get("tipo") == "saldo":
        return (
            "🎉 <b>Gift Card resgatado!</b>\n\n"
            f"💰 Você recebeu <b>R$ {float(gift.get('valor', 0)):.2f}</b> de saldo.\n"
            f"💼 Saldo atualizado no seu perfil.\n{extra}"
        )
    return (
        "🎉 <b>Gift Card resgatado!</b>\n\n"
        "🎁 Você ganhou um produto!\n"
        "Clique em <b>🎁 Usar</b> abaixo para acessá-lo.\n"
        f"{extra}"
    )


def alter_data_text(user: dict) -> str:
    whats = user.get("whatsapp") or "Não cadastrado"
    return (
        "✏️ <b>Alterar Dados</b>\n"
        "Selecione o dado que deseja alterar:\n\n"
        f"📱 WhatsApp atual: <b>{whats}</b>"
    )


def whatsapp_prompt_text() -> str:
    return (
        "📱 <b>Envie seu número de WhatsApp</b>\n"
        "Formato: DDD + Número (apenas números)\n"
        "Exemplo: <code>11999998888</code>\n\n"
        "⚠️ Envie <code>remover</code> para remover o número cadastrado."
    )


def whatsapp_invalid_text() -> str:
    return (
        "❌ <b>Número inválido!</b>\n\n"
        "Formato: DDD + Número (apenas números).\n"
        "Exemplo: <code>11999998888</code>"
    )


def whatsapp_updated_text(number: str) -> str:
    return f"✅ <b>WhatsApp atualizado com sucesso!</b>\n\n📱 Novo número: <b>{number}</b>"


def whatsapp_removed_text() -> str:
    return "✅ <b>WhatsApp removido com sucesso!</b>"


def topup_menu_text() -> str:
    return (
        "💠 Opte por <b>PIX Rápido</b> para que seu saldo seja creditado imediatamente.\n"
        "💰 Selecione uma opção para recarregar:"
    )


def topup_value_prompt_text() -> str:
    return (
        "ℹ️ <b>Informe o valor que deseja recarregar:</b>\n"
        "🔻 Recarga mínima: <b>R$ 4,00</b>\n\n"
        "⚠️ Por favor, envie o valor que deseja recarregar agora.\n"
        "Ao realizar um depósito você declara ter lido e estar de acordo com nossos /termos\n\n"
        "🎁 Bônus de recarga: <b>10%</b>\n"
        "❗ Recarga mínima para ganhar o bônus: <b>R$ 10,00</b>"
    )


def topup_invalid_value_text() -> str:
    return (
        "❌ <b>Valor inválido!</b>\n\n"
        "Envie um número maior ou igual a <b>R$ 4,00</b>.\n"
        "Exemplo: <code>20</code> ou <code>20,00</code>"
    )


def topup_pix_caption(pix_id: str, valor: float, bonus: float, saldo_atual: float, saldo_futuro: float, expira: str) -> str:
    bonus_line = f"🎁 Bônus: <b>R$ {bonus:.2f}</b>\n" if bonus > 0 else ""
    return (
        "💠 <b>PIX de recarga gerado!</b>\n\n"
        f"💰 Valor: <b>R$ {valor:.2f}</b>\n"
        f"{bonus_line}"
        f"💼 Saldo atual: <b>R$ {saldo_atual:.2f}</b>\n"
        f"💸 Saldo após o pagamento: <b>R$ {saldo_futuro:.2f}</b>\n"
        f"🎫 ID: <code>{pix_id}</code>\n"
        f"⏰ Expira em: <b>{expira}</b>\n\n"
        "Escaneie o QR Code ou use o botão <b>📋 Copiar PIX</b>."
    )


def topup_success_text(valor: float, bonus: float, novo_saldo: float) -> str:
    bonus_line = f"🎁 Bônus aplicado: <b>R$ {bonus:.2f}</b>\n" if bonus > 0 else ""
    return (
        "✅ <b>Recarga realizada com sucesso!</b>\n\n"
        f"💰 Valor creditado: <b>R$ {valor + bonus:.2f}</b>\n"
        f"{bonus_line}"
        f"💼 Novo saldo: <b>R$ {novo_saldo:.2f}</b>"
    )


def topup_cancelled_text() -> str:
    return "❌ <b>Recarga cancelada.</b>"


def pix_cancelled_text() -> str:
    return "❌ <b>PIX cancelado.</b>"


# ═══════════════════════════════════════════════
# MÓDULO 4 — AFILIADOS, SAQUES, TOP, PESQUISA
# ═══════════════════════════════════════════════

def affiliates_inactive_text() -> str:
    return (
        "💰 <b>PROGRAMA DE AFILIADOS</b>\n\n"
        "⚙️ Status: ❌ <b>Inativo</b>\n"
        "🧲 Comissão: <b>20.0%</b>\n"
        "💰 Saque mínimo: <b>R$ 20.00</b>\n\n"
        "ℹ️ <b>INFO:</b> Seus indicados continuarão gerando comissão para sempre."
    )


def affiliates_active_text(user: dict, stats: dict, link: str) -> str:
    indicados = stats["indicados"]
    total = stats["total_ganho"]
    media = stats["media"]

    if indicados < 5:
        nivel = "Iniciante"
        emoji_nivel = "🌱"
        meta = 5
    elif indicados < 20:
        nivel = "Bronze"
        emoji_nivel = "🥉"
        meta = 20
    elif indicados < 50:
        nivel = "Prata"
        emoji_nivel = "🥈"
        meta = 50
    else:
        nivel = "Ouro"
        emoji_nivel = "🥇"
        meta = 100

    restantes = max(meta - indicados, 0)

    return (
        "💰 <b>PROGRAMA DE AFILIADOS</b>\n\n"
        "⚙️ Status: ✅ <b>Ativo</b>\n"
        "🧲 Sua comissão: <b>20.0%</b> (de todas recargas do indicado)\n\n"
        f"👥 Indicações: <b>{indicados}</b>\n"
        f"🪙 Total ganho: <b>R$ {total:.2f}</b>\n"
        f"📊 Média: <b>R$ {media:.2f}</b>\n"
        "💰 Saque mínimo: <b>R$ 20.00</b>\n\n"
        f"{emoji_nivel}| Nível: <b>{nivel}</b>\n"
        f"🎯 Próxima meta: <b>{meta}</b> ({restantes} restantes)\n\n"
        "ℹ️ <b>INFO:</b> Seus indicados continuarão gerando comissão para sempre.\n"
        "A comissão pode ser alterada a qualquer momento, fique atento aos avisos.\n\n"
        f"🔗 <b>Seu link:</b>\n<code>{link}</code>"
    )


def top_text(rows: list[dict], filtro: str) -> str:
    titulos = {
        "compras": "usuários que mais compraram (deste mês)",
        "recargas": "usuários que mais recarregaram",
        "gift": "usuários que mais resgataram gift cards",
        "saldo": "usuários com maior saldo",
    }
    t = titulos.get(filtro, titulos["compras"])

    linhas = [f"🏆 <b>Ranking dos {t}</b>\n"]
    medals = ["🥇", "🥈", "🥉"]

    if not rows:
        linhas.append("<i>Sem dados ainda.</i>")
    else:
        for i, r in enumerate(rows):
            pos = medals[i] if i < 3 else f"{i+1}º"
            nome = r.get("first_name") or r.get("username") or f"ID {r['user_id']}"
            total = float(r.get("total") or 0)
            linhas.append(f"{pos}) {nome} — <b>R$ {total:.2f}</b>")

    return "\n".join(linhas)
