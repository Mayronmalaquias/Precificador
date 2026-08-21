"""Propostas efetivas: CRUD, escopo por permissao e acompanhamento de inatividade.

Regras de acesso (o solicitante vem do banco, nunca do que a tela mandou):
- gerente ......... ve e edita SO as propostas da propria equipe; lanca no nome de
                    corretor da propria equipe;
- administrativo .. ve e edita todas (permissao 'administrativo'/'administrador' ou team
                    'administrativo'); lanca no nome de qualquer corretor E escolhe o
                    gerente dono da proposta;
- diretor ......... mesmo alcance do administrativo (pedido em 07/08/2026 — antes era
                    so leitura), inclusive escolher o gerente;
- assistente ...... ve todas, nao edita (perfil usado p/ o estagiario acompanhar).
"""
from datetime import date, datetime, timezone
from decimal import Decimal, InvalidOperation
from zoneinfo import ZoneInfo

from sqlalchemy import func, or_

from app.database import SessionLocal
from app.models.proposta_efetiva import (
    FORMAS_PAGAMENTO,
    SITUACOES,
    SITUACOES_FECHADAS,
    PropostaEfetiva,
    PropostaEfetivaAcao,
)
from app.models.equipe import Equipe
from app.models.usuarios import Usuarios
from app.models.visita import ClienteVisita, Visita

# Dias sem acao a partir dos quais a proposta e sinalizada na tela. Regua alinhada com
# a Visao do Diretor (2026-08-10): 1 dia parado ja pede follow-up, 2+ e critico.
DIAS_ATENCAO = 1
DIAS_CRITICO = 2

# Fuso da operacao. `created_at` e gravado pelo banco em UTC (`func.now()`), mas o filtro
# de periodo vem em datas do calendario brasileiro. Sem a conversao, proposta lancada
# depois das 21h cai no dia UTC seguinte e some do filtro do dia em que foi lancada.
FUSO_OPERACAO = ZoneInfo("America/Sao_Paulo")


def _inicio_utc(dia):
    return datetime.combine(dia, datetime.min.time(), tzinfo=FUSO_OPERACAO).astimezone(
        timezone.utc).replace(tzinfo=None)


def _fim_utc(dia):
    return datetime.combine(dia, datetime.max.time(), tzinfo=FUSO_OPERACAO).astimezone(
        timezone.utc).replace(tzinfo=None)

ROTULO_SITUACAO = {
    "em_analise": "Em análise",
    "contraproposta": "Contraproposta",
    "aceita": "Aceita",
    "vendido": "Vendido",
    "recusada": "Recusada",
    "cancelada": "Cancelada",
}
ROTULO_PAGAMENTO = {
    "permuta": "Permuta",
    "consorcio": "Consórcio",
    "financiamento": "Financiamento",
    "recurso_proprio": "Recurso próprio",
    "outros": "Outros",
}


class PropostaErro(Exception):
    """Erro de validacao/permissao — a rota traduz em 400/403."""

    def __init__(self, mensagem, status=400):
        super().__init__(mensagem)
        self.mensagem = mensagem
        self.status = status


def _num(valor):
    if valor in (None, ""):
        return None
    texto = str(valor).strip().replace("R$", "").replace(" ", "")
    if "," in texto:
        texto = texto.replace(".", "").replace(",", ".")
    try:
        return Decimal(texto)
    except (InvalidOperation, ValueError):
        return None


def _data(valor):
    """'2026-08-01' -> date. Aceita date/datetime prontos. Vazio/invalido -> None."""
    if not valor:
        return None
    if isinstance(valor, datetime):
        return valor.date()
    if isinstance(valor, date):
        return valor
    try:
        return datetime.strptime(str(valor)[:10], "%Y-%m-%d").date()
    except (TypeError, ValueError):
        return None


def _texto(valor, limite=None):
    texto = str(valor or "").strip()
    return texto[:limite] if limite else texto


