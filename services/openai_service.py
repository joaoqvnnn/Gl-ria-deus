"""
IA para chat de atendimento e verificação de idade (+18) por OCR de RG.
Usa OpenAI (GPT-4o-mini).
"""
import os
import json
import logging
from openai import OpenAI

logger = logging.getLogger(__name__)

_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY", ""))


# ═══════════════════════════════════════════════
# CHAT
# ═══════════════════════════════════════════════
def chat_resposta(mensagem: str, contexto: str = "") -> str:
    """
    Retorna a resposta da IA para o chat de atendimento.
    `contexto` pode trazer lista de produtos e regras da loja.
    """
    system_prompt = (
        "Você é o atendente virtual de uma loja digital de streamings e contas. "
        "Responda de forma curta (2-4 frases), educada, em português brasileiro. "
        "Nunca invente preços: use os dados do catálogo fornecidos no contexto. "
        "Se o usuário pedir 'humano', 'atendente' ou reclamar de algo complexo, "
        "diga que está transferindo para um atendente humano."
        + ("\n\n" + contexto if contexto else "")
    )

    try:
        resp = _client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user",   "content": mensagem},
            ],
            max_tokens=220,
            temperature=0.7,
        )
        return resp.choices[0].message.content.strip()
    except Exception as e:
        logger.exception("Erro OpenAI chat: %s", e)
        return "Desculpe, tive um problema técnico. Tente novamente em instantes."


# ═══════════════════════════════════════════════
# VERIFICAÇÃO DE IDADE (+18) — OCR de RG
# ═══════════════════════════════════════════════
def verificar_idade_por_rg(front_b64: str, back_b64: str) -> dict:
    """
    Analisa as fotos do RG (frente e verso) e devolve:
      { aprovado: bool, motivo: str }
    """
    # Aceita tanto data URL quanto base64 puro
    front = front_b64.split(",")[-1] if "," in front_b64 else front_b64
    back  = back_b64.split(",")[-1]  if "," in back_b64  else back_b64

    prompt = (
        "Você é um sistema de validação de identidade. Analise as DUAS imagens "
        "(frente e verso de um documento de identidade brasileiro — pode ser RG, CNH ou CIN). "
        "Verifique:\n"
        "1) Se é um documento de identidade real e legível.\n"
        "2) Se contém data de nascimento visível.\n"
        "3) Se a pessoa tem 18 anos ou mais na data de hoje.\n\n"
        "Responda SOMENTE em JSON no formato exato:\n"
        '{"aprovado": true|false, "motivo": "texto curto explicando"}\n'
        "Se qualquer item falhar, 'aprovado' deve ser false."
    )

    try:
        resp = _client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{front}"}},
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{back}"}},
                ],
            }],
            response_format={"type": "json_object"},
            max_tokens=200,
        )
        resultado = json.loads(resp.choices[0].message.content)
        return {
            "aprovado": bool(resultado.get("aprovado")),
            "motivo":   resultado.get("motivo", ""),
        }
    except Exception as e:
        logger.exception("Erro OpenAI verificar_idade: %s", e)
        return {"aprovado": False, "motivo": "Falha ao analisar documento."}
