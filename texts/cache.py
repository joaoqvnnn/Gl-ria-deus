"""
Cache em memória dos textos e botões do bot.
Carregado do banco na inicialização e atualizado quando o admin salva.
Assim as funções síncronas do messages.py podem ler sem await.
"""
import logging

logger = logging.getLogger(__name__)

_TEXTS: dict[str, str] = {}
_BUTTONS: dict[str, str] = {}
_CONFIG: dict[str, str] = {}


# ═══════════════════════════════════════════════
# CARREGAR DO BANCO
# ═══════════════════════════════════════════════
async def load_all():
    from database import db

    global _TEXTS, _BUTTONS, _CONFIG

    _TEXTS = await db.load_bot_texts()
    _BUTTONS = await db.load_bot_buttons()

    # Config também
    try:
        import aiosqlite
        cur = await db._db.execute("SELECT key, value FROM config")
        rows = await cur.fetchall()
        _CONFIG = {r["key"]: r["value"] for r in rows}
    except Exception:
        _CONFIG = {}

    logger.info(
        "Cache carregado: %d textos, %d botões, %d configs",
        len(_TEXTS), len(_BUTTONS), len(_CONFIG),
    )


# ═══════════════════════════════════════════════
# GETTERS
# ═══════════════════════════════════════════════
def get_text(key: str, default: str = "") -> str:
    return _TEXTS.get(key, default)


def get_button(key: str, default: str = "") -> str:
    return _BUTTONS.get(key, default)


def get_config(key: str, default: str = "") -> str:
    return _CONFIG.get(key, default)


# ═══════════════════════════════════════════════
# ATUALIZAÇÃO (chamada pelo admin)
# ═══════════════════════════════════════════════
def set_text(key: str, value: str):
    _TEXTS[key] = value


def set_button(key: str, value: str):
    _BUTTONS[key] = value


def set_config(key: str, value: str):
    _CONFIG[key] = value
