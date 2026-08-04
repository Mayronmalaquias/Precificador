"""Criação de cartão no Trello (porta o legado `legado/appsheet/trelo.gs`).

Usado no lançamento de imóvel pelos assistentes: além de incluir no Imoview, cria o
cartão no board de estoque. Credenciais (`TRELLO_KEY`/`TRELLO_TOKEN`) vêm do .env; os
IDs de lista/campos/labels são do board (não são segredo) e ficam como constantes.
"""
from __future__ import annotations

import os
from typing import Any, Dict, Optional

import requests

TRELLO_BASE = "https://api.trello.com/1"

# IDs do board de estoque (mesmos do trelo.gs). Lista = coluna onde o cartão entra.
LIST_ID = os.getenv("TRELLO_LIST_ID", "67924635e1cca89d47423734")
FIELD_CODIGO = "666e09411b37e751c1cd08f9"
FIELD_MATRICULA = "666e0b86881cd13960b5d739"
FIELD_IPTU = "666e0b91e2c6e2dee8204a2a"
FIELD_CORRETOR = "667c0287b1bcbd7f63341ca7"
FIELD_ASSISTENTE = "667c3bbb43aa8c4a88c500bc"
LABEL_CESSAO_DIREITOS = "65e7178abf92ddda4fa4fd4c"


def _auth() -> Dict[str, str]:
    key = os.getenv("TRELLO_KEY", "").strip()
    token = os.getenv("TRELLO_TOKEN", "").strip()
    if not key or not token:
        raise RuntimeError("TRELLO_KEY / TRELLO_TOKEN não configurados no .env")
    return {"key": key, "token": token}


def _set_custom_field(card_id: str, field_id: str, value: Any) -> None:
    if value in (None, ""):
        return
    requests.put(
        f"{TRELLO_BASE}/cards/{card_id}/customField/{field_id}/item",
        params=_auth(),
        json={"value": {"text": str(value)}},
        timeout=20,
    )


def _add_label(card_id: str, label_id: str) -> None:
    requests.post(
        f"{TRELLO_BASE}/cards/{card_id}/idLabels",
        params={**_auth(), "value": label_id},
        timeout=20,
    )


def criar_cartao(
    endereco: str,
    codigo: Optional[str] = None,
    matricula: Optional[str] = None,
    iptu: Optional[str] = None,
    corretor: Optional[str] = None,
    assistente: Optional[str] = None,
    cessao_direitos: bool = False,
) -> Dict[str, Any]:
    """Cria o cartão no Trello e preenche os campos personalizados. Retorna id/url."""
    auth = _auth()
    resp = requests.post(
        f"{TRELLO_BASE}/cards",
        params={**auth, "idList": LIST_ID, "name": endereco or "Novo imóvel", "desc": " "},
        timeout=20,
    )
    if resp.status_code not in (200, 201):
        raise RuntimeError(f"Trello HTTP {resp.status_code}: {resp.text[:400]}")
    card = resp.json()
    card_id = card.get("id")

    _set_custom_field(card_id, FIELD_CODIGO, codigo)
    # Cessão de direitos não tem matrícula — o legado grava o texto no campo matrícula.
    _set_custom_field(card_id, FIELD_MATRICULA, "Cessão de Direitos" if cessao_direitos else matricula)
    _set_custom_field(card_id, FIELD_IPTU, iptu)
    _set_custom_field(card_id, FIELD_CORRETOR, corretor)
    _set_custom_field(card_id, FIELD_ASSISTENTE, assistente)

    if cessao_direitos:
        _add_label(card_id, LABEL_CESSAO_DIREITOS)

    return {"id": card_id, "url": card.get("shortUrl") or card.get("url")}