def escopo_do_solicitante(solicitante_id):
    """Traduz o usuario em {ve_tudo, edita, team}. Levanta PropostaErro se nao tem acesso."""
    session = SessionLocal()
    try:
        user = session.query(Usuarios).filter(
            Usuarios.id_usuarios == _texto(solicitante_id), Usuarios.ativo.is_(True)
        ).first()
    finally:
        session.close()
    if not user:
        raise PropostaErro("Sem permissão para ver propostas", 403)

    permissao = _texto(user.permissao).lower()
    team = _texto(user.team)
    # `administrador` estava de fora: 4 dos 7 usuarios com esse papel (Douglas, Miguel,
    # Financeiro, Anna/ADM004) recebiam 403 na tela inteira de propostas — so passavam
    # os que por acaso tinham `team = administrativo`.
    administrativo = (
        permissao in {"administrativo", "administrador"} or team.lower() == "administrativo"
    )

    if administrativo or permissao == "diretor":
        return {"ve_tudo": True, "edita": True, "team": None, "user": user}
    if permissao == "gerente" and team:
        return {"ve_tudo": False, "edita": True, "team": team, "user": user}
    if permissao == "assistente":
        return {"ve_tudo": True, "edita": False, "team": None, "user": user}
    raise PropostaErro("Sem permissão para ver propostas", 403)


def corretores_disponiveis(solicitante_id):
    """Corretores em nome de quem o solicitante pode lançar.

    Gerente só enxerga a própria equipe; diretor/administrativo enxergam todas — é o
    servidor que corta, então mandar outro id na requisição não adianta.
    """
    escopo = escopo_do_solicitante(solicitante_id)
    session = SessionLocal()
    try:
        query = session.query(Usuarios).filter(Usuarios.ativo.is_(True))
        if not escopo["ve_tudo"]:
            query = query.filter(Usuarios.team == escopo["team"])
        rows = query.order_by(Usuarios.nome).all()
        itens = [{
            "id": u.id_usuarios,
            "nome": u.nome or u.username or u.id_usuarios,
            "team": u.team,
            "permissao": _texto(u.permissao).lower(),
        } for u in rows if u.id_usuarios]
        # Gerentes em nome de quem da p/ lancar. So faz sentido para perfil global —
        # gerente lanca no proprio nome, e a lista vazia esconde o campo na tela.
        #
        # Quem entra: permissao 'gerente' OU quem ENCABECA uma equipe, ou seja, cujo
        # `id_usuarios` e o proprio `id_equipe`. A segunda metade existe por causa do
        # Jose Marques: ele e `diretor`, mas G61001 e o id da AGEF, entao a equipe dele
        # ficava sem gerente selecionavel. So a permissao nao bastava.
        gerentes = []
        if escopo["ve_tudo"]:
            equipes = session.query(Equipe.id_equipe).filter(
                Equipe.id_equipe.isnot(None)
            ).subquery()
            gerentes = [
                {"id": u.id_usuarios,
                 "nome": u.nome or u.username or u.id_usuarios,
                 "team": u.team}
                for u in session.query(Usuarios).filter(
                    Usuarios.ativo.is_(True),
                    or_(
                        func.lower(Usuarios.permissao) == "gerente",
                        Usuarios.id_usuarios.in_(session.query(equipes.c.id_equipe)),
                    ),
                ).order_by(Usuarios.nome).all()
                if u.id_usuarios
            ]
        return {
            "ok": True,
            "itens": itens,
            "gerentes": gerentes,
            # Quem esta pedindo — a tela usa p/ marcar o gerente atual como padrao.
            "solicitante": {
                "id": escopo["user"].id_usuarios,
                "nome": _texto(escopo["user"].nome or escopo["user"].username),
                "ve_tudo": escopo["ve_tudo"],
            },
        }
    finally:
        session.close()


