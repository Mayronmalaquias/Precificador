"""Painel de Tarefas: agrega as pendencias dos quatro modulos numa lista so.

## O desenho, em uma frase

**Tarefa nao e registro, e projecao do estado.** Ninguem cria tarefa: cada tipo declara
uma condicao, e a tarefa existe enquanto a condicao for verdadeira. Concluir significa
mudar o estado de ORIGEM — e a tarefa some sozinha na proxima leitura.

Por isso nao ha tabela de tarefas nem flag `concluida`. Se houvesse, ela viraria uma
segunda verdade sobre a mesma proposta: alguem registraria acao pela tela de Propostas, a
tarefa continuaria aberta no hub, e a divergencia so apareceria semanas depois. Essa base
ja teve esse problema duas vezes (card x funil contando proposta por criterios diferentes,
e a lista de situacoes fechadas duplicada entre modelo e painel).

## O que cada tipo resolve

    proposta_sem_acao     POST /propostas/{id}/acoes
    visita_sem_revisao    POST /visitas/vistas
    lead_sem_contato      PUT  /leads/gestao/{id}
    cliente_sem_proposta  POST /propostas

O hub NAO tem endpoint de conclusao proprio: ele chama os mesmos que os modulos chamam.
E o que garante que concluir num lugar reflete no outro sem codigo de sincronizacao.

## Escopo

Sai do cadastro, nunca do que a tela mandou. Gerente ve a equipe; diretor, administrador e
administrativo veem tudo; corretor ve o proprio; assistente ve e nao resolve.
"""
from datetime import date, datetime, timedelta
from typing import Any, Dict, List, Optional

from sqlalchemy import or_

from app.database import SessionLocal
from app.models.estoque_legado import LeadLegado
from app.models.gerente_visita_visualizada import GerenteVisitaVisualizada
from app.models.proposta_efetiva import SITUACOES_FECHADAS, PropostaEfetiva
from app.models.usuarios import Usuarios
from app.models.visita import ClienteVisita, Visita

# Reguas — as mesmas dos modulos de origem, importadas de la para nao divergirem.
from app.services.proposta_service import DIAS_ATENCAO, DIAS_CRITICO

PERFIS_GLOBAIS = {"administrador", "administrativo", "diretor", "inteligencia"}

# Dias a partir dos quais cada pendencia entra na lista.
DIAS_LEAD_SEM_CONTATO = 1
DIAS_CLIENTE_SEM_PROPOSTA = 3
DIAS_VISITA_SEM_REVISAO = 1

# Regua de gravidade POR TIPO (atencao, critico).
#
# Usar a regua da proposta (1/2 dias) em tudo fazia 272 de 273 tarefas virarem criticas —
# e severidade que nunca varia nao informa nada, o gerente passa a ignorar a cor. Cada
# dominio tem ritmo proprio: proposta parada 2 dias e grave, lead de 2 dias e rotina.
REGUAS = {
    "proposta": (DIAS_ATENCAO, DIAS_CRITICO),   # 1 / 2 — regra ja documentada
    "visita":   (3, 7),
    "lead":     (2, 5),
    "cliente":  (7, 15),
}

# Teto por tipo: a lista e para trabalhar, nao para contemplar. O resumo conta tudo.
MAX_POR_TIPO = 100

TIPOS = ("proposta", "visita", "lead", "cliente")


class TarefaErro(Exception):
    def __init__(self, mensagem, status=400):
        super().__init__(mensagem)
        self.mensagem = mensagem
        self.status = status


def _texto(valor) -> str:
    return "" if valor is None else str(valor).strip()


def _dias(desde, hoje: datetime) -> int:
    if not desde:
        return 0
    if isinstance(desde, date) and not isinstance(desde, datetime):
        desde = datetime.combine(desde, datetime.min.time())
    return max((hoje - desde).days, 0)


def _nivel(dias: int, tipo: str) -> str:
    atencao, critico = REGUAS.get(tipo, (DIAS_ATENCAO, DIAS_CRITICO))
    if dias >= critico:
        return "critica"
    if dias >= atencao:
        return "atencao"
    return "normal"


