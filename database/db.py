import aiosqlite
import uuid
from datetime import datetime, timedelta
from config import DB_PATH

_db: aiosqlite.Connection | None = None


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
        """
    )
    await _db.commit()


# ───────────── USERS ─────────────
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


async def set_whatsapp(user_id: int, whatsapp: str | None):
    await _db.execute(
        "UPDATE users SET whatsapp = ? WHERE user_id = ?",
        (whatsapp, user_id),
    )
    await _db.commit()


async def user_stats(user_id: int) -> dict:
    """Retorna estatísticas consolidadas para o perfil."""
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
    row = await cur.fetchone()
    pix_inseridos = float(row["s"])

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


# ───────────── PRODUCTS ─────────────
async def get_products():
    cur = await _db.execute("SELECT * FROM products WHERE active = 1 ORDER BY id ASC")
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


# ───────────── STOCK ITEMS ─────────────
async def take_stock_items(product_id: int, qty: int):
    cur = await _db.execute(
        "SELECT * FROM stock_items WHERE product_id = ? AND used = 0 LIMIT ?",
        (product_id, qty),
    )
    rows = await cur.fetchall()
    items = [dict(r) for r in rows]
    if items:
        ids = [it["id"] for it in items]
        placeholders = ",".join("?" for _ in ids)
        await _db.execute(
            f"UPDATE stock_items SET used = 1 WHERE id IN ({placeholders})", ids
        )
        await _db.commit()
    return items


# ───────────── PURCHASES ─────────────
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
    """Lista compras do usuário, opcionalmente apenas ativas (não vencidas)."""
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


# ───────────── PIX ─────────────
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


# ───────────── GIFT CARDS ─────────────
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


async def create_gift(code: str, tipo: str, valor: float = 0, product_id: int | None = None):
    await _db.execute(
        "INSERT INTO gift_cards (code, tipo, valor, product_id) VALUES (?, ?, ?, ?)",
        (code, tipo, valor, product_id),
    )
    await _db.commit()


# ───────────── SEED ─────────────
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

    for i in range(1, 4):
        await _db.execute(
            "INSERT INTO stock_items (product_id, email, password) VALUES (?, ?, ?)",
            (1, f"canva_cliente{i}@larizinha.com", f"SenhaForte#{i}2026"),
        )

    # Gift card de exemplo
    await _db.execute(
        "INSERT OR IGNORE INTO gift_cards (code, tipo, valor) VALUES (?, ?, ?)",
        ("LARI2026", "saldo", 10.00),
    )

    await _db.commit()
