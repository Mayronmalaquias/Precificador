# app/services/imoview_service.py
from __future__ import annotations

import json as _json
import os
import requests
from typing import Any, Dict, List, Optional

IMOVIEW_BASE = "https://api.imoview.com.br"
IMOVIEW_ENDPOINT = f"{IMOVIEW_BASE}/Imovel/RetornarImoveisDisponiveis"


def _headers() -> Dict[str, str]:
    chave = os.getenv("IMOVIEW_CHAVE", "").strip()
    codigoacesso = os.getenv("IMOVIEW_CODIGOACESSO", "").strip()

    if not chave:
        raise RuntimeError("Env var IMOVIEW_CHAVE não configurada.")

    h = {"chave": chave}

    # Se sua API exigir codigoacesso, configure no .env
    if codigoacesso:
        h["codigoacesso"] = codigoacesso

    return h


def _call_imoview_json(payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Imoview aqui exige JSON de entrada (corpo). Se enviar via querystring dá:
    'Json de entrada não informado!'.
    """
    resp = requests.post(
        IMOVIEW_ENDPOINT,
        headers=_headers(),
        json=payload,
        timeout=30,
    )

    # Imoview às vezes retorna 404 mesmo sendo erro de validação
    if resp.status_code >= 400:
        raise RuntimeError(f"Imoview HTTP {resp.status_code}: {resp.text[:800]}")

    return resp.json() or {}


def buscar_imoveis_por_endereco(
    endereco: str,
    codigocidade: Optional[str] = None,
    codigosbairros: Optional[str] = None,
    page: int = 1,
    page_size: int = 20,
) -> List[Dict[str, Any]]:
    """
    Busca imóveis no Imoview por parte do logradouro (campo 'endereco').

    Observação importante: 'finalidade' é obrigatório:
      1 = ALUGUEL
      2 = VENDA

    Então fazemos 2 chamadas e juntamos sem duplicar pelo 'codigo'.
    """

    endereco = (endereco or "").strip()
    if len(endereco) < 3:
        return []

    page = max(int(page or 1), 1)
    page_size = min(max(int(page_size or 20), 1), 20)

    # Payload base exigido pelo Imoview (JSON)
    base_payload: Dict[str, Any] = {
        "numeropagina": page,
        "numeroregistros": page_size,
        "endereco": endereco,
        "ordenacao": "dataatualizacaodesc",
        # Se quiser, depois dá para ativar filtros adicionais aqui:
        # "situacao": 1,  # vago/disponível (quando usar naoconsiderarmeusite/situacao)
    }

    if codigocidade:
        # o Imoview costuma aceitar int/str, então deixa como vem
        base_payload["codigocidade"] = codigocidade

    if codigosbairros:
        base_payload["codigosbairros"] = codigosbairros

    resultados: Dict[str, Dict[str, Any]] = {}

    for finalidade in (1, 2):
        payload = dict(base_payload)
        payload["finalidade"] = finalidade

        data = _call_imoview_json(payload)
        lista = data.get("lista") or []

        for it in lista:
            codigo = it.get("codigo")
            if codigo is None:
                continue

            codigo_str = str(codigo)

            resultados[codigo_str] = {
                "codigo": codigo,
                "titulo": it.get("titulo") or "",
                "endereco": it.get("endereco") or "",
                "numero": it.get("numero") or "",
                "bairro": it.get("bairro") or "",
                "cidade": it.get("cidade") or "",
                "uf": it.get("estado") or "",
                "urlpublica": it.get("urlpublica") or "",
                "urlfotoprincipal": it.get("urlfotoprincipal") or "",
                "finalidade": "ALUGUEL" if finalidade == 1 else "VENDA",
            }

    return list(resultados.values())


# ============================================================================
# Inclusão de imóvel (lançamento pelos assistentes) + listas de lookup
# ============================================================================

def _get_imoview(endpoint: str, params: Optional[Dict[str, Any]] = None) -> Any:
    """GET nos endpoints de lista (RetornarLista*). Header `chave`."""
    resp = requests.get(
        f"{IMOVIEW_BASE}{endpoint}",
        headers=_headers(),
        params=params or {},
        timeout=30,
    )
    if resp.status_code >= 400:
        raise RuntimeError(f"Imoview HTTP {resp.status_code} em {endpoint}: {resp.text[:500]}")
    try:
        return resp.json()
    except ValueError:
        return []


def _lista(endpoint: str) -> List[Any]:
    """Imoview devolve {'quantidade': n, 'lista': [...]} — desembrulha p/ lista pura."""
    data = _get_imoview(endpoint)
    if isinstance(data, dict):
        return data.get("lista") or []
    return data if isinstance(data, list) else []


# Listas para popular os dropdowns do formulário de lançamento (itens {codigo, nome}).
def listar_unidades() -> List[Any]:
    return _lista("/Imovel/RetornarListaUnidades")


def listar_finalidades() -> List[Any]:
    return _lista("/Imovel/RetornarListaFinalidades")


def listar_destinacoes() -> List[Any]:
    return _lista("/Imovel/RetornarListaDestinacoes")


def listar_tipos() -> List[Any]:
    return _lista("/Imovel/RetornarTiposImoveisDisponiveis")


def listar_localchaves() -> List[Any]:
    return _lista("/Imovel/RetornarListaLocalChaves")


def incluir_imovel(parametros: Dict[str, Any], fotos: Optional[List[Any]] = None) -> Dict[str, Any]:
    """
    POST /Imovel/IncluirImovel — cria um imóvel no Imoview CRM.

    Contrato do Imoview: os campos vão como JSON na QUERY (`parametros`); as fotos
    (opcionais) vão no corpo multipart/form-data no campo `fotos`. Retorna
    `{ "mensagem": str, "codigo": int }`.

    `fotos` pode ser uma lista de FileStorage (Flask) ou tuplas (nome, bytes, mime).
    """
    url = f"{IMOVIEW_BASE}/Imovel/IncluirImovel"

    files: List[Any] = []
    for f in (fotos or []):
        if hasattr(f, "read"):  # werkzeug FileStorage / file-like
            nome = getattr(f, "filename", None) or "foto.jpg"
            mime = getattr(f, "mimetype", None) or "image/jpeg"
            files.append(("fotos", (nome, f.stream if hasattr(f, "stream") else f, mime)))
        elif isinstance(f, (tuple, list)) and len(f) >= 2:
            files.append(("fotos", tuple(f)))

    resp = requests.post(
        url,
        headers=_headers(),
        params={"parametros": _json.dumps(parametros, ensure_ascii=False)},
        files=files or None,
        timeout=60,
    )
    if resp.status_code >= 400:
        raise RuntimeError(f"Imoview HTTP {resp.status_code}: {resp.text[:800]}")
    try:
        return resp.json() or {}
    except ValueError:
        return {"mensagem": resp.text[:500], "codigo": None}