def _escopo(session, solicitante_id: str) -> Dict[str, Any]:
    """{ve_tudo, resolve, team, id} — mesma regra de `proposta_service`."""
    user = session.query(Usuarios).filter(
        Usuarios.id_usuarios == _texto(solicitante_id), Usuarios.ativo.is_(True)
    ).first()
    if not user:
        raise TarefaErro("Sem permissão para ver tarefas", 403)

    permissao = _texto(user.permissao).lower()
    team = _texto(user.team)
    global_ = permissao in PERFIS_GLOBAIS or team.lower() == "administrativo"

    if global_:
        return {"ve_tudo": True, "resolve": True, "team": None, "id": user.id_usuarios, "user": user}
    if permissao == "gerente" and team:
        return {"ve_tudo": False, "resolve": True, "team": team, "id": user.id_usuarios, "user": user}
    if permissao == "assistente":
        # Ve tudo para acompanhar, mas nao resolve — mesmo papel do estagiario nas propostas.
        return {"ve_tudo": True, "resolve": False, "team": None, "id": user.id_usuarios, "user": user}
    return {"ve_tudo": False, "resolve": True, "team": None, "id": user.id_usuarios, "user": user}


def _ids_da_equipe(session, team: str) -> List[str]:
    return [
        u.id_usuarios for u in
        session.query(Usuarios.id_usuarios).filter(Usuarios.team == team).all()
        if u.id_usuarios
    ]


# ── os quatro tipos ──────────────────────────────────────────────────────────────

def _propostas_sem_acao(session, escopo, hoje) -> List[Dict[str, Any]]:
    """Proposta aberta parada. `aberta` = nao vendida e nao cancelada (regra de 21/08)."""
    query = session.query(PropostaEfetiva).filter(
        PropostaEfetiva.ativo.is_(True),
        PropostaEfetiva.situacao.notin_(SITUACOES_FECHADAS),
    )
    if not escopo["ve_tudo"]:
        if escopo["team"]:
            query = query.filter(PropostaEfetiva.team == escopo["team"])
        else:
            query = query.filter(or_(
                PropostaEfetiva.id_corretor == escopo["id"],
                PropostaEfetiva.id_gerente == escopo["id"],
            ))

    tarefas = []
    for p in query.all():
        referencia = p.ultima_acao_em or p.updated_at or p.created_at
        dias = _dias(referencia, hoje)
        if dias < DIAS_ATENCAO:
            continue
        tarefas.append({
            "chave": f"proposta:{p.id}",
            "tipo": "proposta",
            "titulo": p.imovel_endereco or p.codigo_imovel or f"Proposta #{p.id}",
            "detalhe": " · ".join(x for x in [
                p.cliente,
                f"R$ {float(p.valor):,.0f}".replace(",", ".") if p.valor else "",
                p.situacao_label if hasattr(p, "situacao_label") else "",
            ] if x),
            "responsavel": p.corretor_nome or p.gerente_nome or "—",
            "equipe": p.team,
            "dias": dias,
            "nivel": _nivel(dias, "proposta"),
            "motivo": f"Sem ação há {dias} dia{'s' if dias != 1 else ''}",
            "acao": {"rotulo": "Registrar ação", "tipo": "acao_proposta", "id": p.id},
            "link": f"/PropostasEfetivas?id={p.id}",
        })
    return tarefas


def _visitas_sem_revisao(session, escopo, hoje) -> List[Dict[str, Any]]:
    """Visita cujo gerente ainda nao viu anexo/notas ou nao registrou o motivo.

    A janela e de 30 dias, como no painel do diretor: visita de tres meses atras nao e
    tarefa, e virar backlog eterno faz o gerente ignorar a lista inteira.
    """
    corte = (hoje - timedelta(days=30)).date()
    query = session.query(GerenteVisitaVisualizada, Visita, Usuarios).join(
        Visita, Visita.id_visita == GerenteVisitaVisualizada.id_visita
    ).outerjoin(
        Usuarios, Usuarios.id_usuarios == Visita.id_corretor
    ).filter(
        Visita.data_visita >= corte,
        or_(
            GerenteVisitaVisualizada.viu_anexo.is_(False),
            GerenteVisitaVisualizada.viu_notas.is_(False),
            GerenteVisitaVisualizada.add_motivo.is_(False),
        ),
    )
    if not escopo["ve_tudo"] and escopo["team"]:
        query = query.filter(GerenteVisitaVisualizada.id_gerente == escopo["team"])

    tarefas = []
    for flags, visita, corretor in query.limit(MAX_POR_TIPO * 3).all():
        pendentes = [rotulo for valor, rotulo in (
            (flags.viu_anexo, "anexo"), (flags.viu_notas, "notas"), (flags.add_motivo, "motivo"),
        ) if not valor]
        dias = _dias(visita.data_visita, hoje)
        if dias < DIAS_VISITA_SEM_REVISAO:
            continue
        tarefas.append({
            "chave": f"visita:{visita.id_visita}:{flags.id_gerente}",
            "tipo": "visita",
            "titulo": visita.id_imovel or visita.endereco_externo or "Visita sem imóvel",
            "detalhe": " · ".join(x for x in [
                f"visita {visita.data_visita.strftime('%d/%m')}" if visita.data_visita else "",
                f"resposta {visita.proposta}" if visita.proposta else "",
            ] if x),
            "responsavel": (corretor.nome or corretor.username) if corretor else visita.id_corretor,
            "equipe": flags.id_gerente,
            "dias": dias,
            "nivel": _nivel(dias, "visita"),
            "motivo": f"Falta revisar: {', '.join(pendentes)}",
            "acao": {"rotulo": "Marcar revisada", "tipo": "revisar_visita",
                     "id": visita.id_visita, "pendentes": pendentes},
            "link": f"/RelatorioGerente?visita={visita.id_visita}",
        })
    return tarefas


