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
                # `numero` costuma vir "S/N"/"n/a" em prédio; o apartamento real está
                # em `complemento` ("Apto 506"), por isso os dois seguem separados.
                "numero": it.get("numero") or "",
                "bloco": it.get("bloco") or "",
                "complemento": it.get("complemento") or "",
                "edificio": it.get("edificio") or "",
                "tipo": it.get("tipo") or "",
                "bairro": it.get("bairro") or "",
                "cidade": it.get("cidade") or "",
                "uf": it.get("estado") or "",
                "quartos": it.get("numeroquartos") or "",
                "suites": it.get("numerosuites") or "",
                "banhos": it.get("numerobanhos") or "",
                "vagas": it.get("numerovagas") or "",
                "area": it.get("areaprincipal") or it.get("areainterna") or "",
                "valor": it.get("valor") or "",
                "urlpublica": it.get("urlpublica") or "",
                "urlfotoprincipal": it.get("urlfotoprincipal") or "",
                "finalidade": "ALUGUEL" if finalidade == 1 else "VENDA",
            }

    return list(resultados.values())


IMOVIEW_TODOS = f"{IMOVIEW_BASE}/Imovel/RetornarImoveis"


def buscar_brutos_por_endereco(endereco: str, page_size: int = 20) -> List[Dict[str, Any]]:
    """Igual a `buscar_imoveis_por_endereco`, mas devolve o item CRU do Imoview.

    A versão reduzida existe p/ o autocomplete de visita/proposta, que só precisa de
    código e endereço. A consulta de imóvel precisa do payload inteiro (~120 campos:
    valores, características, datas, extras), por isso esta.
    """
    endereco = (endereco or "").strip()
    if len(endereco) < 3:
        return []

    resultados: Dict[str, Dict[str, Any]] = {}
    for finalidade in (1, 2):
        data = _call_imoview_json({
            "numeropagina": 1, "numeroregistros": min(max(page_size, 1), 20),
            "endereco": endereco, "finalidade": finalidade,
            "ordenacao": "dataatualizacaodesc",
        })
        for item in data.get("lista") or []:
            codigo = item.get("codigo")
            if codigo is not None:
                resultados[str(codigo)] = item
    return list(resultados.values())


def _pagina_por_codigo(pagina: int) -> Dict[str, Any]:
    """Uma página do catálogo ordenada por código decrescente.

    `naoconsiderarmeusite=True` é obrigatório: imóvel recém-cadastrado ainda não está
    publicado no site e some do resultado padrão (o 12400 era assim). Com a flag, a base
    vai de 741 para 11.426 imóveis.
    """
    resp = requests.post(
        IMOVIEW_TODOS,
        headers=_headers(),
        json={
            "numeropagina": pagina, "numeroregistros": 20,
            "ordenacao": "codigodesc", "naoconsiderarmeusite": True,
        },
        timeout=30,
    )
    if resp.status_code >= 400:
        raise RuntimeError(f"Imoview HTTP {resp.status_code}: {resp.text[:300]}")
    return resp.json() or {}


def buscar_imovel_por_codigo(codigo: Any) -> Optional[Dict[str, Any]]:
    """Busca UM imóvel pelo código, ao vivo, por **busca binária**.

    A API não tem filtro por código. Mas ela aceita `ordenacao=codigodesc` e informa a
    `quantidade` total — com a lista ordenada, dá p/ saltar direto para a página provável
    em vez de varrer da primeira em diante.

    Custo: ~log2(572 páginas) ≈ **10 requisições no pior caso**, para qualquer código.
    A varredura sequencial anterior gastava 15 requisições e mesmo assim só alcançava os
    300 códigos mais altos — imóvel antigo nunca era encontrado.
    """
    alvo_texto = "".join(ch for ch in str(codigo or "") if ch.isdigit())
    if not alvo_texto:
        return None
    alvo = int(alvo_texto)

    primeira = _pagina_por_codigo(1)
    total = int(primeira.get("quantidade") or 0)
    if not total:
        return None
    ultima_pagina = max(-(-total // 20), 1)

    def _procurar(lista):
        for item in lista:
            if str(item.get("codigo") or "") == alvo_texto:
                return item
        return None

    def _faixa(lista):
        numeros = [int(str(i.get("codigo"))) for i in lista if str(i.get("codigo") or "").isdigit()]
        return (max(numeros), min(numeros)) if numeros else (None, None)

    baixo, alto = 1, ultima_pagina
    pagina_atual, dados = 1, primeira
    while baixo <= alto:
        lista = dados.get("lista") or []
        if not lista:
            return None
        achado = _procurar(lista)
        if achado:
            return achado

        maior, menor = _faixa(lista)
        if maior is None:
            return None
        if alvo > maior:            # códigos maiores estão nas páginas anteriores
            alto = pagina_atual - 1
        elif alvo < menor:          # e os menores, nas seguintes
            baixo = pagina_atual + 1
        else:
            return None             # cairia nesta página; não existe

        if baixo > alto:
            return None
        pagina_atual = (baixo + alto) // 2
        dados = _pagina_por_codigo(pagina_atual)
    return None


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
