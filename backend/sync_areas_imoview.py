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
import unicodedata
from datetime import date, datetime

import requests

from app.database import SessionLocal
from app.models.imovel_area import ImovelArea
from app.models.imovel_situacao_evento import ImovelSituacaoEvento
from app.services.imoview_service import IMOVIEW_BASE, _headers

ENDPOINT = f"{IMOVIEW_BASE}/Imovel/RetornarImoveis"
POR_PAGINA = 20  # teto da API: acima disso responde 404 "N de registros nao pode ser maior que 20!"
MAX_PAGINAS = 200

# Situacoes varridas. 1=Vago/Disponivel (854) e o estoque; 3=Vendido (1.175) importa
# porque some da API depois e e dele que sai a metragem do valor/m2 dos contratos;
# 4=Em reforma (4) e 5=Em moderacao (81) sao baratas e precisam ser distinguidas — sem
# elas, um imovel em moderacao pareceria "desativado" e entraria como saida de estoque,
# que e justamente o que a regra manda excluir.
# Fora daqui so 6=Desativado (9.312): baixar isso todo dia custaria ~466 paginas, e o
# imovel desativado e deduzido por ausencia (ver `gravar`).
SITUACOES = {1: "Vago/Disponivel", 3: "Vendido", 4: "Em reforma", 5: "Em moderacao"}


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


def _inteiro(valor):
    numero = _num(valor)
    return int(numero) if numero is not None else None


def coletar():
    """Percorre o catalogo por situacao e devolve {codigo: dados de area}.

    `naoconsiderarmeusite=True` e obrigatorio: sem ele a API devolve so os 741 imoveis
    publicados no site, e o recem-lancado (que ainda nao foi publicado) fica de fora.
    """
    catalogo = {}
    for situacao in SITUACOES:
        catalogo.update(_coletar_situacao(situacao))
    return catalogo


def _coletar_situacao(situacao):
    catalogo = {}
    pagina = 1
    while pagina <= MAX_PAGINAS:
        resposta = requests.post(
            ENDPOINT, headers=_headers(),
            json={
                "numeropagina": pagina, "numeroregistros": POR_PAGINA,
                "naoconsiderarmeusite": True, "situacao": situacao,
            }, timeout=45,
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
                "quartos": _inteiro(item.get("numeroquartos")),
                "vagas": _inteiro(item.get("numerovagas")),
                "valor": _num(item.get("valor")),
                "endereco": item.get("endereco"),
                "bairro": item.get("bairro"),
                "tipo": item.get("tipo") or item.get("descricaotipo"),
                "situacao": item.get("situacao") or SITUACOES[situacao],
            }
        if len(lista) < POR_PAGINA:
            break
        pagina += 1
    return catalogo


DESATIVADO = "Desativado"


def _sem_acento(texto):
    """A API manda 'Vago/Disponivel' com acento; o fallback local, sem. Compara igual."""
    return unicodedata.normalize("NFKD", str(texto or "")).encode("ascii", "ignore").decode().lower().strip()


def _e_disponivel(situacao):
    return _sem_acento(situacao).startswith("vago")


def gravar(catalogo):
    """Upsert por codigo — nunca apaga: imovel que saiu do catalogo tem que ficar.

    Alem do upsert, registra em `imovel_situacao_evento` toda TRANSICAO de situacao. E
    dai que sai a "saida de estoque" do painel do diretor: a API nao tem endpoint de
    movimentacao, entao a mudanca so existe se a gente comparar duas varreduras.

    Dois tipos de mudanca:
      1. o imovel aparece na varredura com situacao diferente da gravada;
      2. o imovel estava disponivel e SUMIU da varredura -> virou `Desativado` (situacao
         6, 9.312 imoveis: caro demais p/ baixar todo dia so p/ confirmar o obvio).

    Primeira execucao e BASELINE: a tabela de eventos vazia significa que as diferencas
    acumuladas nao sao do dia (hoje sao ~198 imoveis marcados disponiveis que ja sairam
    ha meses). Reconcilia calado e comeca a contar dali.
    """
    session = SessionLocal()
    hoje = date.today()
    try:
        baseline = session.query(ImovelSituacaoEvento.id).first() is None
        existentes = {row.codigo: row for row in session.query(ImovelArea).all()}
        novos = atualizados = 0
        eventos = []

        def _anotar(codigo, antes, depois):
            if _sem_acento(antes) == _sem_acento(depois):
                return
            eventos.append({"codigo": codigo, "antes": antes, "depois": depois})
            if not baseline:
                session.add(ImovelSituacaoEvento(
                    codigo=codigo, situacao_anterior=antes, situacao_nova=depois, detectado_em=hoje,
                ))

        for codigo, dados in catalogo.items():
            registro = existentes.get(codigo)
            if registro is None:
                session.add(ImovelArea(codigo=codigo, origem="imoview", **dados))
                novos += 1
                continue
            anterior = registro.situacao
            for campo, valor in dados.items():
                setattr(registro, campo, valor)
            atualizados += 1
            _anotar(codigo, anterior, dados.get("situacao"))

        # Sumiu da varredura estando disponivel = saiu do ar (desativado).
        for codigo, registro in existentes.items():
            if codigo in catalogo or not _e_disponivel(registro.situacao):
                continue
            _anotar(codigo, registro.situacao, DESATIVADO)
            registro.situacao = DESATIVADO

        session.commit()
        return novos, atualizados, eventos, baseline
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


if __name__ == "__main__":
    agora = datetime.now().isoformat(timespec="seconds")
    try:
        catalogo = coletar()
        novos, atualizados, eventos, baseline = gravar(catalogo)
        saidas = [e for e in eventos if _e_disponivel(e["antes"]) and not _e_disponivel(e["depois"])]
        print(f"[{agora}] areas imoview: catalogo={len(catalogo)} novos={novos} "
              f"atualizados={atualizados} mudancas={len(eventos)} saidas={len(saidas)}"
              + (" [BASELINE: eventos NAO gravados]" if baseline else ""))
    except Exception as e:
        print(f"[{agora}] sync de areas FALHOU: {e}", file=sys.stderr)
        sys.exit(1)
