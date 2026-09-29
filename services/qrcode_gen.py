"""
Gera QR Code com TODOS os textos/valores embutidos na imagem.
- Modo normal: mostra valor, ID, expiração e o Pix Copia e Cola.
- Modo PAGO: mostra QR verde + "✅ PAGO" + valor.
"""
import io
from PIL import Image, ImageDraw, ImageFont
import qrcode


def _font(size: int, bold: bool = False):
    paths = [
        f"/usr/share/fonts/truetype/dejavu/DejaVuSans{'-Bold' if bold else ''}.ttf",
        f"/usr/share/fonts/truetype/liberation/LiberationSans{'-Bold' if bold else '-Regular'}.ttf",
    ]
    for p in paths:
        try:
            return ImageFont.truetype(p, size)
        except Exception:
            continue
    return ImageFont.load_default()


def _wrap(text: str, max_chars: int) -> list[str]:
    """Quebra um texto em linhas de no máximo N caracteres."""
    linhas = []
    while len(text) > max_chars:
        linhas.append(text[:max_chars])
        text = text[max_chars:]
    if text:
        linhas.append(text)
    return linhas


def generate_pix_image(
    pix_code: str,
    valor: float,
    id_recarga: str,
    expira: str,
    titulo: str = "PIX - Larizinha Store",
    saldo_atual: float | None = None,
    saldo_futuro: float | None = None,
    bonus: float | None = None,
) -> bytes:
    """
    Gera imagem única do PIX com TODAS as informações embutidas.
    Ideal para: compra (sem saldo/bonus) e recarga (com saldo/bonus).
    """
    # ─── QR Code
    qr = qrcode.QRCode(
        box_size=8,
        border=2,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
    )
    qr.add_data(pix_code)
    qr.make(fit=True)
    qr_img = qr.make_image(fill_color="black", back_color="white").convert("RGB")

    qr_w, qr_h = qr_img.size
    padding = 30
    header_h = 60

    # ─── Calcula altura do bloco de texto
    linhas_texto = []
    linhas_texto.append(("titulo", titulo))
    linhas_texto.append(("valor", f"Valor: R$ {valor:.2f}"))
    if bonus and bonus > 0:
        linhas_texto.append(("bonus", f"Bonus: R$ {bonus:.2f}"))
    if saldo_atual is not None and saldo_futuro is not None:
        linhas_texto.append(("saldo", f"Saldo atual: R$ {saldo_atual:.2f}"))
        linhas_texto.append(("saldo_futuro", f"Saldo apos pagamento: R$ {saldo_futuro:.2f}"))
    linhas_texto.append(("id", f"ID: {id_recarga}"))
    linhas_texto.append(("exp", f"Expira em: {expira}"))

    # ─── Pix Copia e Cola (quebra em várias linhas)
    copia_linhas = _wrap(pix_code, 44)
    linhas_texto.append(("sep", "Pix Copia e Cola:"))
    for l in copia_linhas:
        linhas_texto.append(("code", l))

    # ─── Calcula altura total do bloco de texto
    alturas = {
        "titulo": 34,
        "valor": 30,
        "bonus": 26,
        "saldo": 24,
        "saldo_futuro": 24,
        "id": 22,
        "exp": 22,
        "sep": 22,
        "code": 20,
    }
    text_h = sum(alturas[t] for t, _ in linhas_texto) + 40

    # ─── Canvas
    total_w = max(qr_w, 500) + padding * 2
    total_h = header_h + qr_h + text_h + padding * 2
    canvas = Image.new("RGB", (total_w, total_h), "white")
    draw = ImageDraw.Draw(canvas)

    # ─── Header
    draw.rectangle([(0, 0), (total_w, header_h)], fill="#6b8afd")
    title_w = draw.textlength(titulo, font=_font(22, bold=True))
    draw.text(
        ((total_w - title_w) / 2, 18),
        titulo,
        fill="white",
        font=_font(22, bold=True),
    )

    # ─── QR centralizado
    qr_x = (total_w - qr_w) // 2
    canvas.paste(qr_img, (qr_x, header_h + padding))

    # ─── Bloco de texto
    y = header_h + qr_h + padding + 8
    x = padding + 10

    for tipo, texto in linhas_texto:
        if tipo == "titulo":
            continue  # já foi no header
        elif tipo == "valor":
            draw.text((x, y), texto, fill="#111111", font=_font(26, bold=True))
            y += 34
        elif tipo == "bonus":
            draw.text((x, y), texto, fill="#16a34a", font=_font(20, bold=True))
            y += 28
        elif tipo == "saldo":
            draw.text((x, y), texto, fill="#333333", font=_font(18))
            y += 26
        elif tipo == "saldo_futuro":
            draw.text((x, y), texto, fill="#333333", font=_font(18))
            y += 28
        elif tipo == "id":
            draw.text((x, y), texto, fill="#555555", font=_font(16))
            y += 24
        elif tipo == "exp":
            draw.text((x, y), texto, fill="#555555", font=_font(16))
            y += 26
        elif tipo == "sep":
            draw.text((x, y), texto, fill="#999999", font=_font(14, bold=True))
            y += 24
        elif tipo == "code":
            draw.text((x, y), texto, fill="#1f2937", font=_font(13))
            y += 20

    buf = io.BytesIO()
    canvas.save(buf, format="PNG")
    buf.seek(0)
    return buf.getvalue()


def generate_paid_image(
    pix_code: str,
    valor: float | None = None,
    titulo: str = "Pagamento Confirmado",
) -> bytes:
    """QR Code VERDE com indicador PAGO."""
    qr = qrcode.QRCode(
        box_size=8,
        border=2,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
    )
    qr.add_data(pix_code)
    qr.make(fit=True)
    qr_img = qr.make_image(fill_color="#22c55e", back_color="white").convert("RGB")

    qr_w, qr_h = qr_img.size
    padding = 30
    header_h = 60
    text_h = 90

    total_w = max(qr_w, 460) + padding * 2
    total_h = header_h + qr_h + text_h + padding * 2
    canvas = Image.new("RGB", (total_w, total_h), "white")
    draw = ImageDraw.Draw(canvas)

    # Header verde
    draw.rectangle([(0, 0), (total_w, header_h)], fill="#22c55e")
    title_w = draw.textlength(titulo, font=_font(22, bold=True))
    draw.text(
        ((total_w - title_w) / 2, 18),
        titulo,
        fill="white",
        font=_font(22, bold=True),
    )

    # QR centralizado
    qr_x = (total_w - qr_w) // 2
    canvas.paste(qr_img, (qr_x, header_h + padding))

    # Texto abaixo
    y = header_h + qr_h + padding + 10
    check_txt = "PAGO"
    check_w = draw.textlength(check_txt, font=_font(40, bold=True))
    draw.text(
        ((total_w - check_w) / 2, y),
        check_txt,
        fill="#22c55e",
        font=_font(40, bold=True),
    )

    if valor:
        valor_txt = f"R$ {valor:.2f}"
        valor_w = draw.textlength(valor_txt, font=_font(24, bold=True))
        draw.text(
            ((total_w - valor_w) / 2, y + 50),
            valor_txt,
            fill="#111111",
            font=_font(24, bold=True),
        )

    buf = io.BytesIO()
    canvas.save(buf, format="PNG")
    buf.seek(0)
    return buf.getvalue()
