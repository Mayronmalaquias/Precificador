from datetime import date, datetime, timedelta
from decimal import Decimal, InvalidOperation
from functools import lru_cache
from pathlib import Path
import re

import pandas as pd
from sqlalchemy import and_, func, or_

from app.database import SessionLocal
from app.extensions import cache
from app.models.captacao import Captacao
from app.models.captacao_historico import CaptacaoHistorico
from app.models.captacao_snapshot import CaptacaoSnapshot
from app.models.contrato import Contrato
from app.models.dfimoveis_acesso import DfImoveisAcesso
from app.models.equipe import Equipe
from app.models.estoque_legado import LeadLegado
from app.models.fato_bases import FatoCaptacao, FatoEstoque, FatoSaida
from app.models.gerente_visita_visualizada import GerenteVisitaVisualizada
from app.models.imovel_area import ImovelArea
from app.models.imovel_situacao_evento import ImovelSituacaoEvento
from app.models.legado_diversos import CampanhaLegado
from app.models.proposta_efetiva import PropostaEfetiva
from app.models.usuarios import Usuarios
from app.models.visita import Visita, VisitaCliente


# Linha-balde do painel de equipes: agrupa as visitas do periodo que nao tem
# equipe ativa. Nao entra no dropdown de filtro (`equipes_opcoes`), so na tabela.
SEM_EQUIPE_ID = "__sem_equipe__"


def _date(value, default):
    try:
        return datetime.strptime(str(value)[:10], "%Y-%m-%d").date()
    except (TypeError, ValueError):
        return default


def _number(value):
    if value in (None, ""):
        return 0.0
    text = str(value).strip().replace("R$", "").replace(" ", "")
    if "," in text:
        text = text.replace(".", "").replace(",", ".")
    try:
        return float(Decimal(text))
    except (InvalidOperation, ValueError):
        return 0.0


def _norm_proposta(value):
    value = str(value or "").strip().lower()
    if value in {"sim", "s", "aceita", "aceito"}:
        return "sim"
    if value in {"não", "nao", "n", "recusada", "recusado"}:
        return "nao"
    if value in {"talvez", "negociação", "negociacao"}:
        return "talvez"
    return None


def _pct(current, previous):
    if not previous:
        return None
    return round((current - previous) / previous * 100, 1)


def _period_query(query, column, start, end):
    return query.filter(column >= start, column <= end)


def _team_maps(session):
    teams = session.query(Equipe).filter(Equipe.ativo.is_(True)).order_by(Equipe.nome).all()
    managers = session.query(Usuarios).filter(
        Usuarios.ativo.is_(True), func.lower(Usuarios.permissao) == "gerente"
    ).all()
    manager_by_team = {str(u.team or ""): u for u in managers}
    result = []
    for team in teams:
        manager = manager_by_team.get(team.id_equipe)
        result.append({
            "id": team.id_equipe,
            "nome": team.nome or team.id_equipe,
            "gerente": manager.nome if manager else "Sem gerente cadastrado",
            "gerente_id": manager.id_usuarios if manager else None,
        })
    return result


def _team_brokers(session, team):
    """Usuarios ativos da equipe — viram as linhas do painel quando uma equipe e escolhida.

    Inclui todo mundo do `team` (nao so permissao=corretor) pra que a soma das linhas
    bata com o total da equipe: visita lancada por gerente/assistente tambem conta.
    """
    if not team:
        return []
    rows = session.query(Usuarios).filter(
        Usuarios.ativo.is_(True), Usuarios.team == team
    ).order_by(Usuarios.nome).all()
    return [{
        "id": row.id_usuarios,
        "nome": row.nome or row.username or row.id_usuarios,
        "permissao": str(row.permissao or "").lower(),
    } for row in rows if row.id_usuarios]


def _team_user_ids(session, team):
    query = session.query(Usuarios.id_usuarios).filter(Usuarios.ativo.is_(True))
    if team:
        query = query.filter(Usuarios.team == team)
    return [row[0] for row in query.all() if row[0]]


def _visit_metrics(session, teams, start, end, selected_team=None):
    selected = [t for t in teams if not selected_team or t["id"] == selected_team]
    counts_by_team = {team["id"]: {"visitas": 0, "sim": 0, "nao": 0, "talvez": 0} for team in selected}
    # Visitas que nao caem em nenhuma equipe ativa: corretor sem `team`, `team`
    # sem equipe cadastrada, equipe inativa, ou id_corretor que nao existe mais
    # em `usuarios`. Continuam sendo visitas do periodo, entao viram uma linha
    # propria — senao o total do painel fica menor que o real e diverge da
    # Gestao de Clientes.
    sem_equipe = {"visitas": 0, "sim": 0, "nao": 0, "talvez": 0}
    proposals = {"sim": 0, "nao": 0, "talvez": 0}
    # outerjoin: nao descarta visita cujo corretor sumiu da tabela de usuarios.
    query = session.query(Visita.proposta, Usuarios.team).outerjoin(
        Usuarios, Usuarios.id_usuarios == Visita.id_corretor
    ).filter(Visita.data_visita >= start, Visita.data_visita <= end)
    if selected_team:
        query = query.filter(Usuarios.team == selected_team)
    for proposal, team_id in query.all():
        target = counts_by_team.get(team_id)
        if target is None:
            if selected_team:
                continue          # equipe filtrada: as orfas nao pertencem a ela
            target = sem_equipe
        target["visitas"] += 1
        status = _norm_proposta(proposal)
        if status:
            target[status] += 1
            proposals[status] += 1
    ids = [team["id"] for team in selected]
    clientes = _clientes_por_equipe(session, start, end, ids) if ids else {}
    leads = _leads_por_equipe(session, start, end, selected) if ids else {}
    rows = [{
        **team, **counts_by_team[team["id"]],
        "clientes": clientes.get(team["id"], 0), "leads": leads.get(team["id"], 0),
    } for team in selected]
    if not selected_team and sem_equipe["visitas"]:
        rows.append({
            "id": SEM_EQUIPE_ID,
            "nome": "Sem equipe",
            "gerente": "Visitas sem equipe ativa",
            "gerente_id": None,
            **sem_equipe,
            "clientes": 0,
            "leads": 0,
        })
    return rows, proposals


def _broker_visit_metrics(session, brokers, start, end, selected_broker=None, team_label=""):
    """Mesma forma de `_visit_metrics`, mas uma linha por corretor da equipe."""
    selected = [b for b in brokers if not selected_broker or b["id"] == selected_broker]
    counts_by_broker = {b["id"]: {"visitas": 0, "sim": 0, "nao": 0, "talvez": 0} for b in selected}
    proposals = {"sim": 0, "nao": 0, "talvez": 0}
    if counts_by_broker:
        query = session.query(Visita.proposta, Visita.id_corretor).filter(
            Visita.data_visita >= start, Visita.data_visita <= end,
            Visita.id_corretor.in_(list(counts_by_broker)),
        )
        for proposal, broker_id in query.all():
            if broker_id not in counts_by_broker:
                continue
            counts_by_broker[broker_id]["visitas"] += 1
            status = _norm_proposta(proposal)
            if status:
                counts_by_broker[broker_id][status] += 1
                proposals[status] += 1
    ids = list(counts_by_broker)
    clientes = _clientes_por_corretor(session, start, end, ids) if ids else {}
    leads = _leads_por_corretor(session, start, end, selected) if ids else {}
    rows = [{
        "id": b["id"], "nome": b["nome"], "gerente": team_label, "gerente_id": None,
        **counts_by_broker[b["id"]],
        "clientes": clientes.get(b["id"], 0), "leads": leads.get(b["id"], 0),
    } for b in selected]
    return rows, proposals


def _sales(session, start, end, selected_team, teams, broker_name=None):
    query = _period_query(session.query(Contrato), Contrato.data_contrato, start, end)
    recent_query = session.query(Contrato).filter(Contrato.data_contrato.isnot(None))
    selected = next((t for t in teams if t["id"] == selected_team), None)
    if broker_name:
        # Contrato guarda corretor por NOME (venda 1/2 e captador 1/2), nao por id.
        by_broker = or_(*[
            coluna.ilike(broker_name) for coluna in (
                Contrato.corretor_venda_1_nome, Contrato.corretor_venda_2_nome,
                Contrato.corretor_captador_1_nome, Contrato.corretor_captador_2_nome,
            )
        ])
        # Filtra so pelo corretor: o contrato dele conta mesmo se o gerente do negocio
        # for de outra equipe (venda casada entre times).
        return _sales_totals(session, query.filter(by_broker), recent_query.filter(by_broker), selected, teams)
    if selected:
        # Todos os nomes que valem como gerente da equipe (atual + histórico) — filtrar
        # só pelo gerente ativo zerava o VGV de equipes cujo contrato traz outro nome.
        nomes = _nomes_de_gerente_por_equipe(session, teams).get(selected["id"], set())
        if nomes:
            condicao = or_(*[
                coluna.ilike(nome)
                for nome in nomes
                for coluna in (Contrato.gerente_venda_nome, Contrato.gerente_captacao_nome)
            ])
            query = query.filter(condicao)
            recent_query = recent_query.filter(condicao)
    return _sales_totals(session, query, recent_query, selected, teams)


