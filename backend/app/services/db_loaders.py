"""
Loaders que devolvem dados do Postgres no MESMO formato que as planilhas do
Google Sheets devolviam (lista de dict, todo valor como string, mesmos nomes
de coluna). Isso permite trocar a ORIGEM dos dados sem tocar na logica de
negocio que ja espera esse formato (_parse_ddmmyyyy_safe, _is_true, float(), etc.).

Cada funcao aqui e o substituto direto de uma leitura de aba especifica do
Google Sheets. Quem usa: visita_service.py, rela_gerentes_service.py,
imovel_rel_service.py, relatorio_visita_service.py, gerente_visitas_service.py
(dominio visitas/corretor) e ranking_service.py / meta_service.py (dominio
contratos/captacao).
"""

from typing import Any, Dict, List

from app.database import SessionLocal
from app.models.usuarios import Usuarios
from app.models.equipe import Equipe
from app.models.visita import (
    ClienteVisita, ParceiroVisita, Visita, VisitaCliente, VisitaParceiro, Avaliacao,
)
from app.models.contrato import Contrato, DivisaoComissao, HEADER_POR_SLUG
from app.models.estoque_legado import LeadLegado
from app.models.eventos_imovel_legado import EventoImovelLegado


def _s(v: Any) -> str:
    return "" if v is None else str(v)


def _data_str(d) -> str:
    return d.strftime("%d/%m/%Y") if d else ""


def _datetime_str(dt_) -> str:
    return dt_.strftime("%d/%m/%Y %H:%M:%S") if dt_ else ""


def _bool_str(b) -> str:
    if b is None:
        return ""
    return "TRUE" if b else "FALSE"


def _num_str(n) -> str:
    return "" if n is None else str(n)


# ---------------------------------------------------------------------------
# Dominio usuarios/equipes (substitui Dim_Corretor / Dim_Gerente)
# ---------------------------------------------------------------------------

def carregar_dim_corretor() -> List[Dict[str, str]]:
    session = SessionLocal()
    try:
        usuarios = session.query(Usuarios).filter(Usuarios.id_usuarios.isnot(None)).all()
        return [
            {
                "IdCorretor": _s(u.id_usuarios),
                "Nome": _s(u.nome),
                "IdGerente": _s(u.team),
                "IdImoview": _s(u.id_imoview),
                "Email": _s(u.email),
                "Instragram": _s(u.instagram),
                "Telefone": _s(u.telefone),
                "Descricao": _s(u.descricao),
                "Gerente?": _bool_str(u.permissao == "gerente"),
            }
            for u in usuarios
        ]
    finally:
        session.close()


def carregar_dim_gerente() -> List[Dict[str, str]]:
    session = SessionLocal()
    try:
        equipes = session.query(Equipe).all()
        nomes_gerente = {
            u.id_usuarios: u.nome
            for u in session.query(Usuarios).filter(Usuarios.permissao == "gerente").all()
        }
        return [
            {
                "IdGerente": _s(e.id_equipe),
                "Nome": _s(nomes_gerente.get(e.id_equipe, "")),
                "Equipe": _s(e.nome),
                "email": _s(e.email),
            }
            for e in equipes
        ]
    finally:
        session.close()


# ---------------------------------------------------------------------------
# Dominio visitas
# ---------------------------------------------------------------------------

def carregar_dim_cliente_visita() -> List[Dict[str, str]]:
    session = SessionLocal()
    try:
        return [
            {
                "Id_Cliente": _s(c.id_cliente),
                "Nome_Cliente": _s(c.nome_cliente),
                "Telefone_Cliente": _s(c.telefone_cliente),
                "Email_Cliente": _s(c.email_cliente),
                "CreatedBy": _s(c.created_by),
                "Id_Corretor": _s(c.id_corretor),
            }
            for c in session.query(ClienteVisita).all()
        ]
    finally:
        session.close()


def carregar_dim_parceiro_visita() -> List[Dict[str, str]]:
    session = SessionLocal()
    try:
        return [
            {
                "Id_Parceiro": _s(p.id_parceiro),
                "Nome_Parceiro": _s(p.nome_parceiro),
                "Imobiliaria": _s(p.imobiliaria),
                "Id_Corretor": _s(p.id_corretor),
            }
            for p in session.query(ParceiroVisita).all()
        ]
    finally:
        session.close()


