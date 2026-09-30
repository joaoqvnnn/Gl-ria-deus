async def top_buyers(limit: int = 10):
    """
    Retorna os produtos mais vendidos (nome + qtd de pedidos).
    """
    cur = await _db.execute(
        "SELECT product_name AS first_name, "
        "       COALESCE(SUM(quantity), 0) AS pedidos, "
        "       COALESCE(SUM(total), 0) AS total "
        "FROM purchases "
        "GROUP BY product_name "
        "ORDER BY pedidos DESC LIMIT ?",
        (limit,),
    )
    return [dict(r) for r in await cur.fetchall()]