def visitas_relacionadas(solicitante_id, filtros=None):
    """Visitas candidatas a virar a origem da proposta, restritas à equipe.

    Gerente vê as da própria equipe; diretor/administrativo veem todas. Se vier
    `corretor`, restringe a ele — é o caso normal ao lançar em nome de alguém.
    """
    escopo = escopo_do_solicitante(solicitante_id)
    filtros = filtros or {}
    session = SessionLocal()
    try:
        # `outerjoin` no cliente assinante: a visita traz o nome de quem assinou a
        # ficha, que é o cliente que a proposta deve herdar.
        query = session.query(Visita, Usuarios, ClienteVisita).join(
            Usuarios, Usuarios.id_usuarios == Visita.id_corretor
        ).outerjoin(
            ClienteVisita, ClienteVisita.id_cliente == Visita.id_cliente_assinante
        )
        if not escopo["ve_tudo"]:
            query = query.filter(Usuarios.team == escopo["team"])
        elif filtros.get("team"):
            query = query.filter(Usuarios.team == filtros["team"])
        if filtros.get("corretor"):
            query = query.filter(Visita.id_corretor == filtros["corretor"])
        if filtros.get("codigo"):
            query = query.filter(Visita.id_imovel.ilike(f"%{filtros['codigo'].strip()}%"))
        # Corretor do filtro do topo do relatorio. Separado da `busca` de proposito: a
        # busca varre imovel/bairro/cliente tambem, e misturar faria "Ana" trazer proposta
        # do bairro "Ana Lucia".
        if filtros.get("corretor"):
            alvo_corretor = f"%{str(filtros['corretor']).strip()}%"
            query = query.filter(or_(
                PropostaEfetiva.corretor_nome.ilike(alvo_corretor),
                PropostaEfetiva.gerente_nome.ilike(alvo_corretor),
                PropostaEfetiva.id_corretor == str(filtros["corretor"]).strip(),
            ))
        if filtros.get("busca"):
            alvo = f"%{filtros['busca'].strip()}%"
            query = query.filter(or_(
                Visita.id_imovel.ilike(alvo),
                Visita.endereco_externo.ilike(alvo),
                Visita.id_visita.ilike(alvo),
            ))
        rows = query.order_by(Visita.data_visita.desc()).limit(40).all()
        return {
            "ok": True,
            "itens": [{
                "id_visita": visita.id_visita,
                "data_visita": visita.data_visita.isoformat() if visita.data_visita else None,
                "imovel": visita.id_imovel or visita.endereco_externo or "Imóvel não informado",
                "corretor": corretor.nome or corretor.username or visita.id_corretor,
                "id_corretor": visita.id_corretor,
                "team": corretor.team,
                "proposta_visita": visita.proposta,
                "cliente": cliente.nome_cliente if cliente else None,
                "telefone_cliente": cliente.telefone_cliente if cliente else None,
            } for visita, corretor, cliente in rows],
        }
    finally:
        session.close()


def _resolver_corretor(session, escopo, id_corretor):
    """Valida o corretor escolhido e devolve (id, nome, team). Fora do escopo => 403."""
    corretor = session.query(Usuarios).filter(
        Usuarios.id_usuarios == _texto(id_corretor), Usuarios.ativo.is_(True)
    ).first()
    if not corretor:
        raise PropostaErro("Corretor não encontrado")
    if not escopo["ve_tudo"] and _texto(corretor.team) != escopo["team"]:
        raise PropostaErro("Esse corretor é de outra equipe", 403)
    return corretor.id_usuarios, (corretor.nome or corretor.username), _texto(corretor.team)


def _resolver_visita(session, escopo, id_visita, team_proposta):
    """Visita só pode ser vinculada se for da mesma equipe da proposta."""
    if not id_visita:
        return None
    linha = session.query(Visita, Usuarios).join(
        Usuarios, Usuarios.id_usuarios == Visita.id_corretor
    ).filter(Visita.id_visita == _texto(id_visita)).first()
    if not linha:
        raise PropostaErro("Visita não encontrada")
    visita, corretor = linha
    team_visita = _texto(corretor.team)
    if not escopo["ve_tudo"] and team_visita != escopo["team"]:
        raise PropostaErro("Essa visita é de outra equipe", 403)
    if team_proposta and team_visita and team_visita != team_proposta:
        raise PropostaErro("A visita é de outra equipe que não a da proposta")
    return visita.id_visita


