"""Gestao de Visitas: listagem com resposta do cliente e pendencia de revisao.

Separado de `gerente_visitas_service` (que serve o Relatorio do Gerente) porque aqui a
unidade e a VISITA com seu estado de revisao, nao o corretor com seus numeros.

`visitas` guarda visita REALIZADA — nao ha campo de agendamento futuro. Qualquer leitura
de "agenda" nesta tela e distribuicao do que ja aconteceu.
"""
from datetime import date, datetime
from typing import Any, Dict, List, Optional

from sqlalchemy import or_

from app.database import SessionLocal
from app.models.gerente_visita_visualizada import GerenteVisitaVisualizada
from app.models.usuarios import Usuarios
from app.models.visita import Avaliacao, ClienteVisita, Visita

PERFIS_GLOBAIS = {"administrador", "administrativo", "diretor", "inteligencia"}
MAX_LINHAS = 3000


class VisitaGestaoErro(Exception):
    def __init__(self, mensagem, status=400):
        super().__init__(mensagem)
        self.mensagem = mensagem
        self.status = status


def _texto(valor) -> str:
    return "" if valor is None else str(valor).strip()


def _data(valor) -> Optional[date]:
    if not valor:
        return None
    try:
        return datetime.strptime(str(valor)[:10], "%Y-%m-%d").date()
    except (TypeError, ValueError):
        return None


def _motivo_preenchido(visita) -> bool:
    """O campo cobrado depende da resposta: SIM -> motivo_sim, TALVEZ -> motivo_talvez."""
    resposta = _texto(visita.proposta).casefold()
    if resposta == "sim":
        return bool(_texto(getattr(visita, "motivo_sim", "")))
    if resposta == "talvez":
        return bool(_texto(getattr(visita, "motivo_talvez", "")))
    return True  # resposta NAO (ou vazia) nao exige motivo


def pendencias_de_revisao(visita, flags) -> List[str]:
    """O que ainda falta o gerente revisar nesta visita.

    Cada evidencia so e cobrada quando ha o que ver: anexo se a visita tem anexo, notas se
    tem nota, motivo se a RESPOSTA exige um (SIM ou TALVEZ). Sem essas condicoes a
    pendencia vira impossivel de resolver — nao da para "ver o anexo" de uma visita que
    nao tem anexo, e nem faz sentido pedir motivo de quem respondeu NAO.

    Definicao unica de proposito: o painel de tarefas tinha a sua propria, olhando so as
    flags, e por isso mostrava 25 pendencias de motivo em visitas que nao exigiam motivo
    nenhum (medido em 25/08/2026).
    """
    tem_nota = bool(visita.audiodescricao_cliente_visita or visita.link_audio)
    tem_anexo = bool(visita.anexo_ficha_visita or visita.link_imagem)

    pendencias = []
    if tem_anexo and not (flags and flags.viu_anexo):
        pendencias.append("anexo")
    if tem_nota and not (flags and flags.viu_notas):
        pendencias.append("notas")
    if not _motivo_preenchido(visita) and not (flags and flags.add_motivo):
        pendencias.append("motivo")
    return pendencias


# Nomes das notas: coluna do banco -> chave que `editar_visita` espera no payload. Sao
# diferentes por heranca do AppSheet, e sem esta traducao a tela leria `planta_imovel` e
# gravaria `planta` — o campo abriria preenchido e salvaria vazio.
NOTAS = (
    ("localizacao", "localizacao"),
    ("tamanho", "tamanho"),
    ("planta_imovel", "planta"),
    ("qualidade_acabamento", "acabamento"),
    ("estado_conservacao", "conservacao"),
    ("condominio_areacomun", "condominio"),
    ("preco", "preco"),
    ("nota_geral", "notaGeral"),
)


def _nota(valor) -> Optional[float]:
    return float(valor) if valor is not None else None


def _avaliacoes_por_visita(session, ids: List[str]) -> Dict[str, List[Dict[str, Any]]]:
    """Notas de cada visita, ja no formato que o PUT aceita.

    Uma consulta para o lote inteiro em vez de uma por visita: a listagem traz ate
    `MAX_LINHAS` visitas e o `N+1` custaria uma ida ao banco por linha.

    Uma visita pode ter mais de uma avaliacao — uma por cliente que assinou. Por isso
    lista, nao objeto: com um objeto so, editar a nota de um cliente sobrescreveria a do
    outro.
    """
    if not ids:
        return {}
    por_visita: Dict[str, List[Dict[str, Any]]] = {}
    # `ClienteVisita` e a dimensao de clientes (uma linha por `id_cliente`), nao a
    # associacao visita-cliente. A avaliacao ja carrega ambos os ids; aqui o join serve
    # somente para resolver o nome de quem avaliou.
    linhas = (session.query(Avaliacao, ClienteVisita)
              .outerjoin(ClienteVisita, ClienteVisita.id_cliente == Avaliacao.id_cliente)
              .filter(Avaliacao.id_visita.in_(ids)).all())
    for avaliacao, cliente in linhas:
        item = {
            "id_avaliacao": avaliacao.id_avaliacao,
            "id_cliente": _texto(avaliacao.id_cliente),
            "cliente": _texto(cliente.nome_cliente) if cliente else "",
            "precoNota10": _texto(avaliacao.preco_n10),
        }
        for coluna, chave in NOTAS:
            item[chave] = _nota(getattr(avaliacao, coluna))
        por_visita.setdefault(_texto(avaliacao.id_visita), []).append(item)
    return por_visita


