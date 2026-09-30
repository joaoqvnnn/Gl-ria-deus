"""
Gerenciamento central dos estados de conversa (awaiting_*).

Problema original: cada handler setava um flag booleano e nunca limpava.
Quando um flag ficava preso em True, o _text_router roteava toda mensagem
para aquele handler errado (bug do "Gift não encontrado" no saque).

Regra:
- Ao INICIAR um fluxo → set_state() (limpa todos os outros automaticamente)
- Ao TERMINAR (sucesso ou erro) → clear_all()
"""

ALL_STATES = (
    "awaiting_multi",
    "awaiting_gift",
    "awaiting_whatsapp",
    "awaiting_topup_value",
    "awaiting_wd_key",
    "awaiting_wd_amount",
    "awaiting_wd_pin",
    "awaiting_search",
)


def clear_all(ud: dict):
    for k in ALL_STATES:
        ud.pop(k, None)


def clear_except(ud: dict, keep: str):
    for k in ALL_STATES:
        if k != keep:
            ud.pop(k, None)


def set_state(ud: dict, state: str):
    """Seta UM estado e limpa todos os outros."""
    clear_all(ud)
    ud[state] = True


def is_set(ud: dict, state: str) -> bool:
    return bool(ud.get(state))
