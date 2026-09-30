from datetime import datetime
from texts import cache


# ═══════════════════════════════════════════════
# HELPER — substituição segura de variáveis
# ═══════════════════════════════════════════════
class _SafeDict(dict):
    def __missing__(self, key):
        return "{" + key + "}"


def _render(tpl: str, **kwargs) -> str:
    """
    Substitui variáveis no template. Também injeta:
      - store_name (do config)
      - support_link
      - bot_username
    """
    data = {
        "store_name":   cache.get_config("store_name", "Minha Loja"),
        "support_link": cache.get_config("telegram_link", ""),
        "bot_username": cache.get_config("bot_username", ""),
        **kwargs,
    }
    try:
        return tpl.format_map(_SafeDict(data))
    except Exception:
        return tpl


# ═══════════════════════════════════════════════
# MÓDULO 1 — GATE, MENU, CATÁLOGO, PRODUTO
# ═══════════════════════════════════════════════

def gate_text() -> str:
    return cache.get_text(
        "gate",
        "❗ <b>Para utilizar nosso serviço é obrigatório que você entre no nosso grupo.</b>",
    )


def welcome_text(user: dict) -> str:
    tpl = cache.get_text("welcome", "")
    return _render(
        tpl,
        user_id=user["user_id"],
        balance=float(user["balance"]),
    )


def catalog_text(user: dict) -> str:
    tpl = cache.get_text("catalog", "")
    return _render(tpl, balance=float(user["balance"]))


def product_text(user: dict, product: dict) -> str:
    tpl = cache.get_text("product", "")
    return _render(
        tpl,
        product_name=product["name"],
        price=float(product["price"]),
        balance=float(user["balance"]),
        stock=int(product["stock"]),
        description=product["description"],
        sold=int(product.get("sold", 0)),
        guarantee=int(product.get("guarantee", 180)),
    )


def about_text() -> str:
    tpl = cache.get_text("about", "")
    return _render(tpl)


def soon_text(area: str) -> str:
    return f"🚧 <b>{area}</b>\n\nEsse módulo será liberado em breve."


# ═══════════════════════════════════════════════
# MÓDULO 2 — COMPRA, PIX, ENTREGA, MULTI
# ═══════════════════════════════════════════════

def insufficient_text(user: dict, product: dict, quantity: int = 1) -> str:
    total = float(product["price"]) * quantity
    saldo = float(user["balance"])
    falta = max(total - saldo, 0)
    tpl = cache.get_text("insufficient", "")
    return _render(tpl, saldo=saldo, total=total, falta=falta)


def generating_payment_text() -> str:
    return cache.get_text("generating_payment", "⏳ <b>Gerando pagamento...</b>")


def pix_caption(pix_id: str, valor: float, expira: str) -> str:
    tpl = cache.get_text("pix_caption", "")
    return _render(tpl, pix_id=pix_id, valor=valor, expira=expira)


def not_paid_text() -> str:
    return cache.get_text("not_paid", "")


def paid_caption() -> str:
    return cache.get_text("paid_caption", "✅ <b>PAGAMENTO CONFIRMADO!</b>")


def pix_cancelled_text() -> str:
    return cache.get_text("pix_cancelled", "❌ <b>PIX cancelado.</b>")


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

    tpl = cache.get_text("delivery", "")
    return _render(
        tpl,
        created_fmt=created_fmt,
        expires_fmt=expires_fmt,
        total=float(purchase["total"]),
        purchase_id=purchase["id"],
        product_name=purchase["product_name"],
        email_show=email_show,
        pass_show=pass_show,
    )


def multi_qty_text(product: dict) -> str:
    tpl = cache.get_text("multi_qty", "")
    return _render(tpl, stock=int(product["stock"]))


def multi_result_text(user: dict, product: dict, qty: int) -> str:
    unit = float(product["price"])
    total = unit * qty
    tpl = cache.get_text("multi_result", "")
    return _render(
        tpl,
        product_name=product["name"],
        qty=qty,
        unit=unit,
        total=total,
        balance=float(user["balance"]),
    )


def multi_cancelled_text() -> str:
    return cache.get_text("multi_cancelled", "")


# ═══════════════════════════════════════════════
# MÓDULO 3 — PERFIL, HISTÓRICO, GIFT, DADOS, RECARGA
# ═══════════════════════════════════════════════

def profile_text(user: dict, stats: dict | None = None) -> str:
    stats = stats or {}
    whatsapp = user.get("whatsapp") or "Não cadastrado"
    tpl = cache.get_text("profile", "")
    return _render(
        tpl,
        user_id=user["user_id"],
        balance=float(user["balance"]),
        whatsapp=whatsapp,
        compras=stats.get("compras", 0),
        gasto=stats.get("gasto", 0.0),
        pix_in=stats.get("pix_inseridos", 0.0),
        gifts=stats.get("gifts_valor", 0.0),
    )


def history_empty_text() -> str:
    return cache.get_text("history_empty", "")


def history_active_empty_text() -> str:
    return cache.get_text("history_active_empty", "")


