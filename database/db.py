import aiosqlite
from config import DB_PATH

_db: aiosqlite.Connection | None = None


async def init_db():
    """Cria conexão e tabelas."""
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
            active       INTEGER DEFAULT 1,
            created_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """
    )
    await _db.commit()


# ───────────── USERS ─────────────
async def get_or_create_user(user_id: int, username: str | None, first_name: str | None) -> dict:
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


async def get_user(user_id: int) -> dict | None:
    cur = await _db.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
    row = await cur.fetchone()
    return dict(row) if row else None


# ───────────── PRODUCTS ─────────────
async def get_products() -> list[dict]:
    cur = await _db.execute("SELECT * FROM products WHERE active = 1 ORDER BY id ASC")
    rows = await cur.fetchall()
    return [dict(r) for r in rows]


async def get_product(pid: int) -> dict | None:
    cur = await _db.execute("SELECT * FROM products WHERE id = ?", (pid,))
    row = await cur.fetchone()
    return dict(row) if row else None


async def add_product(name, description, price, stock, emoji="📦"):
    await _db.execute(
        "INSERT INTO products (name, description, price, stock, emoji) VALUES (?, ?, ?, ?, ?)",
        (name, description, price, stock, emoji),
    )
    await _db.commit()


async def seed_products():
    """Popula o catálogo inicial na primeira execução."""
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
    await _db.commit()
