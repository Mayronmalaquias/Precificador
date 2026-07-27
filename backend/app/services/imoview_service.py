# app/services/imoview_service.py
from __future__ import annotations

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