def _resolver_gerente(session, escopo, id_gerente):
    """Gerente em nome de quem a proposta e lancada. Devolve (id, nome, team).

    So perfil global (diretor/administrador/administrativo) escolhe outro; gerente lanca
    sempre no proprio nome. O nome e a equipe saem do CADASTRO — antes `gerente_nome`
    era gravado exatamente como a tela mandasse, sem conferencia.
    """
    user = escopo["user"]
    pedido = _texto(id_gerente)
    if not pedido or pedido == _texto(user.id_usuarios):
        return (_texto(user.id_usuarios),
                _texto(user.nome or user.username),
                _texto(user.team))
    if not escopo["ve_tudo"]:
        raise PropostaErro("Você só pode lançar proposta no seu próprio nome", 403)
    gerente = session.query(Usuarios).filter(
        Usuarios.id_usuarios == pedido, Usuarios.ativo.is_(True)
    ).first()
    if not gerente:
        raise PropostaErro("Gerente não encontrado")
    return (gerente.id_usuarios,
            _texto(gerente.nome or gerente.username),
            _texto(gerente.team))


def _pode_mexer(escopo, proposta):
    if not escopo["edita"]:
        raise PropostaErro("Seu perfil só pode acompanhar as propostas, não alterar", 403)
    if not escopo["ve_tudo"] and proposta.team != escopo["team"]:
        raise PropostaErro("Proposta de outra equipe", 403)


def _dias_sem_acao(proposta, hoje=None):
    hoje = hoje or datetime.now()
    referencia = proposta.ultima_acao_em or proposta.updated_at or proposta.created_at
    if not referencia:
        return None
    return max((hoje - referencia).days, 0)


def _fim_da_contagem(proposta, hoje_data):
    """Ate quando contar "dias em aberto".

    Proposta fechada para de contar no fechamento. Quando a situacao e fechada mas
    ninguem preencheu `data_fechamento`, cair no `hoje` fazia o contador crescer todo
    dia depois de a proposta ja ter acabado — entao usa-se a ultima mexida registrada
    como melhor aproximacao do momento em que parou.
    """
    if proposta.situacao not in SITUACOES_FECHADAS:
        return hoje_data
    if proposta.data_fechamento:
        return proposta.data_fechamento
    referencia = proposta.ultima_acao_em or proposta.updated_at or proposta.created_at
    return referencia.date() if referencia else hoje_data


def _serializar(proposta, hoje=None, com_acoes=False):
    hoje_data = (hoje or datetime.now()).date()
    fechada = proposta.situacao in SITUACOES_FECHADAS
    fim = _fim_da_contagem(proposta, hoje_data)
    dias_aberto = (fim - proposta.data_proposta).days if proposta.data_proposta else None
    sem_acao = None if fechada else _dias_sem_acao(proposta, hoje)
    dados = {
        "id": proposta.id,
        "codigo_imovel": proposta.codigo_imovel,
        "imovel_endereco": proposta.imovel_endereco,
        "bairro": proposta.bairro,
        "tipo": proposta.tipo,
        "numero": proposta.numero,
        "bloco": proposta.bloco,
        "complemento": proposta.complemento,
        "quartos": proposta.quartos,
        "vagas": proposta.vagas,
        "area": proposta.area,
        "valor": float(proposta.valor) if proposta.valor is not None else None,
        "valor_permuta": float(proposta.valor_permuta) if proposta.valor_permuta is not None else None,
        "descricao_permuta": proposta.descricao_permuta,
        "forma_pagamento": proposta.forma_pagamento,
        "forma_pagamento_label": ROTULO_PAGAMENTO.get(proposta.forma_pagamento, proposta.forma_pagamento),
        "situacao": proposta.situacao,
        "situacao_label": ROTULO_SITUACAO.get(proposta.situacao, proposta.situacao),
        "fechada": fechada,
        "team": proposta.team,
        "id_gerente": proposta.id_gerente,
        "gerente_nome": proposta.gerente_nome,
        "id_corretor": proposta.id_corretor,
        "corretor_nome": proposta.corretor_nome,
        "id_visita": proposta.id_visita,
        "cliente": proposta.cliente,
        "observacao": proposta.observacao,
        "data_proposta": proposta.data_proposta.isoformat() if proposta.data_proposta else None,
        "data_fechamento": proposta.data_fechamento.isoformat() if proposta.data_fechamento else None,
        # Data de LANCAMENTO. E por ela que o painel do diretor e o filtro de periodo
        # recortam — `data_proposta` e digitada e vem retroativa. A tela mostra as duas
        # para o gestor nao comparar numeros que saem de datas diferentes.
        #
        # O banco grava em UTC sem tzinfo; o sufixo "Z" e obrigatorio, senao o
        # `new Date()` do navegador le como hora local e erra o dia por 3 horas.
        "created_at": f"{proposta.created_at.isoformat()}Z" if proposta.created_at else None,
        "dias_em_aberto": max(dias_aberto, 0) if dias_aberto is not None else None,
        "dias_sem_acao": sem_acao,
        "alerta": "critico" if (sem_acao or 0) >= DIAS_CRITICO else "atencao" if (sem_acao or 0) >= DIAS_ATENCAO else None,
        "ultima_acao_em": proposta.ultima_acao_em.isoformat() if proposta.ultima_acao_em else None,
        "total_acoes": len(proposta.acoes) if com_acoes else None,
    }
    if com_acoes:
        dados["acoes"] = [{
            "id": acao.id,
            "descricao": acao.descricao,
            "situacao": acao.situacao,
            "situacao_label": ROTULO_SITUACAO.get(acao.situacao, acao.situacao),
            "autor_nome": acao.autor_nome,
            "created_at": acao.created_at.isoformat() if acao.created_at else None,
        } for acao in proposta.acoes]
    return dados