def _leads_sem_contato(session, escopo, hoje) -> List[Dict[str, Any]]:
    """Lead importado sem nenhum acompanhamento registrado.

    Recorte de 30 dias pelo mesmo motivo das visitas: a base tem 68 mil leads e apenas 13
    com acompanhamento, entao sem janela isso soterraria as outras tres pendencias.
    """
    corte = (hoje - timedelta(days=30)).date()
    limite = (hoje - timedelta(days=DIAS_LEAD_SEM_CONTATO)).date()
    query = session.query(LeadLegado).filter(
        LeadLegado.acompanhamento_em.is_(None),
        LeadLegado.data >= corte,
        LeadLegado.data <= limite,
    )
    if not escopo["ve_tudo"]:
        chaves = _ids_da_equipe(session, escopo["team"]) if escopo["team"] else [escopo["id"]]
        if escopo["team"]:
            chaves.append(escopo["team"])
        query = query.filter(or_(
            LeadLegado.atendimento.in_(chaves), LeadLegado.equipe.in_(chaves)
        ))

    tarefas = []
    for lead in query.order_by(LeadLegado.data.desc()).limit(MAX_POR_TIPO).all():
        dias = _dias(lead.data, hoje)
        tarefas.append({
            "chave": f"lead:{lead.id}",
            "tipo": "lead",
            "titulo": lead.cliente or "Lead sem nome",
            "detalhe": " · ".join(x for x in [
                lead.telefone, lead.codigo_imovel, lead.fonte,
            ] if x),
            "responsavel": lead.atendimento or "—",
            "equipe": lead.equipe,
            "dias": dias,
            "nivel": _nivel(dias, "lead"),
            "motivo": f"Sem contato há {dias} dia{'s' if dias != 1 else ''}",
            "acao": {"rotulo": "Registrar contato", "tipo": "contato_lead", "id": lead.id},
            "link": f"/GestaoLeads?lead={lead.id}",
        })
    return tarefas


