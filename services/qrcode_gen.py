"""
Gera a imagem única do QR Code com os textos/valores embutidos
na própria imagem (como no fluxo pedido).
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


def generate_pix_image(pix_code: str, valor: float, id_recarga: str, expira: str) -> bytes:
    """QR Code normal + textos embutidos."""
    qr = qrcode.QRCode(box_size=9, border=2, error_correction=qrcode.constants.ERROR_CORRECT_M)
    qr.add_data(pix_code)
    qr.make(fit=True)
    qr_img = qr.make_image(fill_color="black", back_color="white").convert("RGB")

    qr_w, qr_h = qr_img.size
    padding = 30
    text_h = 190

    canvas = Image.new("RGB", (qr_w + padding * 2, qr_h + text_h + padding * 2), "white")
    canvas.paste(qr_img, (padding, padding))

    draw = ImageDraw.Draw(canvas)
    y = qr_h + padding + 8

    draw.text((padding, y), f"Valor: R$ {valor:.2f}", fill="black", font=_font(24, bold=True))
    y += 34
    draw.text((padding, y), f"ID: {id_recarga}", fill="#333333", font=_font(16))
    y += 26
    draw.text((padding, y), f"Expira em: {expira}", fill="#333333", font=_font(16))
    y += 26
    draw.text((padding, y), "Pix Copia e Cola abaixo:", fill="#666666", font=_font(14))

    buf = io.BytesIO()
    canvas.save(buf, format="PNG")
    buf.seek(0)
    return buf.getvalue()


def generate_paid_image(pix_code: str) -> bytes:
    """QR Code VERDE com indicador PAGO."""
    qr = qrcode.QRCode(box_size=9, border=2, error_correction=qrcode.constants.ERROR_CORRECT_M)
    qr.add_data(pix_code)
    qr.make(fit=True)
    qr_img = qr.make_image(fill_color="#22c55e", back_color="white").convert("RGB")

    qr_w, qr_h = qr_img.size
    padding = 30
    text_h = 70

    canvas = Image.new("RGB", (qr_w + padding * 2, qr_h + text_h + padding * 2), "white")
    canvas.paste(qr_img, (padding, padding))

    draw = ImageDraw.Draw(canvas)
    draw.text(
        (padding, qr_h + padding + 12),
        "✅ PAGO",
        fill="#22c55e",
        font=_font(32, bold=True),
    )

    buf = io.BytesIO()
    canvas.save(buf, format="PNG")
    buf.seek(0)
    return buf.getvalue()
