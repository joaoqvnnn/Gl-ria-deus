"""
Integração com o Mercado Pago — gera PIX real e consulta status.
"""
import logging
import mercadopago
from config import MERCADOPAGO_ACCESS_TOKEN, MERCADOPAGO_WEBHOOK_URL

logger = logging.getLogger(__name__)

_sdk = mercadopago.SDK(MERCADOPAGO_ACCESS_TOKEN)


def criar_pix(valor: float, descricao: str, user_id: int, purchase_id: str) -> dict:
    """
    Cria um pagamento PIX no Mercado Pago.
    Retorna: { payment_id, status, qr_code_base64, qr_code_text, ticket_url }
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

    result = _sdk.payment().create(payment_data, request_options)
    payment = result.get("response", {})

    if payment.get("status") not in ("pending", "in_process"):
        logger.error("Falha ao criar pagamento MP: %s", payment)
        raise Exception(f"Erro MP: {payment.get('message', 'sem detalhes')}")

    poi = payment.get("point_of_interaction", {})
    tx  = poi.get("transaction_data", {})

    return {
        "payment_id":      payment["id"],
        "status":          payment["status"],
        "qr_code_base64":  tx.get("qr_code_base64"),
        "qr_code_text":    tx.get("qr_code"),
        "ticket_url":      tx.get("ticket_url"),
    }


def consultar_pagamento(payment_id: int) -> dict:
    """Consulta o status de um pagamento pelo ID."""
    result = _sdk.payment().get(payment_id)
    return result.get("response", {})