def _fmt_date(s) -> str:
    try:
        return datetime.strptime(str(s)[:19], "%Y-%m-%d %H:%M:%S").strftime("%d/%m/%Y")
    except Exception:
        return str(s)


def history_item_text(purchase: dict, idx: int, total: int, page: int, pages: int) -> str:
    tpl = cache.get_text("history_item", "")
    return _render(
        tpl,
        total=total,
        created_fmt=_fmt_date(purchase["created_at"]),
        expires_fmt=_fmt_date(purchase["expires_at"]),
        valor=float(purchase["total"]),
        purchase_id=purchase["id"],
        product_name=purchase["product_name"],
        email=purchase.get("email") or "N/A",
        password=purchase.get("password") or "N/A",
        page=page,
        pages=pages,
    )


def gift_prompt_text() -> str:
    return cache.get_text("gift_prompt", "")


def gift_invalid_text() -> str:
    return cache.get_text("gift_invalid", "")


def gift_already_used_text() -> str:
    return cache.get_text("gift_already_used", "")


def gift_success_text(gift: dict, extra: str = "") -> str:
    if gift.get("tipo") == "saldo":
        tpl = cache.get_text("gift_success_saldo", "")
        return _render(tpl, valor=float(gift.get("valor", 0))) + extra
    return cache.get_text("gift_success_produto", "") + extra


def alter_data_text(user: dict) -> str:
    whats = user.get("whatsapp") or "Não cadastrado"
    tpl = cache.get_text("alter_data", "")
    return _render(tpl, whatsapp=whats)


def whatsapp_prompt_text() -> str:
    return cache.get_text("whatsapp_prompt", "")


def whatsapp_invalid_text() -> str:
    return cache.get_text("whatsapp_invalid", "")


def whatsapp_updated_text(number: str) -> str:
    tpl = cache.get_text("whatsapp_updated", "")
    return _render(tpl, numero=number)


def whatsapp_removed_text() -> str:
    return cache.get_text("whatsapp_removed", "")


def topup_menu_text() -> str:
    return cache.get_text("topup_menu", "")


def topup_value_prompt_text() -> str:
    return cache.get_text("topup_value_prompt", "")


def topup_invalid_value_text() -> str:
    return cache.get_text("topup_invalid", "")


def topup_pix_caption(pix_id, valor, bonus, saldo_atual, saldo_futuro, expira) -> str:
    bonus_line = f"🎁 Bônus: <b>R$ {bonus:.2f}</b>\n" if bonus > 0 else ""
    tpl = cache.get_text("topup_pix_caption", "")
    return _render(
        tpl,
        pix_id=pix_id,
        valor=valor,
        bonus=bonus,
        bonus_line=bonus_line,
        saldo_atual=saldo_atual,
        saldo_futuro=saldo_futuro,
        expira=expira,
    )


def topup_success_text(valor, bonus, novo_saldo) -> str:
    bonus_line = f"🎁 Bônus aplicado: <b>R$ {bonus:.2f}</b>\n" if bonus > 0 else ""
    tpl = cache.get_text("topup_success", "")
    return _render(
        tpl,
        valor_total=valor + bonus,
        bonus=bonus,
        bonus_line=bonus_line,
        novo_saldo=novo_saldo,
    )


def topup_cancelled_text() -> str:
    return cache.get_text("topup_cancelled", "")


# ═══════════════════════════════════════════════
# MÓDULO 4 — AFILIADOS, TOP, SAQUES
# ═══════════════════════════════════════════════

def affiliates_inactive_text() -> str:
    tpl = cache.get_text("affiliates_inactive", "")
    return _render(
        tpl,
        comissao=int(cache.get_config("affiliate_commission", "20")),
        saque_min=float(cache.get_config("withdraw_min", "20.00")),
    )


def affiliates_active_text(user: dict, stats: dict, link: str) -> str:
    indicados = stats["indicados"]
    total = stats["total_ganho"]
    media = stats["media"]

    if indicados < 5:
        nivel, emoji_nivel, meta = "Iniciante", "🌱", 5
    elif indicados < 20:
        nivel, emoji_nivel, meta = "Bronze", "🥉", 20
    elif indicados < 50:
        nivel, emoji_nivel, meta = "Prata", "🥈", 50
    else:
        nivel, emoji_nivel, meta = "Ouro", "🥇", 100

    restantes = max(meta - indicados, 0)

    tpl = cache.get_text("affiliates_active", "")
    return _render(
        tpl,
        comissao=int(cache.get_config("affiliate_commission", "20")),
        saque_min=float(cache.get_config("withdraw_min", "20.00")),
        indicados=indicados,
        total=total,
        media=media,
        nivel=nivel,
        emoji_nivel=emoji_nivel,
        meta=meta,
        restantes=restantes,
        link=link,
    )


