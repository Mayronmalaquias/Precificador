"""Sincronizacao do Contact2Sale para `leads_c2s`.

Por que existe: a tela lia a API ao vivo a cada consulta filtrada. Como a API do C2S nao
filtra por equipe, portal nem motivo, qualquer recorte varria o periodo inteiro a 10
requisicoes por minuto — minutos de espera por clique. Aqui a varredura acontece uma vez
por hora, fora do caminho do usuario, e a tela le do banco.

**Lead ja importado muda.** Situacao, etapa do funil, arquivamento e motivo do
arquivamento sao decididos depois que o lead entrou. Por isso o sync e UPSERT por
`id_c2s` (a chave estavel da API) e nao insercao com dedupe — o importador antigo, que so
inseria e pulava duplicado, congelava o lead no estado do dia em que chegou.

Duas janelas, e a diferenca entre elas importa:

  * `updated` (padrao do cron): pega quem MUDOU desde a ultima passada. E barato e e o
    unico jeito de ver mudanca de situacao em lead antigo.
  * `created`: pega quem ENTROU numa janela. Serve para a carga inicial, varrida por
    pedacos.
"""
from __future__ import annotations

import logging
import os
from datetime import date, datetime, timedelta
from typing import Any, Dict, List, Optional

from sqlalchemy import func
from sqlalchemy.dialects.postgresql import insert as pg_insert

from app.database import SessionLocal
from app.models.estoque_legado import LeadLegado
from app.models.lead_c2s import LeadC2S
from app.services import lead_c2s_service as c2s

logger = logging.getLogger(__name__)

# Teto de paginas por execucao. A 10 req/min, 1200 paginas sao ~2h — o suficiente para a
# carga inicial inteira (52 mil leads / 50 por pagina) sem virar processo eterno se a API
# passar a devolver paginacao infinita.
MAX_PAGINAS = 1200

# Margem para tras na janela incremental. O `updated_at` do C2S e do lado deles e o cron
# roda no relogio da VM; sem folga, um lead alterado nos segundos entre uma passada e
# outra cairia no vao e ficaria desatualizado ate mudar de novo.
MARGEM_MINUTOS = 15

# Colunas que o sync NUNCA sobrescreve. `id_c2s` e a chave; `id_legado` e montado por
# `_ligar_legado`; o resto e o acompanhamento, que e nosso e mora aqui desde a migracao
# 20260825_acomp_c2s. O payload da API nao traz nenhuma delas — sem esta lista, o
# `ON CONFLICT DO UPDATE` gravaria NULL por cima toda hora.
CAMPOS_PRESERVADOS = frozenset({
    "id_c2s", "id_legado",
    "contato_status", "visita_agendada", "motivo_sem_visita", "proxima_acao",
    "acompanhamento_por", "acompanhamento_em",
})

CAMPOS_C2S = (
    "cliente", "telefone", "email", "fonte", "canal", "equipe", "corretor",
    "codigo_imovel", "imovel", "url", "observacao", "situacao", "situacao_alias",
    "funil", "arquivado", "motivo_arquivamento", "negocio_fechado", "valor_fechado",
    "criado_em", "atualizado_em", "ultima_atividade", "respondido_em",
)


class SyncErro(Exception):
    def __init__(self, mensagem: str, status: int = 400):
        super().__init__(mensagem)
        self.mensagem = mensagem
        self.status = status


def _dt(valor) -> Optional[datetime]:
    """ISO do C2S -> datetime naive. O banco roda em UTC (`TimeZone=UTC`)."""
    texto = str(valor or "").strip()
    if not texto:
        return None
    try:
        limpo = texto.replace("Z", "+00:00")
        convertido = datetime.fromisoformat(limpo)
        return convertido.replace(tzinfo=None) if convertido.tzinfo else convertido
    except ValueError:
        return None


def _num(valor) -> Optional[float]:
    try:
        return float(valor) if valor not in (None, "") else None
    except (TypeError, ValueError):
        return None