def _codigo_imovel(valor):
    """`contratos.codigo_imovel` chega como número formatado ("10.961,00") — vira "10961"."""
    texto = str(valor or "").strip()
    if not texto:
        return None
    digitos = "".join(ch for ch in texto.split(",")[0] if ch.isdigit())
    return digitos or None


def _area_por_codigo(session, codigos):
    """Metragem por código, do cache `imovel_area` (alimentado por sync_areas_imoview.py).

    Imóvel vendido some da API do Imoview, então só tem área quem foi capturado pelo
    job enquanto ainda estava no catálogo. Sem registro, a coluna fica vazia.
    """
    alvo = {c for c in codigos if c}
    if not alvo:
        return {}
    rows = session.query(ImovelArea.codigo, ImovelArea.area).filter(
        ImovelArea.codigo.in_(list(alvo)), ImovelArea.area.isnot(None)
    ).all()
    return {codigo: float(area) for codigo, area in rows if area}


def _nomes_de_gerente_por_equipe(session, teams):
    """{id_equipe: {nomes que valem como gerente daquela equipe}}.

    O contrato guarda o gerente por NOME, e o nome nem sempre é o do cadastro — o mesmo
    Marcelo aparece como "Marcelo Ribeiro" em `usuarios` e "Marcelo Souza" no contrato.
    Por isso a resolução passa por `pessoa_alias`, que é a tabela de de-para de nomes.

    Também aceita `permissao='diretor'`: há quem acumule diretor e gerente da equipe
    (José Marques, na AGEF), e filtrar só por 'gerente' deixava a equipe órfã.
    """
    from app.models.pessoa_alias import PessoaAlias

    por_equipe = {item["id"]: set() for item in teams}
    for item in teams:
        if item["gerente"] and item["gerente"] != "Sem gerente cadastrado":
            por_equipe[item["id"]].add(item["gerente"])

    # Quem responde pela equipe no cadastro — inclusive inativo e diretor acumulando.
    responsaveis = session.query(Usuarios.id_usuarios, Usuarios.nome, Usuarios.team).filter(
        func.lower(Usuarios.permissao).in_(["gerente", "diretor"]),
        Usuarios.team.isnot(None),
    ).all()
    por_usuario = {}
    for id_usuario, nome, team in responsaveis:
        if team in por_equipe:
            if nome:
                por_equipe[team].add(nome)
            por_usuario.setdefault(id_usuario, team)

    # Aliases desses usuários: é o que traz "Marcelo Souza" para o time do "Marcelo Ribeiro".
    if por_usuario:
        aliases = session.query(PessoaAlias.alias_key, PessoaAlias.id_usuarios).filter(
            PessoaAlias.id_usuarios.in_(list(por_usuario))
        ).all()
        for alias, id_usuario in aliases:
            team = por_usuario.get(id_usuario)
            if team and alias:
                por_equipe[team].add(alias)
    return por_equipe


def _equipe_por_corretor(session, teams):
    """Nome do corretor (casefold) -> equipe, p/ dizer de quem é cada contrato."""
    nome_da_equipe = {item["id"]: item["nome"] for item in teams}
    rows = session.query(Usuarios.nome, Usuarios.username, Usuarios.team).filter(
        Usuarios.ativo.is_(True)
    ).all()
    mapa = {}
    for nome, username, team in rows:
        if not team:
            continue
        for rotulo in (nome, username):
            chave = str(rotulo or "").strip().casefold()
            if chave:
                mapa.setdefault(chave, nome_da_equipe.get(team, team))
    return mapa


def _sales_totals(session, query, recent_query, selected, teams):
    """Devolve (VGV, VGC, quantidade, ultimos contratos).

    No nivel de equipe/empresa o VGV e a soma simples de `valor_negocio` — o rateio
    per-lado-cheio do ranking (que pode somar ate 2x) so vale por corretor. VGC = a
    comissao que fica com a 61 (`valor_total_61`).
    """
    rows = recent_query.order_by(Contrato.data_contrato.desc(), Contrato.created_at.desc()).limit(8).all()
    total = float(query.with_entities(func.coalesce(func.sum(Contrato.valor_negocio), 0)).scalar() or 0)
    comissao = float(query.with_entities(func.coalesce(func.sum(Contrato.valor_total_61), 0)).scalar() or 0)
    # nome do gerente (cadastro OU alias) -> nome da equipe
    rotulo_equipe = {item["id"]: item["nome"] for item in teams}
    manager_team = {
        str(nome).strip().casefold(): rotulo_equipe[team_id]
        for team_id, nomes in _nomes_de_gerente_por_equipe(session, teams).items()
        for nome in nomes
    }
    equipe_de = _equipe_por_corretor(session, teams)
    areas = _area_por_codigo(session, [_codigo_imovel(r.codigo_imovel) for r in rows])

    items = []
    for row in rows:
        corretor = row.corretor_venda_1_nome or row.corretor_captador_1_nome or "Não informado"
        gerente = row.gerente_venda_nome or row.gerente_captacao_nome or "Não informado"
        # Equipe vem do corretor da venda; o gerente do contrato é o plano B.
        equipe = (
            selected["nome"] if selected
            else equipe_de.get(str(corretor).strip().casefold())
            or manager_team.get(str(gerente).strip().casefold())
            or "Não identificada"
        )
        codigo = _codigo_imovel(row.codigo_imovel)
        valor = float(row.valor_negocio or 0)
        area = areas.get(codigo) if codigo else None
        items.append({
            "id": row.id_contrato,
            # O nome do contrato JÁ É o endereço ("SQS 307 Bloco F Apartamento 401").
            "endereco": row.contrato or " · ".join(v for v in (row.bairro, row.tipo) if v) or "Sem endereço",
            "imovel": row.contrato or " · ".join(v for v in (row.bairro, row.tipo) if v) or "Imóvel sem descrição",
            "codigo": codigo,
            "equipe": equipe,
            "corretor": corretor,
            "gerente": gerente,
            "valor": valor,
            "valor_total_61": float(row.valor_total_61 or 0),
            # Comissão efetiva: o que a 61 recebeu sobre o valor do negócio. Não usa o
            # campo `%_comissao_61` (percentual combinado), que diverge do realizado em
            # parte dos contratos — ex.: combinado 5%, efetivo 3,5%.
            "percentual_compra": round(float(row.valor_total_61) / valor * 100, 2) if valor and row.valor_total_61 else None,
            "area": area,
            "valor_m2": round(valor / area, 2) if area else None,
            "data": row.data_contrato.isoformat() if row.data_contrato else None,
        })
    return total, comissao, query.count(), items


# "Disponível" chega do Imoview como "Vago/Disponível". O prefixo é ASCII, então o
# ILIKE casa a versão acentuada da API e a sem acento do fallback local.
DISPONIVEL_LIKE = "vago%"
# Moderação é a exceção pedida na regra: o imóvel sai da vitrine mas continua sendo
# nosso, o corretor está só ajustando o anúncio. Contar como saída inflaria o número.
MODERACAO_LIKE = "%modera%"


def _escopo_por_captacao(session, query, coluna_codigo, selected_team, selected_broker):
    """Amarra uma tabela de imóveis à equipe/corretor pelo código, via `fato_captacao`.

    Nem o catálogo nem o log de situação sabem de quem é o imóvel — a única ponte é a
    captação. Efeito colateral aceito: imóvel sem captação registrada não aparece em
    visão filtrada (só no total da empresa).
    """
    if not (selected_team or selected_broker):
        return query
    dono = session.query(
        FatoCaptacao.codigo_imovel.label("codigo"), FatoCaptacao.captador1.label("captador")
    ).filter(FatoCaptacao.codigo_imovel.isnot(None)).distinct().subquery()
    query = query.join(dono, dono.c.codigo == coluna_codigo)
    if selected_broker:
        return query.filter(dono.c.captador == selected_broker)
    return query.join(Usuarios, Usuarios.id_usuarios == dono.c.captador).filter(
        Usuarios.team == selected_team
    )