def _aplicar_escopo(query, escopo):
    if escopo["ve_tudo"]:
        return query
    return query.filter(PropostaEfetiva.team == escopo["team"])


def listar(solicitante_id, filtros=None):
    escopo = escopo_do_solicitante(solicitante_id)
    filtros = filtros or {}
    session = SessionLocal()
    try:
        query = _aplicar_escopo(
            session.query(PropostaEfetiva).filter(PropostaEfetiva.ativo.is_(True)), escopo
        )
        if filtros.get("situacao"):
            query = query.filter(PropostaEfetiva.situacao == filtros["situacao"])
        if filtros.get("team") and escopo["ve_tudo"]:
            query = query.filter(PropostaEfetiva.team == filtros["team"])
        if filtros.get("forma_pagamento"):
            query = query.filter(PropostaEfetiva.forma_pagamento == filtros["forma_pagamento"])
        # Corretor do filtro do topo do relatorio. Separado da `busca` de proposito: a
        # busca varre imovel/bairro/cliente tambem, e misturar faria "Ana" trazer proposta
        # do bairro "Ana Lucia".
        if filtros.get("corretor"):
            alvo_corretor = f"%{str(filtros['corretor']).strip()}%"
            query = query.filter(or_(
                PropostaEfetiva.corretor_nome.ilike(alvo_corretor),
                PropostaEfetiva.gerente_nome.ilike(alvo_corretor),
                PropostaEfetiva.id_corretor == str(filtros["corretor"]).strip(),
            ))
        if filtros.get("busca"):
            alvo = f"%{filtros['busca'].strip()}%"
            query = query.filter(or_(
                PropostaEfetiva.codigo_imovel.ilike(alvo),
                PropostaEfetiva.imovel_endereco.ilike(alvo),
                PropostaEfetiva.bairro.ilike(alvo),
                PropostaEfetiva.cliente.ilike(alvo),
                PropostaEfetiva.corretor_nome.ilike(alvo),
            ))
        if str(filtros.get("somente_abertas") or "").lower() == "true":
            query = query.filter(PropostaEfetiva.situacao.notin_(SITUACOES_FECHADAS))
        # Periodo pela data de LANCAMENTO (`created_at`), o mesmo criterio do painel do
        # diretor: `data_proposta` e digitada e vem retroativa/futura com frequencia.
        # As fronteiras vao pra UTC porque e assim que `created_at` e gravado — ver
        # `_intervalo_utc`.
        if filtros.get("inicio"):
            query = query.filter(PropostaEfetiva.created_at >= _inicio_utc(_data(filtros["inicio"])))
        if filtros.get("fim"):
            query = query.filter(PropostaEfetiva.created_at <= _fim_utc(_data(filtros["fim"])))

        agora = datetime.now()
        itens = [_serializar(p, agora) for p in query.order_by(PropostaEfetiva.created_at.desc()).all()]
        # Sem acao ha mais tempo primeiro: e essa a leitura que o estagiario acompanha.
        abertas = [i for i in itens if not i["fechada"]]
        abertas.sort(key=lambda i: (-(i["dias_sem_acao"] or 0), -(i["dias_em_aberto"] or 0)))
        return {
            "ok": True,
            "itens": itens,
            "paradas": abertas[:15],
            "escopo": {"ve_tudo": escopo["ve_tudo"], "edita": escopo["edita"], "team": escopo["team"]},
            "resumo": {
                "total": len(itens),
                "abertas": len(abertas),
                "sem_acao_7": sum(1 for i in abertas if (i["dias_sem_acao"] or 0) >= DIAS_ATENCAO),
                "sem_acao_14": sum(1 for i in abertas if (i["dias_sem_acao"] or 0) >= DIAS_CRITICO),
                # Proposta que nunca recebeu ação é o equivalente da visita não
                # visualizada: foi lançada e ninguém encostou nela.
                "nao_vistas": sum(1 for i in itens if not i.get("total_acoes")),
                "valor_aberto": sum(i["valor"] or 0 for i in abertas),
            },
            "opcoes": {
                "situacoes": [{"value": s, "label": ROTULO_SITUACAO[s]} for s in SITUACOES],
                "formas_pagamento": [{"value": f, "label": ROTULO_PAGAMENTO[f]} for f in FORMAS_PAGAMENTO],
                "dias_atencao": DIAS_ATENCAO,
                "dias_critico": DIAS_CRITICO,
            },
        }
    finally:
        session.close()


