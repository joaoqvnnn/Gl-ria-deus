import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()
CHANNEL_ID = os.getenv("CHANNEL_ID", "").strip()
CHANNEL_LINK = os.getenv("CHANNEL_LINK", "").strip()
SUPPORT_LINK = os.getenv("SUPPORT_LINK", "https://t.me/suporte_laricontas").strip()

BOT_USERNAME = os.getenv("BOT_USERNAME", "LarizinhaStoreBot").strip().lstrip("@")
BOT_HANDLE = os.getenv("BOT_HANDLE", "@LarizinhaStoreBot").strip()

ADMIN_IDS = [
    int(x) for x in os.getenv("ADMIN_IDS", "").split(",") if x.strip().isdigit()
]

DB_PATH = os.getenv("DB_PATH", "larizinha.db")
WEBHOOK_URL = os.getenv("WEBHOOK_URL", "").strip()
PORT = int(os.getenv("PORT", "8080"))

# Para o Mini App apontar de volta ao bot
MINIAPP_BASE_URL = os.getenv("MINIAPP_BASE_URL", WEBHOOK_URL or f"http://localhost:{PORT}")

# Config de saques
WITHDRAW_MIN = float(os.getenv("WITHDRAW_MIN", "20.00"))
AFFILIATE_COMMISSION = float(os.getenv("AFFILIATE_COMMISSION", "0.20"))
AFFILIATE_MIN_WITHDRAW = float(os.getenv("AFFILIATE_MIN_WITHDRAW", "20.00"))

if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN não configurado no .env")
