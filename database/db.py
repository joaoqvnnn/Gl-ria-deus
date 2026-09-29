import aiosqlite
import uuid
import hashlib
from datetime import datetime, timedelta
from config import DB_PATH

_db: aiosqlite.Connection | None = None


# ═══════════════════════════════════════════════
# HELPERS
# ═══════════════════════════════════════════════
def hash_pin(pin: str) -> str:
    """Gera hash SHA-256 da senha de saque."""
    return hashlib.sha256(pin.encode()).hexdigest()


async def _try_alter(sql: str):
    """Executa ALTER TABLE silenciosamente (para bases antigas)."""
    try:
        await _db.execute(sql)
        await _db.commit()
    except Exception:
        pass


# ═══════════════════════════════════════════════
# INIT
# ═══════════════════════════════════════════════
async def init_db():
    global _db
    _db = await aiosqlite.connect(DB_PATH)
    _db.row_factory = aiosqlite.Row

    await _db.executescript(
        """
        CREATE TABLE IF NOT EXISTS users (
            user_id      INTEGER PRIMARY KEY,
            username     TEXT,
            first_name   TEXT,
            balance      REAL DEFAULT 0,
            whatsapp     TEXT,
            created_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS products (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            name         TEXT NOT NULL,
            description  TEXT,
            price        REAL NOT NULL,
            stock        INTEGER DEFAULT 0,
            emoji        TEXT DEFAULT '📦',
            sold         INTEGER DEFAULT 0,
            guarantee    INTEGER DEFAULT 180,
            activate_url TEXT DEFAULT 'https://t.me/',
            active       INTEGER DEFAULT 1,
            created_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS stock_items (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            product_id   INTEGER NOT NULL,
            email        TEXT,
            password     TEXT,
            used         INTEGER DEFAULT 0,
            created_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS purchases (
            id           TEXT PRIMARY KEY,
            user_id      INTEGER NOT NULL,
            product_id   INTEGER NOT NULL,
            product_name TEXT,
            quantity     INTEGER DEFAULT 1,
            total        REAL,
            email        TEXT,
            password     TEXT,
            created_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            expires_at   TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS pix_pending (
            id           TEXT PRIMARY KEY,
            user_id      INTEGER NOT NULL,
            valor        REAL NOT NULL,
            tipo         TEXT NOT NULL,
            product_id   INTEGER,
            quantity     INTEGER,
            copia_cola   TEXT,
            status       TEXT DEFAULT 'pending',
            created_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS gift_cards (
            code         TEXT PRIMARY KEY,
            tipo         TEXT NOT NULL,
            valor        REAL DEFAULT 0,
            product_id   INTEGER,
            redeemed_by  INTEGER,
            redeemed_at  TIMESTAMP,
            created_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS affiliate_earnings (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            affiliate_id INTEGER NOT NULL,
            referred_id  INTEGER NOT NULL,
            amount       REAL NOT NULL,
            source       TEXT,
            created_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS withdrawals (
            id           TEXT PRIMARY KEY,
            user_id      INTEGER NOT NULL,
            amount       REAL NOT NULL,
            pix_key_type TEXT,
            pix_key      TEXT,
            status       TEXT DEFAULT 'pending',
            created_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            processed_at TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS cart_views (
            user_id     INTEGER NOT NULL,
            product_id  INTEGER NOT NULL,
            viewed_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            notified    INTEGER DEFAULT 0,
            PRIMARY KEY (user_id, product_id)
        );

        CREATE INDEX IF NOT EXISTS idx_users_referred_by ON users(referred_by);
        CREATE INDEX IF NOT EXISTS idx_purchases_user   ON purchases(user_id);
        CREATE INDEX IF NOT EXISTS idx_purchases_prod   ON purchases(product_id);
        CREATE INDEX IF NOT EXISTS idx_pix_user         ON pix_pending(user_id);
        CREATE INDEX IF NOT EXISTS idx_cart_notified    ON cart_views(notified);
        """
    )
    await _db.commit()

    # ─── Colunas novas em users (seguro para bases existentes)
    await _try_alter("ALTER TABLE users ADD COLUMN referred_by INTEGER")
    await _try_alter("ALTER TABLE users ADD COLUMN is_affiliate INTEGER DEFAULT 0")
    await _try_alter("ALTER TABLE users ADD COLUMN payout_password TEXT")
    await _try_alter("ALTER TABLE users ADD COLUMN pix_key_type TEXT")
    await _try_alter("ALTER TABLE users ADD COLUMN pix_key TEXT")
    await _try_alter("ALTER TABLE users ADD COLUMN pix_name TEXT")
    await _try_alter("ALTER TABLE users ADD COLUMN pix_bank TEXT")