def _linha(item: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Traduz o dicionario de `lead_c2s_service._traduzir` para colunas."""
    id_c2s = str(item.get("id_c2s") or "").strip()
    if not id_c2s:
        return None

    criado = _dt(item.get("criado_em"))
    linha = {campo: item.get(campo) for campo in CAMPOS_C2S}
    linha.update({
        "id_c2s": id_c2s,
        "data": criado.date() if criado else None,
        "criado_em": criado,
        "atualizado_em": _dt(item.get("atualizado_em")),
        "ultima_atividade": _dt(item.get("ultima_atividade")),
        "respondido_em": _dt(item.get("respondido_em")),
        "valor_fechado": _num(item.get("valor_fechado")),
        "sincronizado_em": datetime.now(),
    })
    # Strings vazias viram NULL: com `""` os agrupamentos do resumo criam uma categoria
    # invisivel ao lado de "Nao informado".
    for campo in ("cliente", "telefone", "email", "fonte", "canal", "equipe", "corretor",
                  "codigo_imovel", "imovel", "url", "observacao", "situacao",
                  "situacao_alias", "funil", "motivo_arquivamento"):
        if isinstance(linha.get(campo), str) and not linha[campo].strip():
            linha[campo] = None
    return linha


def _gravar(session, linhas: List[Dict[str, Any]]) -> Dict[str, int]:
    """UPSERT por `id_c2s`.

    `ON CONFLICT DO UPDATE` em vez de SELECT-e-decide: a pagina traz 50 leads e o teste
    linha a linha seria 50 idas ao banco por pagina. Tambem elimina a corrida entre o
    cron e uma carga manual rodando junto.

    `CAMPOS_PRESERVADOS` fica de fora do UPDATE: sao colunas NOSSAS, que o C2S nao
    conhece e nao manda. Sobrescreve-las com o NULL do payload apagaria o elo e o
    acompanhamento do gerente a cada passada horaria.
    """
    if not linhas:
        return {"gravados": 0}

    tabela = LeadC2S.__table__
    stmt = pg_insert(tabela).values(linhas)
    atualizaveis = {
        c.name: stmt.excluded[c.name]
        for c in tabela.columns
        if c.name not in CAMPOS_PRESERVADOS
    }
    session.execute(stmt.on_conflict_do_update(index_elements=["id_c2s"], set_=atualizaveis))
    return {"gravados": len(linhas)}


def _ligar_legado(session, ids: List[str]) -> int:
    """Preenche `id_legado` dos leads recem-gravados que ainda nao tem elo.

    O C2S identifica por hash e `leads_legado` por inteiro; o unico elo e cliente +
    telefone, a mesma chave que a importacao antiga usa. E fragil (nome repetido casa
    errado), mas serve so para achar o acompanhamento — que continua morando em
    `leads_legado` e e escrito pela tela, nao por aqui.
    """
    if not ids:
        return 0
    pendentes = session.query(LeadC2S).filter(
        LeadC2S.id_c2s.in_(ids), LeadC2S.id_legado.is_(None),
        LeadC2S.cliente.isnot(None),
    ).all()
    if not pendentes:
        return 0

    nomes = {p.cliente for p in pendentes if p.cliente}
    indice: Dict[tuple, int] = {}
    for legado in session.query(LeadLegado).filter(LeadLegado.cliente.in_(nomes)).all():
        chave = (c2s._norm(legado.cliente), str(legado.telefone or "").strip())
        indice.setdefault(chave, legado.id)

    ligados = 0
    for p in pendentes:
        achado = indice.get((c2s._norm(p.cliente), str(p.telefone or "").strip()))
        if achado:
            p.id_legado = achado
            ligados += 1
    return ligados


def _ultima_atualizacao(session) -> Optional[datetime]:
    return session.query(func.max(LeadC2S.atualizado_em)).scalar()


def mais_antigo() -> Optional[date]:
    """Data de criacao do lead mais VELHO ja espelhado.

    A carga inicial anda de tras para frente (a API e ordenada por `-created_at`), entao
    este e o ponto ate onde ela chegou. Serve para retomar do lugar em vez de recomecar
    de 2020 — uma varredura de horas nao pode perder o trabalho porque a maquina caiu.
    """
    session = SessionLocal()
    try:
        return session.query(func.min(LeadC2S.data)).scalar()
    finally:
        session.close()


def sincronizar(inicio=None, fim=None, campo_data: str = "updated",
                max_paginas: int = MAX_PAGINAS) -> Dict[str, Any]:
    """Varre o C2S e espelha em `leads_c2s`.

    Sem `inicio`, a janela comeca no maior `atualizado_em` que ja esta na base, menos a
    margem — e o que torna a passada horaria barata. Base vazia cai para a carga inicial
    a partir de 2020.

    Commit por pagina: a importacao anterior guardava tudo para o fim e um timeout de
    leitura no meio descartava horas de trabalho (foi assim que junho e julho sumiram).
    """
    if not (os.getenv("CONTACT2SALE_TOKEN") or os.getenv("C2S_TOKEN")):
        raise SyncErro("Contact2Sale nao configurado (CONTACT2SALE_TOKEN ausente)", 503)
    if campo_data not in {"created", "updated"}:
        raise SyncErro("campo_data deve ser 'created' ou 'updated'")

    session = SessionLocal()
    try:
        if inicio:
            d_inicio = str(inicio)[:10]
        else:
            marca = _ultima_atualizacao(session)
            base = (marca - timedelta(minutes=MARGEM_MINUTOS)) if marca else datetime(2020, 1, 1)
            d_inicio = base.date().isoformat()
        d_fim = str(fim)[:10] if fim else (date.today() + timedelta(days=1)).isoformat()

        resumo = {
            "ok": True, "campo_data": campo_data, "inicio": d_inicio, "fim": d_fim,
            "paginas": 0, "lidos": 0, "gravados": 0, "ligados": 0, "total_c2s": None,
            "parcial": False,
        }

        for pagina in range(1, max_paginas + 1):
            try:
                bruto = c2s._pagina(campo_data, d_inicio, d_fim, pagina, usar_cache=False)
            except c2s.LeadC2SErro as e:
                # Interrompe sem perder o que ja foi gravado — as paginas anteriores ja
                # tiveram commit e a proxima passada retoma pela marca d'agua.
                resumo["parcial"] = True
                resumo["erro"] = e.mensagem
                logger.warning("Sync C2S interrompido na pagina %s: %s", pagina, e.mensagem)
                break

            dados = bruto.get("data") or []
            if resumo["total_c2s"] is None:
                resumo["total_c2s"] = bruto.get("total")
            if not dados:
                break

            linhas = [x for x in (_linha(t) for t in (c2s._traduzir(d) for d in dados) if t) if x]
            # A API pode repetir o mesmo lead dentro da resposta; `ON CONFLICT` nao
            # resolve duplicata dentro do MESMO comando, entao a ultima ocorrencia vence.
            unicas = {linha["id_c2s"]: linha for linha in linhas}

            _gravar(session, list(unicas.values()))
            session.flush()
            resumo["ligados"] += _ligar_legado(session, list(unicas))
            session.commit()

            resumo["paginas"] += 1
            resumo["lidos"] += len(dados)
            resumo["gravados"] += len(unicas)

            if len(dados) < c2s.PER_PAGE_API:
                break
        else:
            resumo["parcial"] = True

        logger.info("Sync C2S: %s", resumo)
        return resumo
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def estado() -> Dict[str, Any]:
    """Quanto a base esta atrasada em relacao ao C2S."""
    session = SessionLocal()
    try:
        total = session.query(func.count(LeadC2S.id_c2s)).scalar() or 0
        ultima = session.query(func.max(LeadC2S.sincronizado_em)).scalar()
        marca = _ultima_atualizacao(session)
        atraso = (datetime.now() - ultima).total_seconds() / 60 if ultima else None
        return {
            "ok": True,
            "total": int(total),
            "ultimo_sync": ultima.isoformat() if ultima else None,
            "lead_mais_recente": marca.isoformat() if marca else None,
            "atraso_minutos": round(atraso, 1) if atraso is not None else None,
        }
    finally:
        session.close()
