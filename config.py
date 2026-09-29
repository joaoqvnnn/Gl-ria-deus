import os
from dotenv import load_dotenv

load_dotenv()

# ═══════════════════════════════════════════════
# BOT
# ═══════════════════════════════════════════════
BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()
BOT_USERNAME = os.getenv("BOT_USERNAME", "LarizinhaStoreBot").strip().lstrip("@")
BOT_HANDLE = os.getenv("BOT_HANDLE", "@LarizinhaStoreBot").strip()

# ═══════════════════════════════════════════════
# CANAIS / SUPORTE
# ═══════════════════════════════════════════════
CHANNEL_ID = os.getenv("CHANNEL_ID", "").strip()
CHANNEL_LINK = os.getenv("CHANNEL_LINK", "").strip()
SUPPORT_LINK = os.getenv("SUPPORT_LINK", "https://t.me/suporte_laricontas").strip()

# Canais de notificação automática (opcional)
NOTIF_CHANNEL_ID = os.getenv("NOTIF_CHANNEL_ID", "").strip()   # canal "Compras"
STOCK_CHANNEL_ID = os.getenv("STOCK_CHANNEL_ID", "").strip()   # canal "Estoque"

# ═══════════════════════════════════════════════
# ADMIN
# ═══════════════════════════════════════════════
ADMIN_IDS = [
    int(x) for x in os.getenv("ADMIN_IDS", "").split(",") if x.strip().isdigit()
]

# ═══════════════════════════════════════════════
# BANCO DE DADOS
# ═══════════════════════════════════════════════
DB_PATH = os.getenv("DB_PATH", "larizinha.db")

# ═══════════════════════════════════════════════
# SERVIDOR / WEBHOOK
# ═══════════════════════════════════════════════
WEBHOOK_URL = os.getenv("WEBHOOK_URL", "").strip()
PORT = int(os.getenv("PORT", "8080"))

# Para o Mini App apontar de volta ao bot
MINIAPP_BASE_URL = os.getenv("MINIAPP_BASE_URL", WEBHOOK_URL or f"http://localhost:{PORT}")

# ═══════════════════════════════════════════════
# REGRAS DE NEGÓCIO
# ═══════════════════════════════════════════════
# Recarga (PIX Rápido)
TOPUP_MIN = float(os.getenv("TOPUP_MIN", "4.00"))
TOPUP_BONUS_MIN = float(os.getenv("TOPUP_BONUS_MIN", "10.00"))
TOPUP_BONUS_RATE = float(os.getenv("TOPUP_BONUS_RATE", "0.10"))  # 10%

# Saques
WITHDRAW_MIN = float(os.getenv("WITHDRAW_MIN", "20.00"))

# Afiliados
AFFILIATE_COMMISSION = float(os.getenv("AFFILIATE_COMMISSION", "0.20"))  # 20%
AFFILIATE_MIN_WITHDRAW = float(os.getenv("AFFILIATE_MIN_WITHDRAW", "20.00"))

# Carrinho abandonado
ABANDONED_CART_MIN = int(os.getenv("ABANDONED_CART_MIN", "5"))

# ═══════════════════════════════════════════════
# VALIDAÇÃO OBRIGATÓRIA
# ═══════════════════════════════════════════════
if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN não configurado no .env")