def obter(solicitante_id, proposta_id):
    escopo = escopo_do_solicitante(solicitante_id)
    session = SessionLocal()
    try:
        proposta = session.query(PropostaEfetiva).filter(PropostaEfetiva.id == proposta_id).first()
        if not proposta or not proposta.ativo:
            raise PropostaErro("Proposta não encontrada", 404)
        if not escopo["ve_tudo"] and proposta.team != escopo["team"]:
            raise PropostaErro("Proposta de outra equipe", 403)
        dados = _serializar(proposta, com_acoes=True)
        # Dados da visita de origem, p/ a tela não precisar de outra chamada.
        dados["visita"] = None
        if proposta.id_visita:
            linha = session.query(Visita, Usuarios, ClienteVisita).outerjoin(
                Usuarios, Usuarios.id_usuarios == Visita.id_corretor
            ).outerjoin(
                ClienteVisita, ClienteVisita.id_cliente == Visita.id_cliente_assinante
            ).filter(Visita.id_visita == proposta.id_visita).first()
            if linha:
                visita, corretor, cliente_visita = linha
                dados["visita"] = {
                    "id_visita": visita.id_visita,
                    "data_visita": visita.data_visita.isoformat() if visita.data_visita else None,
                    "imovel": visita.id_imovel or visita.endereco_externo or "Imóvel não informado",
                    "corretor": (corretor.nome or corretor.username) if corretor else visita.id_corretor,
                    "proposta_visita": visita.proposta,
                    "cliente": cliente_visita.nome_cliente if cliente_visita else None,
                }
        return {"ok": True, "proposta": dados, "pode_editar": escopo["edita"]}
    finally:
        session.close()


def _validar(dados, parcial=False):
    situacao = _texto(dados.get("situacao")).lower() or ("em_analise" if not parcial else None)
    if situacao and situacao not in SITUACOES:
        raise PropostaErro(f"Situação inválida. Use uma destas: {', '.join(SITUACOES)}")
    forma = _texto(dados.get("forma_pagamento")).lower() or None
    if forma and forma not in FORMAS_PAGAMENTO:
        raise PropostaErro(f"Forma de pagamento inválida. Use uma destas: {', '.join(FORMAS_PAGAMENTO)}")
    return situacao, forma