def listar(solicitante_id, inicio=None, fim=None, equipe=None, id_visita=None) -> Dict[str, Any]:
    session = SessionLocal()
    try:
        user = session.query(Usuarios).filter(
            Usuarios.id_usuarios == _texto(solicitante_id), Usuarios.ativo.is_(True)
        ).first()
        if not user:
            raise VisitaGestaoErro("Sem permissão para ver visitas", 403)

        permissao = _texto(user.permissao).casefold()
        team = _texto(user.team)
        ve_tudo = permissao in PERFIS_GLOBAIS or team.casefold() == "administrativo"

        # `outerjoin` no corretor: visita de corretor apagado nao pode sumir da lista.
        query = session.query(Visita, Usuarios, ClienteVisita, GerenteVisitaVisualizada).outerjoin(
            Usuarios, Usuarios.id_usuarios == Visita.id_corretor
        ).outerjoin(
            ClienteVisita, ClienteVisita.id_cliente == Visita.id_cliente_assinante
        ).outerjoin(
            GerenteVisitaVisualizada,
            (GerenteVisitaVisualizada.id_visita == Visita.id_visita)
            & (GerenteVisitaVisualizada.id_gerente == Usuarios.team),
        )

        # Recorte por id: e o caminho do detalhe. Passa pelo mesmo filtro de escopo
        # abaixo de proposito — abrir uma visita pelo id nao pode furar a regra de
        # equipe que a listagem aplica.
        if _texto(id_visita):
            query = query.filter(Visita.id_visita == _texto(id_visita))

        d_inicio, d_fim = _data(inicio), _data(fim)
        if d_inicio:
            query = query.filter(Visita.data_visita >= d_inicio)
        if d_fim:
            query = query.filter(Visita.data_visita <= d_fim)

        if not ve_tudo:
            if permissao == "gerente" and team:
                query = query.filter(Usuarios.team == team)
            else:
                query = query.filter(Visita.id_corretor == user.id_usuarios)
        elif _texto(equipe):
            query = query.filter(Usuarios.team == _texto(equipe))

        itens: List[Dict[str, Any]] = []
        linhas_visita = query.order_by(
            Visita.data_visita.desc()
        ).limit(MAX_LINHAS).all()
        notas = _avaliacoes_por_visita(session, [v.id_visita for v, *_ in linhas_visita])

        for visita, corretor, cliente, flags in linhas_visita:
            tem_nota = bool(visita.audiodescricao_cliente_visita or visita.link_audio)
            tem_anexo = bool(visita.anexo_ficha_visita or visita.link_imagem)
            pendencias = pendencias_de_revisao(visita, flags)

            itens.append({
                "id_visita": visita.id_visita,
                "data_visita": visita.data_visita.isoformat() if visita.data_visita else None,
                "imovel": visita.id_imovel or visita.endereco_externo or "",
                # Separados do rotulo acima: o PDF do imovel e o do cliente precisam do
                # ID, e `imovel` mistura codigo com endereco livre — nao da para derivar.
                "id_imovel": _texto(visita.id_imovel),
                "id_cliente": _texto(visita.id_cliente_assinante),
                "cliente": _texto(cliente.nome_cliente) if cliente else "",
                "corretor": _texto(corretor.nome or corretor.username) if corretor else _texto(visita.id_corretor),
                "equipe": _texto(corretor.team) if corretor else "",
                "proposta": _texto(visita.proposta),
                "tem_nota": tem_nota,
                "tem_anexo": tem_anexo,
                # Campos editaveis pela propria tela — sem eles o modal abriria vazio e
                # salvar apagaria o que ja estava preenchido.
                "endereco_externo": _texto(visita.endereco_externo),
                "motivo_sim": _texto(getattr(visita, "motivo_sim", "")),
                "motivo_talvez": _texto(getattr(visita, "motivo_talvez", "")),
                "link_imagem": _texto(visita.link_imagem),
                "link_audio": _texto(visita.link_audio),
                "anexo_ficha_visita": _texto(visita.anexo_ficha_visita),
                # `situacao_imovel` e derivado, nao coluna: a escrita aceita quatro
                # valores mas grava so dois estados (`tipo_captacao` preenchido ou
                # `imovel_nao_captado`), entao CAPTACAO_61 / _PROPRIA / _PARCEIRO
                # colapsam num so. Devolver o estado real evita a tela mostrar uma
                # escolha que o banco nao guarda.
                "situacao_imovel": ("IMOVEL_NAO_CAPTADO" if visita.imovel_nao_captado
                                    else ("CAPTACAO_61" if _texto(visita.tipo_captacao) else "")),
                "motivo_ok": _motivo_preenchido(visita),
                # Uma por cliente que assinou a visita — o PUT aceita a lista de volta.
                "avaliacoes": notas.get(_texto(visita.id_visita), []),
                "pendencias": pendencias,
                "revisao_pendente": bool(pendencias),
                "visto_em": flags.visualizado_em.isoformat() if flags and flags.visualizado_em else None,
            })

        return {
            "ok": True,
            "itens": itens,
            "escopo": {"ve_tudo": ve_tudo, "team": team or None},
        }
    finally:
        session.close()


def detalhe(solicitante_id, id_visita) -> Dict[str, Any]:
    """Uma visita, com o mesmo formato e o mesmo escopo da listagem.

    Reusa `listar` em vez de repetir os joins e o calculo de pendencia: duas montagens
    do mesmo payload divergiriam na primeira vez que a regra de pendencia mudasse, e a
    tela de tarefas mostraria uma coisa e a de visitas outra.
    """
    resposta = listar(solicitante_id, id_visita=id_visita)
    itens = resposta.get("itens") or []
    if not itens:
        raise VisitaGestaoErro("Visita nao encontrada ou fora do seu escopo", 404)
    return {"ok": True, "visita": itens[0], "escopo": resposta.get("escopo")}
