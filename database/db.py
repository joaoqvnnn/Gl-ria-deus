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
    return hashlib.sha256(pin.encode()).hexdigest()


async def _try_alter(sql: str):
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

        CREATE TABLE IF NOT EXISTS pix_meta (
            pix_id       TEXT PRIMARY KEY,
            purchase_id  TEXT,
            itens_json   TEXT
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

        CREATE TABLE IF NOT EXISTS config (
            key TEXT PRIMARY KEY,
            value TEXT
        );

        CREATE TABLE IF NOT EXISTS bot_texts (
            key        TEXT PRIMARY KEY,
            value      TEXT NOT NULL,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS bot_buttons (
            key        TEXT PRIMARY KEY,
            value      TEXT NOT NULL,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS admin_logs (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            admin_id   INTEGER NOT NULL,
            action     TEXT NOT NULL,
            target     TEXT,
            details    TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS sub_admins (
            user_id     INTEGER PRIMARY KEY,
            nome        TEXT NOT NULL,
            permissoes  TEXT DEFAULT 'all',
            created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE INDEX IF NOT EXISTS idx_purchases_user ON purchases(user_id);
        CREATE INDEX IF NOT EXISTS idx_purchases_prod ON purchases(product_id);
        CREATE INDEX IF NOT EXISTS idx_pix_user       ON pix_pending(user_id);
        CREATE INDEX IF NOT EXISTS idx_cart_notified  ON cart_views(notified);
        """
    )
    await _db.commit()

    # ─── Colunas novas em users (seguro para bases antigas)
    await _try_alter("ALTER TABLE users ADD COLUMN referred_by INTEGER")
    await _try_alter("ALTER TABLE users ADD COLUMN is_affiliate INTEGER DEFAULT 0")
    await _try_alter("ALTER TABLE users ADD COLUMN payout_password TEXT")
    await _try_alter("ALTER TABLE users ADD COLUMN pix_key_type TEXT")
    await _try_alter("ALTER TABLE users ADD COLUMN pix_key TEXT")
    await _try_alter("ALTER TABLE users ADD COLUMN pix_name TEXT")
    await _try_alter("ALTER TABLE users ADD COLUMN pix_bank TEXT")
    await _try_alter("ALTER TABLE users ADD COLUMN balance_web REAL DEFAULT 0")
    await _try_alter("ALTER TABLE users ADD COLUMN age_verified INTEGER DEFAULT 0")
    await _try_alter("ALTER TABLE users ADD COLUMN banned INTEGER DEFAULT 0")

    # ─── Colunas novas em products
    await _try_alter("ALTER TABLE products ADD COLUMN image_url TEXT")

    # ─── Coluna nova em purchases
    await _try_alter("ALTER TABLE purchases ADD COLUMN status TEXT DEFAULT 'active'")

    # ─── Índices que dependem de colunas novas
    await _try_alter(
        "CREATE INDEX IF NOT EXISTS idx_users_referred_by ON users(referred_by)"
    )


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
    cur = await _db.execute(
        "SELECT COUNT(*) AS c, COALESCE(SUM(total), 0) AS s FROM purchases WHERE user_id = ?",
        (user_id,),
    )
    row = await cur.fetchone()
    compras = int(row["c"])
    gasto = float(row["s"])

    cur = await _db.execute(
        "SELECT COALESCE(SUM(valor), 0) AS s FROM pix_pending "
        "WHERE user_id = ? AND tipo = 'recarga' AND status = 'paid'",
        (user_id,),
    )
    pix_inseridos = float((await cur.fetchone())["s"])

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


async def increment_stock(pid: int, qty: int):
    await _db.execute(
        "UPDATE products SET stock = stock + ? WHERE id = ?",
        (qty, pid),
    )
    await _db.commit()


async def add_product(name, description, price, stock, emoji="📦", activate_url="https://t.me/", image_url=None):
    await _db.execute(
        "INSERT INTO products (name, description, price, stock, emoji, activate_url, image_url) "
        "VALUES (?, ?, ?, ?, ?, ?, ?)",
        (name, description, price, stock, emoji, activate_url, image_url),
    )
    await _db.commit()


async def set_product_image(pid: int, image_url: str):
    await _db.execute(
        "UPDATE products SET image_url = ? WHERE id = ?",
        (image_url, pid),
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


async def add_stock_item(product_id: int, email: str, password: str):
    await _db.execute(
        "INSERT INTO stock_items (product_id, email, password) VALUES (?, ?, ?)",
        (product_id, email, password),
    )
    await _db.commit()


async def list_available_stock(product_id: int):
    cur = await _db.execute(
        "SELECT * FROM stock_items WHERE product_id = ? AND used = 0 ORDER BY id ASC",
        (product_id,),
    )
    return [dict(r) for r in await cur.fetchall()]


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


async def create_purchase_with_id(purchase_id, user_id, product_id, product_name,
                                  quantity, total, email, password, days=30):
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
    cur = await _db.execute(
        "SELECT COUNT(*) AS c FROM users WHERE referred_by = ?", (user_id,)
    )
    indicados = int((await cur.fetchone())["c"])

    cur = await _db.execute(
        "SELECT COALESCE(SUM(amount), 0) AS s, COUNT(*) AS c "
        "FROM affiliate_earnings WHERE affiliate_id = ?",
        (user_id,),
    )
    row = await cur.fetchone()
    total_ganho = float(row["s"])
    ganhos_count = int(row["c"])
    media = (total_ganho / ganhos_count) if ganhos_count else 0.0

    return {"indicados": indicados, "total_ganho": total_ganho, "media": media}


async def add_affiliate_earning(affiliate_id, referred_id, amount, source="recarga"):
    await _db.execute(
        "INSERT INTO affiliate_earnings (affiliate_id, referred_id, amount, source) "
        "VALUES (?, ?, ?, ?)",
        (affiliate_id, referred_id, amount, source),
    )
    await _db.commit()
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
    """Produtos mais vendidos (nome + qtd de pedidos)."""
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
    await _db.execute(
        "INSERT INTO cart_views (user_id, product_id, viewed_at, notified) "
        "VALUES (?, ?, CURRENT_TIMESTAMP, 0) "
        "ON CONFLICT(user_id, product_id) DO UPDATE SET "
        "viewed_at = CURRENT_TIMESTAMP, notified = 0",
        (user_id, product_id),
    )
    await _db.commit()


async def clear_cart_view(user_id: int, product_id: int | None = None):
    if product_id is None:
        await _db.execute("DELETE FROM cart_views WHERE user_id = ?", (user_id,))
    else:
        await _db.execute(
            "DELETE FROM cart_views WHERE user_id = ? AND product_id = ?",
            (user_id, product_id),
        )
    await _db.commit()


async def list_abandoned_carts(minutes: int = 5):
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
# BOT TEXTS / BUTTONS / CONFIG
# ═══════════════════════════════════════════════
async def load_bot_texts() -> dict:
    cur = await _db.execute("SELECT key, value FROM bot_texts")
    rows = await cur.fetchall()
    return {r["key"]: r["value"] for r in rows}


async def load_bot_buttons() -> dict:
    cur = await _db.execute("SELECT key, value FROM bot_buttons")
    rows = await cur.fetchall()
    return {r["key"]: r["value"] for r in rows}


async def save_bot_text(key: str, value: str):
    await _db.execute(
        "INSERT INTO bot_texts (key, value, updated_at) VALUES (?, ?, CURRENT_TIMESTAMP) "
        "ON CONFLICT(key) DO UPDATE SET value = ?, updated_at = CURRENT_TIMESTAMP",
        (key, value, value),
    )
    await _db.commit()


async def save_bot_button(key: str, value: str):
    await _db.execute(
        "INSERT INTO bot_buttons (key, value, updated_at) VALUES (?, ?, CURRENT_TIMESTAMP) "
        "ON CONFLICT(key) DO UPDATE SET value = ?, updated_at = CURRENT_TIMESTAMP",
        (key, value, value),
    )
    await _db.commit()


async def get_config(key: str, default: str = "") -> str:
    cur = await _db.execute("SELECT value FROM config WHERE key = ?", (key,))
    row = await cur.fetchone()
    return row["value"] if row else default


async def set_config(key: str, value: str):
    await _db.execute(
        "INSERT INTO config (key, value) VALUES (?, ?) "
        "ON CONFLICT(key) DO UPDATE SET value = ?",
        (key, value, value),
    )
    await _db.commit()


async def admin_load_config() -> dict:
    cur = await _db.execute("SELECT key, value FROM config")
    rows = await cur.fetchall()
    return {r["key"]: r["value"] for r in rows}


async def admin_set_config(key: str, value: str):
    await set_config(key, value)


# ═══════════════════════════════════════════════
# ADMIN — STATS / USUÁRIOS / LOGS
# ═══════════════════════════════════════════════
async def admin_stats() -> dict:
    hoje = datetime.now().strftime("%Y-%m-%d")
    semana = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
    mes = datetime.now().strftime("%Y-%m")

    cur = await _db.execute("SELECT COUNT(*) AS c FROM users")
    total_users = int((await cur.fetchone())["c"])

    cur = await _db.execute("SELECT COUNT(*) AS c FROM users WHERE banned = 1")
    total_banned = int((await cur.fetchone())["c"])

    cur = await _db.execute(
        "SELECT COUNT(*) AS c, COALESCE(SUM(total), 0) AS s FROM purchases"
    )
    row = await cur.fetchone()
    total_vendas = int(row["c"])
    receita_total = float(row["s"])

    cur = await _db.execute(
        "SELECT COUNT(*) AS c, COALESCE(SUM(total), 0) AS s FROM purchases "
        "WHERE DATE(created_at) = ?", (hoje,),
    )
    row = await cur.fetchone()
    vendas_hoje = int(row["c"])
    receita_hoje = float(row["s"])

    cur = await _db.execute(
        "SELECT COALESCE(SUM(total), 0) AS s FROM purchases WHERE DATE(created_at) >= ?",
        (semana,),
    )
    receita_semana = float((await cur.fetchone())["s"])

    cur = await _db.execute(
        "SELECT COALESCE(SUM(total), 0) AS s FROM purchases WHERE strftime('%Y-%m', created_at) = ?",
        (mes,),
    )
    receita_mes = float((await cur.fetchone())["s"])

    cur = await _db.execute("SELECT COALESCE(SUM(balance), 0) AS s FROM users")
    saldo_circulacao = float((await cur.fetchone())["s"])

    cur = await _db.execute("SELECT COUNT(*) AS c FROM products WHERE active = 1")
    total_produtos = int((await cur.fetchone())["c"])

    cur = await _db.execute("SELECT COUNT(*) AS c FROM cart_views WHERE notified = 0")
    carrinhos = int((await cur.fetchone())["c"])

    manutencao = await get_maintenance()

    return {
        "total_users": total_users,
        "total_banned": total_banned,
        "total_vendas": total_vendas,
        "receita_total": receita_total,
        "vendas_hoje": vendas_hoje,
        "receita_hoje": receita_hoje,
        "receita_semana": receita_semana,
        "receita_mes": receita_mes,
        "saldo_circulacao": saldo_circulacao,
        "total_produtos": total_produtos,
        "carrinhos_abandonados": carrinhos,
        "manutencao": manutencao,
    }


async def list_users(limit: int = 10, offset: int = 0):
    cur = await _db.execute(
        "SELECT * FROM users ORDER BY created_at DESC LIMIT ? OFFSET ?",
        (limit, offset),
    )
    return [dict(r) for r in await cur.fetchall()]


async def count_users() -> int:
    cur = await _db.execute("SELECT COUNT(*) AS c FROM users")
    return int((await cur.fetchone())["c"])


async def search_users(term: str, limit: int = 10):
    if term.isdigit():
        cur = await _db.execute(
            "SELECT * FROM users WHERE user_id = ?", (int(term),)
        )
        rows = await cur.fetchall()
        if rows:
            return [dict(r) for r in rows]

    cur = await _db.execute(
        "SELECT * FROM users WHERE LOWER(first_name) LIKE ? OR LOWER(username) LIKE ? LIMIT ?",
        (f"%{term.lower()}%", f"%{term.lower()}%", limit),
    )
    return [dict(r) for r in await cur.fetchall()]


async def ban_user(user_id: int):
    await _db.execute("UPDATE users SET banned = 1 WHERE user_id = ?", (user_id,))
    await _db.commit()


async def unban_user(user_id: int):
    await _db.execute("UPDATE users SET banned = 0 WHERE user_id = ?", (user_id,))
    await _db.commit()


async def is_banned(user_id: int) -> bool:
    cur = await _db.execute("SELECT banned FROM users WHERE user_id = ?", (user_id,))
    row = await cur.fetchone()
    return bool(row and row["banned"])


async def log_admin_action(admin_id: int, action: str, target: str = "", details: str = ""):
    await _db.execute(
        "INSERT INTO admin_logs (admin_id, action, target, details) VALUES (?, ?, ?, ?)",
        (admin_id, action, target, details),
    )
    await _db.commit()


async def list_admin_logs(limit: int = 20):
    cur = await _db.execute(
        "SELECT * FROM admin_logs ORDER BY created_at DESC LIMIT ?", (limit,)
    )
    return [dict(r) for r in await cur.fetchall()]


async def set_maintenance(ativo: bool):
    await set_config("maintenance", "1" if ativo else "0")


async def get_maintenance() -> bool:
    return (await get_config("maintenance", "0")) == "1"


async def all_user_ids():
    cur = await _db.execute("SELECT user_id FROM users WHERE banned = 0")
    return [int(r["user_id"]) for r in await cur.fetchall()]


async def buyers_user_ids():
    cur = await _db.execute("SELECT DISTINCT user_id FROM purchases")
    return [int(r["user_id"]) for r in await cur.fetchall()]


async def inactive_user_ids(days: int = 7):
    limite = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d %H:%M:%S")
    cur = await _db.execute(
        "SELECT user_id FROM users WHERE banned = 0 AND created_at < ?", (limite,)
    )
    return [int(r["user_id"]) for r in await cur.fetchall()]


# ═══════════════════════════════════════════════
# ADMIN — VENDAS / GIFTS / SAQUES / AFILIADOS
# ═══════════════════════════════════════════════
async def admin_list_purchases(limit: int = 10, offset: int = 0):
    cur = await _db.execute(
        "SELECT * FROM purchases ORDER BY created_at DESC LIMIT ? OFFSET ?",
        (limit, offset),
    )
    return [dict(r) for r in await cur.fetchall()]


async def admin_count_purchases() -> int:
    cur = await _db.execute("SELECT COUNT(*) AS c FROM purchases")
    return int((await cur.fetchone())["c"])


async def admin_search_purchases(term: str, limit: int = 10):
    if term.isdigit():
        cur = await _db.execute(
            "SELECT * FROM purchases WHERE user_id = ? ORDER BY created_at DESC LIMIT ?",
            (int(term), limit),
        )
    else:
        cur = await _db.execute(
            "SELECT * FROM purchases WHERE LOWER(product_name) LIKE ? OR id LIKE ? "
            "ORDER BY created_at DESC LIMIT ?",
            (f"%{term.lower()}%", f"%{term}%", limit),
        )
    return [dict(r) for r in await cur.fetchall()]


async def admin_cancel_purchase(purchase_id: str):
    cur = await _db.execute("SELECT * FROM purchases WHERE id = ?", (purchase_id,))
    row = await cur.fetchone()
    if not row:
        return None
    p = dict(row)

    await update_balance(p["user_id"], +float(p["total"]))
    await _db.execute(
        "UPDATE products SET sold = MAX(sold - ?, 0), stock = stock + ? WHERE id = ?",
        (p["quantity"], p["quantity"], p["product_id"]),
    )
    if p.get("email"):
        await _db.execute(
            "UPDATE stock_items SET used = 0 WHERE product_id = ? AND email = ? "
            "AND used = 1", (p["product_id"], p["email"]),
        )
    await _db.execute(
        "UPDATE purchases SET status = 'cancelled' WHERE id = ?", (purchase_id,)
    )
    await _db.commit()
    return p


async def admin_list_gifts(limit: int = 10, offset: int = 0):
    cur = await _db.execute(
        "SELECT * FROM gift_cards ORDER BY created_at DESC LIMIT ? OFFSET ?",
        (limit, offset),
    )
    return [dict(r) for r in await cur.fetchall()]


async def admin_count_gifts() -> int:
    cur = await _db.execute("SELECT COUNT(*) AS c FROM gift_cards")
    return int((await cur.fetchone())["c"])


async def admin_delete_gift(code: str):
    await _db.execute("DELETE FROM gift_cards WHERE code = ?", (code,))
    await _db.commit()


async def admin_create_gift_batch(code_base, quantidade, tipo, valor=0, product_id=None):
    import secrets
    import string
    codigos = []
    for _ in range(quantidade):
        sufixo = "".join(secrets.choice(string.ascii_uppercase + string.digits) for _ in range(6))
        codigo = f"{code_base}-{sufixo}"
        try:
            await _db.execute(
                "INSERT INTO gift_cards (code, tipo, valor, product_id) VALUES (?, ?, ?, ?)",
                (codigo, tipo, valor, product_id),
            )
            codigos.append(codigo)
        except Exception:
            continue
    await _db.commit()
    return codigos


async def admin_list_withdrawals(status: str | None = None, limit: int = 10):
    if status:
        cur = await _db.execute(
            "SELECT * FROM withdrawals WHERE status = ? ORDER BY created_at DESC LIMIT ?",
            (status, limit),
        )
    else:
        cur = await _db.execute(
            "SELECT * FROM withdrawals ORDER BY created_at DESC LIMIT ?", (limit,)
        )
    return [dict(r) for r in await cur.fetchall()]


async def admin_count_withdrawals(status: str = "pending") -> int:
    cur = await _db.execute(
        "SELECT COUNT(*) AS c FROM withdrawals WHERE status = ?", (status,)
    )
    return int((await cur.fetchone())["c"])


async def admin_get_withdrawal(wid: str):
    cur = await _db.execute("SELECT * FROM withdrawals WHERE id = ?", (wid,))
    row = await cur.fetchone()
    return dict(row) if row else None


async def admin_approve_withdrawal(wid: str):
    wd = await admin_get_withdrawal(wid)
    if not wd:
        return None
    if wd["status"] == "processed":
        return wd

    await _db.execute(
        "UPDATE withdrawals SET status='processed', processed_at=CURRENT_TIMESTAMP WHERE id = ?",
        (wid,),
    )
    await update_balance(wd["user_id"], -float(wd["amount"]))
    await _db.commit()
    return await admin_get_withdrawal(wid)


async def admin_reject_withdrawal(wid: str):
    await _db.execute("UPDATE withdrawals SET status='rejected' WHERE id = ?", (wid,))
    await _db.commit()
    return await admin_get_withdrawal(wid)


async def admin_top_affiliates(limit: int = 10):
    cur = await _db.execute(
        "SELECT u.user_id, u.first_name, u.username, "
        "  COUNT(DISTINCT r.user_id) AS indicados, "
        "  COALESCE(SUM(a.amount), 0) AS total_ganho "
        "FROM users u "
        "LEFT JOIN users r ON r.referred_by = u.user_id "
        "LEFT JOIN affiliate_earnings a ON a.affiliate_id = u.user_id "
        "WHERE u.is_affiliate = 1 "
        "GROUP BY u.user_id "
        "ORDER BY total_ganho DESC LIMIT ?",
        (limit,),
    )
    return [dict(r) for r in await cur.fetchall()]


async def admin_set_affiliate(user_id: int, ativo: bool):
    await _db.execute(
        "UPDATE users SET is_affiliate = ? WHERE user_id = ?",
        (1 if ativo else 0, user_id),
    )
    await _db.commit()


# ═══════════════════════════════════════════════
# ADMIN — ESTATÍSTICAS DETALHADAS
# ═══════════════════════════════════════════════
async def admin_sales_by_day(days: int = 7):
    cur = await _db.execute(
        """
        SELECT DATE(created_at) AS dia,
               COUNT(*) AS vendas,
               COALESCE(SUM(total), 0) AS receita
        FROM purchases
        WHERE DATE(created_at) >= DATE('now', ?)
        GROUP BY DATE(created_at)
        ORDER BY dia ASC
        """,
        (f"-{days} days",),
    )
    return [dict(r) for r in await cur.fetchall()]


async def admin_top_products(limit: int = 5):
    cur = await _db.execute(
        "SELECT product_name, "
        "       COALESCE(SUM(quantity), 0) AS qtd, "
        "       COALESCE(SUM(total), 0) AS receita "
        "FROM purchases GROUP BY product_name ORDER BY qtd DESC LIMIT ?",
        (limit,),
    )
    return [dict(r) for r in await cur.fetchall()]


async def admin_top_spenders(limit: int = 5):
    cur = await _db.execute(
        "SELECT u.user_id, u.first_name, u.username, "
        "       COUNT(p.id) AS compras, "
        "       COALESCE(SUM(p.total), 0) AS total "
        "FROM users u JOIN purchases p ON p.user_id = u.user_id "
        "GROUP BY u.user_id ORDER BY total DESC LIMIT ?",
        (limit,),
    )
    return [dict(r) for r in await cur.fetchall()]


async def admin_ticket_medio() -> float:
    cur = await _db.execute("SELECT COALESCE(AVG(total), 0) AS media FROM purchases")
    return float((await cur.fetchone())["media"])


async def admin_saldo_em_contas() -> dict:
    cur = await _db.execute(
        "SELECT COALESCE(SUM(balance), 0) AS bot, COALESCE(SUM(balance_web), 0) AS web FROM users"
    )
    row = await cur.fetchone()
    return {"bot": float(row["bot"]), "web": float(row["web"])}


async def admin_carrinhos_pendentes() -> int:
    cur = await _db.execute("SELECT COUNT(*) AS c FROM cart_views WHERE notified = 0")
    return int((await cur.fetchone())["c"])


# ═══════════════════════════════════════════════
# ADMIN — TEXTOS / BOTÕES
# ═══════════════════════════════════════════════
async def admin_list_texts():
    cur = await _db.execute("SELECT key, value FROM bot_texts ORDER BY key ASC")
    return [dict(r) for r in await cur.fetchall()]


async def admin_list_buttons():
    cur = await _db.execute("SELECT key, value FROM bot_buttons ORDER BY key ASC")
    return [dict(r) for r in await cur.fetchall()]


async def admin_get_text(key: str):
    cur = await _db.execute("SELECT value FROM bot_texts WHERE key = ?", (key,))
    row = await cur.fetchone()
    return row["value"] if row else None


async def admin_get_button(key: str):
    cur = await _db.execute("SELECT value FROM bot_buttons WHERE key = ?", (key,))
    row = await cur.fetchone()
    return row["value"] if row else None


async def admin_update_text(key: str, value: str):
    await save_bot_text(key, value)


async def admin_update_button(key: str, value: str):
    await save_bot_button(key, value)


# ═══════════════════════════════════════════════
# ADMIN — BANNER
# ═══════════════════════════════════════════════
async def admin_set_banner(file_id: str):
    await set_config("banner_file_id", file_id)
    await save_bot_text("__banner__", file_id)


async def admin_get_banner() -> str:
    return (await get_config("banner_file_id", "")) or ""


# ═══════════════════════════════════════════════
# ADMIN — PRODUTOS COMPLETOS
# ═══════════════════════════════════════════════
async def admin_create_product(name, description, price, stock,
                               emoji="📦", guarantee=180, activate_url="https://t.me/"):
    cur = await _db.execute(
        "INSERT INTO products (name, description, price, stock, emoji, guarantee, activate_url) "
        "VALUES (?, ?, ?, ?, ?, ?, ?)",
        (name, description, price, stock, emoji, guarantee, activate_url),
    )
    await _db.commit()
    return cur.lastrowid


async def admin_update_product(pid: int, **campos):
    if not campos:
        return
    permitidos = {
        "name", "description", "price", "stock",
        "emoji", "guarantee", "activate_url", "image_url", "active", "sold",
    }
    sets, valores = [], []
    for k, v in campos.items():
        if k in permitidos:
            sets.append(f"{k} = ?")
            valores.append(v)
    if not sets:
        return
    valores.append(pid)
    await _db.execute(f"UPDATE products SET {', '.join(sets)} WHERE id = ?", valores)
    await _db.commit()


async def admin_delete_product(pid: int):
    await _db.execute("UPDATE products SET active = 0 WHERE id = ?", (pid,))
    await _db.commit()


async def admin_really_delete_product(pid: int):
    await _db.execute("DELETE FROM stock_items WHERE product_id = ?", (pid,))
    await _db.execute("DELETE FROM products WHERE id = ?", (pid,))
    await _db.commit()


# ═══════════════════════════════════════════════
# ADMIN — ESTOQUE
# ═══════════════════════════════════════════════
async def admin_add_stock_batch(pid: int, contas: list[tuple[str, str]]) -> int:
    if not contas:
        return 0
    for email, senha in contas:
        await _db.execute(
            "INSERT INTO stock_items (product_id, email, password) VALUES (?, ?, ?)",
            (pid, email, senha),
        )
    await _db.execute(
        "UPDATE products SET stock = stock + ? WHERE id = ?", (len(contas), pid)
    )
    await _db.commit()
    return len(contas)


async def admin_list_stock(pid: int, only_available: bool = True):
    if only_available:
        cur = await _db.execute(
            "SELECT * FROM stock_items WHERE product_id = ? AND used = 0 ORDER BY id ASC",
            (pid,),
        )
    else:
        cur = await _db.execute(
            "SELECT * FROM stock_items WHERE product_id = ? ORDER BY id ASC", (pid,)
        )
    return [dict(r) for r in await cur.fetchall()]


async def admin_count_stock(pid: int) -> dict:
    cur = await _db.execute(
        "SELECT "
        "  SUM(CASE WHEN used = 0 THEN 1 ELSE 0 END) AS disponiveis, "
        "  SUM(CASE WHEN used = 1 THEN 1 ELSE 0 END) AS usadas "
        "FROM stock_items WHERE product_id = ?", (pid,),
    )
    row = await cur.fetchone()
    return {
        "disponiveis": int(row["disponiveis"] or 0),
        "usadas": int(row["usadas"] or 0),
    }


async def admin_clear_stock(pid: int, apenas_nao_usadas: bool = True) -> int:
    if apenas_nao_usadas:
        cur = await _db.execute(
            "DELETE FROM stock_items WHERE product_id = ? AND used = 0", (pid,)
        )
    else:
        cur = await _db.execute(
            "DELETE FROM stock_items WHERE product_id = ?", (pid,)
        )
    await _db.execute("UPDATE products SET stock = 0 WHERE id = ?", (pid,))
    await _db.commit()
    return cur.rowcount or 0


# ═══════════════════════════════════════════════
# ADMIN — MENSAGEM DIRETA / CARRINHOS / BACKUP
# ═══════════════════════════════════════════════
async def admin_send_direct(user_id: int, texto: str) -> bool:
    return (await get_user(user_id)) is not None


async def admin_list_abandoned(limit: int = 10):
    cur = await _db.execute(
        """
        SELECT c.user_id, c.product_id, c.viewed_at, c.notified,
               u.first_name, u.username,
               p.name AS product_name
        FROM cart_views c
        LEFT JOIN users u ON u.user_id = c.user_id
        LEFT JOIN products p ON p.id = c.product_id
        WHERE c.notified = 0
        ORDER BY c.viewed_at DESC LIMIT ?
        """,
        (limit,),
    )
    return [dict(r) for r in await cur.fetchall()]


async def admin_count_abandoned() -> int:
    cur = await _db.execute("SELECT COUNT(*) AS c FROM cart_views WHERE notified = 0")
    return int((await cur.fetchone())["c"])


async def admin_clear_abandoned(user_id: int, product_id: int):
    await _db.execute(
        "DELETE FROM cart_views WHERE user_id = ? AND product_id = ?",
        (user_id, product_id),
    )
    await _db.commit()


async def admin_backup_bytes() -> bytes:
    with open(DB_PATH, "rb") as f:
        return f.read()


# ═══════════════════════════════════════════════
# SUB-ADMINS
# ═══════════════════════════════════════════════
async def admin_list_subadmins():
    cur = await _db.execute("SELECT * FROM sub_admins ORDER BY created_at DESC")
    return [dict(r) for r in await cur.fetchall()]


async def admin_add_subadmin(user_id: int, nome: str, permissoes: str = "all"):
    await _db.execute(
        "INSERT INTO sub_admins (user_id, nome, permissoes) VALUES (?, ?, ?) "
        "ON CONFLICT(user_id) DO UPDATE SET nome = ?, permissoes = ?",
        (user_id, nome, permissoes, nome, permissoes),
    )
    await _db.commit()


async def admin_remove_subadmin(user_id: int):
    await _db.execute("DELETE FROM sub_admins WHERE user_id = ?", (user_id,))
    await _db.commit()


async def admin_get_subadmin(user_id: int):
    cur = await _db.execute("SELECT * FROM sub_admins WHERE user_id = ?", (user_id,))
    row = await cur.fetchone()
    return dict(row) if row else None


async def admin_is_admin_or_sub(user_id: int):
    from config import ADMIN_IDS
    if user_id in ADMIN_IDS:
        return True, "all"
    sub = await admin_get_subadmin(user_id)
    if sub:
        return True, sub.get("permissoes", "")
    return False, ""


def sub_tem_permissao(permissoes: str, area: str) -> bool:
    if permissoes == "all":
        return True
    if not permissoes:
        return False
    return area in [p.strip() for p in permissoes.split(",")]


# ═══════════════════════════════════════════════
# EXPORTAR CSV
# ═══════════════════════════════════════════════
async def admin_export_users_csv() -> str:
    import csv, io
    cur = await _db.execute(
        "SELECT user_id, username, first_name, balance, balance_web, whatsapp, "
        "banned, is_affiliate, created_at FROM users ORDER BY user_id ASC"
    )
    rows = await cur.fetchall()
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(["user_id", "username", "first_name", "balance",
                     "balance_web", "whatsapp", "banned", "is_affiliate", "created_at"])
    for r in rows:
        writer.writerow([
            r["user_id"], r["username"] or "", r["first_name"] or "",
            f"{float(r['balance'] or 0):.2f}", f"{float(r['balance_web'] or 0):.2f}",
            r["whatsapp"] or "", r["banned"] or 0, r["is_affiliate"] or 0, r["created_at"] or "",
        ])
    return buf.getvalue()


async def admin_export_purchases_csv() -> str:
    import csv, io
    cur = await _db.execute(
        "SELECT id, user_id, product_name, quantity, total, email, "
        "created_at, expires_at, status FROM purchases ORDER BY created_at DESC"
    )
    rows = await cur.fetchall()
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(["id", "user_id", "product_name", "quantity", "total", "email",
                     "created_at", "expires_at", "status"])
    for r in rows:
        writer.writerow([
            r["id"], r["user_id"], r["product_name"] or "", r["quantity"] or 1,
            f"{float(r['total'] or 0):.2f}", r["email"] or "",
            r["created_at"] or "", r["expires_at"] or "", r["status"] or "active",
        ])
    return buf.getvalue()


async def admin_export_withdrawals_csv() -> str:
    import csv, io
    cur = await _db.execute(
        "SELECT id, user_id, amount, pix_key_type, pix_key, status, "
        "created_at, processed_at FROM withdrawals ORDER BY created_at DESC"
    )
    rows = await cur.fetchall()
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(["id", "user_id", "amount", "pix_key_type", "pix_key",
                     "status", "created_at", "processed_at"])
    for r in rows:
        writer.writerow([
            r["id"], r["user_id"], f"{float(r['amount'] or 0):.2f}",
            r["pix_key_type"] or "", r["pix_key"] or "",
            r["status"] or "pending", r["created_at"] or "", r["processed_at"] or "",
        ])
    return buf.getvalue()


# ═══════════════════════════════════════════════
# SEED — textos e botões
# ═══════════════════════════════════════════════
async def seed_bot_content():
    cur = await _db.execute("SELECT COUNT(*) AS c FROM bot_texts")
    row = await cur.fetchone()
    if row["c"] == 0:
        textos = {
            "gate": "❗ <b>Para utilizar nosso serviço é obrigatório que você entre no nosso grupo.</b>",

            "welcome": (
                "📡 <b>Bem-vindo à {store_name}!</b>\n"
                "✨ A sua central de streamings com entrega 100% automática.\n"
                "Pagou, recebeu. Sem filas, sem precisar falar com atendente, 24 horas por dia! ⚡\n\n"
                "🛡 <b>Segurança e Suporte:</b>\n"
                "Mais de 12.000 clientes já passaram por aqui.\n"
                "Participe da nossa comunidade e veja as referências\n\n"
                "● <b>Seus Dados:</b>\n"
                "├ 👤 ID: <code>{user_id}</code>\n"
                "└ 💰 Saldo Atual: <b>R$ {balance:.2f}</b>\n\n"
                "👇 <b>COMO COMEÇAR:</b>\n"
                "Clique no botão \"🛍 Comprar Produtos\" abaixo para ver nosso catálogo e escolher sua tela!"
            ),

            "catalog": (
                "⚡ <b>{store_name} | Catálogo de Serviços</b>\n"
                "────────────────────────\n"
                "💰 | Saldo da Carteira: <b>R$ {balance:.2f}</b>\n\n"
                "⬇️ Selecione uma categoria abaixo para ver nossos planos:"
            ),

            "product": (
                "🔥 <b>OPORTUNIDADE EXCLUSIVA</b> 🔥\n"
                "🚀 <b>{product_name}</b>\n\n"
                "🟢 <b>DISPONÍVEL AGORA</b>\n"
                "├ 💵 Preço: <b>R$ {price:.2f}</b>\n"
                "├ 💰 Seu Saldo: <b>R$ {balance:.2f}</b>\n"
                "└ 📦 Estoque: <b>{stock}</b>\n\n"
                "📝 <b>Descrição:</b>\n"
                "{description}\n\n"
                "📊 <b>Estatísticas em tempo real:</b>\n"
                "⚡️ Já foram vendidas {sold} unidades!\n"
                "👀 14 pessoas estão vendo isso agora.\n\n"
                "🛡 Garantia: {guarantee} dias\n"
                "✅ Compra segura. Ao adquirir, concorda com /termos"
            ),

            "about": (
                "🤖 <b>Sobre o Bot</b>\n\n"
                "{store_name} — central de streamings com entrega automática.\n"
                "Pagou, recebeu. 24h por dia.\n\n"
                "Para suporte, use o botão 📩 Atendimento."
            ),

            "profile": (
                "👤 <b>Meu perfil</b>\n\n"
                "🔍 Veja aqui os detalhes da sua conta:\n\n"
                "- 👤 <b>Informações:</b>\n"
                "🆔 ID da Carteira: <code>{user_id}</code>\n"
                "💰 Saldo Atual: <b>R$ {balance:.2f}</b>\n"
                "📲 Seu Whatsapp: <code>{whatsapp}</code>\n\n"
                "─── 📊 <b>Suas Movimentações:</b>\n"
                "ー 🛒 Compras Realizadas: <b>{compras}</b>\n"
                "ー 💰 Total Gasto Em Compras: <b>R$ {gasto:.2f}</b>\n"
                "ー 💠 Pix Inseridos: <b>R$ {pix_in:.2f}</b>\n"
                "ー 🎁 Gifts Resgatados: <b>R$ {gifts:.2f}</b>"
            ),

            "insufficient": (
                "❌ <b>Saldo insuficiente!</b>\n\n"
                "💰 Seu saldo: <b>R$ {saldo:.2f}</b>\n"
                "💵 Valor do produto: <b>R$ {total:.2f}</b>\n"
                "📉 Faltam: <b>R$ {falta:.2f}</b>\n\n"
                "💡 Deseja gerar um PIX no valor de <b>R$ {total:.2f}</b> para completar a compra?"
            ),

            "generating_payment": "⏳ <b>Gerando pagamento...</b>",

            "not_paid": (
                "⚠️ <b>Nosso sistema viu que você não realizou o pagamento</b>\n\n"
                "Se já pagou, aguarde alguns segundos e clique novamente em <b>⏰ AGUARDANDO PAGAMENTO</b>."
            ),
            "paid_caption": "✅ <b>PAGAMENTO CONFIRMADO!</b>",
            "pix_cancelled": "❌ <b>PIX cancelado.</b>",

            "pix_caption": (
                "💠 <b>PIX gerado com sucesso!</b>\n\n"
                "💰 Valor: <b>R$ {valor:.2f}</b>\n"
                "🎫 ID: <code>{pix_id}</code>\n"
                "⏰ Expira em: <b>{expira}</b>\n\n"
                "Escaneie o QR Code ou use o botão <b>📋 Copiar PIX</b>."
            ),

            "delivery": (
                "✅ <b>Produto realizado com sucesso!</b>\n\n"
                "⏰ Data da compra: <b>{created_fmt}</b>\n"
                "📆 Vencimento: <b>{expires_fmt}</b>\n"
                "💰 Valor: <b>R$ {total:.2f}</b>\n"
                "🎫 ID da compra: <code>{purchase_id}</code>\n"
                "⚜️ Serviço: <b>{product_name}</b>\n"
                "📧 Email: <code>{email_show}</code>\n"
                "🔐 Senha: <code>{pass_show}</code>\n"
                "📃 Nota: Use o botão abaixo para ativar:"
            ),

            "multi_qty": (
                "Quantos logins deseja comprar?\n\n"
                "📦 Estoque disponível: <b>{stock}</b>\n\n"
                "💡 Digite /cancelar a qualquer momento para sair."
            ),
            "multi_result": (
                "🛒 <b>RESULTADO DO PEDIDO</b>\n"
                "🚀 <b>{product_name}</b>\n"
                "📦 Quantidade: <b>{qty}</b>\n"
                "💵 Preço unitário: <b>R$ {unit:.2f}</b>\n"
                "💰 Total: <b>R$ {total:.2f}</b>\n"
                "💰 Seu Saldo: <b>R$ {balance:.2f}</b>"
            ),
            "multi_cancelled": "❌ <b>Compra cancelada!</b>\n\nOperação de compra múltipla foi cancelada.",

            "history_empty": (
                "Você não tem compras no bot.\n"
                "Quando comprar alguma conta, as informações dela ficarão exibidas aqui."
            ),
            "history_active_empty": (
                "Você não tem compras ativas (não vencidas) no bot.\n"
                "Use o botão abaixo para ver todas as compras."
            ),
            "history_item": (
                "📦 <b>Compras: {total}</b>\n\n"
                "⏰ Data da compra: <b>{created_fmt}</b>\n"
                "📆 Vencimento: <b>{expires_fmt}</b>\n"
                "💰 Valor: <b>R$ {valor:.2f}</b>\n"
                "🎫 ID da compra: <code>{purchase_id}</code>\n"
                "⚜️ Serviço: <b>{product_name}</b>\n"
                "📧 Email: <code>{email}</code>\n"
                "🔐 Senha: <code>{password}</code>\n"
                "📃 Nota: Use o link abaixo para ativar:\n\n"
                "<i>Página {page}/{pages}</i>"
            ),

            "gift_prompt": (
                "🎁 <b>RESGATAR GIFT CARD</b>\n"
                "Digite o código do seu gift card abaixo:\n"
                "Exemplo: <code>ABC123XYZ456</code>"
            ),
            "gift_invalid": "❌ <b>Gift não encontrado.</b>\n\nVerifique o código e tente novamente.",
            "gift_already_used": "❌ <b>Este gift card já foi resgatado.</b>",
            "gift_success_saldo": (
                "🎉 <b>Gift Card resgatado!</b>\n\n"
                "💰 Você recebeu <b>R$ {valor:.2f}</b> de saldo.\n"
                "💼 Saldo atualizado no seu perfil."
            ),
            "gift_success_produto": (
                "🎉 <b>Gift Card resgatado!</b>\n\n"
                "🎁 Você ganhou um produto!\n"
                "Clique em <b>🎁 Usar</b> abaixo para acessá-lo."
            ),

            "alter_data": (
                "✏️ <b>Alterar Dados</b>\n"
                "Selecione o dado que deseja alterar:\n\n"
                "📱 WhatsApp atual: <b>{whatsapp}</b>"
            ),
            "whatsapp_prompt": (
                "📱 <b>Envie seu número de WhatsApp</b>\n"
                "Formato: DDD + Número (apenas números)\n"
                "Exemplo: <code>11999998888</code>\n\n"
                "⚠️ Envie <code>remover</code> para remover o número cadastrado."
            ),
            "whatsapp_invalid": (
                "❌ <b>Número inválido!</b>\n\n"
                "Formato: DDD + Número (apenas números).\n"
                "Exemplo: <code>11999998888</code>"
            ),
            "whatsapp_updated": "✅ <b>WhatsApp atualizado com sucesso!</b>\n\n📱 Novo número: <b>{numero}</b>",
            "whatsapp_removed": "✅ <b>WhatsApp removido com sucesso!</b>",

            "topup_menu": (
                "💠 Opte por <b>PIX Rápido</b> para que seu saldo seja creditado imediatamente.\n"
                "💰 Selecione uma opção para recarregar:"
            ),
            "topup_value_prompt": (
                "ℹ️ <b>Informe o valor que deseja recarregar:</b>\n"
                "🔻 Recarga mínima: <b>R$ 4,00</b>\n\n"
                "⚠️ Por favor, envie o valor que deseja recarregar agora.\n"
                "Ao realizar um depósito você declara ter lido e estar de acordo com nossos /termos\n\n"
                "🎁 Bônus de recarga: <b>10%</b>\n"
                "❗ Recarga mínima para ganhar o bônus: <b>R$ 10,00</b>"
            ),
            "topup_invalid": (
                "❌ <b>Valor inválido!</b>\n\n"
                "Envie um número maior ou igual a <b>R$ 4,00</b>.\n"
                "Exemplo: <code>20</code> ou <code>20,00</code>"
            ),
            "topup_pix_caption": (
                "💠 <b>PIX de recarga gerado!</b>\n\n"
                "💰 Valor: <b>R$ {valor:.2f}</b>\n"
                "{bonus_line}"
                "💼 Saldo atual: <b>R$ {saldo_atual:.2f}</b>\n"
                "💸 Saldo após o pagamento: <b>R$ {saldo_futuro:.2f}</b>\n"
                "🎫 ID: <code>{pix_id}</code>\n"
                "⏰ Expira em: <b>{expira}</b>\n\n"
                "Escaneie o QR Code ou use o botão <b>📋 Copiar PIX</b>."
            ),
            "topup_success": (
                "✅ <b>Recarga realizada com sucesso!</b>\n\n"
                "💰 Valor creditado: <b>R$ {valor_total:.2f}</b>\n"
                "{bonus_line}"
                "💼 Novo saldo: <b>R$ {novo_saldo:.2f}</b>"
            ),
            "topup_cancelled": "❌ <b>Recarga cancelada.</b>",

            "affiliates_inactive": (
                "💰 <b>PROGRAMA DE AFILIADOS</b>\n\n"
                "⚙️ Status: ❌ <b>Inativo</b>\n"
                "🧲 Comissão: <b>{comissao}%</b>\n"
                "💰 Saque mínimo: <b>R$ {saque_min:.2f}</b>\n\n"
                "ℹ️ <b>INFO:</b> Seus indicados continuarão gerando comissão para sempre."
            ),
            "affiliates_active": (
                "💰 <b>PROGRAMA DE AFILIADOS</b>\n\n"
                "⚙️ Status: ✅ <b>Ativo</b>\n"
                "🧲 Sua comissão: <b>{comissao}%</b> (de todas recargas do indicado)\n\n"
                "👥 Indicações: <b>{indicados}</b>\n"
                "🪙 Total ganho: <b>R$ {total:.2f}</b>\n"
                "📊 Média: <b>R$ {media:.2f}</b>\n"
                "💰 Saque mínimo: <b>R$ {saque_min:.2f}</b>\n\n"
                "{emoji_nivel}| Nível: <b>{nivel}</b>\n"
                "🎯 Próxima meta: <b>{meta}</b> ({restantes} restantes)\n\n"
                "ℹ️ <b>INFO:</b> Seus indicados continuarão gerando comissão para sempre.\n"
                "A comissão pode ser alterada a qualquer momento, fique atento aos avisos.\n\n"
                "🔗 <b>Seu link:</b>\n<code>{link}</code>"
            ),

            "top_ranking": (
                "🏆 <b>Ranking dos {titulo}</b>\n\n"
                "{linhas}"
            ),
        }

        for k, v in textos.items():
            await _db.execute(
                "INSERT OR IGNORE INTO bot_texts (key, value) VALUES (?, ?)", (k, v),
            )
        await _db.commit()

    # ─── Botões
    cur = await _db.execute("SELECT COUNT(*) AS c FROM bot_buttons")
    row = await cur.fetchone()
    if row["c"] == 0:
        botoes = {
            "btn_catalog":         "🛍 Comprar Produtos",
            "btn_store":           "🛒 Abrir Loja",
            "btn_profile":         "👤 Meu Perfil",
            "btn_topup":           "💠 Recarregar Saldo",
            "btn_affiliates":      "👥 Afiliados",
            "btn_top":             "🏆 Top Compradores",
            "btn_support":         "📩 Atendimento",
            "btn_about":           "🤖 Sobre o Bot",
            "btn_search":          "🔎 Pesquisar Serviços",
            "btn_back":            "⬅️ VOLTAR",
            "btn_back_to_profile": "⬅️ VOLTAR",
            "btn_buy":             "🛒 COMPRAR",
            "btn_buymulti":        "🛒 Comprar mais de um",
            "btn_gift_cancel":     "❌ Cancelar",
            "btn_gift_use":        "🎁 Usar",
        }
        for k, v in botoes.items():
            await _db.execute(
                "INSERT OR IGNORE INTO bot_buttons (key, value) VALUES (?, ?)", (k, v),
            )
        await _db.commit()


# ═══════════════════════════════════════════════
# SEED — produtos de exemplo
# ═══════════════════════════════════════════════
async def seed_products():
    cur = await _db.execute("SELECT COUNT(*) AS c FROM products")
    row = await cur.fetchone()
    if row["c"] > 0:
        await seed_bot_content()
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

    await _db.execute(
        "INSERT OR IGNORE INTO gift_cards (code, tipo, valor) VALUES (?, ?, ?)",
        ("LARI2026", "saldo", 10.00),
    )

    await _db.commit()

    # Popula textos/botões
    await seed_bot_content()
