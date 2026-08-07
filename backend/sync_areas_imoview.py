"""Snapshot das areas do catalogo Imoview -> tabela `imovel_area` (rodar via cron).

Por que existe: a API do Imoview so lista imovel ATIVO. Quando o imovel vende ele
some da API, e e nesse momento que precisamos da metragem p/ o valor do m2 do
contrato. Rodando periodicamente, a area fica gravada antes da venda.

Cobre o que estiver no catalogo no momento da execucao — venda antiga cujo imovel
ja saiu do ar continua sem area (nao ha de onde tirar).

Uso (cwd = backend/):
    cd /caminho/Precificador/backend && venv/bin/python sync_areas_imoview.py
"""
import sys
from datetime import datetime

import requests

from app.database import SessionLocal
from app.models.imovel_area import ImovelArea
from app.services.imoview_service import IMOVIEW_BASE, _headers

ENDPOINT = f"{IMOVIEW_BASE}/Imovel/RetornarImoveis"
POR_PAGINA = 20  # teto da API: acima disso responde 404 "N de registros nao pode ser maior que 20!"
MAX_PAGINAS = 200


def _num(valor):
    """Area do Imoview vem como texto BR ("95,00").

    Cuidado: `areaprivativa`/`areaservico` sao BOOLEANOS no mesmo payload — sem
    barrar bool, um `True` viraria "1 m2" e estragaria o valor do m2.
    """
    if isinstance(valor, bool) or valor in (None, ""):
        return None
    if isinstance(valor, (int, float)):
        numero = float(valor)
    else:
        texto = str(valor).strip().replace("R$", "").replace(" ", "")
        if "," in texto:
            texto = texto.replace(".", "").replace(",", ".")
        try:
            numero = float(texto)
        except ValueError:
            return None
    return numero if numero > 0 else None


def coletar():
    """Percorre o catalogo e devolve {codigo: dados de area}."""
    catalogo = {}
    pagina = 1
    while pagina <= MAX_PAGINAS:
        resposta = requests.post(
            ENDPOINT, headers=_headers(),
            json={"numeropagina": pagina, "numeroregistros": POR_PAGINA}, timeout=45,
        )
        if resposta.status_code >= 400:
            raise RuntimeError(f"Imoview HTTP {resposta.status_code}: {resposta.text[:300]}")
        lista = (resposta.json() or {}).get("lista") or []
        if not lista:
            break
        for item in lista:
            codigo = str(item.get("codigo") or "").strip()
            if not codigo:
                continue
            principal = _num(item.get("areaprincipal"))
            interna = _num(item.get("areainterna"))
            # `areaprivativa` costuma vir como flag; só entra se for número de verdade.
            privativa = _num(item.get("areaprivativa"))
            catalogo[codigo] = {
                "area": principal or interna or privativa,
                "area_principal": principal,
                "area_interna": interna,
                "area_privativa": privativa,
                "area_lote": _num(item.get("arealote")),
                "endereco": item.get("endereco"),
                "bairro": item.get("bairro"),
                "tipo": item.get("tipo") or item.get("descricaotipo"),
            }
        if len(lista) < POR_PAGINA:
            break
        pagina += 1
    return catalogo


def gravar(catalogo):
    """Upsert por codigo — nunca apaga: imovel que saiu do catalogo tem que ficar."""
    session = SessionLocal()
    try:
        existentes = {row.codigo: row for row in session.query(ImovelArea).all()}
        novos = atualizados = 0
        for codigo, dados in catalogo.items():
            registro = existentes.get(codigo)
            if registro is None:
                session.add(ImovelArea(codigo=codigo, origem="imoview", **dados))
                novos += 1
                continue
            for campo, valor in dados.items():
                setattr(registro, campo, valor)
            atualizados += 1
        session.commit()
        return novos, atualizados
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


if __name__ == "__main__":
    agora = datetime.now().isoformat(timespec="seconds")
    try:
        catalogo = coletar()
        novos, atualizados = gravar(catalogo)
        print(f"[{agora}] areas imoview: catalogo={len(catalogo)} novos={novos} atualizados={atualizados}")
    except Exception as e:
        print(f"[{agora}] sync de areas FALHOU: {e}", file=sys.stderr)
        sys.exit(1)