# ═══════════════════════════════════════════════
# USERS
# ═══════════════════════════════════════════════
async def get_or_create_user(user_id, username, first_name):
    cur = await _db.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
    row = await cur.fetchone()
    if row is None:
        await _db.execute(
            "INSERT INTO users (user_id, username, first_name) VALUES (?, ?, ?)",
            (user_id, username or "", first_name or ""),
        )
        await _db.commit()
        cur = await _db.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
        row = await cur.fetchone()
    return dict(row)


async def get_user(user_id):
    cur = await _db.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
    row = await cur.fetchone()
    return dict(row) if row else None


async def update_balance(user_id: int, delta: float):
    await _db.execute(
        "UPDATE users SET balance = balance + ? WHERE user_id = ?",
        (delta, user_id),
    )
    await _db.commit()


async def set_whatsapp(user_id: int, whatsapp):
    await _db.execute(
        "UPDATE users SET whatsapp = ? WHERE user_id = ?",
        (whatsapp, user_id),
    )
    await _db.commit()


async def set_referred_by(user_id: int, referrer_id: int):
    """Define quem indicou o usuário (não sobrescreve se já tiver)."""
    if user_id == referrer_id:
        return
    u = await get_user(user_id)
    if not u or u.get("referred_by"):
        return
    await _db.execute(
        "UPDATE users SET referred_by = ? WHERE user_id = ?",
        (referrer_id, user_id),
    )
    await _db.commit()


async def activate_affiliate(user_id: int):
    await _db.execute(
        "UPDATE users SET is_affiliate = 1 WHERE user_id = ?", (user_id,)
    )
    await _db.commit()


async def set_payout_password(user_id: int, pin: str):
    await _db.execute(
        "UPDATE users SET payout_password = ? WHERE user_id = ?",
        (hash_pin(pin), user_id),
    )
    await _db.commit()


async def check_payout_password(user_id: int, pin: str) -> bool:
    u = await get_user(user_id)
    if not u or not u.get("payout_password"):
        return False
    return u["payout_password"] == hash_pin(pin)


async def set_pix_key(user_id, key_type, pix_key, name=None, bank=None):
    await _db.execute(
        "UPDATE users SET pix_key_type=?, pix_key=?, pix_name=?, pix_bank=? "
        "WHERE user_id=?",
        (key_type, pix_key, name, bank, user_id),
    )
    await _db.commit()


async def user_stats(user_id: int) -> dict:
    """Estatísticas consolidadas para o perfil."""
    # Compras
    cur = await _db.execute(
        "SELECT COUNT(*) AS c, COALESCE(SUM(total), 0) AS s FROM purchases WHERE user_id = ?",
        (user_id,),
    )
    row = await cur.fetchone()
    compras = int(row["c"])
    gasto = float(row["s"])

    # PIX inseridos (só recarga paga)
    cur = await _db.execute(
        "SELECT COALESCE(SUM(valor), 0) AS s FROM pix_pending "
        "WHERE user_id = ? AND tipo = 'recarga' AND status = 'paid'",
        (user_id,),
    )
    pix_inseridos = float((await cur.fetchone())["s"])

    # Gifts resgatados
    cur = await _db.execute(
        "SELECT COUNT(*) AS c, COALESCE(SUM(valor), 0) AS s FROM gift_cards "
        "WHERE redeemed_by = ?",
        (user_id,),
    )
    row = await cur.fetchone()
    gifts_count = int(row["c"])
    gifts_valor = float(row["s"])

    return {
        "compras": compras,
        "gasto": gasto,
        "pix_inseridos": pix_inseridos,
        "gifts_count": gifts_count,
        "gifts_valor": gifts_valor,
    }


# ═══════════════════════════════════════════════
# PRODUCTS
# ═══════════════════════════════════════════════
async def get_products():
    cur = await _db.execute("SELECT * FROM products WHERE active = 1 ORDER BY id ASC")
    return [dict(r) for r in await cur.fetchall()]


async def search_products(term: str):
    cur = await _db.execute(
        "SELECT * FROM products WHERE active = 1 AND name LIKE ? ORDER BY id ASC LIMIT 20",
        (f"%{term}%",),
    )
    return [dict(r) for r in await cur.fetchall()]


async def get_product(pid: int):
    cur = await _db.execute("SELECT * FROM products WHERE id = ?", (pid,))
    row = await cur.fetchone()
    return dict(row) if row else None