def _estoque_semanal(session, start, end, selected_team, selected_broker=None):
    """Captações, saídas e estoque — as três leituras do movimento de imóveis.

    Definições (fechadas com a diretoria em 12/08/2026):

    - **Estoque** = imóveis com situação *Vago/Disponível* AGORA, do catálogo
      `imovel_area`. É um saldo, não um acumulado: não tem recorte de período.
    - **Captações** = imóveis registrados no sistema dentro do período
      (`fato_captacao.data_entrada`).
    - **Saídas** = imóveis que *deixaram* de estar disponíveis no período — vendido,
      desativado, em reforma. **Em moderação não conta**, o imóvel continua sendo nosso.

    Saída é uma transição, e a API do Imoview não tem endpoint de movimentação: quem
    detecta é o `sync_areas_imoview.py`, comparando varreduras e gravando em
    `imovel_situacao_evento`. Antes da primeira varredura não há log — para períodos
    anteriores a ele, cai na planilha semanal (`fato_saida`), sinalizado em
    `saidas_fonte`.
    """
    def _escopo(query, tabela, usa_join=True):
        if selected_broker:
            return query.filter(or_(
                tabela.captador1 == selected_broker,
                tabela.captador2 == selected_broker,
                tabela.captador3 == selected_broker,
            ))
        if selected_team and usa_join:
            return query.join(Usuarios, Usuarios.id_usuarios == tabela.captador1).filter(
                Usuarios.team == selected_team
            )
        return query

    entradas = _escopo(
        session.query(func.count(FatoCaptacao.id)).filter(
            FatoCaptacao.data_entrada >= start, FatoCaptacao.data_entrada <= end
        ), FatoCaptacao
    ).scalar() or 0

    # ── Saídas: log de transição de situação, com a planilha cobrindo o passado ──
    # As duas fontes são separadas por DATA, nunca sobrepostas: até a véspera do
    # primeiro evento vale a planilha semanal; dali em diante, o log. Um período que
    # cruza a virada soma os dois pedaços — senão o mês da virada apareceria vazio.
    primeiro_evento = session.query(func.min(ImovelSituacaoEvento.detectado_em)).scalar()
    corte = primeiro_evento if primeiro_evento else None
    saidas = 0
    fontes = []

    if corte is None or start < corte:
        fim_planilha = min(end, corte - timedelta(days=1)) if corte else end
        if fim_planilha >= start:
            planilha_query = session.query(func.count(func.distinct(FatoSaida.id))).filter(
                FatoSaida.data_saida >= start, FatoSaida.data_saida <= fim_planilha
            )
            parcial = _escopo_por_captacao(
                session, planilha_query, FatoSaida.codigo_imovel, selected_team, selected_broker
            ).scalar() or 0
            saidas += int(parcial)
            if parcial or corte is None:
                fontes.append("planilha")

    if corte and end >= corte:
        log_query = session.query(func.count(func.distinct(ImovelSituacaoEvento.codigo))).filter(
            ImovelSituacaoEvento.detectado_em >= max(start, corte),
            ImovelSituacaoEvento.detectado_em <= end,
            ImovelSituacaoEvento.situacao_anterior.ilike(DISPONIVEL_LIKE),
            ~ImovelSituacaoEvento.situacao_nova.ilike(DISPONIVEL_LIKE),
            ~ImovelSituacaoEvento.situacao_nova.ilike(MODERACAO_LIKE),
        )
        parcial = _escopo_por_captacao(
            session, log_query, ImovelSituacaoEvento.codigo, selected_team, selected_broker
        ).scalar() or 0
        saidas += int(parcial)
        fontes.append("situacao")

    saidas_fonte = "+".join(fontes) if fontes else "planilha"

    # ── Estoque: quantos estão disponíveis agora ────────────────────────────────
    estoque_query = session.query(func.count(func.distinct(ImovelArea.codigo))).filter(
        ImovelArea.situacao.ilike(DISPONIVEL_LIKE)
    )
    estoque = _escopo_por_captacao(
        session, estoque_query, ImovelArea.codigo, selected_team, selected_broker
    ).scalar() or 0
    data_catalogo = session.query(func.max(ImovelArea.atualizado_em)).scalar()

    return {
        "entradas": int(entradas),
        "saidas": int(saidas),
        "estoque": int(estoque),
        "estoque_fonte": "catalogo",
        "saidas_fonte": saidas_fonte,
        "data_estoque": data_catalogo.date().isoformat() if data_catalogo else None,
        "saldo": int(entradas) - int(saidas),
    }


def _captation(session, start, end, selected_team, selected_broker=None):
    # Só carteira de corretor ativo — ver `_somente_corretor_ativo`.
    base = _somente_corretor_ativo(session.query(Captacao))
    if selected_broker:
        base = base.filter(Captacao.id_corretor == selected_broker)
    elif selected_team:
        base = base.filter(Captacao.team == selected_team)
    inicio = datetime.combine(start, datetime.min.time())
    fim = datetime.combine(end, datetime.max.time())

    # ENTRARAM no período: captações criadas no intervalo. O contador antigo usava
    # `updated_at`, que responde "foi mexida no período" — imóvel de meses atrás editado
    # hoje contava como novo, e imóvel criado no período sem edição posterior sumia.
    # Nome distinto do `entraram` do laço de etapas abaixo — reaproveitar o nome fazia
    # o card herdar o número da última etapa.
    entraram_periodo = base.filter(Captacao.created_at >= inicio, Captacao.created_at <= fim).count()

    # CAPTADOS no período: pelo evento de captação no histórico, não por `updated_at`.
    # `captou_imovel` sozinho responde "já foi captado alguma vez", sem data.
    ids = [row[0] for row in base.with_entities(Captacao.id).all()]
    captados = 0
    if ids:
        data_evento = func.coalesce(CaptacaoHistorico.data_acao, func.date(CaptacaoHistorico.created_at))
        captados = session.query(func.count(func.distinct(CaptacaoHistorico.captacao_id))).filter(
            CaptacaoHistorico.captacao_id.in_(ids), CaptacaoHistorico.tipo == "captado",
            data_evento >= start, data_evento <= end,
        ).scalar() or 0

    # EM ANDAMENTO hoje: mesma régua da tela da Jornada — nem fechada, nem captada.
    # É foto do momento, não depende do período escolhido.
    em_andamento = base.filter(Captacao.status.notin_(["fechado", "captado"])).count()
    encerradas = base.filter(Captacao.status == "fechado").filter(
        Captacao.data_fechamento >= start, Captacao.data_fechamento <= end
    ).count()

    # Quem esteve na etapa em ALGUM dia do periodo (inclui quem ja estava antes de
    # comecar). Vem do snapshot diario, que guarda a etapa vigente de cada dia.
    #
    # Encerradas ficam de fora: `fechar_captacao` marca status='fechado' mas o snapshot
    # continua gravando a captacao todo dia, com a ultima etapa. Sem este filtro, imovel
    # desistido meses atras seguia contando como "no periodo" (140 de 662 em Prospeccao,
    # agosto/2026). Quem fechou NO MEIO do periodo continua contando, porque os dias
    # anteriores ao fechamento ainda estao como ativo/exclusividade/captado.
    presentes = {}
    if ids:
        snap = session.query(
            CaptacaoSnapshot.etapa_atual, func.count(func.distinct(CaptacaoSnapshot.captacao_id))
        ).filter(
            CaptacaoSnapshot.captacao_id.in_(ids),
            CaptacaoSnapshot.data_snapshot >= start,
            CaptacaoSnapshot.data_snapshot <= end,
            or_(CaptacaoSnapshot.status.is_(None), CaptacaoSnapshot.status != "fechado"),
        ).group_by(CaptacaoSnapshot.etapa_atual).all()
        presentes = {etapa: int(total) for etapa, total in snap if etapa}

    # Como cada etapa terminou. Se o período alcança hoje, o "fim" é a Jornada AO VIVO
    # (`captacao.etapa_atual`) — o snapshot de hoje só é gravado à noite pelo cron, e
    # mostrar a foto de ontem como "atual" esconderia o que o gerente mexeu hoje.
    hoje = date.today()
    periodo_corrente = end >= hoje
    no_fim = {}
    data_fim = None
    if periodo_corrente:
        data_fim = hoje
        vivo = base.filter(Captacao.status != "fechado").with_entities(
            Captacao.etapa_atual, func.count(Captacao.id)
        ).group_by(Captacao.etapa_atual).all()
        no_fim = {etapa: int(total) for etapa, total in vivo if etapa}
    elif ids:
        data_fim = session.query(func.max(CaptacaoSnapshot.data_snapshot)).filter(
            CaptacaoSnapshot.captacao_id.in_(ids), CaptacaoSnapshot.data_snapshot <= end
        ).scalar()
        if data_fim:
            fim_rows = session.query(
                CaptacaoSnapshot.etapa_atual, func.count(func.distinct(CaptacaoSnapshot.captacao_id))
            ).filter(
                CaptacaoSnapshot.captacao_id.in_(ids),
                CaptacaoSnapshot.data_snapshot == data_fim,
                or_(CaptacaoSnapshot.status.is_(None), CaptacaoSnapshot.status != "fechado"),
            ).group_by(CaptacaoSnapshot.etapa_atual).all()
            no_fim = {etapa: int(total) for etapa, total in fim_rows if etapa}

    stages = []
    for key, label in (("prospeccao", "Prospecção"), ("interacao", "Interação"), ("apresentacao", "Apresentação"), ("captacao", "Captação")):
        entraram = 0
        if ids:
            movement_date = func.coalesce(CaptacaoHistorico.data_acao, func.date(CaptacaoHistorico.created_at))
            entraram = session.query(
                func.count(func.distinct(CaptacaoHistorico.captacao_id))
            ).filter(
                CaptacaoHistorico.captacao_id.in_(ids), CaptacaoHistorico.tipo == "avanco",
                CaptacaoHistorico.etapa == key, movement_date >= start,
                movement_date <= end,
            ).scalar() or 0
        # Se o snapshot tiver buraco (cron parado), nunca deixa o total menor que
        # quem comprovadamente entrou.
        no_periodo = max(int(presentes.get(key, 0)), int(entraram))
        stages.append({
            "etapa": key, "label": label,
            "entraram": int(entraram),
            "no_periodo": no_periodo,
            "ja_estavam": max(no_periodo - int(entraram), 0),
            "no_fim": int(no_fim.get(key, 0)),
            "total": int(entraram),  # compat com quem já lia `total`
        })
    return {
        "entraram": int(entraram_periodo),
        "captados": int(captados),
        "em_andamento": int(em_andamento),
        "encerradas": int(encerradas),
        # `trabalhados` mantido p/ compatibilidade de quem já lia a chave antiga.
        "trabalhados": int(entraram_periodo),
        "etapas": stages,
        "data_fim": data_fim.isoformat() if data_fim else None,
        # `ao_vivo` diz à tela se o último número é a Jornada de agora ou uma foto.
        "ao_vivo": bool(periodo_corrente),
    }


