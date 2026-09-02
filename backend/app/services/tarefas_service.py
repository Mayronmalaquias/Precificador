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

from sqlalchemy import func, or_

from app.database import SessionLocal
from app.models.estoque_legado import LeadLegado
from app.models.lead_c2s import LeadC2S
from app.models.gerente_visita_visualizada import GerenteVisitaVisualizada
from app.services.gestao_visitas_service import pendencias_de_revisao
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
    # "cliente": (7, 15),  # tipo desativado; ver o comentario de TIPOS
}


# Teto de COLETA: quanto cada tipo pode trazer do banco. Alto de proposito — os chips
# contam o que foi coletado, entao um teto baixo aqui vira numero errado na tela, nao
# lista curta. Com teto de 100, o painel do diretor dizia 100 leads quando havia 2.868.
# Existe so como protecao contra caso patologico; a janela de dias e o filtro de verdade.
TETO_COLETA = 5000

# Teto de EXIBICAO por tipo: quantas linhas a lista mostra. Ninguem rola 2.868 itens, e o
# rodizio ja garante que os quatro tipos aparecem no topo.
MAX_POR_TIPO = 100

# `cliente` saiu do painel (25/08/2026). A pendencia era "visita SIM/TALVEZ sem proposta
# depois dela" — informacao util, mas que so se resolve LANCANDO uma proposta, um fluxo
# completo que nao cabe na ficha. Ficava como a maior fila do painel (314 para o diretor)
# sem nada acionavel dentro da tela. O coletor continua no modulo, desregistrado, para
# quem quiser reativa-lo.
TIPOS = ("proposta", "visita", "lead")


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


def _gerentes_disponiveis(session) -> List[Dict[str, str]]:
    """Gerentes ativos que possuem equipe e podem ser usados como recorte global.

    Alem da permissao formal de gerente, inclui quem encabeca a equipe usando o proprio
    id como `team` (caso de diretor que tambem responde por uma equipe).
    """
    rows = session.query(Usuarios).filter(
        Usuarios.ativo.is_(True),
        Usuarios.id_usuarios.isnot(None),
        Usuarios.team.isnot(None),
        func.trim(Usuarios.team) != "",
        or_(
            func.lower(func.trim(Usuarios.permissao)) == "gerente",
            Usuarios.id_usuarios == Usuarios.team,
        ),
    ).order_by(Usuarios.nome, Usuarios.username, Usuarios.id_usuarios).all()

    return [{
        "id": _texto(user.id_usuarios),
        "nome": _texto(user.nome or user.username or user.id_usuarios),
        "team": _texto(user.team),
    } for user in rows if _texto(user.id_usuarios) and _texto(user.team)]


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
    # Parte da VISITA, com as flags em `outerjoin` — mesma montagem de
    # `gestao_visitas_service.listar`. Antes a consulta comecava na tabela de flags com
    # join interno, e visita ainda nao aberta por ninguem nao tem linha la: ela nunca
    # virava tarefa. Medido em 01/09/2026: 138 das 476 visitas dos ultimos 30 dias
    # estavam nessa situacao, e TODAS as 138 tinham anexo ou nota — ou seja, pendencia
    # real invisivel. Sem linha de flags, "nada foi revisado" e a leitura certa.
    query = session.query(GerenteVisitaVisualizada, Visita, Usuarios).select_from(
        Visita
    ).outerjoin(
        Usuarios, Usuarios.id_usuarios == Visita.id_corretor
    ).outerjoin(
        GerenteVisitaVisualizada,
        (GerenteVisitaVisualizada.id_visita == Visita.id_visita)
        & (GerenteVisitaVisualizada.id_gerente == Usuarios.team),
    ).filter(Visita.data_visita >= corte)
    # O pre-filtro por flags saiu junto: com `outerjoin` ele descartaria justamente as
    # linhas nulas. Quem decide e `pendencias_de_revisao`, e a janela de 30 dias mantem
    # a varredura pequena.
    if not escopo["ve_tudo"] and escopo["team"]:
        # Escopo pela equipe do CORRETOR, nao pela linha de flags, que pode nao existir.
        query = query.filter(Usuarios.team == escopo["team"])

    tarefas = []
    for flags, visita, corretor in query.limit(TETO_COLETA).all():
        # Mesma regra da Gestao de Visitas, importada em vez de repetida: aqui a lista
        # era montada so pelas flags, e cobrava anexo de visita sem anexo e motivo de
        # quem respondeu NAO. O `or_` do SQL acima e pre-filtro grosso; a decisao fina e
        # esta.
        pendentes = pendencias_de_revisao(visita, flags)
        if not pendentes:
            continue
        equipe_visita = (flags.id_gerente if flags else None) or (
            corretor.team if corretor else None) or ""
        dias = _dias(visita.data_visita, hoje)
        if dias < DIAS_VISITA_SEM_REVISAO:
            continue
        tarefas.append({
            # A equipe vem do corretor quando ainda nao ha linha de flags.
            "chave": f"visita:{visita.id_visita}:{equipe_visita}",
            "tipo": "visita",
            "titulo": visita.id_imovel or visita.endereco_externo or "Visita sem imóvel",
            "detalhe": " · ".join(x for x in [
                f"visita {visita.data_visita.strftime('%d/%m')}" if visita.data_visita else "",
                f"resposta {visita.proposta}" if visita.proposta else "",
            ] if x),
            "responsavel": (corretor.nome or corretor.username) if corretor else visita.id_corretor,
            "equipe": equipe_visita,
            "dias": dias,
            "nivel": _nivel(dias, "visita"),
            "motivo": f"Falta revisar: {', '.join(pendentes)}",
            "acao": {"rotulo": "Abrir visita", "tipo": "abrir_visita",
                     "id": visita.id_visita, "pendentes": pendentes},
            "link": f"/GestaoVisitas?visita={visita.id_visita}",
        })
    return tarefas