def top_text(rows: list[dict], filtro: str) -> str:
    titulos = {
        "compras": "serviços mais vendidos (deste mês)",
        "recargas": "usuários que mais recarregaram",
        "gift": "usuários que mais resgataram gift cards",
        "saldo": "usuários com maior saldo",
    }
    t = titulos.get(filtro, titulos["compras"])

    medals = ["🥇", "🥈", "🥉"]
    linhas = []

    if not rows:
        linhas.append("<i>Sem dados ainda.</i>")
    else:
        for i, r in enumerate(rows):
            pos = medals[i] if i < 3 else f"{i+1}º"
            nome = r.get("first_name") or r.get("username") or f"ID {r['user_id']}"
            total = float(r.get("total") or 0)

            if filtro == "compras":
                qtd = int(r.get("pedidos") or 0)
                linhas.append(f"{pos}) {nome} {pos if i < 3 else ''} - Com {qtd} pedidos")
            else:
                linhas.append(f"{pos}) {nome} — <b>R$ {total:.2f}</b>")

    tpl = cache.get_text("top_ranking", "")
    return _render(tpl, titulo=t, linhas="\n".join(linhas))


# ═══════════════════════════════════════════════
# TELAS DE SAQUE
# ═══════════════════════════════════════════════

def withdraw_menu_text() -> str:
    return (
        "💸 <b>Você deseja sacar?</b>\n"
        "Para que possamos realizar seu saque, selecione o tipo de chave PIX:"
    )


def withdraw_key_prompt(key_type_label: str) -> str:
    return f"Cadastre o seu <b>{key_type_label}</b> como chave de saque:"


def withdraw_confirm_key_text(user: dict, key_type: str) -> str:
    pix_key = user.get("pix_key") or "-"
    name = user.get("pix_name") or (user.get("first_name") or "Usuário")
    bank = user.get("pix_bank") or "—"

    masked = pix_key
    if key_type == "cpf":
        digits = "".join(c for c in pix_key if c.isdigit())
        if len(digits) == 11:
            masked = f"***.***.***-{digits[-2:]}"

    return (
        "Confirma essa é sua chave?\n"
        f"👤 Nome: <b>{name}</b>\n"
        f"🏦 Banco: <b>{bank}</b>\n"
        f"🆔 {key_type.upper()}: <code>{masked}</code>"
    )


def withdraw_confirm_balance_text(balance: float) -> str:
    return (
        f"💰 Você possui <b>R$ {balance:.2f}</b> disponível para saque.\n"
        "💵 Saque mínimo: <b>R$ 20,00</b>"
    )


def greet_by_hour(name: str) -> str:
    h = datetime.now().hour
    if 5 <= h < 12:
        prefix = "🌅 Bom dia"
    elif 12 <= h < 18:
        prefix = "🌇 Boa tarde"
    else:
        prefix = "🌙 Boa noite"
    return f"{prefix}, <b>{name}</b>!"


def withdraw_amount_prompt(name: str, balance: float) -> str:
    return (
        f"{greet_by_hour(name)}\n"
        "💸 Quantos você quer sacar?\n"
        f"💰 Saldo disponível: <b>R$ {balance:.2f}</b>\n"
        "💵 Saque mínimo: <b>R$ 20,00</b>"
    )


def withdraw_password_prompt() -> str:
    return "🔐 Digite sua senha de 6 dígitos para confirmar o saque:"


def withdraw_wrong_password() -> str:
    return "❌ <b>Senha incorreta!</b>"


def withdraw_processing() -> str:
    return "⏳ <b>Pagamento em processamento...</b>"


def withdraw_success_text(wd: dict) -> str:
    return (
        "✅ <b>Pagamento realizado com sucesso!</b>\n\n"
        f"💰 Valor: <b>R$ {float(wd['amount']):.2f}</b>\n"
        f"🔑 Chave: <code>{wd['pix_key']}</code>\n"
        f"📄 ID: <code>{wd['id']}</code>\n"
        f"🕐 {wd.get('created_at', '')}"
    )


def withdraw_invalid_amount() -> str:
    return (
        "❌ <b>Valor inválido!</b>\n\n"
        "Envie um número >= R$ 20,00 e menor/igual ao seu saldo."
    )


def withdraw_no_pin() -> str:
    return (
        "🔐 <b>Você ainda não cadastrou uma senha de saque.</b>\n\n"
        "Use o botão <b>🔐 Cadastrar Senha de Saque</b> no menu de Afiliados."
    )


# ═══════════════════════════════════════════════
# TELAS DE PESQUISA
# ═══════════════════════════════════════════════

def search_prompt_text() -> str:
    return (
        "🔎 <b>Como procurar um serviço?</b>\n"
        "Digite: <code>procurar &lt;nome do serviço&gt;</code>"
    )


def search_no_results(term: str) -> str:
    return f"❌ <b>Nenhum serviço encontrado com \"{term}\"</b>"


def search_results_intro(term: str, count: int) -> str:
    return f"🔎 Encontrados <b>{count}</b> resultados para \"{term}\":"


def search_product_card(product: dict) -> str:
    price = float(product["price"])
    return (
        f"<b>{product['emoji']} {product['name']}</b> — R$ {price:.2f}\n"
        f"{(product.get('description') or '')[:120]}"
    )
