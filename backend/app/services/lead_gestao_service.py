"""Leads para o Relatorio do Gerente: listar com escopo e lancar no Contact2Sale.

Separado de `leads_service` de proposito: la mora a IMPORTACAO (C2S -> `leads_legado`,
rodada por cron); aqui mora o uso pela tela, que e o caminho inverso — o gerente cria o
lead no C2S e a importacao do dia seguinte o traz de volta para a base.

Escopo, como no resto do sistema, sai do cadastro do solicitante e nunca do que a tela
manda.
"""
import os
import re
from typing import Any, Dict, List, Optional

import requests
from sqlalchemy import and_, case, func

from datetime import datetime, timedelta

from app.database import SessionLocal
from app.models.estoque_legado import LeadLegado
from app.models.imovel_area import ImovelArea
from app.models.lead_c2s import LeadC2S
from app.models.fato_bases import FatoCaptacao
from app.models.imovel_area import ImovelArea
from app.models.usuarios import Usuarios

C2S_LEADS_URL = "https://api.contact2sale.com/integration/leads"

# Acompanhamento do lead — valores fechados p/ a tela e p/ relatorio depois.
CONTATOS = {
    "sem_contato": "Sem contato",
    "whatsapp": "Contato WhatsApp",
    "telefone": "Contato telefone",
    "email": "Contato e-mail",
}

# Quem enxerga a base inteira.
PERFIS_GLOBAIS = {"administrador", "diretor", "administrativo"}
PERFIS_GESTAO = PERFIS_GLOBAIS | {"gerente"}


class LeadErro(Exception):
    def __init__(self, mensagem, status=400):
        super().__init__(mensagem)
        self.mensagem = mensagem
        self.status = status


def _texto(valor) -> str:
    return str(valor or "").strip()


def _digitos(valor) -> str:
    return re.sub(r"\D", "", _texto(valor))


def _perfil(session, solicitante_id: str) -> Dict[str, Any]:
    user = session.query(Usuarios).filter(
        Usuarios.id_usuarios == _texto(solicitante_id), Usuarios.ativo.is_(True)
    ).first()
    if not user:
        raise LeadErro("Sem permissão para ver leads", 403)
    return {
        "id": user.id_usuarios,
        "nome": _texto(user.nome or user.username),
        "permissao": _texto(user.permissao).lower(),
        "team": _texto(user.team),
    }


def _chaves_do_usuario(user: Usuarios) -> List[str]:
    """`leads_legado.atendimento` guarda ora o id, ora o nome, ora o username."""
    return [v for v in (user.id_usuarios, user.nome, user.username) if _texto(v)]


def _chaves_da_equipe(session, team: str) -> List[str]:
    """Todos os valores que identificam a equipe em `atendimento`/`equipe`."""
    membros = session.query(Usuarios).filter(Usuarios.team == team).all()
    return [c for m in membros for c in _chaves_do_usuario(m)] + [team]


def _filtro_de_escopo(session, perfil: Dict[str, Any], equipe_pedida: Optional[str] = None):
    """Devolve a lista de valores aceitos em `atendimento`, ou None p/ ver tudo.

    `equipe_pedida` só vale para quem já enxerga tudo — é o dropdown de gerente do
    Relatório. Para gerente e corretor ele é ignorado de propósito: o escopo deles sai do
    cadastro, e aceitar o que a tela manda seria deixar o filtro virar burla.
    """
    if perfil["permissao"] in PERFIS_GLOBAIS or perfil["team"].lower() == "administrativo":
        if _texto(equipe_pedida):
            return _chaves_da_equipe(session, _texto(equipe_pedida))
        return None
    if perfil["permissao"] == "gerente" and perfil["team"]:
        # A equipe tambem vem gravada direto no lead (id do gerente ou nome da equipe).
        return _chaves_da_equipe(session, perfil["team"])
    # Corretor e assistente: so os proprios.
    proprio = session.query(Usuarios).filter(Usuarios.id_usuarios == perfil["id"]).first()
    return _chaves_do_usuario(proprio) if proprio else [perfil["id"]]


def _codigo_limpo(valor) -> str:
    """"10.258" -> "10258". O codigo do lead vem do C2S como texto livre."""
    texto = _texto(valor)
    return "".join(ch for ch in texto.split(",")[0] if ch.isdigit()) if texto else ""


def _imovel_do_lead(session, codigo: str) -> Optional[Dict[str, Any]]:
    """Endereco, valor, metragem e data da captacao do imovel citado no lead.

    Duas fontes porque nenhuma tem tudo: o catalogo (`imovel_area`) traz endereco, valor e
    area; a data de captacao so existe em `fato_captacao`. Lead sem codigo, ou com codigo
    que nao esta em lugar nenhum, devolve None — a tela simplesmente nao mostra o bloco.
    """
    codigo = _codigo_limpo(codigo)
    if not codigo:
        return None

    area = session.query(ImovelArea).filter(ImovelArea.codigo == codigo).first()
    captacao = session.query(FatoCaptacao).filter(
        FatoCaptacao.codigo_imovel == codigo
    ).order_by(FatoCaptacao.data_entrada.desc()).first()
    if not area and not captacao:
        return None

    return {
        "codigo": codigo,
        "endereco": (area.endereco if area else None),
        "bairro": (area.bairro if area else None) or (captacao.bairro_nome if captacao else None),
        "tipo": (area.tipo if area else None) or (captacao.tipo_nome if captacao else None),
        "valor": float(area.valor) if area and area.valor is not None
                 else (float(captacao.valor) if captacao and captacao.valor is not None else None),
        "area": float(area.area) if area and area.area is not None else None,
        "quartos": area.quartos if area else None,
        "vagas": area.vagas if area else None,
        "situacao": area.situacao if area else None,
        "data_captacao": captacao.data_entrada.isoformat() if captacao and captacao.data_entrada else None,
    }