async def decrement_stock(pid: int, qty: int):
    await _db.execute(
        "UPDATE products SET stock = MAX(stock - ?, 0), sold = sold + ? WHERE id = ?",
        (qty, qty, pid),
    )
    await _db.commit()


async def add_product(name, description, price, stock, emoji="📦", activate_url="https://t.me/"):
    await _db.execute(
        "INSERT INTO products (name, description, price, stock, emoji, activate_url) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        (name, description, price, stock, emoji, activate_url),
    )
    await _db.commit()


# ═══════════════════════════════════════════════
# STOCK ITEMS
# ═══════════════════════════════════════════════
async def take_stock_items(product_id: int, qty: int):
    cur = await _db.execute(
        "SELECT * FROM stock_items WHERE product_id = ? AND used = 0 LIMIT ?",
        (product_id, qty),
    )
    rows = await cur.fetchall()
    items = [dict(r) for r in rows]
    if items:
        ids = [it["id"] for it in items]
        ph = ",".join("?" for _ in ids)
        await _db.execute(
            f"UPDATE stock_items SET used = 1 WHERE id IN ({ph})", ids
        )
        await _db.commit()
    return items


# ═══════════════════════════════════════════════
# PURCHASES
# ═══════════════════════════════════════════════
async def create_purchase(user_id, product_id, product_name, quantity, total, email, password, days=30):
    purchase_id = str(uuid.uuid4())
    expires = (datetime.now() + timedelta(days=days)).strftime("%Y-%m-%d %H:%M:%S")
    await _db.execute(
        "INSERT INTO purchases (id, user_id, product_id, product_name, quantity, total, email, password, expires_at) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (purchase_id, user_id, product_id, product_name, quantity, total, email, password, expires),
    )
    await _db.commit()
    cur = await _db.execute("SELECT * FROM purchases WHERE id = ?", (purchase_id,))
    return dict(await cur.fetchone())


async def get_purchase(pid: str):
    cur = await _db.execute("SELECT * FROM purchases WHERE id = ?", (pid,))
    row = await cur.fetchone()
    return dict(row) if row else None


async def list_purchases(user_id: int, only_active: bool = False):
    if only_active:
        cur = await _db.execute(
            "SELECT * FROM purchases WHERE user_id = ? AND expires_at > datetime('now') "
            "ORDER BY created_at DESC",
            (user_id,),
        )
    else:
        cur = await _db.execute(
            "SELECT * FROM purchases WHERE user_id = ? ORDER BY created_at DESC",
            (user_id,),
        )
    return [dict(r) for r in await cur.fetchall()]


# ═══════════════════════════════════════════════
# PIX
# ═══════════════════════════════════════════════
async def create_pix(pix_id, user_id, valor, tipo, product_id, quantity, copia_cola):
    await _db.execute(
        "INSERT INTO pix_pending (id, user_id, valor, tipo, product_id, quantity, copia_cola) "
        "VALUES (?, ?, ?, ?, ?, ?, ?)",
        (pix_id, user_id, valor, tipo, product_id, quantity, copia_cola),
    )
    await _db.commit()


async def get_pix(pix_id):
    cur = await _db.execute("SELECT * FROM pix_pending WHERE id = ?", (pix_id,))
    row = await cur.fetchone()
    return dict(row) if row else None


async def mark_pix_paid(pix_id):
    await _db.execute("UPDATE pix_pending SET status = 'paid' WHERE id = ?", (pix_id,))
    await _db.commit()


async def cancel_pix(pix_id):
    await _db.execute("UPDATE pix_pending SET status = 'cancelled' WHERE id = ?", (pix_id,))
    await _db.commit()


# ═══════════════════════════════════════════════
# GIFT CARDS
# ═══════════════════════════════════════════════
async def get_gift(code: str):
    cur = await _db.execute("SELECT * FROM gift_cards WHERE code = ?", (code,))
    row = await cur.fetchone()
    return dict(row) if row else None


async def redeem_gift(code: str, user_id: int):
    await _db.execute(
        "UPDATE gift_cards SET redeemed_by = ?, redeemed_at = CURRENT_TIMESTAMP WHERE code = ?",
        (user_id, code),
    )
    await _db.commit()


async def create_gift(code, tipo, valor=0, product_id=None):
    await _db.execute(
        "INSERT INTO gift_cards (code, tipo, valor, product_id) VALUES (?, ?, ?, ?)",
        (code, tipo, valor, product_id),
    )
    await _db.commit()


