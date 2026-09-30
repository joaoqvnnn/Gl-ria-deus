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


def _fmt_date(s):
    try:
        return datetime.strptime(str(s)[:19], "%Y-%m-%d %H:%M:%S").strftime("%d/%m/%Y")
    except Exception:
        return str(s)


# ═══════════════════════════════════════════════
# EXTRATO DE SAQUES
# ═══════════════════════════════════════════════
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
    c.drawString(
        20 * mm,
        h - 38 * mm,
        f"Usuário: {user.get('first_name') or user['user_id']} (ID {user['user_id']})",
    )
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


# ═══════════════════════════════════════════════
# PDF DO PEDIDO (com dados de acesso)
# ═══════════════════════════════════════════════
def gerar_pdf_pedido(purchase: dict, item: dict | None = None) -> bytes:
    """
    Gera PDF do pedido com e-mail e senha.
    `purchase` vem da tabela `purchases`.
    `item` opcional, se quiser pegar de stock_items.
    """
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    w, h = A4

    # ─── Cabeçalho
    c.setFont("Helvetica-Bold", 20)
    c.drawString(20 * mm, h - 25 * mm, "Larizinha Store")
    c.setFont("Helvetica", 11)
    c.setFillColorRGB(0.4, 0.4, 0.4)
    c.drawString(20 * mm, h - 32 * mm, "Comprovante de Acesso e Ativação")
    c.drawString(20 * mm, h - 38 * mm, f"Emitido em: {datetime.now().strftime('%d/%m/%Y %H:%M')}")

    c.setStrokeColorRGB(0.8, 0.8, 0.8)
    c.line(20 * mm, h - 44 * mm, w - 20 * mm, h - 44 * mm)

    # ─── Dados do pedido
    y = h - 56 * mm
    c.setFillColorRGB(0, 0, 0)
    c.setFont("Helvetica-Bold", 12)
    c.drawString(20 * mm, y, "Detalhes do Pedido")
    y -= 8 * mm

    c.setFont("Helvetica", 10)
    c.drawString(20 * mm, y, f"ID: {purchase['id']}")
    y -= 6 * mm
    c.drawString(20 * mm, y, f"Data da compra: {_fmt_date(purchase.get('created_at'))}")
    y -= 6 * mm
    c.drawString(20 * mm, y, f"Vencimento: {_fmt_date(purchase.get('expires_at'))}")
    y -= 6 * mm
    c.drawString(20 * mm, y, f"Valor: R$ {float(purchase.get('total', 0)):.2f}")
    y -= 6 * mm
    c.drawString(20 * mm, y, f"Serviço: {purchase.get('product_name', '-')}")
    y -= 6 * mm
    c.drawString(20 * mm, y, f"Quantidade: {purchase.get('quantity', 1)}")

    # ─── Credenciais
    y -= 12 * mm
    c.setFont("Helvetica-Bold", 12)
    c.drawString(20 * mm, y, "Dados de Acesso")
    y -= 8 * mm

    c.setFont("Helvetica", 10)
    email = purchase.get("email") or "-"
    senha = purchase.get("password") or "-"
    c.drawString(20 * mm, y, f"E-mail: {email}")
    y -= 6 * mm
    c.drawString(20 * mm, y, f"Senha:  {senha}")

    # ─── Aviso
    y -= 14 * mm
    c.setFont("Helvetica-Oblique", 9)
    c.setFillColorRGB(0.5, 0.5, 0.5)
    c.drawString(
        20 * mm,
        y,
        "Não compartilhe seus dados de acesso. Cada conta é pessoal e intransferível.",
    )

    # ─── Rodapé
    c.setFont("Helvetica", 8)
    c.drawString(20 * mm, 15 * mm, "© Larizinha Store — Todos os direitos reservados.")

    c.showPage()
    c.save()
    buf.seek(0)
    return buf.getvalue()