def carregar_fato_visitas() -> List[Dict[str, str]]:
    session = SessionLocal()
    try:
        return [
            {
                "Id_Visita": _s(v.id_visita),
                "Id_Imovel": _s(v.id_imovel),
                "Data_Visita": _data_str(v.data_visita),
                "Id_Corretor": _s(v.id_corretor),
                "Anexo_Ficha_Visita": _s(v.anexo_ficha_visita),
                "AudiodescricaoClienteVisita": _s(v.audiodescricao_cliente_visita),
                "Link_Audio": _s(v.link_audio),
                "Link_Imagem": _s(v.link_imagem),
                "Visita_Com_Parceiro": _bool_str(v.visita_com_parceiro),
                "Tipo_Captacao": _s(v.tipo_captacao),
                "Endereco_Externo": _s(v.endereco_externo),
                "Proposta": _s(v.proposta),
                "CreatedAt": _datetime_str(v.created_at),
                "CreatedBy": _s(v.created_by),
                "Assinatura": _s(v.assinatura),
                "Id_Cliente_Assinante": _s(v.id_cliente_assinante),
                "Id_Parceiro": _s(v.id_parceiro),
                "Imovel_Nao_Captado": _bool_str(v.imovel_nao_captado),
                "Motivo_Talvez": _s(v.motivo_talvez),
                "Revisita": _bool_str(v.revisita),
            }
            for v in session.query(Visita).all()
        ]
    finally:
        session.close()


def carregar_fato_cliente_visita() -> List[Dict[str, str]]:
    session = SessionLocal()
    try:
        return [
            {
                "Id_ClienteVisita": _s(r.id_clientevisita_origem or r.id),
                "Id_Visita": _s(r.id_visita),
                "Id_Cliente": _s(r.id_cliente),
                "Papel_na_Visita": _s(r.papel_na_visita),
            }
            for r in session.query(VisitaCliente).all()
        ]
    finally:
        session.close()


def carregar_fato_parceiro_visita() -> List[Dict[str, str]]:
    session = SessionLocal()
    try:
        return [
            {
                "Id_ParceiroVisita": _s(r.id_parceirovisita_origem or r.id),
                "Id_Visita": _s(r.id_visita),
                "Id_Parceiro": _s(r.id_parceiro),
                "Papel_na_Visita": _s(r.papel_na_visita),
            }
            for r in session.query(VisitaParceiro).all()
        ]
    finally:
        session.close()


def carregar_fato_avaliacao() -> List[Dict[str, str]]:
    session = SessionLocal()
    try:
        return [
            {
                "id_Avaliacao": _s(a.id_avaliacao),
                "Id_Visita": _s(a.id_visita),
                "Id_Cliente": _s(a.id_cliente),
                "Localizacao": _num_str(a.localizacao),
                "Tamanho": _num_str(a.tamanho),
                "Planta_Imovel": _num_str(a.planta_imovel),
                "Qualidade_Acabamento": _num_str(a.qualidade_acabamento),
                "Estado_Conservacao": _num_str(a.estado_conservacao),
                "Condominio_AreaComun": _num_str(a.condominio_areacomun),
                "Preco": _num_str(a.preco),
                "Nota_Geral": _num_str(a.nota_geral),
                "Preco_N10": _s(a.preco_n10),
                "CreatedBy": _s(a.created_by),
                "Id_Parceiro": _s(a.id_parceiro),
            }
            for a in session.query(Avaliacao).all()
        ]
    finally:
        session.close()


# Dispatcher unico: nome da aba original (Sheets) -> funcao que devolve as
# linhas equivalentes vindas do Postgres. Usado por TODO servico que antes lia
# Sheets (visita_service, rela_gerentes_service, imovel_rel_service,
# relatorio_visita_service, gerente_visitas_service, ranking_service, meta_service).
LOADERS_POR_ABA = {
    "Dim_Corretor": carregar_dim_corretor,
    "Dim_Gerente": carregar_dim_gerente,
    "Dim_Cliente_Visita": carregar_dim_cliente_visita,
    "Dim_Parceiro_Visita": carregar_dim_parceiro_visita,
    "Fato_Visitas": carregar_fato_visitas,
    "Fato_Cliente_Visita": carregar_fato_cliente_visita,
    "Fato_Parceiro_Visita": carregar_fato_parceiro_visita,
    "Fato_Avaliacao": carregar_fato_avaliacao,
    # preenchidos depois, no fim do arquivo (dependem de funcoes definidas mais abaixo)
}