def criar(solicitante_id, dados):
    escopo = escopo_do_solicitante(solicitante_id)
    if not escopo["edita"]:
        raise PropostaErro("Seu perfil só pode acompanhar as propostas, não lançar", 403)
    if not _texto(dados.get("codigo_imovel")) and not _texto(dados.get("imovel_endereco")):
        raise PropostaErro("Informe o imóvel (código do Imoview ou endereço)")
    valor = _num(dados.get("valor"))
    if valor is None or valor <= 0:
        raise PropostaErro("Informe o valor da proposta")
    situacao, forma = _validar(dados)
    valor_permuta = _num(dados.get("valor_permuta"))
    if forma == "permuta" and (valor_permuta is None or valor_permuta <= 0):
        raise PropostaErro("Permuta entra como 2ª proposta: informe o valor do bem permutado")

    user = escopo["user"]
    agora = datetime.now()
    session = SessionLocal()
    try:
        # Lançar "no nome de" alguém: a equipe da proposta passa a ser a do corretor
        # escolhido, não a de quem está lançando.
        id_corretor = corretor_nome = None
        # O gerente escolhido define a equipe quando nao ha corretor: sem isso, a
        # proposta que o diretor lanca para a SENNA nascia sem equipe (ou na dele).
        id_gerente, gerente_nome, team_gerente = _resolver_gerente(
            session, escopo, dados.get("id_gerente"))
        team = (_texto(dados.get("team")) or team_gerente or escopo["team"]
                or _texto(user.team) or None)
        if _texto(dados.get("id_corretor")):
            id_corretor, corretor_nome, team_corretor = _resolver_corretor(session, escopo, dados.get("id_corretor"))
            team = team_corretor or team
        id_visita = _resolver_visita(session, escopo, dados.get("id_visita"), team)

        proposta = PropostaEfetiva(
            codigo_imovel=_texto(dados.get("codigo_imovel"), 50) or None,
            imovel_endereco=_texto(dados.get("imovel_endereco")) or None,
            bairro=_texto(dados.get("bairro"), 120) or None,
            tipo=_texto(dados.get("tipo"), 80) or None,
            numero=_texto(dados.get("numero"), 40) or None,
            bloco=_texto(dados.get("bloco"), 40) or None,
            complemento=_texto(dados.get("complemento"), 80) or None,
            quartos=_texto(dados.get("quartos"), 10) or None,
            vagas=_texto(dados.get("vagas"), 10) or None,
            area=_texto(dados.get("area"), 20) or None,
            valor=valor,
            valor_permuta=valor_permuta if forma == "permuta" else None,
            descricao_permuta=_texto(dados.get("descricao_permuta")) or None if forma == "permuta" else None,
            forma_pagamento=forma,
            situacao=situacao or "em_analise",
            team=team,
            id_gerente=id_gerente,
            gerente_nome=gerente_nome,
            id_corretor=id_corretor,
            corretor_nome=corretor_nome,
            id_visita=id_visita,
            cliente=_texto(dados.get("cliente"), 255) or None,
            observacao=_texto(dados.get("observacao")) or None,
            data_proposta=_data(dados.get("data_proposta")) or date.today(),
            data_fechamento=_data(dados.get("data_fechamento")),
            ultima_acao_em=agora,
            criado_por=_texto(user.id_usuarios),
        )
        session.add(proposta)
        session.flush()
        session.add(PropostaEfetivaAcao(
            proposta_id=proposta.id, descricao="Proposta lançada", situacao=proposta.situacao,
            autor_id=_texto(user.id_usuarios), autor_nome=_texto(user.nome or user.username),
        ))
        session.commit()
        return {"ok": True, "id": proposta.id}
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


CAMPOS_TEXTO = ("codigo_imovel", "imovel_endereco", "bairro", "tipo", "numero", "bloco",
                "complemento", "quartos", "vagas", "area", "cliente", "observacao", "descricao_permuta")


