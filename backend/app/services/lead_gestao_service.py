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
from sqlalchemy import func

from datetime import datetime, timedelta

from app.database import SessionLocal
from app.models.estoque_legado import LeadLegado
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
                "acompanhamento": _acompanhamento(lead),
            },
            "imovel": _imovel_do_lead(session, lead.codigo_imovel),
            "pode_editar": perfil["permissao"] in PERFIS_GESTAO,
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


def atualizar_acompanhamento(solicitante_id, lead_id, dados: Dict[str, Any]) -> Dict[str, Any]:
    """Grava o acompanhamento do lead: contato, visita agendada, motivo e próxima ação.

    Regra de consistência: **visita agendada = não** exige motivo. Sem isso o campo vira
    uma caixa de "não" sem explicação, que é o que o bloco existe para evitar. Com "sim",
    motivo e próxima ação são limpos — deixá-los para trás mostraria um motivo de recusa
    ao lado de uma visita marcada.
    """
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
            # Edição parcial (só o motivo, por exemplo) não pode contornar a regra acima.
            if "motivo_sem_visita" in dados and lead.visita_agendada is False:
                lead.motivo_sem_visita = _texto(dados.get("motivo_sem_visita")) or lead.motivo_sem_visita
            if "proxima_acao" in dados and lead.visita_agendada is False:
                lead.proxima_acao = _texto(dados.get("proxima_acao")) or None

        lead.acompanhamento_por = perfil["id"]
        lead.acompanhamento_em = datetime.now()
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


def resumo(solicitante_id, inicio=None, fim=None, equipe=None, corretor=None) -> Dict[str, Any]:
    """Distribuicoes dos leads do periodo para os graficos.

    Le de `leads_legado` (base interna, indexada), nao do C2S ao vivo: contar precisa
    responder na hora, e a varredura da API deles leva minutos. O custo e que a situacao
    aqui e a da importacao, nao a de agora — por isso a tela diz de onde cada numero vem.

    Uma consulta por eixo com `group by`, em vez de puxar as linhas e agrupar em Python:
    sao 68 mil leads na base e o recorte de um diretor sem filtro pega quase todos.
    """
    session = SessionLocal()
    try:
        perfil = _perfil(session, solicitante_id)
        base = _query_com_escopo(session, perfil, equipe, inicio, fim, corretor)

        def agrupar(coluna):
            linhas = base.with_entities(coluna, func.count(LeadLegado.id)).group_by(coluna).all()
            contagem: Dict[str, int] = {}
            for valor, total in linhas:
                chave = _rotulo(valor)
                contagem[chave] = contagem.get(chave, 0) + int(total or 0)
            return contagem

        total = base.with_entities(func.count(LeadLegado.id)).scalar() or 0

        # Serie do grafico de linha, com granularidade automatica. Um diretor sem filtro
        # de data pega 1591 dias distintos — 1591 circulos no SVG travam a tela e os
        # rotulos viram uma mancha. Acima do limite a serie e agregada por semana e
        # depois por mes; os totais continuam exatos, so o balde muda.
        diario = [
            (d, int(t or 0))
            for d, t in base.with_entities(LeadLegado.data, func.count(LeadLegado.id))
                            .group_by(LeadLegado.data).order_by(LeadLegado.data).all()
            if d
        ]
        if len(diario) <= 62:
            granularidade = "dia"
            por_dia = [
                {"data": d.isoformat(), "label": d.strftime("%d/%m"), "total": t}
                for d, t in diario
            ]
        elif len(diario) <= 400:
            granularidade = "semana"
            baldes: Dict[Any, int] = {}
            for d, t in diario:
                # Segunda-feira da semana do lead.
                inicio_semana = d - timedelta(days=d.weekday())
                baldes[inicio_semana] = baldes.get(inicio_semana, 0) + t
            por_dia = [
                {"data": k.isoformat(), "label": k.strftime("%d/%m"), "total": v}
                for k, v in sorted(baldes.items())
            ]
        else:
            granularidade = "mes"
            baldes = {}
            for d, t in diario:
                baldes[(d.year, d.month)] = baldes.get((d.year, d.month), 0) + t
            por_dia = [
                {"data": f"{ano:04d}-{mes:02d}", "label": f"{mes:02d}/{str(ano)[2:]}", "total": v}
                for (ano, mes), v in sorted(baldes.items())
            ]

        # Acompanhamento: o unico eixo que e nosso, nao do C2S.
        com_acomp = base.filter(LeadLegado.acompanhamento_em.isnot(None)).with_entities(
            func.count(LeadLegado.id)).scalar() or 0
        agendadas = base.filter(LeadLegado.visita_agendada.is_(True)).with_entities(
            func.count(LeadLegado.id)).scalar() or 0
        sem_visita = base.filter(LeadLegado.visita_agendada.is_(False)).with_entities(
            func.count(LeadLegado.id)).scalar() or 0

        contato = agrupar(LeadLegado.contato_status)
        # `contato_status` nulo vira "Nao informado" no agrupador; neste eixo o nome certo
        # e "Sem acompanhamento", que e o que a ausencia significa.
        if "Nao informado" in contato:
            contato["Sem acompanhamento"] = contato.pop("Nao informado")
        contato = {CONTATOS.get(k, k): v for k, v in contato.items()}

        return {
            "ok": True,
            "total": int(total),
            "com_acompanhamento": int(com_acomp),
            "sem_acompanhamento": int(total) - int(com_acomp),
            "visita_agendada": int(agendadas),
            "sem_visita": int(sem_visita),
            "por_dia": por_dia,
            "granularidade": granularidade,
            "dias_com_entrada": len(diario),
            "por_fonte": _top_n(agrupar(LeadLegado.fonte)),
            "por_equipe": _top_n(agrupar(LeadLegado.equipe)),
            "por_corretor": _top_n(agrupar(LeadLegado.atendimento), 10),
            "por_contato": _top_n(contato),
            "motivos_sem_visita": _top_n(agrupar(LeadLegado.motivo_sem_visita), 6),
            "escopo": {
                "ve_tudo": perfil["permissao"] in PERFIS_GLOBAIS,
                "pode_lancar": perfil["permissao"] in PERFIS_GESTAO,
            },
        }
    finally:
        session.close()


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