def _clientes_por_equipe(session, start, end, ids_equipes):
    """Clientes distintos atendidos em visitas, por equipe do corretor da visita."""
    rows = session.query(
        Usuarios.team, func.count(func.distinct(VisitaCliente.id_cliente))
    ).select_from(VisitaCliente).join(
        Visita, Visita.id_visita == VisitaCliente.id_visita
    ).join(
        Usuarios, Usuarios.id_usuarios == Visita.id_corretor
    ).filter(
        Visita.data_visita >= start, Visita.data_visita <= end,
        Usuarios.team.in_(list(ids_equipes)),
    ).group_by(Usuarios.team).all()
    return {team: int(total) for team, total in rows if team}


def _leads_por_equipe(session, start, end, teams):
    """Leads do período por equipe. `leads_legado.equipe` grava o id (G610xx), mas
    parte da base legada gravou o nome — casa os dois no mesmo balde."""
    por_chave = {}
    rows = _period_query(
        session.query(LeadLegado.equipe, func.count(LeadLegado.id)), LeadLegado.data, start, end
    ).group_by(LeadLegado.equipe).all()
    for equipe, total in rows:
        por_chave[str(equipe or "").strip().casefold()] = por_chave.get(str(equipe or "").strip().casefold(), 0) + int(total)
    saida = {}
    for item in teams:
        saida[item["id"]] = (
            por_chave.get(str(item["id"]).casefold(), 0)
            + por_chave.get(str(item["nome"]).casefold(), 0)
        )
    return saida


def _clientes_por_corretor(session, start, end, ids_corretores):
    rows = session.query(
        Visita.id_corretor, func.count(func.distinct(VisitaCliente.id_cliente))
    ).select_from(VisitaCliente).join(
        Visita, Visita.id_visita == VisitaCliente.id_visita
    ).filter(
        Visita.data_visita >= start, Visita.data_visita <= end,
        Visita.id_corretor.in_(list(ids_corretores)),
    ).group_by(Visita.id_corretor).all()
    return {corretor: int(total) for corretor, total in rows if corretor}


def _leads_por_corretor(session, start, end, brokers):
    """`atendimento` guarda o id do corretor, mas às vezes o nome — soma os dois."""
    rows = _period_query(
        session.query(LeadLegado.atendimento, func.count(LeadLegado.id)), LeadLegado.data, start, end
    ).group_by(LeadLegado.atendimento).all()
    por_chave = {}
    for atendimento, total in rows:
        chave = str(atendimento or "").strip().casefold()
        por_chave[chave] = por_chave.get(chave, 0) + int(total)
    return {
        b["id"]: por_chave.get(str(b["id"]).casefold(), 0) + por_chave.get(str(b["nome"]).casefold(), 0)
        for b in brokers
    }


def _clientes(session, start, end, selected_team, selected_broker=None):
    """Clientes distintos atendidos em visitas no periodo.

    `clientes_visita` nao tem data, entao 'cliente do periodo' = cliente ligado a uma
    visita do periodo (via `visita_cliente`, que aceita mais de um cliente por visita).
    """
    query = session.query(func.count(func.distinct(VisitaCliente.id_cliente))).join(
        Visita, Visita.id_visita == VisitaCliente.id_visita
    ).filter(Visita.data_visita >= start, Visita.data_visita <= end)
    if selected_broker:
        query = query.filter(Visita.id_corretor == selected_broker)
    elif selected_team:
        query = query.join(Usuarios, Usuarios.id_usuarios == Visita.id_corretor).filter(
            Usuarios.team == selected_team
        )
    return int(query.scalar() or 0)


def _propostas_efetivas(session, start, end, selected_team, selected_broker=None):
    """Propostas efetivas lancadas no periodo (a tela Propostas Efetivas).

    Nao tem relacao com `Visita.proposta` (SIM/NAO/TALVEZ). A proposta pertence ao
    gerente, entao filtrar por corretor so acha algo se o corretor for o gerente.
    """
    # TODAS as situações entram (em análise, contraproposta, aceita, recusada,
    # cancelada) — o card é volume de proposta, não de fechamento.
    #
    # Período pela data de LANÇAMENTO (`created_at`), não por `data_proposta`: esta
    # última é digitada e vem retroativa ou futura com frequência (em 10/08/2026, 5 das
    # 6 propostas lançadas no mês tinham data de julho ou 13/08), o que fazia o card
    # mostrar 1 onde havia 6.
    inicio = datetime.combine(start, datetime.min.time())
    fim = datetime.combine(end, datetime.max.time())
    query = session.query(func.count(PropostaEfetiva.id)).filter(
        PropostaEfetiva.ativo.is_(True),
        PropostaEfetiva.created_at >= inicio,
        PropostaEfetiva.created_at <= fim,
    )
    if selected_broker:
        query = query.filter(or_(
            PropostaEfetiva.id_corretor == selected_broker,
            PropostaEfetiva.id_gerente == selected_broker,
        ))
    elif selected_team:
        query = query.filter(PropostaEfetiva.team == selected_team)
    return int(query.scalar() or 0)


def _leads(session, start, end, selected_team, teams, selected_broker=None, broker_name=None):
    query = _period_query(session.query(LeadLegado), LeadLegado.data, start, end)
    if selected_broker:
        # `atendimento` guarda o id do corretor (ex.: C61095), mas parte da base legada
        # gravou o nome — casa os dois, senao o corretor perde os leads antigos.
        condicoes = [LeadLegado.atendimento == selected_broker]
        if broker_name:
            condicoes.append(LeadLegado.atendimento.ilike(broker_name))
        return query.filter(or_(*condicoes)).count()
    selected = next((t for t in teams if t["id"] == selected_team), None)
    if selected:
        query = query.filter(or_(LeadLegado.equipe.ilike(selected["id"]), LeadLegado.equipe.ilike(selected["nome"])))
    return query.count()


@lru_cache(maxsize=4)
def _read_dfimoveis_report(file_path, modified_ns):
    del modified_ns  # faz parte da chave e invalida o cache quando o arquivo muda
    df = pd.read_excel(file_path, sheet_name="Relatório")
    return df