def atualizar(solicitante_id, proposta_id, dados):
    escopo = escopo_do_solicitante(solicitante_id)
    session = SessionLocal()
    try:
        proposta = session.query(PropostaEfetiva).filter(PropostaEfetiva.id == proposta_id).first()
        if not proposta or not proposta.ativo:
            raise PropostaErro("Proposta não encontrada", 404)
        _pode_mexer(escopo, proposta)

        situacao, forma = _validar(dados, parcial=True)
        situacao_anterior = proposta.situacao

        for campo in CAMPOS_TEXTO:
            if campo in dados:
                setattr(proposta, campo, _texto(dados.get(campo)) or None)
        if "id_corretor" in dados:
            if _texto(dados.get("id_corretor")):
                proposta.id_corretor, proposta.corretor_nome, team_corretor = _resolver_corretor(
                    session, escopo, dados.get("id_corretor")
                )
                proposta.team = team_corretor or proposta.team
            else:
                proposta.id_corretor = proposta.corretor_nome = None
        # Trocar o gerente responsavel. Ficava de fora: a tela mandava `id_gerente` e o
        # update ignorava, entao a edicao "salvava" sem mudar nada.
        if "id_gerente" in dados:
            proposta.id_gerente, proposta.gerente_nome, team_gerente = _resolver_gerente(
                session, escopo, dados.get("id_gerente"))
            # A equipe so segue o gerente quando nao ha corretor — o corretor e mais
            # especifico e ja definiu a equipe no bloco acima.
            if not proposta.id_corretor and team_gerente:
                proposta.team = team_gerente
        if "id_visita" in dados:
            proposta.id_visita = _resolver_visita(session, escopo, dados.get("id_visita"), proposta.team)
        if "valor" in dados:
            proposta.valor = _num(dados.get("valor"))
        if "valor_permuta" in dados:
            proposta.valor_permuta = _num(dados.get("valor_permuta"))
        if forma:
            proposta.forma_pagamento = forma
        if "data_proposta" in dados:
            proposta.data_proposta = _data(dados.get("data_proposta")) or proposta.data_proposta
        if situacao:
            proposta.situacao = situacao
            # Fechou: carimba a data (a menos que tenham mandado uma explicita).
            if situacao in SITUACOES_FECHADAS:
                proposta.data_fechamento = _data(dados.get("data_fechamento")) or proposta.data_fechamento or date.today()
            else:
                proposta.data_fechamento = _data(dados.get("data_fechamento"))
        elif "data_fechamento" in dados:
            proposta.data_fechamento = _data(dados.get("data_fechamento"))

        if proposta.forma_pagamento == "permuta" and (proposta.valor_permuta is None or proposta.valor_permuta <= 0):
            raise PropostaErro("Permuta entra como 2ª proposta: informe o valor do bem permutado")

        user = escopo["user"]
        proposta.ultima_acao_em = datetime.now()
        if situacao and situacao != situacao_anterior:
            session.add(PropostaEfetivaAcao(
                proposta_id=proposta.id,
                descricao=f"Situação alterada de {ROTULO_SITUACAO.get(situacao_anterior, situacao_anterior)} para {ROTULO_SITUACAO.get(situacao, situacao)}",
                situacao=situacao, autor_id=_texto(user.id_usuarios),
                autor_nome=_texto(user.nome or user.username),
            ))
        session.commit()
        return {"ok": True}
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def registrar_acao(solicitante_id, proposta_id, dados):
    escopo = escopo_do_solicitante(solicitante_id)
    descricao = _texto(dados.get("descricao"))
    if not descricao:
        raise PropostaErro("Descreva a ação realizada")
    session = SessionLocal()
    try:
        proposta = session.query(PropostaEfetiva).filter(PropostaEfetiva.id == proposta_id).first()
        if not proposta or not proposta.ativo:
            raise PropostaErro("Proposta não encontrada", 404)
        _pode_mexer(escopo, proposta)

        situacao = _texto(dados.get("situacao")).lower() or None
        if situacao and situacao not in SITUACOES:
            raise PropostaErro(f"Situação inválida. Use uma destas: {', '.join(SITUACOES)}")

        user = escopo["user"]
        session.add(PropostaEfetivaAcao(
            proposta_id=proposta.id, descricao=descricao, situacao=situacao,
            autor_id=_texto(user.id_usuarios), autor_nome=_texto(user.nome or user.username),
        ))
        if situacao:
            proposta.situacao = situacao
            if situacao in SITUACOES_FECHADAS and not proposta.data_fechamento:
                proposta.data_fechamento = date.today()
        proposta.ultima_acao_em = datetime.now()
        session.commit()
        return {"ok": True}
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def excluir(solicitante_id, proposta_id):
    """Soft delete — a proposta some da tela mas o historico fica no banco."""
    escopo = escopo_do_solicitante(solicitante_id)
    session = SessionLocal()
    try:
        proposta = session.query(PropostaEfetiva).filter(PropostaEfetiva.id == proposta_id).first()
        if not proposta or not proposta.ativo:
            raise PropostaErro("Proposta não encontrada", 404)
        _pode_mexer(escopo, proposta)
        proposta.ativo = False
        session.commit()
        return {"ok": True}
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
