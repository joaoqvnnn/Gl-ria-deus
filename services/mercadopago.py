import os
import mercadopago
from config import (
    MERCADOPAGO_ACCESS_TOKEN,
    MERCADOPAGO_WEBHOOK_URL,
)

# Inicializa o SDK
sdk = mercadopago.SDK(MERCADOPAGO_ACCESS_TOKEN)


def criar_pagamento_pix(valor: float, descricao: str, user_id: int, purchase_id: str):
    """
    Cria um pagamento PIX no Mercado Pago.
    Retorna um dicionário com:
      - payment_id
      - qr_code (base64)
      - qr_code_text (copia e cola)
      - status
    """
    payment_data = {
        "transaction_amount": float(valor),
        "description": descricao,
        "payment_method_id": "pix",
        "payer": {
            "email": f"user_{user_id}@larizinha.com",
        },
        "external_reference": purchase_id,
        "notification_url": MERCADOPAGO_WEBHOOK_URL,
    }

    request_options = mercadopago.config.RequestOptions()
    request_options.custom_headers = {
        "x-idempotency-key": purchase_id,  # evita duplicidade
    }

    result = sdk.payment().create(payment_data, request_options)
    payment = result["response"]

    if payment.get("status") not in ("pending", "in_process"):
        raise Exception(f"Erro ao criar pagamento: {payment}")

    # Dados do PIX
    point_of_interaction = payment.get("point_of_interaction", {})
    transaction_data = point_of_interaction.get("transaction_data", {})

    return {
        "payment_id": payment["id"],
        "status": payment["status"],
        "qr_code": transaction_data.get("qr_code_base64"),
        "qr_code_text": transaction_data.get("qr_code"),
        "ticket_url": transaction_data.get("ticket_url"),
    }


def consultar_pagamento(payment_id: int):
    """Consulta o status de um pagamento no Mercado Pago."""
    result = sdk.payment().get(payment_id)
    return result["response"]