def _faixa_metragem(area):
    """0-100, 100-200, … 1000+ — rótulo e chave de ordenação."""
    if area is None or area <= 0:
        return None, 9999
    limite = min(int(area // 100) * 100, 1000)
    if limite >= 1000:
        return "1000+ m²", 1000
    return f"{limite}–{limite + 100} m²", limite


def _faixa_valor(valor):
    """200k-400k, 400k-600k, … 10M+. Abaixo de 200k entra numa faixa própria."""
    if valor is None or valor <= 0:
        return None, 999999999
    valor = float(valor)
    if valor < 200_000:
        return "até R$ 200 mil", 0
    if valor >= 10_000_000:
        return "R$ 10 mi+", 10_000_000
    limite = int(valor // 200_000) * 200_000
    return f"R$ {limite // 1000} mil – {(limite + 200_000) // 1000} mil", limite


def _perfis_midia(session, data_relatorio):
    """Perfis de conversão da mídia em 4 dimensões.

    Bairro sai do próprio relatório do DFImóveis. Quartos, metragem e valor **não
    existem no arquivo** — vêm de `imovel_area` (cache do catálogo Imoview), casando
    pelo código do imóvel. Imóvel sem correspondência fica de fora dessas três.
    """
    linhas = session.query(
        DfImoveisAcesso.codigo_busca,
        DfImoveisAcesso.bairro,
        DfImoveisAcesso.impressao,
        DfImoveisAcesso.acesso,
        (DfImoveisAcesso.emails + DfImoveisAcesso.telefone + DfImoveisAcesso.whatsapp_emails_gerados
         + DfImoveisAcesso.visita + DfImoveisAcesso.proposta).label("leads"),
        ImovelArea.quartos,
        ImovelArea.area,
        ImovelArea.valor,
    ).outerjoin(
        ImovelArea, ImovelArea.codigo == DfImoveisAcesso.codigo_busca
    ).filter(DfImoveisAcesso.data_relatorio == data_relatorio).all()

    dimensoes = {"bairro": {}, "quartos": {}, "metragem": {}, "valor": {}}

    def _somar(dimensao, chave, ordem, impressao, acesso, leads):
        if chave is None:
            return
        alvo = dimensoes[dimensao].setdefault(
            chave, {"imoveis": 0, "impressoes": 0, "acessos": 0, "leads": 0, "ordem": ordem}
        )
        alvo["imoveis"] += 1
        alvo["impressoes"] += int(impressao or 0)
        alvo["acessos"] += int(acesso or 0)
        alvo["leads"] += int(leads or 0)

    for _codigo, bairro, impressao, acesso, leads, quartos, area, valor in linhas:
        _somar("bairro", bairro or "Não identificado", 0, impressao, acesso, leads)
        if quartos:
            _somar("quartos", f"{quartos} quarto{'s' if quartos > 1 else ''}", quartos, impressao, acesso, leads)
        rotulo_area, ordem_area = _faixa_metragem(float(area) if area else None)
        _somar("metragem", rotulo_area, ordem_area, impressao, acesso, leads)
        rotulo_valor, ordem_valor = _faixa_valor(valor)
        _somar("valor", rotulo_valor, ordem_valor, impressao, acesso, leads)

    def _formatar(dimensao, ordenar_por_ordem):
        itens = [{
            "id": f"{dimensao}-{chave}", "perfil": chave, "bairro": chave,
            "detalhe": f"{dados['imoveis']} imóveis no relatório",
            "impressoes": dados["impressoes"], "acessos": dados["acessos"],
            "leads": dados["leads"], "delta": None,
            "conversao": round(dados["leads"] / dados["acessos"] * 100, 2) if dados["acessos"] else None,
            "_ordem": dados["ordem"],
        } for chave, dados in dimensoes[dimensao].items()]
        if ordenar_por_ordem:
            itens.sort(key=lambda i: i["_ordem"])
        else:
            itens.sort(key=lambda i: -i["acessos"])
            itens = itens[:12]
        for item in itens:
            item.pop("_ordem", None)
        return itens

    return {
        "bairro": _formatar("bairro", False),
        "quartos": _formatar("quartos", True),
        "metragem": _formatar("metragem", True),
        "valor": _formatar("valor", True),
    }


def _media(session, start, end):
    latest_date = session.query(func.max(DfImoveisAcesso.data_relatorio)).scalar()
    if latest_date:
        base = session.query(DfImoveisAcesso).filter(DfImoveisAcesso.data_relatorio == latest_date)
        rows = base.all()
        grouped = session.query(
            DfImoveisAcesso.bairro,
            func.count(func.distinct(DfImoveisAcesso.codigo_busca)),
            func.coalesce(func.sum(DfImoveisAcesso.impressao), 0),
            func.coalesce(func.sum(DfImoveisAcesso.acesso), 0),
            func.coalesce(func.sum(
                DfImoveisAcesso.emails + DfImoveisAcesso.telefone +
                DfImoveisAcesso.whatsapp_emails_gerados + DfImoveisAcesso.visita +
                DfImoveisAcesso.proposta
            ), 0),
        ).filter(DfImoveisAcesso.data_relatorio == latest_date).group_by(
            DfImoveisAcesso.bairro
        ).order_by(func.sum(DfImoveisAcesso.acesso).desc()).limit(12).all()
        profiles = [{
            "id": bairro or "nao-identificado", "bairro": bairro or "Não identificado",
            "perfil": bairro or "Não identificado", "detalhe": f"{int(imoveis)} imóveis no relatório",
            "impressoes": int(impressions), "acessos": int(accesses), "leads": int(leads), "delta": None,
        } for bairro, imoveis, impressions, accesses, leads in grouped]
        # Perfis nas 4 dimensões (bairro, quartos, metragem, valor). `perfis` continua
        # sendo o de bairro p/ não quebrar quem já lia a chave antiga.
        perfis_por_dimensao = _perfis_midia(session, latest_date)
        first = rows[0]
        leads_total = sum(row.emails + row.telefone + row.whatsapp_emails_gerados + row.visita + row.proposta for row in rows)
        return {
            "disponivel": True, "fonte": "banco", "arquivo": first.arquivo_origem,
            "data_relatorio": latest_date.isoformat(), "impressoes": sum(row.impressao for row in rows),
            "acessos": sum(row.acesso for row in rows), "leads": leads_total,
            "imoveis": len({row.codigo_busca for row in rows}), "perfis": profiles,
            "perfis_por_dimensao": perfis_por_dimensao,
            "mensagem": "Quartos, metragem e valor não vêm do DFImóveis — são cruzados por código com o catálogo do Imoview.",
        }

    report_dir = Path(__file__).resolve().parents[3] / "legado"
    files = sorted(report_dir.glob("Relatorio-de-acesso-imoveis-*.xlsx"), key=lambda path: path.stat().st_mtime, reverse=True)
    if files:
        df = _read_dfimoveis_report(str(files[0]), files[0].stat().st_mtime_ns).copy()
        required = {"Endereco", "CodigoDeBusca", "Acesso", "Impressao"}
        if not required.issubset(df.columns):
            raise ValueError("Planilha DFImóveis sem as colunas obrigatórias: Endereco, CodigoDeBusca, Acesso e Impressao")
        numeric = ["Acesso", "Impressao", "Emails", "Telefone", "WhatsAppEmailsGerados", "Visita", "Proposta"]
        for column in numeric:
            if column not in df.columns:
                df[column] = 0
            df[column] = pd.to_numeric(df[column], errors="coerce").fillna(0)
        df["Leads"] = df[["Emails", "Telefone", "WhatsAppEmailsGerados", "Visita", "Proposta"]].sum(axis=1)

        def bairro(endereco):
            parts = [part.strip() for part in str(endereco or "").split("-") if part.strip()]
            if len(parts) >= 3 and parts[1].upper() == "BRASILIA":
                return parts[2]
            return parts[1] if len(parts) >= 2 else "Não identificado"

        df["Bairro"] = df["Endereco"].map(bairro)
        profiles = []
        grouped = df.groupby("Bairro", dropna=False).agg(
            impressoes=("Impressao", "sum"), acessos=("Acesso", "sum"), leads=("Leads", "sum"), imoveis=("CodigoDeBusca", "nunique")
        ).sort_values("acessos", ascending=False).head(12)
        for index, row in grouped.iterrows():
            profiles.append({
                "id": str(index), "bairro": str(index).title(), "perfil": str(index).title(),
                "detalhe": f"{int(row['imoveis'])} imóveis no relatório",
                "impressoes": int(row["impressoes"]), "acessos": int(row["acessos"]),
                "leads": int(row["leads"]), "delta": None,
            })
        match = re.search(r"(\d{2})_(\d{2})_(\d{4})", files[0].name)
        report_date = f"{match.group(3)}-{match.group(2)}-{match.group(1)}" if match else None
        return {
            "disponivel": True, "arquivo": files[0].name, "data_relatorio": report_date,
            "impressoes": int(df["Impressao"].sum()), "acessos": int(df["Acesso"].sum()),
            "leads": int(df["Leads"].sum()), "imoveis": int(df["CodigoDeBusca"].nunique()),
            "perfis": profiles,
            "mensagem": "Tipologia, faixa de valor e metragem não existem no arquivo exportado pelo DFImóveis.",
        }

    rows = _period_query(session.query(CampanhaLegado), CampanhaLegado.dia, start, end).all()
    return {
        "disponivel": bool(rows),
        "impressoes": int(sum(_number(row.impressoes) for row in rows)),
        "alcance": int(sum(_number(row.alcance) for row in rows)),
        "leads": int(sum(_number(row.resultados) for row in rows)),
        "acessos": None,
        "perfis": [],
        "mensagem": "Nenhum relatório de acesso do DFImóveis foi encontrado. Exibindo somente campanhas importadas.",
    }


DIAS_SEM_ASSINATURA = 30
# Contrato anterior a isso não é backlog, é base histórica incompleta: os de 2015-2024
# simplesmente não têm data de assinatura preenchida.
JANELA_ATRASO_DIAS = 365


ROTULO_ETAPA = {
    "escolha": "Escolha",
    "prospeccao": "Prospecção",
    "interacao": "Interação",
    "apresentacao": "Apresentação",
    "captacao": "Captação",
}


def _somente_corretor_ativo(query):
    """Descarta captação de corretor desativado (ou que sumiu de `usuarios`).

    Carteira de quem saiu da empresa não é pendência de ninguém — some do painel até a
    reatribuição acontecer. São 48 imóveis em 10/08/2026.
    """
    return query.join(Usuarios, Usuarios.id_usuarios == Captacao.id_corretor).filter(
        Usuarios.ativo.is_(True)
    )


def _imoveis_parados(session, today, selected_team, selected_broker=None):
    """Imóveis da Jornada parados, pelo tempo na ETAPA ATUAL.

    O relógio é `data_entrada_etapa` — avançar de etapa zera a contagem, então o número
    mede estagnação real, não idade do imóvel.

    Fora da conta: encerradas, captadas e quem já está na etapa **Captação** (fim da
    jornada — ficar lá não é estar parado).

    Faixas: 7–14 (azul), 14–30 (amarelo), 30+ (vermelho).
    """
    query = _somente_corretor_ativo(session.query(Captacao)).filter(
        Captacao.status.notin_(["fechado", "captado"]),
        Captacao.etapa_atual != "captacao",
    )
    if selected_broker:
        query = query.filter(Captacao.id_corretor == selected_broker)
    elif selected_team:
        query = query.filter(Captacao.team == selected_team)

    faixas = {"7_14": 0, "14_30": 0, "30_mais": 0}
    itens = []
    for row in query.all():
        referencia = row.data_entrada_etapa or row.created_at
        if not referencia:
            continue
        dias = (today - referencia.date()).days
        if dias < 7:
            continue
        if dias < 14:
            faixa, nivel = "7_14", "atencao_leve"
        elif dias < 30:
            faixa, nivel = "14_30", "atencao"
        else:
            faixa, nivel = "30_mais", "critico"
        faixas[faixa] += 1
        itens.append({
            "id": row.id,
            "endereco": row.endereco or "Sem endereço",
            "bairro": row.bairro,
            "etapa": row.etapa_atual,
            "etapa_label": ROTULO_ETAPA.get(row.etapa_atual, row.etapa_atual),
            "responsavel": row.nome_corretor or row.team or "Não informado",
            "dias": dias,
            "faixa": faixa,
            "nivel": nivel,
        })

    itens.sort(key=lambda i: -i["dias"])
    # Manda a lista COMPLETA: filtro e paginação da tela são client-side, e cortar aqui
    # faria a última página sumir. São ~700 itens pequenos (endereço, etapa, dias).
    por_etapa = {}
    for item in itens:
        por_etapa[item["etapa_label"]] = por_etapa.get(item["etapa_label"], 0) + 1
    return {
        "faixa_7_14": faixas["7_14"],
        "faixa_14_30": faixas["14_30"],
        "faixa_30_mais": faixas["30_mais"],
        "total": sum(faixas.values()),
        "por_etapa": por_etapa,
        "itens": itens,
    }


def _contratos_atrasados(session, today, selected_team, teams, broker_name=None):
    """Contratos travados no processo.

    A base não tem flag de concluído/pago — só datas previstas —, então "atraso" aqui é
    prazo vencido em dois sinais que indicam trava de verdade:
      1. prazo final da comissão (`parcelas_comissao`) já passou;
      2. contrato fechado há mais de 30 dias e ainda sem data de assinatura.
    Quitação/posse previstas vencidas foram descartadas de propósito: sem marcação de
    conclusão, praticamente todo contrato antigo cairia nelas.
    """
    query = session.query(Contrato).filter(
        Contrato.data_contrato.isnot(None),
        Contrato.data_contrato >= today - timedelta(days=JANELA_ATRASO_DIAS),
    )
    if broker_name:
        query = query.filter(or_(*[
            coluna.ilike(broker_name) for coluna in (
                Contrato.corretor_venda_1_nome, Contrato.corretor_venda_2_nome,
                Contrato.corretor_captador_1_nome, Contrato.corretor_captador_2_nome,
            )
        ]))
    elif selected_team:
        selecionada = next((t for t in teams if t["id"] == selected_team), None)
        if selecionada and selecionada["gerente"] != "Sem gerente cadastrado":
            gerente = selecionada["gerente"]
            query = query.filter(or_(
                Contrato.gerente_venda_nome.ilike(gerente),
                Contrato.gerente_captacao_nome.ilike(gerente),
            ))

    limite_assinatura = today - timedelta(days=DIAS_SEM_ASSINATURA)
    comissao_vencida = []
    sem_assinatura = []
    for row in query.all():
        prazo = _data_iso(row.parcelas_comissao)
        if prazo and prazo < today:
            comissao_vencida.append((row, (today - prazo).days, "comissao"))
        if row.data_assinatura is None and row.data_contrato <= limite_assinatura:
            sem_assinatura.append((row, (today - row.data_contrato).days, "assinatura"))

    itens = []
    for row, dias, tipo in sorted(comissao_vencida + sem_assinatura, key=lambda x: -x[1])[:20]:
        itens.append({
            "id": f"{tipo}-{row.id_contrato}",
            "id_contrato": row.id_contrato,
            "endereco": row.contrato or row.codigo_imovel or "Sem endereço",
            "motivo": "Comissão vencida" if tipo == "comissao" else "Sem assinatura",
            "dias": dias,
            "valor": float(row.valor_negocio or 0),
            "gerente": row.gerente_venda_nome or row.gerente_captacao_nome or "Não informado",
            "nivel": "critical" if dias >= 60 else "warning",
        })
    return {
        "total": len(comissao_vencida) + len(sem_assinatura),
        "comissao_vencida": len(comissao_vencida),
        "sem_assinatura": len(sem_assinatura),
        "dias_sem_assinatura": DIAS_SEM_ASSINATURA,
        "itens": itens,
    }


def _data_iso(valor):
    """`parcelas_comissao` é texto e nem sempre é data (ex.: '2026-10-18' ou vazio)."""
    texto = str(valor or "").strip()[:10]
    try:
        return datetime.strptime(texto, "%Y-%m-%d").date()
    except (TypeError, ValueError):
        return None


# Régua de follow-up das PROPOSTAS: 1 dia parado já pede ação, 2+ é crítico.
# Não vale para captação: imóvel sem atualização tem régua própria (14 dias), senão
# 97% da carteira viraria alerta e o painel deixaria de separar sinal de ruído.
DIAS_FOLLOWUP = 1
DIAS_CRITICO_ALERTA = 2
DIAS_IMOVEL_PARADO = 14
DIAS_ACAO_CRITICA = 7
# Teto da lista devolvida — antes eram 30 e o corte escondia pendência real.
MAX_ALERTAS = 300


def _nivel_alerta(dias):
    return "critical" if dias >= DIAS_CRITICO_ALERTA else "warning"


def _propostas_sem_acao(session, today, selected_team, selected_broker=None):
    """Propostas efetivas abertas paradas há >= 1 dia — vira flag de acompanhamento.

    Mesma régua da tela de Propostas (`proposta_service.DIAS_ATENCAO/DIAS_CRITICO`).
    """
    query = session.query(PropostaEfetiva).filter(
        PropostaEfetiva.ativo.is_(True),
        PropostaEfetiva.situacao.notin_(["aceita", "recusada", "cancelada"]),
    )
    if selected_broker:
        query = query.filter(or_(
            PropostaEfetiva.id_corretor == selected_broker,
            PropostaEfetiva.id_gerente == selected_broker,
        ))
    elif selected_team:
        query = query.filter(PropostaEfetiva.team == selected_team)

    agora = datetime.combine(today, datetime.max.time())
    flags = []
    for proposta in query.all():
        referencia = proposta.ultima_acao_em or proposta.updated_at or proposta.created_at
        if not referencia:
            continue
        dias = max((agora - referencia).days, 0)
        if dias < DIAS_FOLLOWUP:
            continue
        endereco = proposta.imovel_endereco or (f"Imóvel #{proposta.codigo_imovel}" if proposta.codigo_imovel else "Proposta sem endereço")
        flags.append({
            "id": f"proposta-{proposta.id}",
            "tipo": "Proposta sem ação",
            "descricao": f"{endereco} · {proposta.situacao}",
            "responsavel": proposta.corretor_nome or proposta.gerente_nome or proposta.team or "Não informado",
            "atraso": f"{dias} dia(s)",
            "dias": dias,
            "nivel": _nivel_alerta(dias),
        })
    return flags


def _alerts(session, selected_team, today, selected_broker=None):
    query = session.query(Captacao)
    if selected_broker:
        query = query.filter(Captacao.id_corretor == selected_broker)
    elif selected_team:
        query = query.filter(Captacao.team == selected_team)
    alerts = []
    for row in query.filter(Captacao.status.in_(["ativo", "exclusividade"])).all():
        due = None
        done = False
        if row.etapa_atual == "escolha": due, done = row.data_acao_sem_numero, row.acao_escolha_realizada
        elif row.etapa_atual == "interacao": due, done = row.data_proxima_acao_interacao, row.acao_interacao_realizada
        elif row.etapa_atual == "apresentacao": due, done = row.data_proxima_acao_apresentacao, row.acao_apresentacao_realizada
        elif row.etapa_atual == "captacao": due, done = row.data_proxima_acao_captacao, row.acao_captacao_realizada
        if due and due < today and not done:
            days = (today - due).days
            alerts.append({"id": f"acao-{row.id}", "tipo": "Atividade atrasada", "descricao": row.endereco, "responsavel": row.nome_corretor or row.team or "Não informado", "atraso": f"{days} dia(s)", "dias": days, "nivel": "critical" if days >= DIAS_ACAO_CRITICA else "warning"})
        updated = row.updated_at.date() if row.updated_at else row.created_at.date() if row.created_at else None
        parado = (today - updated).days if updated else 0
        if updated and parado >= DIAS_IMOVEL_PARADO:
            alerts.append({"id": f"stale-{row.id}", "tipo": "Imóvel sem atualização", "descricao": row.endereco, "responsavel": row.nome_corretor or row.team or "Não informado", "atraso": f"{parado} dia(s)", "dias": parado, "nivel": "warning"})

    review_query = session.query(GerenteVisitaVisualizada, Visita).join(Visita, Visita.id_visita == GerenteVisitaVisualizada.id_visita).filter(
        Visita.data_visita >= today - timedelta(days=30),
        or_(GerenteVisitaVisualizada.viu_anexo.is_(False), GerenteVisitaVisualizada.viu_notas.is_(False), GerenteVisitaVisualizada.add_motivo.is_(False)),
    )
    if selected_broker:
        review_query = review_query.filter(Visita.id_corretor == selected_broker)
    elif selected_team:
        review_query = review_query.filter(GerenteVisitaVisualizada.id_gerente == selected_team)
    for flags, visit in review_query.limit(MAX_ALERTAS).all():
        pending = [label for value, label in ((flags.viu_anexo, "anexo"), (flags.viu_notas, "notas"), (flags.add_motivo, "motivo")) if not value]
        dias = (today - visit.data_visita).days if visit.data_visita else 0
        alerts.append({"id": f"visita-{visit.id_visita}", "tipo": "Revisão de visita pendente", "descricao": f"Pendente: {', '.join(pending)}", "responsavel": flags.id_gerente, "atraso": f"{dias} dia(s)", "dias": dias, "nivel": "critical"})

    # Propostas paradas entram na mesma lista de flags, com a régua de 1/2 dias.
    alerts.extend(_propostas_sem_acao(session, today, selected_team, selected_broker))
    # Rodízio entre os tipos: dentro de cada tipo vem o mais atrasado primeiro, e a
    # lista alterna os tipos. Ordenar só por dias fazia "Proposta sem ação" (1-5 dias)
    # ser cortada por imóveis parados há 60 — o tipo sumia da tela.
    por_tipo = {}
    for item in alerts:
        por_tipo.setdefault(item["tipo"], []).append(item)
    for fila in por_tipo.values():
        fila.sort(key=lambda a: (0 if a["nivel"] == "critical" else 1, -a.get("dias", 0)))
    intercalados = []
    filas = list(por_tipo.values())
    while filas:
        for fila in list(filas):
            if fila:
                intercalados.append(fila.pop(0))
            else:
                filas.remove(fila)
    alerts = intercalados
    resumo = {
        "total": len(alerts),
        "criticos": sum(1 for a in alerts if a["nivel"] == "critical"),
        "followup": sum(1 for a in alerts if a["nivel"] == "warning"),
        "por_tipo": {},
        "exibindo": min(len(alerts), MAX_ALERTAS),
        "dias_followup": DIAS_FOLLOWUP,
        "dias_critico": DIAS_CRITICO_ALERTA,
    }
    for item in alerts:
        resumo["por_tipo"][item["tipo"]] = resumo["por_tipo"].get(item["tipo"], 0) + 1
    # A lista é cortada, o resumo não — senão o rodapé contaria só o que coube na tela.
    return {"itens": alerts[:MAX_ALERTAS], "resumo": resumo}


def _propostas_por_equipe(session, selected_team, selected_broker=None):
    """Por equipe: quantas propostas estão abertas e quantas estão paradas.

    "Parada" = sem ação há >= DIAS_FOLLOWUP (1 dia), mesma régua da tela de Propostas.
    """
    query = session.query(PropostaEfetiva).filter(
        PropostaEfetiva.ativo.is_(True),
        PropostaEfetiva.situacao.notin_(["aceita", "recusada", "cancelada"]),
    )
    if selected_broker:
        query = query.filter(or_(
            PropostaEfetiva.id_corretor == selected_broker,
            PropostaEfetiva.id_gerente == selected_broker,
        ))
    elif selected_team:
        query = query.filter(PropostaEfetiva.team == selected_team)

    agora = datetime.now()
    contagem = {}
    for proposta in query.all():
        chave = proposta.team or "sem-equipe"
        alvo = contagem.setdefault(chave, {"abertas": 0, "sem_acao": 0})
        alvo["abertas"] += 1
        referencia = proposta.ultima_acao_em or proposta.updated_at or proposta.created_at
        if referencia and (agora - referencia).days >= DIAS_FOLLOWUP:
            alvo["sem_acao"] += 1
    return contagem


def _visit_reviews(session, start, end, selected_team, teams, selected_broker=None):
    query = session.query(Visita, Usuarios, GerenteVisitaVisualizada).join(
        Usuarios, Usuarios.id_usuarios == Visita.id_corretor
    ).outerjoin(
        GerenteVisitaVisualizada,
        and_(
            GerenteVisitaVisualizada.id_visita == Visita.id_visita,
            GerenteVisitaVisualizada.id_gerente == Usuarios.team,
        ),
    ).filter(Visita.data_visita >= start, Visita.data_visita <= end)
    if selected_broker:
        query = query.filter(Usuarios.id_usuarios == selected_broker)
    elif selected_team:
        query = query.filter(Usuarios.team == selected_team)

    items = []
    for visit, broker, flags in query.order_by(Visita.data_visita.desc()).limit(500).all():
        viewed = flags is not None
        items.append({
            "id": visit.id_visita,
            "data": visit.data_visita.isoformat() if visit.data_visita else None,
            "imovel": visit.id_imovel or visit.endereco_externo or "Imóvel não informado",
            "corretor": broker.nome or broker.username or visit.id_corretor,
            "equipe_id": broker.team,
            "proposta": _norm_proposta(visit.proposta),
            "tem_nota": bool(visit.audiodescricao_cliente_visita or visit.link_audio),
            "tem_anexo": bool(visit.anexo_ficha_visita or visit.link_imagem),
            "viu_visita": viewed,
            "viu_nota": bool(flags.viu_notas) if flags else False,
            "viu_anexo": bool(flags.viu_anexo) if flags else False,
            "adicionou_motivo": bool(flags.add_motivo) if flags else False,
            "visualizado_em": flags.visualizado_em.isoformat() if flags and flags.visualizado_em else None,
        })

    totals = {
        "total": len(items),
        "viu_visita": sum(1 for item in items if item["viu_visita"]),
        "viu_nota": sum(1 for item in items if item["viu_nota"]),
        "viu_anexo": sum(1 for item in items if item["viu_anexo"]),
        "adicionou_motivo": sum(1 for item in items if item["adicionou_motivo"]),
    }
    team_names = {team["id"]: team for team in teams}
    grouped = {}
    for item in items:
        team_id = item["equipe_id"] or "sem-equipe"
        team_info = team_names.get(team_id, {})
        row = grouped.setdefault(team_id, {
            "equipe_id": team_id,
            "equipe": team_info.get("nome") or team_id,
            "gerente": team_info.get("gerente") or "Sem gerente cadastrado",
            "total_visitas": 0,
            "nao_viu_visita": 0,
            "notas_aplicaveis": 0,
            "nao_viu_nota": 0,
            "anexos_aplicaveis": 0,
            "nao_viu_anexo": 0,
            "motivos_aplicaveis": 0,
            "nao_adicionou_motivo": 0,
        })
        row["total_visitas"] += 1
        if not item["viu_visita"]:
            row["nao_viu_visita"] += 1
        if item["tem_nota"]:
            row["notas_aplicaveis"] += 1
            if not item["viu_nota"]:
                row["nao_viu_nota"] += 1
        if item["tem_anexo"]:
            row["anexos_aplicaveis"] += 1
            if not item["viu_anexo"]:
                row["nao_viu_anexo"] += 1
        if item["proposta"] in {"sim", "talvez"}:
            row["motivos_aplicaveis"] += 1
            if not item["adicionou_motivo"]:
                row["nao_adicionou_motivo"] += 1

    # Propostas paradas entram como mais uma coluna de pendência do gerente: mostra
    # "X de Y" (sem ação de N dias / total em aberto da equipe).
    propostas = _propostas_por_equipe(session, selected_team, selected_broker)
    team_names = {team["id"]: team for team in teams}
    for team_id, contagem in propostas.items():
        row = grouped.get(team_id)
        if row is None:
            # Equipe sem visita no período mas com proposta parada continua aparecendo.
            info = team_names.get(team_id, {})
            row = grouped.setdefault(team_id, {
                "equipe_id": team_id,
                "equipe": info.get("nome") or team_id,
                "gerente": info.get("gerente") or "Sem gerente cadastrado",
                "total_visitas": 0, "nao_viu_visita": 0,
                "notas_aplicaveis": 0, "nao_viu_nota": 0,
                "anexos_aplicaveis": 0, "nao_viu_anexo": 0,
                "motivos_aplicaveis": 0, "nao_adicionou_motivo": 0,
            })
        row["propostas_abertas"] = contagem["abertas"]
        row["propostas_sem_acao"] = contagem["sem_acao"]
    for row in grouped.values():
        row.setdefault("propostas_abertas", 0)
        row.setdefault("propostas_sem_acao", 0)

    by_team = sorted(grouped.values(), key=lambda row: (
        -(row["nao_viu_visita"] + row["nao_viu_nota"] + row["nao_viu_anexo"]
          + row["nao_adicionou_motivo"] + row["propostas_sem_acao"]),
        row["equipe"],
    ))
    totals["propostas_sem_acao"] = sum(r["propostas_sem_acao"] for r in by_team)
    totals["propostas_abertas"] = sum(r["propostas_abertas"] for r in by_team)
    return {"totais": totals, "por_equipe": by_team, "dias_followup": DIAS_FOLLOWUP}


@cache.memoize(timeout=180)
def executive_view(start_value=None, end_value=None, team=None, broker=None, somente_equipe=False):
    today = date.today()
    end = _date(end_value, today)
    start = _date(start_value, end.replace(day=1))
    if start > end:
        start, end = end, start
    length = (end - start).days + 1
    previous_end = start - timedelta(days=1)
    previous_start = previous_end - timedelta(days=length - 1)

    session = SessionLocal()
    try:
        teams = _team_maps(session)
        if somente_equipe:
            # Gerente: a equipe vem do banco e NAO pode virar None — se ela nao estiver na
            # lista (equipe inativa), o fallback global mostraria a empresa inteira.
            if not team:
                return {"ok": False, "error": "Solicitante sem equipe definida"}
            teams = [item for item in teams if item["id"] == team] or [
                {"id": team, "nome": team, "gerente": "Sem gerente cadastrado", "gerente_id": None}
            ]
        else:
            team = team if any(item["id"] == team for item in teams) else None
        # Sem equipe escolhida a visao e por equipe; com equipe, vira por corretor —
        # e o filtro de corretor so existe dentro de uma equipe.
        brokers = _team_brokers(session, team)
        broker = broker if any(item["id"] == broker for item in brokers) else None
        broker_name = next((b["nome"] for b in brokers if b["id"] == broker), None)
        team_label = next((t["nome"] for t in teams if t["id"] == team), "") if team else ""

        if team:
            team_rows, proposals = _broker_visit_metrics(session, brokers, start, end, broker, team_label)
            previous_rows, previous_proposals = _broker_visit_metrics(session, brokers, previous_start, previous_end, broker, team_label)
        else:
            team_rows, proposals = _visit_metrics(session, teams, start, end, team)
            previous_rows, previous_proposals = _visit_metrics(session, teams, previous_start, previous_end, team)
        vgv, vgc, sales_count, recent_sales = _sales(session, start, end, team, teams, broker_name)
        vgv_anterior, vgc_anterior, sales_count_anterior, _ = _sales(session, previous_start, previous_end, team, teams, broker_name)
        leads = _leads(session, start, end, team, teams, broker, broker_name)
        previous_leads = _leads(session, previous_start, previous_end, team, teams, broker, broker_name)
        clientes = _clientes(session, start, end, team, broker)
        clientes_anterior = _clientes(session, previous_start, previous_end, team, broker)
        propostas_efetivas = _propostas_efetivas(session, start, end, team, broker)
        propostas_anterior = _propostas_efetivas(session, previous_start, previous_end, team, broker)
        visits = sum(row["visitas"] for row in team_rows)
        previous_visits = sum(row["visitas"] for row in previous_rows)
        # Detalhamento por equipe/corretor segue com sim/nao/talvez (funil e grafico).
        proposal_total = proposals.get("sim", 0)
        previous_proposal_total = previous_proposals.get("sim", 0)
        # VGC/VGV: quanto da venda vira comissao da 61. Sem VGV nao ha percentual.
        # 2 casas: a razao gira em torno de 3% e a diferenca entre 3,4% e 3,5% e
        # dinheiro — arredondar p/ 1 casa escondia a variacao.
        pct_vgc_vgv = round(vgc / vgv * 100, 2) if vgv else None
        pct_anterior = round(vgc_anterior / vgv_anterior * 100, 2) if vgv_anterior else None
        return {
            "ok": True, "atualizado_em": datetime.now().isoformat(),
            "periodo": {"inicio": start.isoformat(), "fim": end.isoformat()},
            "equipes_opcoes": teams,
            "corretores_opcoes": brokers,
            "escopo": "equipe" if somente_equipe else "global",
            "dimensao": "corretor" if team else "equipe",
            "filtros": {"equipe": team, "corretor": broker, "corretor_nome": broker_name},
            "kpis": {
                "leads": {"valor": leads, "variacao_pct": _pct(leads, previous_leads)},
                "clientes": {"valor": clientes, "variacao_pct": _pct(clientes, clientes_anterior)},
                "visitas": {"valor": visits, "variacao_pct": _pct(visits, previous_visits)},
                "propostas": {"valor": propostas_efetivas, "variacao_pct": _pct(propostas_efetivas, propostas_anterior)},
                "vendas_quantidade": {"valor": sales_count, "variacao_pct": _pct(sales_count, sales_count_anterior)},
                "vgv": {"valor": vgv, "variacao_pct": _pct(vgv, vgv_anterior)},
                "vgc": {"valor": vgc, "variacao_pct": _pct(vgc, vgc_anterior)},
                "vgc_sobre_vgv": {"valor": pct_vgc_vgv, "variacao_pct": _pct(pct_vgc_vgv or 0, pct_anterior or 0)},
                # Mantidos p/ o restante da tela (funil de visitas e rodapé do gráfico).
                "vendas": {"valor": vgv, "quantidade": sales_count, "variacao_pct": _pct(vgv, vgv_anterior)},
                "propostas_visita_sim": {"valor": proposal_total, "variacao_pct": _pct(proposal_total, previous_proposal_total)},
            },
            "equipes": team_rows, "propostas": proposals,
            "captacao": _captation(session, start, end, team, broker),
            "estoque_semanal": _estoque_semanal(session, start, end, team, broker),
            "vendas_recentes": recent_sales, "midia": _media(session, start, end),
            "imoveis_parados": _imoveis_parados(session, today, team, broker),
            "revisao_visitas": _visit_reviews(session, start, end, team, teams, broker),
        }
    finally:
        session.close()
