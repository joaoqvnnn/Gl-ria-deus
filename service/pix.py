"""
Serviço de geração de PIX.
Por padrão gera um "PIX fake" para desenvolvimento.
Para produção, substitua `gerar_pix()` pela integração real
(Mercado Pago, Efí, Gerencianet, Pagar.me, etc.).
"""
import uuid
from datetime import datetime, timedelta


def gerar_pix(valor: float, descricao: str = "Larizinha Store") -> dict:
    pix_id = str(uuid.uuid4())
    expira = datetime.now() + timedelta(minutes=30)

    # ⚠️ PAYLOAD FAKE — substitua pela geração real do PSP
    copia_cola = (
        "00020126580014BR.GOV.BCB.PIX0136"
        f"{pix_id}"
        "5204000053039865802BR5913LARIZINHA STORE6009SAO PAULO"
        "62070503***6304ABCD"
    )

    return {
        "id": pix_id,
        "valor": valor,
        "descricao": descricao,
        "copia_cola": copia_cola,
        "expira_em": expira.strftime("%d/%m/%Y %H:%M"),
        "status": "pending",
    }


def is_paid(pix_record: dict) -> bool:
    """Em produção, aqui você consulta a API do PSP."""
    return pix_record.get("status") == "paid"
