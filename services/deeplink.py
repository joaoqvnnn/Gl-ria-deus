"""
Serviço responsável por interpretar o payload do deep link (?start=...).
Formatos suportados:
  - "8939269687"     → indicação de afiliado (ID do indicador)
  - "promo_<termo>"  → abre produto buscando por nome (ex: promo_netflix)
  - "prod_<id>"      → abre produto pelo ID exato (ex: prod_3)
  - "loja"           → abre direto o catálogo
"""
from database import db


async def resolve_payload(payload: str) -> dict:
    """
    Retorna um dict com o tipo e dados resolvidos.
    Tipos possíveis:
      - {"type": "referral", "referrer_id": int}
      - {"type": "product",  "product_id": int}
      - {"type": "catalog"}
      - {"type": "unknown"}
    """
    if not payload:
        return {"type": "unknown"}

    payload = payload.strip()

    # ─── Indicação (só números)
    if payload.isdigit():
        try:
            return {"type": "referral", "referrer_id": int(payload)}
        except ValueError:
            return {"type": "unknown"}

    # ─── Produto exato: prod_3
    if payload.startswith("prod_"):
        try:
            pid = int(payload.replace("prod_", "", 1))
        except ValueError:
            return {"type": "unknown"}

        product = await db.get_product(pid)
        if product:
            return {"type": "product", "product_id": pid}
        return {"type": "unknown"}

    # ─── Promoção: promo_netflix (busca por nome)
    if payload.startswith("promo_"):
        term = payload.replace("promo_", "", 1).strip()
        results = await db.search_products(term)
        if results:
            return {"type": "product", "product_id": results[0]["id"]}
        return {"type": "unknown"}

    # ─── Loja direta
    if payload == "loja":
        return {"type": "catalog"}

    return {"type": "unknown"}