# ═══════════════════════════════════════════════
# AFILIADOS
# ═══════════════════════════════════════════════
async def affiliate_stats(user_id: int) -> dict:
    # Quantos usuários foram indicados por ele
    cur = await _db.execute(
        "SELECT COUNT(*) AS c FROM users WHERE referred_by = ?", (user_id,)
    )
    indicados = int((await cur.fetchone())["c"])

    # Total ganho em comissões
    cur = await _db.execute(
        "SELECT COALESCE(SUM(amount), 0) AS s, COUNT(*) AS c "
        "FROM affiliate_earnings WHERE affiliate_id = ?",
        (user_id,),
    )
    row = await cur.fetchone()
    total_ganho = float(row["s"])
    ganhos_count = int(row["c"])
    media = (total_ganho / ganhos_count) if ganhos_count else 0.0

    return {
        "indicados": indicados,
        "total_ganho": total_ganho,
        "media": media,
    }


async def add_affiliate_earning(affiliate_id, referred_id, amount, source="recarga"):
    await _db.execute(
        "INSERT INTO affiliate_earnings (affiliate_id, referred_id, amount, source) "
        "VALUES (?, ?, ?, ?)",
        (affiliate_id, referred_id, amount, source),
    )
    await _db.commit()
    # Credita no saldo do afiliado automaticamente
    await update_balance(affiliate_id, amount)


async def list_affiliate_earnings(affiliate_id: int, limit: int = 50):
    cur = await _db.execute(
        "SELECT * FROM affiliate_earnings WHERE affiliate_id = ? "
        "ORDER BY created_at DESC LIMIT ?",
        (affiliate_id, limit),
    )
    return [dict(r) for r in await cur.fetchall()]


# ═══════════════════════════════════════════════
# SAQUES
# ═══════════════════════════════════════════════
async def create_withdrawal(user_id, amount, pix_key_type, pix_key):
    wid = str(uuid.uuid4())
    await _db.execute(
        "INSERT INTO withdrawals (id, user_id, amount, pix_key_type, pix_key) "
        "VALUES (?, ?, ?, ?, ?)",
        (wid, user_id, amount, pix_key_type, pix_key),
    )
    await _db.commit()
    cur = await _db.execute("SELECT * FROM withdrawals WHERE id = ?", (wid,))
    return dict(await cur.fetchone())


async def list_withdrawals(user_id: int):
    cur = await _db.execute(
        "SELECT * FROM withdrawals WHERE user_id = ? ORDER BY created_at DESC",
        (user_id,),
    )
    return [dict(r) for r in await cur.fetchall()]


async def mark_withdrawal_processed(wid: str):
    await _db.execute(
        "UPDATE withdrawals SET status='processed', processed_at=CURRENT_TIMESTAMP "
        "WHERE id = ?",
        (wid,),
    )
    await _db.commit()


# ═══════════════════════════════════════════════
# TOP COMPRADORES
# ═══════════════════════════════════════════════
async def top_buyers(limit: int = 10):
    cur = await _db.execute(
        "SELECT u.user_id, u.first_name, u.username, "
        "COALESCE(SUM(p.total), 0) AS total "
        "FROM users u LEFT JOIN purchases p ON p.user_id = u.user_id "
        "GROUP BY u.user_id ORDER BY total DESC LIMIT ?",
        (limit,),
    )
    return [dict(r) for r in await cur.fetchall()]


async def top_by_balance(limit: int = 10):
    cur = await _db.execute(
        "SELECT user_id, first_name, username, balance AS total "
        "FROM users ORDER BY balance DESC LIMIT ?",
        (limit,),
    )
    return [dict(r) for r in await cur.fetchall()]


async def top_by_topup(limit: int = 10):
    cur = await _db.execute(
        "SELECT u.user_id, u.first_name, u.username, "
        "COALESCE(SUM(px.valor),0) AS total "
        "FROM users u LEFT JOIN pix_pending px ON px.user_id = u.user_id "
        "AND px.tipo='recarga' AND px.status='paid' "
        "GROUP BY u.user_id ORDER BY total DESC LIMIT ?",
        (limit,),
    )
    return [dict(r) for r in await cur.fetchall()]


async def top_by_gift(limit: int = 10):
    cur = await _db.execute(
        "SELECT u.user_id, u.first_name, u.username, "
        "COALESCE(SUM(g.valor),0) AS total "
        "FROM users u LEFT JOIN gift_cards g ON g.redeemed_by = u.user_id "
        "GROUP BY u.user_id ORDER BY total DESC LIMIT ?",
        (limit,),
    )
    return [dict(r) for r in await cur.fetchall()]


