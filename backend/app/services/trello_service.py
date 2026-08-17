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
    urlvideo: Optional[str] = None,
) -> Dict[str, Any]:
    """Cria o cartão no Trello e preenche os campos personalizados. Retorna id/url."""
    auth = _auth()
    # O link do vídeo vai na descrição: o board não tem campo personalizado p/ ele.
    descricao = f"Vídeo do imóvel: {urlvideo}" if str(urlvideo or "").strip() else " "
    resp = requests.post(
        f"{TRELLO_BASE}/cards",
        params={**auth, "idList": LIST_ID, "name": endereco or "Novo imóvel", "desc": descricao},
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


# ── Atualização de cartão já existente ──────────────────────────────────────────

def tem_cessao_direitos(card_id: str) -> bool:
    """O cartão está marcado como cessão de direitos?

    Nesses cartões o campo matrícula guarda o texto `"Cessão de Direitos"` no lugar do
    número (regra herdada do legado `trelo.gs`) — é informação, não um valor a corrigir.
    """
    resp = requests.get(
        f"{TRELLO_BASE}/cards/{card_id}",
        params={**_auth(), "fields": "idLabels"},
        timeout=20,
    )
    if resp.status_code >= 400:
        return False
    return LABEL_CESSAO_DIREITOS in ((resp.json() or {}).get("idLabels") or [])


def atualizar_campos(
    card_id: str,
    matricula: Optional[str] = None,
    iptu: Optional[str] = None,
) -> Dict[str, Any]:
    """Regrava matrícula e/ou inscrição num cartão que já existe.

    Só escreve o que veio preenchido: `_set_custom_field` ignora vazio, então mandar
    `None` deixa o campo do cartão como está em vez de apagá-lo.

    **Cartão de cessão de direitos preserva a matrícula.** Lá o campo guarda o texto
    "Cessão de Direitos"; sobrescrever apagaria a marcação que o board usa para
    diferenciar esses imóveis. O IPTU continua sendo atualizado normalmente.
    """
    if not card_id:
        raise RuntimeError("Cartão do Trello não informado")

    cessao = bool(matricula) and tem_cessao_direitos(card_id)
    if not cessao:
        _set_custom_field(card_id, FIELD_MATRICULA, matricula)
    _set_custom_field(card_id, FIELD_IPTU, iptu)
    return {"matricula_preservada": cessao}


def _board_da_lista() -> str:
    resp = requests.get(f"{TRELLO_BASE}/lists/{LIST_ID}/board", params={**_auth(), "fields": "id"}, timeout=20)
    if resp.status_code >= 400:
        raise RuntimeError(f"Trello HTTP {resp.status_code} ao achar o board: {resp.text[:200]}")
    return (resp.json() or {}).get("id") or ""


def buscar_cartao_por_codigo(codigo: Any) -> Optional[Dict[str, Any]]:
    """Acha o cartão pelo campo personalizado CÓDIGO, varrendo o board.

    Existe para os imóveis lançados **antes** de guardarmos o id do cartão. É caro (baixa
    os cartões do board inteiro), então quem chama grava o id no banco depois — a
    varredura acontece uma vez por imóvel.

    O `/search` do Trello não consulta campo personalizado, por isso a varredura.
    """
    alvo = str(codigo or "").strip()
    if not alvo:
        return None

    board = _board_da_lista()
    if not board:
        return None

    resp = requests.get(
        f"{TRELLO_BASE}/boards/{board}/cards",
        params={**_auth(), "customFieldItems": "true", "fields": "id,shortUrl,name"},
        timeout=45,
    )
    if resp.status_code >= 400:
        raise RuntimeError(f"Trello HTTP {resp.status_code} ao listar cartões: {resp.text[:200]}")

    for card in resp.json() or []:
        for item in card.get("customFieldItems") or []:
            if item.get("idCustomField") != FIELD_CODIGO:
                continue
            texto = str(((item.get("value") or {}).get("text") or "")).strip()
            if texto and texto == alvo:
                return {"id": card.get("id"), "url": card.get("shortUrl"), "nome": card.get("name")}
    return None