def carregar_aba(nome_aba: str) -> List[Dict[str, str]]:
    """Ponto unico de entrada: nome da aba (Sheets) -> linhas (do Postgres)."""
    loader = LOADERS_POR_ABA.get(nome_aba)
    if loader is None:
        return []
    return loader()


# ---------------------------------------------------------------------------
# Dominio contratos (Vendas / Divisao_Comissao)
# ---------------------------------------------------------------------------

def carregar_vendas() -> List[Dict[str, str]]:
    """Mesmo formato da aba 'Vendas' original (146 colunas)."""
    session = SessionLocal()
    try:
        out = []
        for c in session.query(Contrato).all():
            linha = {"Id_Contrato": _s(c.id_contrato)}
            for slug_nome, header in HEADER_POR_SLUG.items():
                valor = getattr(c, slug_nome, None)
                col_tipo = type(Contrato.__table__.columns[slug_nome].type).__name__
                if col_tipo == "Date":
                    linha[header] = _data_str(valor)
                elif col_tipo in ("Numeric", "DECIMAL"):
                    linha[header] = _num_str(valor)
                else:
                    linha[header] = _s(valor)
            out.append(linha)
        return out
    finally:
        session.close()


def carregar_divisao_comissao() -> List[Dict[str, str]]:
    session = SessionLocal()
    try:
        return [
            {
                "Id_Contrato": _s(d.id_contrato),
                "Papel": _s(d.papel),
                "Id_Corretor": _s(d.id_corretor),
                "Nome_Corretor": _s(d.nome_corretor),
                "Percentual": _num_str(d.percentual),
                "Comissao_Valor": _num_str(d.comissao_valor),
                "Observacao": _s(d.observacao),
                "UpdatedAt": _datetime_str(d.atualizado_em),
            }
            for d in session.query(DivisaoComissao).all()
        ]
    finally:
        session.close()


def carregar_fato_captacao() -> List[Dict[str, str]]:
    """Captacoes p/ ranking: historico congelado (eventos_imovel_legado tipo='captacao')
    UNIDO com as captacoes correntes (fato_captacao, geridas pelo AdminBases).
    Dedup por (codigo, data_entrada, captador1) pra nao contar 2x."""
    from app.models.fato_bases import FatoCaptacao

    session = SessionLocal()
    try:
        out = []
        vistos = set()

        def _add(codigo, c1, c2, c3, ger, data):
            data_str = _data_str(data)
            chave = (_s(codigo), data_str, _s(c1))
            if chave in vistos:
                return
            vistos.add(chave)
            out.append({
                "Código": _s(codigo),
                "Captador1": _s(c1),
                "Captador2": _s(c2),
                "Captador3": _s(c3),
                "Gerente": _s(ger),
                "DataEntrada": data_str,
            })

        # histórico
        for c in session.query(EventoImovelLegado).filter(EventoImovelLegado.tipo_evento == "captacao").all():
            _add(c.codigo_imovel, c.captador1, c.captador2, c.captador3, c.id_gerente, c.data_evento)
        # corrente (AdminBases)
        for c in session.query(FatoCaptacao).all():
            _add(c.codigo_imovel, c.captador1, c.captador2, c.captador3, c.id_gerente, c.data_entrada)

        return out
    finally:
        session.close()


def carregar_fato_lead() -> List[Dict[str, str]]:
    session = SessionLocal()
    try:
        return [
            {
                "Data": _data_str(lead.data),
                "Fonte": _s(lead.fonte),
                "Contato": _s(lead.contato),
                "RelatÃ³rio": _s(lead.relatorio),
                "Cliente": _s(lead.cliente),
                "Telefone": _s(lead.telefone),
                "CÃ³digo": _s(lead.codigo_imovel),
                "Atendimento": _s(lead.atendimento),
                "Equipe": _s(lead.equipe),
                "Extra": _s(lead.observacao),
                "QUAT.": _s(lead.san_observacao),
            }
            for lead in session.query(LeadLegado).all()
        ]
    finally:
        session.close()


LOADERS_POR_ABA.update({
    "Vendas": carregar_vendas,
    "Divisao_Comissao": carregar_divisao_comissao,
    "Fato_Captacao": carregar_fato_captacao,
    "Fato_Lead": carregar_fato_lead,
})