# ═══════════════════════════════════════════════
# CARRINHO ABANDONADO
# ═══════════════════════════════════════════════
async def save_cart_view(user_id: int, product_id: int):
    """Salva que o usuário visualizou um produto (upsert)."""
    await _db.execute(
        "INSERT INTO cart_views (user_id, product_id, viewed_at, notified) "
        "VALUES (?, ?, CURRENT_TIMESTAMP, 0) "
        "ON CONFLICT(user_id, product_id) DO UPDATE SET "
        "viewed_at = CURRENT_TIMESTAMP, notified = 0",
        (user_id, product_id),
    )
    await _db.commit()


async def clear_cart_view(user_id: int, product_id: int):
    """Remove o carrinho abandonado quando o usuário compra."""
    await _db.execute(
        "DELETE FROM cart_views WHERE user_id = ? AND product_id = ?",
        (user_id, product_id),
    )
    await _db.commit()


async def list_abandoned_carts(minutes: int = 5):
    """
    Retorna carrinhos abandonados:
      - Viu o produto há mais de X minutos
      - Ainda não foi notificado
      - Não comprou depois disso
    """
    cur = await _db.execute(
        """
        SELECT c.user_id, c.product_id, c.viewed_at
        FROM cart_views c
        WHERE c.notified = 0
          AND c.viewed_at <= datetime('now', ?)
          AND NOT EXISTS (
              SELECT 1 FROM purchases p
              WHERE p.user_id = c.user_id
                AND p.product_id = c.product_id
                AND p.created_at >= c.viewed_at
          )
        """,
        (f"-{minutes} minutes",),
    )
    return [dict(r) for r in await cur.fetchall()]


async def mark_cart_notified(user_id: int, product_id: int):
    await _db.execute(
        "UPDATE cart_views SET notified = 1 WHERE user_id = ? AND product_id = ?",
        (user_id, product_id),
    )
    await _db.commit()


# ═══════════════════════════════════════════════
# SEED (popula o catálogo na 1ª execução)
# ═══════════════════════════════════════════════
async def seed_products():
    cur = await _db.execute("SELECT COUNT(*) AS c FROM products")
    row = await cur.fetchone()
    if row["c"] > 0:
        return

    catalogo = [
        ("CANVA PRO (6 MESES)",
         "LEIA A DESCRIÇÃO DO PRODUTO\nApós a compra, enviaremos o e-mail e a senha.\n\n"
         "✅ Assinatura de 6 meses\n✅ Funciona 24 horas por dia, sem interrupções\n"
         "✅ Renovação automática\n✅ Conta privada\n✅ Plano CANVA EDUCATION\n\n"
         "🔥🔥🔥 Garantia total 🔥🔥🔥",
         18.00, 3, "🎨"),

        ("Disney+ Plano Padrão", "Plano padrão Disney+ com catálogo completo.", 2.90, 10, "🏰"),
        ("GLOBO + CS + PREMIERE + TELECINE", "Pacote completo Globo + canais.", 5.90, 5, "📺"),
        ("GLOBOPLAY + CANAIS", "Tela (globoplay + canais) Plano Premium.", 3.90, 8, "🎬"),
        ("HBO MAX", "Plano HBO Max completo.", 8.00, 5, "🎥"),
        ("IPTV Elite", "+30k Conteúdos e Canais. Pacote IPTV Elite mensal.", 25.00, 10, "📡"),
        ("IPTV REVENDA (10 CREDITOS)", "Revenda IPTV com 10 créditos.", 50.00, 3, "💼"),
        ("IPTV Standard", "Canais Aberto e Fechado.", 15.00, 10, "📺"),
        ("NETFLIX 4K PREMIUM", "Plano Netflix 4K Premium.", 14.90, 5, "🎞"),
        ("P2P ANTI-TRAVAMENTO", "Sistema anti-travamento P2P.", 20.00, 4, "🛡"),
        ("SKY + Hbo + Paramount + Premiere", "Combo SKY completo.", 9.90, 5, "🛰"),
    ]
    for name, desc, price, stock, emoji in catalogo:
        await _db.execute(
            "INSERT INTO products (name, description, price, stock, emoji) VALUES (?, ?, ?, ?, ?)",
            (name, desc, price, stock, emoji),
        )

    # 3 contas Canva de exemplo
    for i in range(1, 4):
        await _db.execute(
            "INSERT INTO stock_items (product_id, email, password) VALUES (?, ?, ?)",
            (1, f"canva_cliente{i}@larizinha.com", f"SenhaForte#{i}2026"),
        )

    # Gift card de teste
    await _db.execute(
        "INSERT OR IGNORE INTO gift_cards (code, tipo, valor) VALUES (?, ?, ?)",
        ("LARI2026", "saldo", 10.00),
    )

    await _db.commit()
