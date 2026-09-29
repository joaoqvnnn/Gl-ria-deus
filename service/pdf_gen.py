import io
from datetime import datetime
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas


def _fmt(s):
    try:
        return datetime.strptime(str(s)[:19], "%Y-%m-%d %H:%M:%S").strftime("%d/%m/%Y %H:%M")
    except Exception:
        return str(s)


def generate_withdraw_history_pdf(bot_handle: str, user: dict, withdrawals: list) -> bytes:
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    w, h = A4

    # Cabeçalho
    c.setFont("Helvetica-Bold", 20)
    c.drawString(20 * mm, h - 25 * mm, "Extrato do Bot")
    c.setFont("Helvetica", 11)
    c.setFillColorRGB(0.4, 0.4, 0.4)
    c.drawString(20 * mm, h - 32 * mm, f"Bot: {bot_handle}")
    c.drawString(20 * mm, h - 38 * mm, f"Usuário: {user.get('first_name') or user['user_id']} (ID {user['user_id']})")
    c.drawString(20 * mm, h - 44 * mm, f"Emitido em: {datetime.now().strftime('%d/%m/%Y %H:%M')}")

    # Linha
    c.setStrokeColorRGB(0.8, 0.8, 0.8)
    c.line(20 * mm, h - 48 * mm, w - 20 * mm, h - 48 * mm)

    # Cabeçalho tabela
    y = h - 58 * mm
    c.setFillColorRGB(0, 0, 0)
    c.setFont("Helvetica-Bold", 10)
    c.drawString(20 * mm, y, "Data")
    c.drawString(60 * mm, y, "Valor")
    c.drawString(90 * mm, y, "Chave")
    c.drawString(140 * mm, y, "Status")

    y -= 6 * mm
    c.setFont("Helvetica", 9)

    if not withdrawals:
        c.drawString(20 * mm, y, "Você não possui saques.")
    else:
        for wd in withdrawals:
            if y < 30 * mm:
                c.showPage()
                y = h - 25 * mm
                c.setFont("Helvetica", 9)
            c.drawString(20 * mm, y, _fmt(wd.get("created_at")))
            c.drawString(60 * mm, y, f"R$ {float(wd['amount']):.2f}")
            key = str(wd.get("pix_key") or "-")
            c.drawString(90 * mm, y, key[:28])
            c.drawString(140 * mm, y, wd.get("status", "-"))
            y -= 6 * mm

    c.showPage()
    c.save()
    buf.seek(0)
    return buf.getvalue()