def _acompanhamento(lead) -> Dict[str, Any]:
    return {
        "contato_status": lead.contato_status,
        "contato_label": CONTATOS.get(_texto(lead.contato_status)),
        "visita_agendada": lead.visita_agendada,
        "motivo_sem_visita": lead.motivo_sem_visita,
        "proxima_acao": lead.proxima_acao,
        "por": lead.acompanhamento_por,
        "em": lead.acompanhamento_em.isoformat() if lead.acompanhamento_em else None,
    }


def listar(solicitante_id, busca="", page=1, per_page=30, inicio=None, fim=None,
           equipe=None, apenas_nao_vistos=False, corretor=None) -> Dict[str, Any]:
    """Leads do escopo do solicitante, paginados e filtráveis por texto e data.

    "Não visualizado" = sem acompanhamento registrado (`acompanhamento_em` nulo). É o
    equivalente do aviso de visita não visualizada: lead que chegou e ninguém respondeu.
    """
    page = max(int(page or 1), 1)
    per_page = min(max(int(per_page or 30), 1), 100)

    session = SessionLocal()
    try:
        perfil = _perfil(session, solicitante_id)
        query = session.query(LeadLegado)

        chaves = _filtro_de_escopo(session, perfil, equipe)
        if chaves is not None:
            # `equipe` entra no OR porque lead de recepcao chega sem atendimento
            # definido, mas com a equipe preenchida — sem isso ele sumia da tela do
            # gerente justamente quando mais importa (lead novo, ainda sem dono).
            query = query.filter(
                LeadLegado.atendimento.in_(chaves) | LeadLegado.equipe.in_(chaves)
            )

        # Filtro de corretor do topo do relatorio: texto livre com o NOME. Como
        # `atendimento` guarda ora o id, ora o nome, resolve o texto -> ids antes de
        # comparar; sem isso, digitar "Alan" nao acharia os leads gravados como "C61132".
        corretor = _texto(corretor)
        if corretor:
            alvo = f"%{corretor}%"
            chaves_corretor = [c for u in session.query(Usuarios).filter(
                Usuarios.nome.ilike(alvo) | Usuarios.username.ilike(alvo)
                | (Usuarios.id_usuarios == corretor)
            ).all() for c in _chaves_do_usuario(u)]
            condicao = LeadLegado.atendimento.ilike(alvo)
            if chaves_corretor:
                condicao = condicao | LeadLegado.atendimento.in_(chaves_corretor)
            query = query.filter(condicao)

        busca = _texto(busca)
        if busca:
            alvo = f"%{busca}%"
            query = query.filter(
                LeadLegado.cliente.ilike(alvo)
                | LeadLegado.telefone.ilike(alvo)
                | LeadLegado.codigo_imovel.ilike(alvo)
                | LeadLegado.fonte.ilike(alvo)
            )
        if inicio:
            query = query.filter(LeadLegado.data >= inicio)
        if fim:
            query = query.filter(LeadLegado.data <= fim)

        # Conta ANTES da paginação e do filtro de não-vistos, senão o aviso mostraria
        # só o que coube na página.
        total = query.count()
        nao_vistos = query.filter(LeadLegado.acompanhamento_em.is_(None)).count()
        if apenas_nao_vistos:
            query = query.filter(LeadLegado.acompanhamento_em.is_(None))
            total = nao_vistos

        linhas = query.order_by(
            LeadLegado.data.desc().nullslast(), LeadLegado.id.desc()
        ).offset((page - 1) * per_page).limit(per_page).all()

        # Nome de quem atende, p/ a tela nao mostrar "C61064" cru.
        ids = {_texto(l.atendimento) for l in linhas if _texto(l.atendimento)}
        nomes = {}
        if ids:
            nomes = {
                u.id_usuarios: _texto(u.nome or u.username)
                for u in session.query(Usuarios).filter(Usuarios.id_usuarios.in_(list(ids))).all()
            }

        return {
            "ok": True, "total": total, "page": page, "per_page": per_page,
            "paginas": max(-(-total // per_page), 1),
            "escopo": "global" if chaves is None else perfil["permissao"],
            "nao_vistos": nao_vistos,
            "equipe_filtrada": _texto(equipe) or None,
            "pode_lancar": perfil["permissao"] in PERFIS_GESTAO,
            "itens": [{
                "id": l.id,
                "data": l.data.isoformat() if l.data else None,
                "cliente": l.cliente,
                "telefone": l.telefone,
                "codigo_imovel": l.codigo_imovel,
                "fonte": l.fonte,
                "contato": l.contato,
                "relatorio": l.relatorio,
                "atendimento": l.atendimento,
                "atendimento_nome": nomes.get(_texto(l.atendimento)) or l.atendimento,
                "equipe": l.equipe,
                "observacao": l.observacao,
                "contato_status": l.contato_status,
                "contato_label": CONTATOS.get(_texto(l.contato_status)),
                "visita_agendada": l.visita_agendada,
            } for l in linhas],
            "opcoes": {"contatos": [{"value": k, "label": v} for k, v in CONTATOS.items()]},
        }
    finally:
        session.close()


def detalhe(solicitante_id, lead_id) -> Dict[str, Any]:
    session = SessionLocal()
    try:
        perfil = _perfil(session, solicitante_id)
        lead = session.query(LeadLegado).filter(LeadLegado.id == lead_id).first()
        if not lead:
            raise LeadErro("Lead não encontrado", 404)

        chaves = _filtro_de_escopo(session, perfil)
        if chaves is not None and _texto(lead.atendimento) not in chaves and _texto(lead.equipe) not in chaves:
            raise LeadErro("Esse lead é de outra equipe", 403)

        atendente = session.query(Usuarios).filter(
            Usuarios.id_usuarios == _texto(lead.atendimento)
        ).first()
        espelho = session.query(LeadC2S).filter(LeadC2S.id_legado == lead.id).first()
        return {
            "ok": True,
            "lead": {
                "id": lead.id,
                "data": lead.data.isoformat() if lead.data else None,
                "cliente": lead.cliente,
                "telefone": lead.telefone,
                "codigo_imovel": lead.codigo_imovel,
                "fonte": lead.fonte,
                "contato": lead.contato,
                "relatorio": lead.relatorio,
                "atendimento": lead.atendimento,
                "atendimento_nome": _texto(atendente.nome) if atendente else lead.atendimento,
                "equipe": lead.equipe,
                "observacao": lead.observacao,
                "san_observacao": lead.san_observacao,
                # Preferir o espelho: e onde o acompanhamento passou a ser gravado. A
                # coluna do legado continua sendo espelhada por `acompanhar_espelho`,
                # mas ler dela como fonte primaria mostraria dado velho se algum dia o
                # espelhamento falhar.
                "acompanhamento": _acompanhamento(espelho or lead),
                "id_c2s": espelho.id_c2s if espelho else None,
            },
            "imovel": _imovel_do_lead(session, lead.codigo_imovel),
            "pode_editar": perfil["permissao"] in PERFIS_GESTAO,
            "pode_corrigir_dados": perfil["permissao"] in PERFIS_GESTAO,
            "opcoes": {"contatos": [{"value": k, "label": v} for k, v in CONTATOS.items()]},
        }
    finally:
        session.close()


def detalhe_espelho(solicitante_id, id_c2s) -> Dict[str, Any]:
    """Detalhe do lead a partir de `leads_c2s`, no mesmo formato de `detalhe`.

    Existe porque o detalhe antigo so sabia abrir por `leads_legado.id`, e **26% dos
    leads do espelho nao tem linha la**: a importacao legada so aceita lead criado pela
    recepcao ou de fonte Faixa/Indicacao, entao lead de portal (Grupo Zap, DF imoveis,
    ImovelWeb) nunca entrou. Na tela isso aparecia como lead que simplesmente nao abre.

    Medido em 25/08/2026: 5.203 leads sem elo, dos quais 4.761 (91,5%) nao existem em
    `leads_legado` de jeito nenhum. Normalizar a chave de casamento recuperaria 442 —
    por isso o conserto e ler do espelho, nao melhorar o casamento.

    O acompanhamento continua morando em `leads_legado`: quando ha elo (`id_legado`) ele
    vem junto e pode ser editado; sem elo, o lead abre em leitura e a tela diz por que.
    """
    from app.services import lead_c2s_service as c2s

    session = SessionLocal()
    try:
        perfil = _perfil(session, solicitante_id)
        lead = session.query(LeadC2S).filter(LeadC2S.id_c2s == _texto(id_c2s)).first()
        if not lead:
            raise LeadErro("Lead não encontrado", 404)

        # O escopo do espelho e por NOME (o C2S nao conhece nossos ids) — mesma regra da
        # listagem. Duas regras de escopo sobre a mesma tela divergiriam.
        escopo = c2s._escopo(session, solicitante_id, None)
        if escopo["equipe"] and c2s._norm_equipe(lead.equipe) != c2s._norm_equipe(escopo["equipe"]):
            raise LeadErro("Esse lead é de outra equipe", 403)
        if escopo["corretor"] and c2s._norm(escopo["corretor"]) not in c2s._norm(lead.corretor):
            raise LeadErro("Esse lead é de outro corretor", 403)

        legado = None
        if lead.id_legado:
            legado = session.query(LeadLegado).filter(LeadLegado.id == lead.id_legado).first()

        return {
            "ok": True,
            "lead": {
                # `id` e o do legado quando existe: e ele que o PUT/PATCH usam. Nulo
                # avisa a tela de que acompanhamento e edicao nao estao disponiveis.
                "id": legado.id if legado else None,
                "id_c2s": lead.id_c2s,
                "data": lead.data.isoformat() if lead.data else None,
                "cliente": lead.cliente,
                "telefone": lead.telefone,
                "email": lead.email,
                "codigo_imovel": lead.codigo_imovel,
                "fonte": lead.fonte,
                "contato": lead.canal,
                "relatorio": lead.imovel,
                "atendimento": lead.corretor,
                "atendimento_nome": lead.corretor,
                "equipe": lead.equipe,
                "observacao": lead.observacao,
                "san_observacao": None,
                "situacao": lead.situacao,
                "funil": lead.funil,
                "arquivado": lead.arquivado,
                "motivo_arquivamento": lead.motivo_arquivamento,
                "negocio_fechado": lead.negocio_fechado,
                "url": lead.url,
                "ultima_atividade": (lead.ultima_atividade.isoformat()
                                     if lead.ultima_atividade else None),
                # Do proprio espelho: e onde o acompanhamento mora desde a migracao
                # 20260825_acomp_c2s. Antes vinha do legado e por isso 26% dos leads
                # abriam sem nenhum acompanhamento possivel.
                "acompanhamento": _acompanhamento(lead),
            },
            "imovel": _imovel_do_lead(session, lead.codigo_imovel),
            # Acompanhamento vale para todo lead do espelho. `pode_corrigir_dados` e
            # que continua preso ao legado: corrigir nome/telefone grava la, porque no
            # espelho a proxima passada do sync sobrescreveria com o valor do C2S.
            "pode_editar": perfil["permissao"] in PERFIS_GESTAO,
            "pode_corrigir_dados": bool(legado) and perfil["permissao"] in PERFIS_GESTAO,
            "sem_registro_interno": legado is None,
            "opcoes": {"contatos": [{"value": k, "label": v} for k, v in CONTATOS.items()]},
        }
    finally:
        session.close()


# ── Criação no Contact2Sale ─────────────────────────────────────────────────────

# Canais aceitos pela API (`channel_abbrev`).
CANAIS = ("internet", "whatsapp", "telefone", "showroom")


def _headers_c2s(token: str, bearer: bool) -> Dict[str, str]:
    return {
        "Authorization": f"Bearer {token}" if bearer else token,
        "Content-Type": "application/json",
    }


def criar_lead(solicitante_id, dados: Dict[str, Any]) -> Dict[str, Any]:
    """Cria o lead direto no Contact2Sale.

    A API exige **telefone ou e-mail** (sem um dos dois responde 423) e, para empresa do
    tipo imobiliária, o `prop_ref` (código do imóvel) — que aceita os valores especiais
    "Sem código" / "Não localizado" quando o cliente não citou imóvel.

    Não grava em `leads_legado`: quem traz o lead de volta é a importação diária, que já
    resolve corretor e equipe pelas regras dela. Gravar aqui criaria uma segunda verdade,
    com risco de o mesmo lead entrar duas vezes com donos diferentes.
    """
    session = SessionLocal()
    try:
        perfil = _perfil(session, solicitante_id)
        if perfil["permissao"] not in PERFIS_GESTAO:
            raise LeadErro("Sem permissão para lançar lead", 403)
    finally:
        session.close()

    token = os.getenv("CONTACT2SALE_TOKEN") or os.getenv("C2S_TOKEN")
    if not token:
        raise LeadErro("Contact2Sale não configurado (CONTACT2SALE_TOKEN ausente)", 503)

    nome = _texto(dados.get("nome"))
    telefone = _digitos(dados.get("telefone"))
    email = _texto(dados.get("email"))
    if not telefone and not email:
        raise LeadErro("Informe telefone ou e-mail — a API do C2S recusa lead sem os dois")

    canal = _texto(dados.get("canal")).lower() or "telefone"
    if canal not in CANAIS:
        raise LeadErro(f"Canal inválido. Use um destes: {', '.join(CANAIS)}")

    atributos = {
        "name": nome or "Não identificado",
        "phone": telefone,
        "email": email,
        "prop_ref": _texto(dados.get("codigo_imovel")) or "Sem código",
        "description": _texto(dados.get("descricao"))[:250],
        "type_negotiation": _texto(dados.get("negociacao")) or "Comprar",
        "city": _texto(dados.get("cidade")),
        "neighbourhood": _texto(dados.get("bairro")),
        "channel_abbrev": canal,
        "body": _texto(dados.get("mensagem"))[:15000],
        "observation": _texto(dados.get("observacao")),
        "source": _texto(dados.get("origem")) or "lancamento_interno",
    }
    payload = {"data": {"type": "lead", "attributes": {k: v for k, v in atributos.items() if v}}}

    # A importação usa o token cru em `Authorization`; a doc de criação prefere `Bearer`.
    # Tenta o documentado e cai no formato que sabidamente funciona nesta conta.
    resposta = requests.post(C2S_LEADS_URL, headers=_headers_c2s(token, True), json=payload, timeout=45)
    if resposta.status_code in (401, 403):
        resposta = requests.post(C2S_LEADS_URL, headers=_headers_c2s(token, False), json=payload, timeout=45)

    if resposta.status_code == 423:
        raise LeadErro("O C2S recusou: lead precisa de telefone ou e-mail válido", 423)
    if resposta.status_code >= 400:
        raise LeadErro(f"Contact2Sale HTTP {resposta.status_code}: {resposta.text[:300]}", 502)

    corpo = resposta.json() if resposta.content else {}
    return {
        "ok": True,
        "lead_id": corpo.get("lead_id"),
        "recebido_por": (corpo.get("received_by") or {}).get("name"),
        "empresa": corpo.get("company"),
        "aviso": "O lead entra na base interna na próxima importação do C2S (cron diário).",
        "resposta": corpo,
    }


def _aplicar_acompanhamento(lead, dados: Dict[str, Any], autor: str) -> None:
    """Grava contato, visita agendada, motivo e proxima acao em `lead`.

    Regra de consistencia: **visita agendada = nao** exige motivo. Sem isso o campo vira
    uma caixa de "nao" sem explicacao, que e o que o bloco existe para evitar. Com "sim",
    motivo e proxima acao sao limpos — deixa-los para tras mostraria um motivo de recusa
    ao lado de uma visita marcada.

    Extraido para os dois caminhos (espelho e legado) compartilharem a MESMA regra: com a
    validacao duplicada, o primeiro ajuste feito num so deixaria a tela aceitando pela
    Gestao de Leads o que o painel de tarefas recusa.
    """
    if "contato_status" in dados:
        escolha = _texto(dados.get("contato_status"))
        if escolha and escolha not in CONTATOS:
            raise LeadErro(f"Contato inválido. Use um destes: {', '.join(CONTATOS)}")
        lead.contato_status = escolha or None

    if "visita_agendada" in dados:
        bruto = dados.get("visita_agendada")
        agendada = None if bruto in (None, "") else str(bruto).lower() in {"true", "1", "sim"}
        lead.visita_agendada = agendada

        if agendada is False:
            motivo = _texto(dados.get("motivo_sem_visita"))
            if not motivo:
                raise LeadErro("Sem visita agendada: informe o motivo")
            lead.motivo_sem_visita = motivo
            lead.proxima_acao = _texto(dados.get("proxima_acao")) or None
        else:
            lead.motivo_sem_visita = None
            lead.proxima_acao = None
    else:
        # Edicao parcial (so o motivo, por exemplo) nao pode contornar a regra acima.
        if "motivo_sem_visita" in dados and lead.visita_agendada is False:
            lead.motivo_sem_visita = _texto(dados.get("motivo_sem_visita")) or lead.motivo_sem_visita
        if "proxima_acao" in dados and lead.visita_agendada is False:
            lead.proxima_acao = _texto(dados.get("proxima_acao")) or None

    lead.acompanhamento_por = autor
    lead.acompanhamento_em = datetime.now()


def acompanhar_espelho(solicitante_id, id_c2s, dados: Dict[str, Any]) -> Dict[str, Any]:
    """Grava o acompanhamento em `leads_c2s`, pelo id do Contact2Sale.

    E o caminho novo. O antigo escrevia em `leads_legado`, que so tem 74% dos leads: a
    importacao historica descarta lead de portal, entao Grupo Zap, DF imoveis e ImovelWeb
    nao tinham onde registrar acompanhamento.

    `id_legado` continua sendo mantido em espelho quando existe, para o relatorio antigo
    (que le de `leads_legado`) nao regredir enquanto ainda houver quem o consulte.
    """
    from app.services import lead_c2s_service as c2s

    session = SessionLocal()
    try:
        perfil = _perfil(session, solicitante_id)
        if perfil["permissao"] not in PERFIS_GESTAO:
            raise LeadErro("Sem permissão para editar o acompanhamento", 403)

        lead = session.query(LeadC2S).filter(LeadC2S.id_c2s == _texto(id_c2s)).first()
        if not lead:
            raise LeadErro("Lead não encontrado", 404)

        # Escopo por NOME, como no resto do espelho — o C2S nao conhece nossos ids.
        escopo = c2s._escopo(session, solicitante_id, None)
        if escopo["equipe"] and c2s._norm_equipe(lead.equipe) != c2s._norm_equipe(escopo["equipe"]):
            raise LeadErro("Esse lead é de outra equipe", 403)
        if escopo["corretor"] and c2s._norm(escopo["corretor"]) not in c2s._norm(lead.corretor):
            raise LeadErro("Esse lead é de outro corretor", 403)

        _aplicar_acompanhamento(lead, dados, perfil["id"])

        # Espelha no legado quando ha elo: o relatorio historico ainda le de la.
        if lead.id_legado:
            legado = session.query(LeadLegado).filter(LeadLegado.id == lead.id_legado).first()
            if legado:
                for campo in ("contato_status", "visita_agendada", "motivo_sem_visita",
                              "proxima_acao", "acompanhamento_por", "acompanhamento_em"):
                    setattr(legado, campo, getattr(lead, campo))

        session.commit()
        return {"ok": True, "id_c2s": lead.id_c2s, "acompanhamento": _acompanhamento(lead)}
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def atualizar_acompanhamento(solicitante_id, lead_id, dados: Dict[str, Any]) -> Dict[str, Any]:
    """Compatibilidade: grava o acompanhamento pelo id de `leads_legado`.

    O acompanhamento mudou de casa para `leads_c2s` (migracao 20260825_acomp_c2s). Esta
    rota continua existindo porque links e integracoes antigas usam o id inteiro, mas o
    trabalho e feito em `acompanhar_espelho` — uma implementacao so, nao duas regras.

    Sem lead correspondente no espelho, grava direto no legado: e o caso do lead que a
    importacao trouxe mas o sync ainda nao alcancou.
    """
    session = SessionLocal()
    try:
        espelho = session.query(LeadC2S.id_c2s).filter(LeadC2S.id_legado == lead_id).first()
    finally:
        session.close()

    if espelho:
        return acompanhar_espelho(solicitante_id, espelho[0], dados)

    session = SessionLocal()
    try:
        perfil = _perfil(session, solicitante_id)
        if perfil["permissao"] not in PERFIS_GESTAO:
            raise LeadErro("Sem permissão para editar o acompanhamento", 403)

        lead = session.query(LeadLegado).filter(LeadLegado.id == lead_id).first()
        if not lead:
            raise LeadErro("Lead não encontrado", 404)

        chaves = _filtro_de_escopo(session, perfil)
        if chaves is not None and _texto(lead.atendimento) not in chaves and _texto(lead.equipe) not in chaves:
            raise LeadErro("Esse lead é de outra equipe", 403)

        _aplicar_acompanhamento(lead, dados, perfil["id"])
        session.commit()
        return {"ok": True, "id": lead.id, "acompanhamento": _acompanhamento(lead)}
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


# ---------------------------------------------------------------------------
# Resumo agregado para os graficos da Gestao de Leads
# ---------------------------------------------------------------------------

# Campos do lead que a tela pode corrigir. `atendimento` e `equipe` ficam de fora desta
# lista porque nao sao correcao de digitacao — sao repasse de dono, tratado a parte.
CAMPOS_EDITAVEIS = ("cliente", "telefone", "codigo_imovel", "fonte", "observacao")

# Teto de fatias por grafico. Acima disso a pizza vira um anel de lascas ilegiveis e o
# que importa (quem sao os maiores) some no ruido. O resto entra como "Outros".
TOPO_FATIAS = 8


def _rotulo(valor, vazio: str = "Nao informado") -> str:
    return _texto(valor) or vazio


def _top_n(contagem: Dict[str, int], limite: int = TOPO_FATIAS) -> List[Dict[str, Any]]:
    ordenado = sorted(contagem.items(), key=lambda kv: (-kv[1], kv[0]))
    principais = [{"rotulo": k, "total": v} for k, v in ordenado[:limite]]
    resto = sum(v for _, v in ordenado[limite:])
    if resto:
        principais.append({"rotulo": "Outros", "total": resto})
    return principais


def _query_com_escopo(session, perfil, equipe, inicio, fim, corretor=None):
    """Mesmo recorte de `listar`, sem paginacao — para contar em vez de exibir."""
    query = session.query(LeadLegado)
    chaves = _filtro_de_escopo(session, perfil, equipe)
    if chaves is not None:
        query = query.filter(
            LeadLegado.atendimento.in_(chaves) | LeadLegado.equipe.in_(chaves)
        )
    corretor = _texto(corretor)
    if corretor:
        alvo = f"%{corretor}%"
        chaves_corretor = [c for u in session.query(Usuarios).filter(
            Usuarios.nome.ilike(alvo) | Usuarios.username.ilike(alvo)
            | (Usuarios.id_usuarios == corretor)
        ).all() for c in _chaves_do_usuario(u)]
        condicao = LeadLegado.atendimento.ilike(alvo)
        if chaves_corretor:
            condicao = condicao | LeadLegado.atendimento.in_(chaves_corretor)
        query = query.filter(condicao)
    if inicio:
        query = query.filter(LeadLegado.data >= inicio)
    if fim:
        query = query.filter(LeadLegado.data <= fim)
    return query


def _float_ou_none(valor):
    """Numeric do Postgres -> float serializavel. `None` continua `None`."""
    return float(valor) if valor is not None else None


# Faixas de preco do imovel procurado. Cortes redondos e do jeito que a operacao fala do
# produto; faixas de largura igual dariam uma barra gigante embaixo e nada em cima,
# porque a distribuicao de preco e assimetrica.
FAIXAS_VALOR_LEAD = [
    ("Ate 500 mil", None, 500_000),
    ("500 mil a 1 mi", 500_000, 1_000_000),
    ("1 a 2 mi", 1_000_000, 2_000_000),
    ("2 a 3 mi", 2_000_000, 3_000_000),
    ("3 a 5 mi", 3_000_000, 5_000_000),
    ("Acima de 5 mi", 5_000_000, None),
]

# Recencia da ultima atividade no C2S. E a unica leitura de INTERACAO disponivel:
# `replied_at` da API vem vazio em 100% dos leads desta conta, entao tempo de primeira
# resposta nao existe como dado.
FAIXAS_INTERACAO = [
    ("Hoje", 0, 0),
    ("1 a 3 dias", 1, 3),
    ("4 a 7 dias", 4, 7),
    ("8 a 30 dias", 8, 30),
    ("Mais de 30 dias", 31, None),
]


def _base_espelho(session, solicitante_id, inicio, fim, equipe, corretor):
    """Query sobre `leads_c2s` com o mesmo escopo que a listagem da tela usa.

    O escopo do espelho e por NOME (o C2S nao conhece nossos ids), entao reusa
    `lead_c2s_service._escopo` em vez de `_filtro_de_escopo`, que trabalha com ids de
    `leads_legado`. Duas regras de escopo sobre a mesma tela divergiriam.
    """
    from app.services import lead_c2s_service as c2s

    escopo = c2s._escopo(session, solicitante_id, equipe)
    query = session.query(LeadC2S)
    if escopo["equipe"]:
        query = query.filter(func.lower(LeadC2S.equipe) == escopo["equipe"].strip().lower())
    elif _texto(equipe):
        query = query.filter(func.lower(LeadC2S.equipe) == _texto(equipe).strip().lower())
    if escopo["corretor"]:
        query = query.filter(LeadC2S.corretor.ilike(f"%{escopo['corretor'].strip()}%"))
    elif _texto(corretor):
        query = query.filter(LeadC2S.corretor.ilike(f"%{_texto(corretor).strip()}%"))
    if inicio:
        query = query.filter(LeadC2S.data >= inicio)
    if fim:
        query = query.filter(LeadC2S.data <= fim)
    return query, escopo


def resumo(solicitante_id, inicio=None, fim=None, equipe=None, corretor=None) -> Dict[str, Any]:
    """Distribuicoes dos leads do periodo para os graficos.

    Le do espelho `leads_c2s`, a MESMA fonte da listagem. Antes lia `leads_legado`, que
    passa por um filtro de negocio na importacao (so lead criado pela recepcao, ou de
    fonte Faixa/Indicacao) — o resultado eram dois totais na mesma tela: 1474 nos cards
    contra 2264 na lista, para agosto/2026. Populacao diferente, nao bug de contagem.

    Uma consulta por eixo com `group by`: sao dezenas de milhares de leads e o recorte de
    um diretor sem filtro pega quase todos.
    """
    session = SessionLocal()
    try:
        base, escopo_c2s = _base_espelho(session, solicitante_id, inicio, fim, equipe, corretor)
        perfil = _perfil(session, solicitante_id)

        def agrupar(coluna):
            linhas = base.with_entities(coluna, func.count(LeadC2S.id_c2s)).group_by(coluna).all()
            contagem: Dict[str, int] = {}
            for valor, total in linhas:
                chave = _rotulo(valor)
                contagem[chave] = contagem.get(chave, 0) + int(total or 0)
            return contagem

        total = base.with_entities(func.count(LeadC2S.id_c2s)).scalar() or 0

        # Serie do grafico de linha, com granularidade automatica. Um diretor sem filtro
        # de data pega milhares de dias distintos — um circulo por dia trava o SVG e os
        # rotulos viram mancha. Acima do limite a serie e agregada por semana e depois
        # por mes; os totais continuam exatos, so o balde muda.
        diario = [
            (d, int(t or 0))
            for d, t in base.with_entities(LeadC2S.data, func.count(LeadC2S.id_c2s))
                            .group_by(LeadC2S.data).order_by(LeadC2S.data).all()
            if d
        ]
        if len(diario) <= 62:
            granularidade = "dia"
            por_dia = [{"data": d.isoformat(), "label": d.strftime("%d/%m"), "total": t}
                       for d, t in diario]
        elif len(diario) <= 400:
            granularidade = "semana"
            baldes: Dict[Any, int] = {}
            for d, t in diario:
                inicio_semana = d - timedelta(days=d.weekday())
                baldes[inicio_semana] = baldes.get(inicio_semana, 0) + t
            por_dia = [{"data": k.isoformat(), "label": k.strftime("%d/%m"), "total": v}
                       for k, v in sorted(baldes.items())]
        else:
            granularidade = "mes"
            baldes = {}
            for d, t in diario:
                baldes[(d.year, d.month)] = baldes.get((d.year, d.month), 0) + t
            por_dia = [{"data": f"{ano:04d}-{mes:02d}", "label": f"{mes:02d}/{str(ano)[2:]}",
                        "total": v}
                       for (ano, mes), v in sorted(baldes.items())]

        arquivados = base.filter(LeadC2S.arquivado.is_(True)).with_entities(
            func.count(LeadC2S.id_c2s)).scalar() or 0
        fechados = base.filter(LeadC2S.negocio_fechado.is_(True)).with_entities(
            func.count(LeadC2S.id_c2s)).scalar() or 0

        # Acompanhamento e coluna NOSSA (`leads_legado`), nao vem do C2S. O elo e o
        # `id_legado` resolvido no sync — sem ele o lead nunca teve acompanhamento.
        # Acompanhamento agora e coluna do proprio espelho: some o join com
        # `leads_legado`, que so cobria 74% dos leads e por isso subcontava.
        com_acomp = base.filter(LeadC2S.acompanhamento_em.isnot(None)).with_entities(
            func.count(LeadC2S.id_c2s)).scalar() or 0
        agendadas = base.filter(LeadC2S.visita_agendada.is_(True)).with_entities(
            func.count(LeadC2S.id_c2s)).scalar() or 0
        sem_visita = base.filter(LeadC2S.visita_agendada.is_(False)).with_entities(
            func.count(LeadC2S.id_c2s)).scalar() or 0

        contato: Dict[str, int] = {}
        for valor, qtd in base.with_entities(
            LeadC2S.contato_status, func.count(LeadC2S.id_c2s)
        ).group_by(LeadC2S.contato_status).all():
            rotulo = CONTATOS.get(_texto(valor), _texto(valor)) if _texto(valor) else None
            if rotulo:
                contato[rotulo] = contato.get(rotulo, 0) + int(qtd or 0)
        contato["Sem acompanhamento"] = int(total) - sum(contato.values())

        # ── o que o lead procurava ────────────────────────────────────────────
        # Bairro, tipo, quartos e valor nao existem no lead: moram no catalogo, e o elo e
        # o `prop_ref` que o cliente citou. O join e INTERNO de proposito — lead sem
        # codigo, ou com codigo que nao esta no catalogo, simplesmente nao entra nestes
        # graficos. Contar esses como "Nao informado" inflaria uma categoria que nao diz
        # nada sobre demanda; `leads_com_imovel` deixa a cobertura explicita.
        com_imovel = base.join(ImovelArea, ImovelArea.codigo == LeadC2S.codigo_imovel)
        leads_com_imovel = com_imovel.with_entities(func.count(LeadC2S.id_c2s)).scalar() or 0

        def agrupar_imovel(coluna, limite=TOPO_FATIAS):
            linhas = com_imovel.with_entities(coluna, func.count(LeadC2S.id_c2s)) \
                               .group_by(coluna).all()
            contagem: Dict[str, int] = {}
            for valor, qtd in linhas:
                if valor is None or _texto(valor) == "":
                    continue
                contagem[_texto(valor)] = contagem.get(_texto(valor), 0) + int(qtd or 0)
            return _top_n(contagem, limite)

        # Quartos e numero: ordena por quantidade de quartos, nao por volume — fora dessa
        # ordem o grafico deixa de ser distribuicao e vira ranking.
        quartos_bruto = {
            int(q): int(qtd or 0)
            for q, qtd in com_imovel.with_entities(
                ImovelArea.quartos, func.count(LeadC2S.id_c2s)
            ).filter(ImovelArea.quartos.isnot(None)).group_by(ImovelArea.quartos).all()
            if q is not None
        }
        por_quartos = [
            {"rotulo": f"{q} quarto{'s' if q != 1 else ''}" if q else "Sem quarto",
             "total": quartos_bruto[q]}
            for q in sorted(quartos_bruto)
        ]

        # Faixa de valor num `case` so, para nao virar seis consultas.
        ramos_valor = []
        for rotulo, minimo, maximo in FAIXAS_VALOR_LEAD:
            condicoes = []
            if minimo is not None:
                condicoes.append(ImovelArea.valor >= minimo)
            if maximo is not None:
                condicoes.append(ImovelArea.valor < maximo)
            ramos_valor.append((and_(*condicoes), rotulo))
        faixa_valor = case(*ramos_valor, else_=None)
        valor_bruto = dict(
            com_imovel.with_entities(faixa_valor, func.count(LeadC2S.id_c2s))
                      .group_by(faixa_valor).all()
        )
        por_faixa_valor = [{"rotulo": r, "total": int(valor_bruto.get(r, 0) or 0)}
                           for r, _, _ in FAIXAS_VALOR_LEAD]

        # Metricas do imovel procurado. A mediana entra ao lado da media porque um lead
        # numa mansao de 20 mi puxa a media inteira; a mediana diz onde a demanda esta.
        metricas = com_imovel.with_entities(
            func.avg(ImovelArea.valor),
            func.percentile_cont(0.5).within_group(ImovelArea.valor.asc()),
            func.min(ImovelArea.valor),
            func.max(ImovelArea.valor),
            func.avg(func.nullif(ImovelArea.area, 0)),
            func.avg(ImovelArea.quartos),
            func.count(ImovelArea.valor),
        ).one()
        metricas_imovel = {
            "valor_medio": _float_ou_none(metricas[0]),
            "valor_mediano": _float_ou_none(metricas[1]),
            "valor_min": _float_ou_none(metricas[2]),
            "valor_max": _float_ou_none(metricas[3]),
            "area_media": _float_ou_none(metricas[4]),
            "quartos_medio": _float_ou_none(metricas[5]),
            "com_valor": int(metricas[6] or 0),
        }

        # ── interacao: recencia da ultima atividade no C2S ────────────────────
        dias_sem = func.date_part("day", func.now() - LeadC2S.ultima_atividade)
        ramos_int = []
        for rotulo, minimo, maximo in FAIXAS_INTERACAO:
            condicoes = [dias_sem >= minimo]
            if maximo is not None:
                condicoes.append(dias_sem <= maximo)
            ramos_int.append((and_(*condicoes), rotulo))
        faixa_int = case(*ramos_int, else_="Sem atividade")
        int_bruto = dict(
            base.with_entities(faixa_int, func.count(LeadC2S.id_c2s))
                .group_by(faixa_int).all()
        )
        por_interacao = [{"rotulo": r, "total": int(int_bruto.get(r, 0) or 0)}
                         for r, _, _ in FAIXAS_INTERACAO]
        sem_atividade = int(int_bruto.get("Sem atividade", 0) or 0)
        if sem_atividade:
            por_interacao.append({"rotulo": "Sem atividade", "total": sem_atividade})

        sincronizado = session.query(func.max(LeadC2S.sincronizado_em)).scalar()

        return {
            "ok": True,
            "total": int(total),
            "com_acompanhamento": int(com_acomp),
            "sem_acompanhamento": int(total) - int(com_acomp),
            "visita_agendada": int(agendadas),
            "sem_visita": int(sem_visita),
            "arquivados": int(arquivados),
            "negocios_fechados": int(fechados),
            "por_dia": por_dia,
            "granularidade": granularidade,
            "dias_com_entrada": len(diario),
            "por_fonte": _top_n(agrupar(LeadC2S.fonte)),
            "por_equipe": _top_n(agrupar(LeadC2S.equipe)),
            "por_corretor": _top_n(agrupar(LeadC2S.corretor), 10),
            # Lista COMPLETA para o dropdown de filtro — `por_corretor` e o grafico, e
            # corta no 10o com "Outros". Os nomes saem do proprio espelho para casarem
            # exatamente com o que o filtro compara; uma lista vinda do cadastro traria
            # grafia diferente e o filtro devolveria vazio.
            "corretores": sorted(
                {c for c in agrupar(LeadC2S.corretor) if c and c != "Nao informado"},
                key=lambda x: x.lower(),
            ),
            "por_situacao": _top_n(agrupar(LeadC2S.situacao)),
            "por_canal": _top_n(agrupar(LeadC2S.canal)),
            "por_funil": _top_n(agrupar(LeadC2S.funil)),
            "motivos_arquivamento": _top_n(
                {k: v for k, v in agrupar(LeadC2S.motivo_arquivamento).items()
                 if k != "Nao informado"}, 8),
            "por_contato": _top_n(contato),
            "por_interacao": por_interacao,
            "leads_com_imovel": int(leads_com_imovel),
            "por_bairro_imovel": agrupar_imovel(ImovelArea.bairro, 10),
            "por_tipo_imovel": agrupar_imovel(ImovelArea.tipo),
            "por_quartos": por_quartos,
            "por_faixa_valor_imovel": por_faixa_valor,
            "metricas_imovel": metricas_imovel,
            "fonte_dados": "leads_c2s",
            "sincronizado_em": sincronizado.isoformat() if sincronizado else None,
            "escopo": {
                "ve_tudo": perfil["permissao"] in PERFIS_GLOBAIS,
                "pode_lancar": perfil["permissao"] in PERFIS_GESTAO,
            },
        }
    finally:
        session.close()

def editar_lead_espelho(solicitante_id, id_c2s, dados: Dict[str, Any]) -> Dict[str, Any]:
    """Corrige os dados do lead a partir do id do C2S.

    A correcao continua gravando em `leads_legado`, nao no espelho: `cliente`, `telefone`
    e `fonte` sao campos DO C2S, e a passada horaria do sync sobrescreveria o que fosse
    escrito no espelho. Por isso, sem registro no legado nao ha onde corrigir — e a
    resposta diz isso em vez de fingir que gravou.
    """
    session = SessionLocal()
    try:
        lead = session.query(LeadC2S).filter(LeadC2S.id_c2s == _texto(id_c2s)).first()
        if not lead:
            raise LeadErro("Lead não encontrado", 404)
        id_legado = lead.id_legado
    finally:
        session.close()

    if not id_legado:
        raise LeadErro(
            "Esse lead veio de portal e não tem registro na base histórica — não há onde "
            "gravar a correção. O acompanhamento continua disponível.", 409)
    return editar_lead(solicitante_id, id_legado, dados)


def editar_lead(solicitante_id, lead_id, dados: Dict[str, Any]) -> Dict[str, Any]:
    """Corrige os dados do lead na base interna.

    Nao propaga para o Contact2Sale: a integracao e de leitura, e a importacao diaria
    pula o que ja existe em vez de reescrever — entao a correcao feita aqui sobrevive a
    proxima carga. O outro lado disso: o C2S continua com o valor antigo, e quem olhar
    la vai ver a divergencia.

    Repasse de dono (`atendimento`) e tratado a parte de proposito. Nao e correcao de
    digitacao: muda de quem e o lead, entao gerente so repassa dentro da propria equipe
    e perfil global repassa para qualquer um.
    """
    session = SessionLocal()
    try:
        perfil = _perfil(session, solicitante_id)
        if perfil["permissao"] not in PERFIS_GESTAO:
            raise LeadErro("Sem permissao para editar lead", 403)

        lead = session.query(LeadLegado).filter(LeadLegado.id == lead_id).first()
        if not lead:
            raise LeadErro("Lead nao encontrado", 404)

        chaves = _filtro_de_escopo(session, perfil)
        if chaves is not None and _texto(lead.atendimento) not in chaves and _texto(lead.equipe) not in chaves:
            raise LeadErro("Esse lead e de outra equipe", 403)

        alterados: List[str] = []
        for campo in CAMPOS_EDITAVEIS:
            if campo not in dados:
                continue
            valor = _texto(dados.get(campo))
            if campo == "cliente" and not valor:
                raise LeadErro("Nome do cliente nao pode ficar vazio")
            if campo == "telefone":
                valor = _digitos(valor) or valor
            if valor != _texto(getattr(lead, campo)):
                setattr(lead, campo, valor or None)
                alterados.append(campo)

        if "atendimento" in dados:
            novo_dono = _texto(dados.get("atendimento"))
            if novo_dono:
                usuario = session.query(Usuarios).filter(
                    Usuarios.id_usuarios == novo_dono, Usuarios.ativo.is_(True)
                ).first()
                if not usuario:
                    raise LeadErro("Corretor de destino nao encontrado", 404)
                if chaves is not None and _texto(usuario.team) != _texto(perfil["team"]):
                    raise LeadErro("So da para repassar dentro da propria equipe", 403)
                if _texto(lead.atendimento) != novo_dono:
                    lead.atendimento = novo_dono
                    lead.equipe = _texto(usuario.team) or lead.equipe
                    alterados.append("atendimento")

        if alterados:
            session.commit()

        return {"ok": True, "id": lead.id, "alterados": alterados}
    except LeadErro:
        session.rollback()
        raise
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