def _clientes_sem_proposta(session, escopo, hoje) -> List[Dict[str, Any]]:
    """Visita com resposta SIM/TALVEZ e nenhuma proposta do cliente depois dela.

    E a unica das quatro que cruza dois dominios. O casamento com a proposta e por NOME
    do cliente — `proposta_efetiva.cliente` e texto livre, nao ha id. Casos de grafia
    diferente escapam; e o mesmo limite que a base ja tem em outros cruzamentos.
    """
    corte = (hoje - timedelta(days=45)).date()
    limite = (hoje - timedelta(days=DIAS_CLIENTE_SEM_PROPOSTA)).date()

    query = session.query(Visita, ClienteVisita, Usuarios).join(
        ClienteVisita, ClienteVisita.id_cliente == Visita.id_cliente_assinante
    ).outerjoin(
        Usuarios, Usuarios.id_usuarios == Visita.id_corretor
    ).filter(
        Visita.data_visita >= corte,
        Visita.data_visita <= limite,
        Visita.proposta.isnot(None),
    )
    if not escopo["ve_tudo"]:
        if escopo["team"]:
            query = query.filter(Usuarios.team == escopo["team"])
        else:
            query = query.filter(Visita.id_corretor == escopo["id"])

    linhas = query.limit(MAX_POR_TIPO * 3).all()
    nomes = {_texto(c.nome_cliente) for _, c, _ in linhas if _texto(c.nome_cliente)}
    com_proposta = set()
    if nomes:
        com_proposta = {
            _texto(p.cliente).casefold()
            for p in session.query(PropostaEfetiva.cliente).filter(
                PropostaEfetiva.ativo.is_(True), PropostaEfetiva.cliente.in_(nomes)
            ).all()
        }

    tarefas = []
    for visita, cliente, corretor in linhas:
        resposta = _texto(visita.proposta).casefold()
        if resposta not in {"sim", "talvez"}:
            continue
        if _texto(cliente.nome_cliente).casefold() in com_proposta:
            continue
        dias = _dias(visita.data_visita, hoje)
        tarefas.append({
            "chave": f"cliente:{cliente.id_cliente}:{visita.id_visita}",
            "tipo": "cliente",
            "titulo": cliente.nome_cliente or "Cliente sem nome",
            "detalhe": " · ".join(x for x in [
                cliente.telefone_cliente,
                f"visitou {visita.id_imovel}" if visita.id_imovel else "",
                f"resposta {visita.proposta}",
            ] if x),
            "responsavel": (corretor.nome or corretor.username) if corretor else "—",
            "equipe": corretor.team if corretor else None,
            "dias": dias,
            "nivel": _nivel(dias, "cliente"),
            "motivo": f"Visita {visita.proposta} há {dias} dias, sem proposta",
            "acao": {"rotulo": "Lançar proposta", "tipo": "nova_proposta",
                     "cliente": cliente.nome_cliente, "codigo": visita.id_imovel,
                     "id_visita": visita.id_visita,
                     # Sem o id do cliente a tarefa so conseguia lancar proposta; com ele
                     # da para abrir e corrigir o cadastro sem sair do painel.
                     "id_cliente": cliente.id_cliente},
            "link": f"/PropostasEfetivas?novo=1&cliente={cliente.nome_cliente or ''}",
        })
    return tarefas


COLETORES = {
    "proposta": _propostas_sem_acao,
    "visita": _visitas_sem_revisao,
    "lead": _leads_sem_contato,
    "cliente": _clientes_sem_proposta,
}


# ── agregacao ────────────────────────────────────────────────────────────────────

def listar(solicitante_id, tipos: Optional[List[str]] = None,
           nivel: Optional[str] = None, responsavel: Optional[str] = None) -> Dict[str, Any]:
    session = SessionLocal()
    try:
        escopo = _escopo(session, solicitante_id)
        hoje = datetime.now()
        alvos = [t for t in (tipos or TIPOS) if t in COLETORES]

        tarefas: List[Dict[str, Any]] = []
        for tipo in alvos:
            try:
                tarefas.extend(COLETORES[tipo](session, escopo, hoje))
            except Exception:
                # Um tipo que falha nao pode derrubar o painel inteiro — o gerente
                # continua vendo e resolvendo os outros tres.
                continue

        if nivel:
            tarefas = [t for t in tarefas if t["nivel"] == nivel]
        if responsavel:
            alvo = _texto(responsavel).casefold()
            tarefas = [t for t in tarefas if alvo in _texto(t["responsavel"]).casefold()]

        # Rodizio entre tipos: dentro de cada um, o mais atrasado primeiro. Ordenar so
        # por dias faria "proposta sem acao" (1-5 dias) sumir atras de lead de 30.
        por_tipo: Dict[str, List[Dict[str, Any]]] = {}
        for t in tarefas:
            por_tipo.setdefault(t["tipo"], []).append(t)
        for fila in por_tipo.values():
            fila.sort(key=lambda t: (0 if t["nivel"] == "critica" else 1, -t["dias"]))

        # Conta antes de intercalar: o rodizio abaixo esvazia as filas com `pop`.
        contagem_tipo = {t: len(por_tipo.get(t, [])) for t in TIPOS}

        intercalado: List[Dict[str, Any]] = []
        filas = [f for f in por_tipo.values() if f]
        while filas:
            for fila in list(filas):
                if fila:
                    intercalado.append(fila.pop(0))
                else:
                    filas.remove(fila)

        return {
            "ok": True,
            "itens": intercalado,
            "resumo": {
                "total": len(intercalado),
                "criticas": sum(1 for t in intercalado if t["nivel"] == "critica"),
                "atencao": sum(1 for t in intercalado if t["nivel"] == "atencao"),
                "por_tipo": contagem_tipo,
            },
            "escopo": {
                "ve_tudo": escopo["ve_tudo"],
                "resolve": escopo["resolve"],
                "team": escopo["team"],
            },
            "reguas": {"atencao": DIAS_ATENCAO, "critico": DIAS_CRITICO},
        }
    finally:
        session.close()