def _leads_sem_contato(session, escopo, hoje) -> List[Dict[str, Any]]:
    """Lead sem nenhum acompanhamento registrado.

    Le de `leads_c2s`, nao de `leads_legado`: aquela tabela passa por um filtro de negocio
    na importacao (so lead da recepcao ou de fonte Faixa/Indicacao) e por isso nao tem 26%
    dos leads. Lead de portal nunca virava pendencia aqui, embora seja lead como
    qualquer outro.

    Recorte de 30 dias pelo mesmo motivo das visitas: sem janela isso soterraria as outras
    tres pendencias.
    """
    from app.services import lead_c2s_service as c2s

    corte = (hoje - timedelta(days=30)).date()
    limite = (hoje - timedelta(days=DIAS_LEAD_SEM_CONTATO)).date()
    query = session.query(LeadC2S).filter(
        LeadC2S.acompanhamento_em.is_(None),
        LeadC2S.data >= corte,
        LeadC2S.data <= limite,
    )

    if not escopo["ve_tudo"]:
        # O espelho guarda NOME de equipe e de corretor (o C2S nao conhece nossos ids),
        # entao o recorte tem que ser traduzido. Mesma regra da tela de leads — duas
        # regras de escopo sobre o mesmo dado divergiriam.
        recorte = c2s._escopo(session, escopo["id"], None)
        if recorte["equipe"]:
            query = query.filter(
                func.lower(LeadC2S.equipe) == recorte["equipe"].strip().lower()
            )
        elif recorte["corretor"]:
            query = query.filter(LeadC2S.corretor.ilike(f"%{recorte['corretor'].strip()}%"))
        else:
            return []

    tarefas = []
    for lead in query.order_by(LeadC2S.data.desc()).limit(TETO_COLETA).all():
        dias = _dias(lead.data, hoje)
        tarefas.append({
            "chave": f"lead:{lead.id_c2s}",
            "tipo": "lead",
            "titulo": lead.cliente or "Lead sem nome",
            "detalhe": " · ".join(x for x in [
                lead.telefone, lead.codigo_imovel, lead.fonte,
            ] if x),
            "responsavel": lead.corretor or "—",
            "equipe": lead.equipe,
            "dias": dias,
            "nivel": _nivel(dias, "lead"),
            "motivo": f"Sem contato há {dias} dia{'s' if dias != 1 else ''}",
            # `id` e o do C2S: e por ele que `PUT /leads/c2s/<id>` grava, e e o unico id
            # que todo lead tem.
            "acao": {"rotulo": "Registrar contato", "tipo": "contato_lead",
                     "id": lead.id_c2s},
            "link": f"/GestaoLeads?lead={lead.id_c2s}",
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

    linhas = query.limit(TETO_COLETA).all()
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
            "link": f"/GestaoClientes?cliente={cliente.id_cliente}",
        })
    return tarefas


