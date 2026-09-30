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
SUPPORT_MESSAGE = os.getenv(
    "SUPPORT_MESSAGE",
    "Olá, vim através do bot e gostaria de ajuda.",
).strip()

NOTIF_CHANNEL_ID = os.getenv("NOTIF_CHANNEL_ID", "").strip()
STOCK_CHANNEL_ID = os.getenv("STOCK_CHANNEL_ID", "").strip()

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

MINIAPP_BASE_URL = os.getenv("MINIAPP_BASE_URL", WEBHOOK_URL or f"http://localhost:{PORT}")

# ═══════════════════════════════════════════════
# REGRAS DE NEGÓCIO
# ═══════════════════════════════════════════════
TOPUP_MIN = float(os.getenv("TOPUP_MIN", "4.00"))
TOPUP_BONUS_MIN = float(os.getenv("TOPUP_BONUS_MIN", "10.00"))
TOPUP_BONUS_RATE = float(os.getenv("TOPUP_BONUS_RATE", "0.10"))

WITHDRAW_MIN = float(os.getenv("WITHDRAW_MIN", "20.00"))

AFFILIATE_COMMISSION = float(os.getenv("AFFILIATE_COMMISSION", "0.20"))
AFFILIATE_MIN_WITHDRAW = float(os.getenv("AFFILIATE_MIN_WITHDRAW", "20.00"))

ABANDONED_CART_MIN = int(os.getenv("ABANDONED_CART_MIN", "5"))

# ═══════════════════════════════════════════════
# E-MAIL (Gmail SMTP)
# ═══════════════════════════════════════════════
GMAIL_USER = os.getenv("GMAIL_USER", "").strip()
GMAIL_APP_PASSWORD = os.getenv("GMAIL_APP_PASSWORD", "").strip()
STORE_NAME = os.getenv("STORE_NAME", "Larizinha Store").strip()

# ═══════════════════════════════════════════════
# MERCADO PAGO
# ═══════════════════════════════════════════════
MERCADOPAGO_ACCESS_TOKEN = os.getenv("MERCADOPAGO_ACCESS_TOKEN", "").strip()
MERCADOPAGO_PUBLIC_KEY   = os.getenv("MERCADOPAGO_PUBLIC_KEY", "").strip()
MERCADOPAGO_WEBHOOK_URL  = os.getenv("MERCADOPAGO_WEBHOOK_URL", "").strip()

# ═══════════════════════════════════════════════
# OPENAI
# ═══════════════════════════════════════════════
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "").strip()

# ═══════════════════════════════════════════════
# LOJA VIRTUAL — Configurações
# ═══════════════════════════════════════════════
STORE_CNPJ       = os.getenv("STORE_CNPJ", "00.000.000/0000-00").strip()
STORE_HOURS      = os.getenv("STORE_HOURS", "Seg a Sex, 09h às 18h").strip()
SUPPORT_WHATSAPP = os.getenv("SUPPORT_WHATSAPP", "https://wa.me/").strip()

# ═══════════════════════════════════════════════
# VALIDAÇÃO
# ═══════════════════════════════════════════════
if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN não configurado no .env")