COLETORES = {
    "proposta": _propostas_sem_acao,
    "visita": _visitas_sem_revisao,
    "lead": _leads_sem_contato,
}


# ── agregacao ────────────────────────────────────────────────────────────────────

def listar(solicitante_id, tipos: Optional[List[str]] = None,
           nivel: Optional[str] = None, responsavel: Optional[str] = None,
           gerente_id: Optional[str] = None) -> Dict[str, Any]:
    session = SessionLocal()
    try:
        escopo_original = _escopo(session, solicitante_id)
        permissao = _texto(escopo_original["user"].permissao).casefold()
        pode_filtrar_gerente = (
            escopo_original["ve_tudo"]
            and (permissao in PERFIS_GLOBAIS
                 or _texto(escopo_original["user"].team).casefold() == "administrativo")
        )
        gerentes = _gerentes_disponiveis(session) if pode_filtrar_gerente else []

        gerente_selecionado = None
        gerente_alvo = _texto(gerente_id)
        if gerente_alvo:
            if not pode_filtrar_gerente:
                raise TarefaErro("Sem permissao para filtrar tarefas de outro gerente", 403)
            gerente_selecionado = next(
                (gerente for gerente in gerentes if gerente["id"] == gerente_alvo), None
            )
            if not gerente_selecionado:
                raise TarefaErro("Gerente nao encontrado ou sem equipe ativa", 400)

            # Reusa exatamente o escopo do gerente escolhido. Isso e importante para
            # leads, cujo espelho traduz equipe a partir do id do usuario, e impede que
            # o filtro seja apenas cosmetico depois dos limites de cada coletor.
            escopo = {
                **escopo_original,
                "ve_tudo": False,
                "team": gerente_selecionado["team"],
                "id": gerente_selecionado["id"],
            }
        else:
            escopo = escopo_original

        hoje = datetime.now()
        # Coleta SEMPRE os quatro tipos, mesmo com recorte pedido. Os contadores dos
        # chips sao navegacao — precisam dizer quanto existe de cada tipo para o usuario
        # poder trocar. Rodando so o coletor pedido, escolher "Leads" zerava Propostas e
        # Visitas e nao havia como voltar. O recorte e aplicado adiante, so na lista.
        pedidos = {t for t in (tipos or []) if t in COLETORES}

        tarefas: List[Dict[str, Any]] = []
        for tipo in TIPOS:
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
        # Conta sobre TODOS os tipos, antes do recorte — ver o comentario da coleta.
        contagem_tipo = {t: len(por_tipo.get(t, [])) for t in TIPOS}

        # Cabecalho e chips descrevem o ESCOPO inteiro; a lista abaixo e que e o
        # recorte. Contar so o recorte fazia "Tudo" mostrar o mesmo numero do tipo
        # escolhido — a soma dos chips deixava de fechar com o total.
        criticas = sum(1 for t in tarefas if t["nivel"] == "critica")
        atencao = sum(1 for t in tarefas if t["nivel"] == "atencao")

        # Agora sim o recorte, que vale so para a lista exibida.
        if pedidos:
            por_tipo = {t: fila for t, fila in por_tipo.items() if t in pedidos}
        # E o teto de exibicao, aplicado DEPOIS da contagem: os chips mostram quanto
        # existe, a lista mostra o que cabe. Como cada fila ja esta ordenada por
        # gravidade, o corte tira as menos urgentes.
        por_tipo = {t: fila[:MAX_POR_TIPO] for t, fila in por_tipo.items()}

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
                "total": sum(contagem_tipo.values()),
                "criticas": criticas,
                "atencao": atencao,
                "por_tipo": contagem_tipo,
                # Quantas a lista abaixo esta mostrando de fato. Sem isto nao daria para
                # a tela dizer "75 de 231" quando ha recorte por tipo.
                "exibidas": len(intercalado),
            },
            "escopo": {
                "ve_tudo": escopo_original["ve_tudo"],
                "resolve": escopo_original["resolve"],
                "team": escopo_original["team"],
            },
            "filtros": {
                "pode_filtrar_gerente": pode_filtrar_gerente,
                "gerentes": gerentes,
                "gerente_id": gerente_selecionado["id"] if gerente_selecionado else None,
            },
            "reguas": {"atencao": DIAS_ATENCAO, "critico": DIAS_CRITICO},
        }
    finally:
        session.close()
