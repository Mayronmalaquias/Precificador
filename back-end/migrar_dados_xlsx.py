"""
Migra os 3 snapshots .xlsx em back-end/dados/ para o Postgres.

Por padrao roda em DRY-RUN: monta os objetos, faz flush (valida contra o banco
real, incluindo FKs e tipos) e da ROLLBACK no final - nada e persistido.
Use --apply para de fato commitar.

Ordem de dependencia (sempre respeitada, mesmo com --only):
    usuarios (Dim_Corretor/Dim_Gerente) -> visitas -> contratos

Uso:
    python migrar_dados_xlsx.py                          # dry-run, tudo
    python migrar_dados_xlsx.py --only usuarios           # dry-run, só usuarios
    python migrar_dados_xlsx.py --apply                   # aplica tudo de vez
    python migrar_dados_xlsx.py --apply --only contratos  # aplica só contratos

Politica de merge:
    - usuarios: tabela ja existe com dados reais (logins). So preenche campos
      em branco (backfill). Nunca sobrescreve username/password/permissao/ativo
      de quem ja existe. Corretor/gerente sem login vira linha ativo=False sem senha.
    - equipes / visitas / contratos: tabelas novas, upsert completo por chave natural.
"""

import argparse
import csv
import datetime as dt
import hashlib
import io
import re
import unicodedata
from decimal import Decimal, InvalidOperation

import pandas as pd
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.config import Config
from app.models.usuarios import Usuarios
from app.models.equipe import Equipe
from app.models.visita import (
    ClienteVisita, ParceiroVisita, Visita, VisitaCliente, VisitaParceiro, Avaliacao,
)
from app.models.contrato import Contrato, DivisaoComissao
from app.models.venda_legado import VendaLegado, HEADER_POR_SLUG as VENDA_LEGADO_HEADER_POR_SLUG
from app.models.legado_diversos import (
    ClienteLegado, NichoLegado, TipoImovelLegado, BairroLegado, ImovelLegado,
    DiretorLegado, AnuncioImovelLegado, PortalLegado, FonteLegado, AtendimentoLegado,
    CampanhaLegado, MetaMensalLegado,
    RecebidoLegado, RelatorioImovelLegado, SessaoUsuarioLegado, AdminLegado, MenuLegado,
)
from app.models.estoque_legado import LeadLegado
from app.models.eventos_imovel_legado import EventoImovelLegado


DADOS_DIR = "dados"
ARQ_VISITAS = f"{DADOS_DIR}/Modelo_Visitas (6).xlsx"
ARQ_CONTRATOS = f"{DADOS_DIR}/Controle de Contratos 61 Imóveis (7).xlsx"
ARQ_BASE_INTELIGENCIA = f"{DADOS_DIR}/Base Inteligência 61 (6).xlsx"

TRUE_SET = {"true", "sim", "1", "yes", "y"}


# ---------------------------------------------------------------------------
# Helpers de coerção (tolerantes, nunca explodem - retornam None e logam)
# ---------------------------------------------------------------------------

def slug(header: str) -> str:
    h = str(header).strip()
    h = unicodedata.normalize("NFKD", h)
    h = "".join(c for c in h if not unicodedata.combining(c))
    h = h.replace("$", "valor").replace("%", "percentual").replace("/", "_")
    h = re.sub(r"[^0-9a-zA-Z]+", "_", h)
    h = re.sub(r"_+", "_", h).strip("_").lower()
    return h


def is_blank(v) -> bool:
    if v is None:
        return True
    try:
        if pd.isna(v):
            return True
    except (TypeError, ValueError):
        pass
    if isinstance(v, str) and not v.strip():
        return True
    return False


def to_str(v):
    if is_blank(v):
        return None
    return str(v).strip()


def _canonical_numeric_str(v):
    """str() estavel pra numero, independente de pandas ter lido como int ou float
    (evita 8.7544e+65 vs 875440...872 pro MESMO valor em sheets diferentes)."""
    if isinstance(v, float):
        return str(int(v)) if v.is_integer() else repr(v)
    if isinstance(v, int):
        return str(v)
    return str(v).strip()


def to_id_str(v, report=None, ctx="", max_len=50):
    """Pros IDs gerados pelo AppSheet (Id_Visita, Id_Cliente, Id_Parceiro, etc):
    sao sempre hex de 8 chars. Se a celula foi lida como numero (Excel confundiu
    o hex com notacao cientifica - corrupcao na planilha-fonte, ja irrecuperavel),
    troca por um placeholder deterministico em vez de travar ou perder a linha.
    Mesmo valor corrompido => mesmo placeholder, em qualquer aba (mantem os joins)."""
    if is_blank(v):
        return None
    canonical = _canonical_numeric_str(v)
    if len(canonical) <= max_len:
        return canonical
    placeholder = "CORR_" + hashlib.sha1(canonical.encode()).hexdigest()[:12]
    if report:
        report.warn_once(canonical, f"{ctx}: valor corrompido na planilha-fonte ({canonical[:40]}...) -> {placeholder}")
    return placeholder


def to_date(v):
    if is_blank(v):
        return None
    if isinstance(v, dt.date):
        return v.date() if isinstance(v, dt.datetime) else v
    s = str(v).strip()
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y"):
        try:
            return dt.datetime.strptime(s, fmt).date()
        except ValueError:
            continue
    return None


def to_datetime(v):
    if is_blank(v):
        return None
    if isinstance(v, dt.datetime):
        return v
    if isinstance(v, dt.date):
        return dt.datetime(v.year, v.month, v.day)
    s = str(v).strip()
    for fmt in ("%Y-%m-%d %H:%M:%S", "%d/%m/%Y %H:%M:%S", "%Y-%m-%d", "%d/%m/%Y"):
        try:
            return dt.datetime.strptime(s, fmt)
        except ValueError:
            continue
    return None


def to_decimal(v, report=None, ctx=""):
    if is_blank(v):
        return None
    if isinstance(v, (int, float, Decimal)):
        try:
            return Decimal(str(v))
        except InvalidOperation:
            return None
    s = str(v).strip()
    s = s.replace("R$", "").strip()
    if "," in s and "." in s:
        s = s.replace(".", "").replace(",", ".")
    elif "," in s:
        s = s.replace(",", ".")
    s = re.sub(r"[^0-9.\-]", "", s)
    if not s:
        return None
    try:
        return Decimal(s)
    except InvalidOperation:
        if report:
            report.warn(f"valor numerico nao reconhecido ({ctx}): {v!r}")
        return None


def to_bool(v):
    if is_blank(v):
        return None
    return str(v).strip().lower() in TRUE_SET


def _csv_val(v) -> str:
    """Serializa 1 valor pro formato que o COPY ... WITH (FORMAT csv, NULL '') espera."""
    if v is None:
        return ""
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, dt.date):
        return v.isoformat()
    return str(v)


def copy_insert(session, tabela: str, colunas: list, linhas: list) -> None:
    """Insere em lote via COPY (psycopg2) - MUITO mais rapido que INSERT/executemany
    pra muitas linhas (testado: ~0.25s/linha com bulk_insert_mappings num banco remoto;
    COPY faz o mesmo volume em segundos). Participa da mesma transacao da session
    (dry-run com rollback continua funcionando)."""
    if not linhas:
        return
    buf = io.StringIO()
    writer = csv.writer(buf)
    for linha in linhas:
        writer.writerow([_csv_val(linha.get(c)) for c in colunas])
    buf.seek(0)

    raw_conn = session.connection().connection
    cur = raw_conn.cursor()
    cols_sql = ", ".join(colunas)
    cur.copy_expert(
        f"COPY {tabela} ({cols_sql}) FROM STDIN WITH (FORMAT csv, NULL '')",
        buf,
    )


# ---------------------------------------------------------------------------
# Relatorio de execucao
# ---------------------------------------------------------------------------

class Report:
    def __init__(self):
        self.counts = {}
        self.warnings = []
        self._vistos = set()

    def bump(self, table, kind):
        key = (table, kind)
        self.counts[key] = self.counts.get(key, 0) + 1

    def warn(self, msg):
        self.warnings.append(msg)

    def warn_once(self, key, msg):
        if key in self._vistos:
            return
        self._vistos.add(key)
        self.warnings.append(msg)

    def print_summary(self, dry_run):
        print("\n" + "=" * 70)
        print(f"RESUMO ({'DRY-RUN, nada foi salvo' if dry_run else 'APLICADO'})")
        print("=" * 70)
        tables = sorted({t for (t, _k) in self.counts})
        for table in tables:
            inseridos = self.counts.get((table, "inserido"), 0)
            atualizados = self.counts.get((table, "atualizado"), 0)
            pulados = self.counts.get((table, "pulado"), 0)
            print(f"  {table:<20} inseridos={inseridos:<6} atualizados={atualizados:<6} pulados={pulados:<6}")
        if self.warnings:
            print(f"\n  {len(self.warnings)} avisos:")
            for w in self.warnings[:50]:
                print(f"   - {w}")
            if len(self.warnings) > 50:
                print(f"   ... e mais {len(self.warnings) - 50}")
        print("=" * 70)


_EXCEL_FILE_CACHE = {}


def ler_aba(caminho, aba):
    """Cacheia o pd.ExcelFile por caminho - sem isso, cada chamada reabre/reparseia
    o workbook inteiro do zero (lento pra arquivo com varias abas grandes)."""
    excel_file = _EXCEL_FILE_CACHE.get(caminho)
    if excel_file is None:
        excel_file = pd.ExcelFile(caminho)
        _EXCEL_FILE_CACHE[caminho] = excel_file
    return excel_file.parse(sheet_name=aba, dtype=object)


# ---------------------------------------------------------------------------
# Fase 1 - usuarios / equipes (Modelo_Visitas!Dim_Corretor, Dim_Gerente)
# ---------------------------------------------------------------------------

def migrar_usuarios(session, report: Report):
    df_gerente = ler_aba(ARQ_VISITAS, "Dim_Gerente")
    df_corretor = ler_aba(ARQ_VISITAS, "Dim_Corretor")

    # Pre-carrega tudo que existe (poucas queries, em vez de 1 select por linha)
    equipes_existentes = {e.id_equipe: e for e in session.query(Equipe).all()}
    usuarios_existentes = {u.id_usuarios: u for u in session.query(Usuarios).all() if u.id_usuarios}

    # Equipes: upsert completo (tabela nova, dado de referencia)
    for _, row in df_gerente.iterrows():
        id_equipe = to_str(row.get("IdGerente"))
        if not id_equipe:
            report.bump("equipes", "pulado")
            continue
        equipe = equipes_existentes.get(id_equipe)
        if equipe is None:
            equipe = Equipe(id_equipe=id_equipe)
            session.add(equipe)
            equipes_existentes[id_equipe] = equipe
            report.bump("equipes", "inserido")
        else:
            report.bump("equipes", "atualizado")
        equipe.nome = to_str(row.get("Equipe")) or equipe.nome
        equipe.email = to_str(row.get("email")) or equipe.email

    def upsert_pessoa(id_usuarios, nome, email, telefone, instagram, descricao,
                       team, id_imoview, permissao_default):
        if not id_usuarios:
            return None
        existente = usuarios_existentes.get(id_usuarios)
        if existente is None:
            usuario = Usuarios(
                id_usuarios=id_usuarios,
                username=id_usuarios,
                password=None,
                ativo=False,
                permissao=permissao_default,
                team=team,
                nome=nome,
                email=email,
                telefone=telefone,
                instagram=instagram,
                descricao=descricao,
                id_imoview=id_imoview,
            )
            session.add(usuario)
            usuarios_existentes[id_usuarios] = usuario
            return "inserido"

        # backfill: so preenche o que estiver vazio, nunca sobrescreve dado real
        if not existente.nome and nome:
            existente.nome = nome
        if not existente.email and email:
            existente.email = email
        if not existente.telefone and telefone:
            existente.telefone = telefone
        if not existente.instagram and instagram:
            existente.instagram = instagram
        if not existente.descricao and descricao:
            existente.descricao = descricao
        if not existente.id_imoview and id_imoview:
            existente.id_imoview = id_imoview
        return "atualizado"

    # Gerentes primeiro (corretores podem referenciar IdGerente como team)
    for _, row in df_gerente.iterrows():
        id_gerente = to_str(row.get("IdGerente"))
        resultado = upsert_pessoa(
            id_usuarios=id_gerente,
            nome=to_str(row.get("Nome")),
            email=to_str(row.get("email")),
            telefone=None,
            instagram=None,
            descricao=None,
            team=id_gerente,
            id_imoview=None,
            permissao_default="gerente",
        )
        report.bump("usuarios(gerente)", resultado or "pulado")

    # Corretores - dedupe por IdCorretor mantendo a ultima ocorrencia (sheet tem stale rows)
    por_corretor = {}
    for _, row in df_corretor.iterrows():
        id_corretor = to_str(row.get("IdCorretor"))
        if id_corretor:
            por_corretor[id_corretor] = row

    for id_corretor, row in por_corretor.items():
        eh_gerente = to_bool(row.get("Gerente?"))
        resultado = upsert_pessoa(
            id_usuarios=id_corretor,
            nome=to_str(row.get("Nome")),
            email=to_str(row.get("Email")),
            telefone=to_str(row.get("Telefone")),
            instagram=to_str(row.get("Instragram")),
            descricao=to_str(row.get("Descricao")),
            team=to_str(row.get("IdGerente")),
            id_imoview=to_str(row.get("IdImoview")),
            permissao_default="gerente" if eh_gerente else "corretor",
        )
        report.bump("usuarios(corretor)", resultado or "pulado")


# ---------------------------------------------------------------------------
# Fase 2 - dominio visitas
# ---------------------------------------------------------------------------

def migrar_visitas(session, report: Report):
    df_clientes = ler_aba(ARQ_VISITAS, "Dim_Cliente_Visita")
    df_parceiros = ler_aba(ARQ_VISITAS, "Dim_Parceiro_Visita")
    df_visitas = ler_aba(ARQ_VISITAS, "Fato_Visitas")
    df_fc = ler_aba(ARQ_VISITAS, "Fato_Cliente_Visita")
    df_fp = ler_aba(ARQ_VISITAS, "Fato_Parceiro_Visita")
    df_aval = ler_aba(ARQ_VISITAS, "Fato_Avaliacao")

    clientes_existentes = {c.id_cliente: c for c in session.query(ClienteVisita).all()}
    parceiros_existentes = {p.id_parceiro: p for p in session.query(ParceiroVisita).all()}
    visitas_existentes = {v.id_visita: v for v in session.query(Visita).all()}

    ids_cliente_validos = set()
    for _, row in df_clientes.iterrows():
        id_cliente = to_id_str(row.get("Id_Cliente"), report, "Dim_Cliente_Visita.Id_Cliente")
        if not id_cliente:
            report.bump("clientes_visita", "pulado")
            continue
        cliente = clientes_existentes.get(id_cliente)
        if cliente is None:
            cliente = ClienteVisita(id_cliente=id_cliente)
            session.add(cliente)
            clientes_existentes[id_cliente] = cliente
            report.bump("clientes_visita", "inserido")
        else:
            report.bump("clientes_visita", "atualizado")
        cliente.nome_cliente = to_str(row.get("Nome_Cliente"))
        cliente.telefone_cliente = to_str(row.get("Telefone_Cliente"))
        cliente.email_cliente = to_str(row.get("Email_Cliente"))
        cliente.created_by = to_str(row.get("CreatedBy"))
        cliente.id_corretor = to_str(row.get("Id_Corretor"))
        ids_cliente_validos.add(id_cliente)

    ids_parceiro_validos = set()
    for _, row in df_parceiros.iterrows():
        id_parceiro = to_id_str(row.get("Id_Parceiro"), report, "Dim_Parceiro_Visita.Id_Parceiro")
        if not id_parceiro:
            report.bump("parceiros_visita", "pulado")
            continue
        parceiro = parceiros_existentes.get(id_parceiro)
        if parceiro is None:
            parceiro = ParceiroVisita(id_parceiro=id_parceiro)
            session.add(parceiro)
            parceiros_existentes[id_parceiro] = parceiro
            report.bump("parceiros_visita", "inserido")
        else:
            report.bump("parceiros_visita", "atualizado")
        parceiro.nome_parceiro = to_str(row.get("Nome_Parceiro"))
        parceiro.imobiliaria = to_str(row.get("Imobiliaria"))
        parceiro.id_corretor = to_str(row.get("Id_Corretor"))
        ids_parceiro_validos.add(id_parceiro)

    session.flush()  # garante que os pais existem antes das FKs dos filhos

    ids_visita_validos = set()
    for _, row in df_visitas.iterrows():
        id_visita = to_id_str(row.get("Id_Visita"), report, "Fato_Visitas.Id_Visita")
        if not id_visita:
            report.bump("visitas", "pulado")
            continue

        id_cliente_assinante = to_id_str(row.get("Id_Cliente_Assinante"), report, f"visita {id_visita}.Id_Cliente_Assinante")
        if id_cliente_assinante and id_cliente_assinante not in ids_cliente_validos:
            report.warn(f"visita {id_visita}: Id_Cliente_Assinante {id_cliente_assinante} nao existe em Dim_Cliente_Visita, zerado")
            id_cliente_assinante = None

        id_parceiro = to_id_str(row.get("Id_Parceiro"), report, f"visita {id_visita}.Id_Parceiro")
        if id_parceiro and id_parceiro not in ids_parceiro_validos:
            report.warn(f"visita {id_visita}: Id_Parceiro {id_parceiro} nao existe em Dim_Parceiro_Visita, zerado")
            id_parceiro = None

        visita = visitas_existentes.get(id_visita)
        if visita is None:
            visita = Visita(id_visita=id_visita)
            session.add(visita)
            visitas_existentes[id_visita] = visita
            report.bump("visitas", "inserido")
        else:
            report.bump("visitas", "atualizado")

        visita.id_imovel = to_str(row.get("Id_Imovel"))
        visita.data_visita = to_date(row.get("Data_Visita"))
        visita.id_corretor = to_str(row.get("Id_Corretor"))
        visita.anexo_ficha_visita = to_str(row.get("Anexo_Ficha_Visita"))
        visita.audiodescricao_cliente_visita = to_str(row.get("AudiodescricaoClienteVisita"))
        visita.link_audio = to_str(row.get("Link_Audio"))
        visita.link_imagem = to_str(row.get("Link_Imagem"))
        visita.visita_com_parceiro = to_bool(row.get("Visita_Com_Parceiro"))
        visita.tipo_captacao = to_str(row.get("Tipo_Captacao"))
        visita.endereco_externo = to_str(row.get("Endereco_Externo"))
        visita.proposta = to_str(row.get("Proposta"))
        visita.created_at = to_datetime(row.get("CreatedAt"))
        visita.created_by = to_str(row.get("CreatedBy"))
        visita.assinatura = to_str(row.get("Assinatura"))
        visita.id_cliente_assinante = id_cliente_assinante
        visita.id_parceiro = id_parceiro
        visita.imovel_nao_captado = to_bool(row.get("Imovel_Nao_Captado"))
        visita.motivo_talvez = to_str(row.get("Motivo_Talvez"))
        ids_visita_validos.add(id_visita)

    session.flush()

    # Fato_Cliente_Visita -> visita_cliente (idempotente via origem)
    existentes_vc = {
        vc.id_clientevisita_origem
        for vc in session.query(VisitaCliente.id_clientevisita_origem).all()
        if vc[0]
    }
    for _, row in df_fc.iterrows():
        origem = to_id_str(row.get("Id_ClienteVisita"), report, "Fato_Cliente_Visita.Id_ClienteVisita")
        id_visita = to_id_str(row.get("Id_Visita"), report, "Fato_Cliente_Visita.Id_Visita")
        id_cliente = to_id_str(row.get("Id_Cliente"), report, "Fato_Cliente_Visita.Id_Cliente")
        if not id_visita or not id_cliente:
            report.bump("visita_cliente", "pulado")
            continue
        if id_visita not in ids_visita_validos or id_cliente not in ids_cliente_validos:
            report.warn(f"Fato_Cliente_Visita {origem}: visita/cliente inexistente, pulado")
            report.bump("visita_cliente", "pulado")
            continue
        if origem and origem in existentes_vc:
            report.bump("visita_cliente", "atualizado")
            continue
        session.add(VisitaCliente(
            id_clientevisita_origem=origem,
            id_visita=id_visita,
            id_cliente=id_cliente,
            papel_na_visita=to_str(row.get("Papel_na_Visita")),
        ))
        report.bump("visita_cliente", "inserido")

    # Fato_Parceiro_Visita -> visita_parceiro
    existentes_vp = {
        vp.id_parceirovisita_origem
        for vp in session.query(VisitaParceiro.id_parceirovisita_origem).all()
        if vp[0]
    }
    for _, row in df_fp.iterrows():
        origem = to_id_str(row.get("Id_ParceiroVisita"), report, "Fato_Parceiro_Visita.Id_ParceiroVisita")
        id_visita = to_id_str(row.get("Id_Visita"), report, "Fato_Parceiro_Visita.Id_Visita")
        id_parceiro = to_id_str(row.get("Id_Parceiro"), report, "Fato_Parceiro_Visita.Id_Parceiro")
        if not id_visita or not id_parceiro:
            report.bump("visita_parceiro", "pulado")
            continue
        if id_visita not in ids_visita_validos or id_parceiro not in ids_parceiro_validos:
            report.warn(f"Fato_Parceiro_Visita {origem}: visita/parceiro inexistente, pulado")
            report.bump("visita_parceiro", "pulado")
            continue
        if origem and origem in existentes_vp:
            report.bump("visita_parceiro", "atualizado")
            continue
        session.add(VisitaParceiro(
            id_parceirovisita_origem=origem,
            id_visita=id_visita,
            id_parceiro=id_parceiro,
            papel_na_visita=to_str(row.get("Papel_na_Visita")),
        ))
        report.bump("visita_parceiro", "inserido")

    # Fato_Avaliacao -> avaliacoes_visita
    avaliacoes_existentes = {a.id_avaliacao: a for a in session.query(Avaliacao).all()}
    for _, row in df_aval.iterrows():
        id_avaliacao = to_id_str(row.get("id_Avaliacao"), report, "Fato_Avaliacao.id_Avaliacao")
        if not id_avaliacao:
            report.bump("avaliacoes_visita", "pulado")
            continue
        id_visita = to_id_str(row.get("Id_Visita"), report, f"avaliacao {id_avaliacao}.Id_Visita")
        id_cliente = to_id_str(row.get("Id_Cliente"), report, f"avaliacao {id_avaliacao}.Id_Cliente")
        id_parceiro = to_id_str(row.get("Id_Parceiro"), report, f"avaliacao {id_avaliacao}.Id_Parceiro")
        if id_visita and id_visita not in ids_visita_validos:
            report.warn(f"avaliacao {id_avaliacao}: Id_Visita {id_visita} inexistente, zerado")
            id_visita = None
        if id_cliente and id_cliente not in ids_cliente_validos:
            id_cliente = None
        if id_parceiro and id_parceiro not in ids_parceiro_validos:
            id_parceiro = None

        aval = avaliacoes_existentes.get(id_avaliacao)
        if aval is None:
            aval = Avaliacao(id_avaliacao=id_avaliacao)
            session.add(aval)
            avaliacoes_existentes[id_avaliacao] = aval
            report.bump("avaliacoes_visita", "inserido")
        else:
            report.bump("avaliacoes_visita", "atualizado")

        aval.id_visita = id_visita
        aval.id_cliente = id_cliente
        aval.id_parceiro = id_parceiro
        aval.localizacao = to_decimal(row.get("Localizacao"))
        aval.tamanho = to_decimal(row.get("Tamanho"))
        aval.planta_imovel = to_decimal(row.get("Planta_Imovel"))
        aval.qualidade_acabamento = to_decimal(row.get("Qualidade_Acabamento"))
        aval.estado_conservacao = to_decimal(row.get("Estado_Conservacao"))
        aval.condominio_areacomun = to_decimal(row.get("Condominio_AreaComun"))
        aval.preco = to_decimal(row.get("Preco"))
        aval.nota_geral = to_decimal(row.get("Nota_Geral"))
        aval.preco_n10 = to_str(row.get("Preco_N10"))
        aval.created_by = to_str(row.get("CreatedBy"))


# ---------------------------------------------------------------------------
# Fase 3 - contratos (Vendas / Divisao_Comissao)
# ---------------------------------------------------------------------------

NUMERIC_PREFIXES = ("valor_", "percentual_")
NUMERIC_EXACT = {
    "nf_61_imoveis", "liquido_61", "vgv_v1", "vgv_v2", "vgv_c1", "vgv_c2",
    "neg_gerado_v1", "neg_gerado_v2", "neg_gerado_c1", "neg_gerado_c2",
}


def classificar_coluna(nome_slug):
    if nome_slug.startswith("data_"):
        return "data"
    if nome_slug.startswith(NUMERIC_PREFIXES) or nome_slug in NUMERIC_EXACT:
        return "numerico"
    return "texto"


def migrar_contratos(session, report: Report):
    df = ler_aba(ARQ_CONTRATOS, "Vendas")
    colunas_contrato = set(Contrato.__table__.columns.keys())
    contratos_existentes = {c.id_contrato: c for c in session.query(Contrato).all()}
    vistos_nesta_planilha = {}

    for idx, row in df.iterrows():
        id_contrato_origem = to_str(row.get("Id_Contrato"))
        if not id_contrato_origem:
            report.bump("contratos", "pulado")
            continue

        # Id_Contrato duplicado na planilha (2 contratos distintos, mesmo codigo por erro
        # de digitacao) nao pode sobrescrever um ao outro - sufixa pra manter os dois.
        vezes = vistos_nesta_planilha.get(id_contrato_origem, 0)
        vistos_nesta_planilha[id_contrato_origem] = vezes + 1
        id_contrato = id_contrato_origem if vezes == 0 else f"{id_contrato_origem}__dup{vezes}"
        if vezes:
            report.warn(
                f"Id_Contrato {id_contrato_origem!r} duplicado na planilha (linha {idx + 2}) "
                f"-> salvo como {id_contrato!r}, corrigir o codigo na planilha-fonte"
            )

        contrato = contratos_existentes.get(id_contrato)
        if contrato is None:
            contrato = Contrato(id_contrato=id_contrato)
            session.add(contrato)
            contratos_existentes[id_contrato] = contrato
            report.bump("contratos", "inserido")
        else:
            report.bump("contratos", "atualizado")

        for header, valor in row.items():
            nome_slug = slug(header)
            if nome_slug == "id_contrato" or nome_slug not in colunas_contrato:
                continue
            tipo = classificar_coluna(nome_slug)
            if tipo == "data":
                setattr(contrato, nome_slug, to_date(valor))
            elif tipo == "numerico":
                setattr(contrato, nome_slug, to_decimal(valor, report, ctx=f"contrato {id_contrato}.{nome_slug}"))
            else:
                setattr(contrato, nome_slug, to_str(valor))

    df_div = ler_aba(ARQ_CONTRATOS, "Divisao_Comissao")
    if df_div.empty:
        report.warn("aba Divisao_Comissao esta vazia no xlsx - nada a importar (tabela criada vazia)")
        return

    for _, row in df_div.iterrows():
        id_contrato = to_str(row.get("Id_Contrato"))
        id_corretor = to_str(row.get("Id_Corretor"))
        if not id_contrato or not id_corretor:
            report.bump("divisao_comissao", "pulado")
            continue
        existente = (
            session.query(DivisaoComissao)
            .filter(
                DivisaoComissao.id_contrato == id_contrato,
                DivisaoComissao.id_corretor == id_corretor,
                DivisaoComissao.papel == to_str(row.get("Papel")),
            )
            .first()
        )
        if existente is None:
            existente = DivisaoComissao(
                id_contrato=id_contrato,
                id_corretor=id_corretor,
                papel=to_str(row.get("Papel")),
            )
            session.add(existente)
            report.bump("divisao_comissao", "inserido")
        else:
            report.bump("divisao_comissao", "atualizado")
        existente.nome_corretor = to_str(row.get("Nome_Corretor"))
        existente.percentual = to_decimal(row.get("Percentual"))
        existente.comissao_valor = to_decimal(row.get("Comissao_Valor"))


# ---------------------------------------------------------------------------
# Fase 4 - eventos_imovel_legado (Fato_Captacao/Fato_Saida/Fato_Estoque/
# Fato_Destaque/Fato_Destaque_Mensal, Base Inteligencia - 1 tabela so,
# discriminada por tipo_evento, ja que as 5 tinham o mesmo shape base)
# ---------------------------------------------------------------------------

EVENTOS_IMOVEL_COLS = [
    "tipo_evento", "codigo_imovel", "captador1", "captador2", "captador3", "id_gerente",
    "data_evento", "motivo", "publicacao_na_internet", "exclusivo", "id_anuncio_meta",
    "endereco", "bairro", "publicacao_web", "categoria_df_assinado", "valor",
    "categoria_df", "categoria_df_seguro", "categoria_wi",
]


def migrar_eventos_imovel_legado(session, report: Report):
    ja_existe = session.query(EventoImovelLegado).first()
    if ja_existe:
        report.warn("eventos_imovel_legado ja tem dados - import historico e feito uma vez so, pulando")
        return

    def base(tipo_evento, codigo_imovel, c1, c2, c3, gerente, data_evento=None, **extra):
        linha = {c: None for c in EVENTOS_IMOVEL_COLS}
        linha.update({
            "tipo_evento": tipo_evento,
            "codigo_imovel": to_str(codigo_imovel),
            "captador1": to_str(c1),
            "captador2": to_str(c2),
            "captador3": to_str(c3),
            "id_gerente": to_str(gerente),
            "data_evento": data_evento,
        })
        linha.update(extra)
        return linha

    linhas = []

    df = ler_aba(ARQ_BASE_INTELIGENCIA, "Fato_Captacao")
    df.columns = ["codigo_imovel", "captador1", "captador2", "captador3", "id_gerente", "data_entrada"]
    for _, row in df.iterrows():
        linhas.append(base("captacao", row.get("codigo_imovel"), row.get("captador1"),
                            row.get("captador2"), row.get("captador3"), row.get("id_gerente"),
                            to_date(row.get("data_entrada"))))

    df = ler_aba(ARQ_BASE_INTELIGENCIA, "Fato_Saida")
    df.columns = ["codigo_imovel", "captador1", "captador2", "captador3", "id_gerente", "motivo", "data_saida"]
    for _, row in df.iterrows():
        linhas.append(base("saida", row.get("codigo_imovel"), row.get("captador1"),
                            row.get("captador2"), row.get("captador3"), row.get("id_gerente"),
                            to_date(row.get("data_saida")), motivo=to_str(row.get("motivo"))))

    df = ler_aba(ARQ_BASE_INTELIGENCIA, "Fato_Estoque")
    df.columns = ["codigo_imovel", "captador1", "captador2", "captador3", "id_gerente",
                  "data_estoque", "publicacao_na_internet", "exclusivo", "categoria_df",
                  "categoria_df_seguro", "categoria_wi", "id_anuncio_meta"]
    for _, row in df.iterrows():
        linhas.append(base("estoque", row.get("codigo_imovel"), row.get("captador1"),
                            row.get("captador2"), row.get("captador3"), row.get("id_gerente"),
                            to_date(row.get("data_estoque")),
                            publicacao_na_internet=to_str(row.get("publicacao_na_internet")),
                            exclusivo=to_str(row.get("exclusivo")),
                            categoria_df=to_str(row.get("categoria_df")),
                            categoria_df_seguro=to_str(row.get("categoria_df_seguro")),
                            categoria_wi=to_str(row.get("categoria_wi")),
                            id_anuncio_meta=to_str(row.get("id_anuncio_meta"))))

    for aba, tipo_evento in [("Fato_Destaque", "destaque"), ("Fato_Destaque_Mensal", "destaque_mensal")]:
        df = ler_aba(ARQ_BASE_INTELIGENCIA, aba)
        df.columns = ["codigo_imovel", "captador1", "captador2", "captador3", "id_gerente",
                      "endereco", "bairro", "publicacao_web", "categoria_df", "categoria_wi",
                      "categoria_df_seguro", "categoria_df_assinado", "valor"]
        for _, row in df.iterrows():
            linhas.append(base(tipo_evento, row.get("codigo_imovel"), row.get("captador1"),
                                row.get("captador2"), row.get("captador3"), row.get("id_gerente"),
                                endereco=to_str(row.get("endereco")), bairro=to_str(row.get("bairro")),
                                publicacao_web=to_str(row.get("publicacao_web")),
                                categoria_df=to_str(row.get("categoria_df")),
                                categoria_wi=to_str(row.get("categoria_wi")),
                                categoria_df_seguro=to_str(row.get("categoria_df_seguro")),
                                categoria_df_assinado=to_str(row.get("categoria_df_assinado")),
                                valor=to_str(row.get("valor"))))

    copy_insert(session, "eventos_imovel_legado", EVENTOS_IMOVEL_COLS, linhas)
    for _ in linhas:
        report.bump("eventos_imovel_legado", "inserido")


# ---------------------------------------------------------------------------
# Fase 5 - vendas_legado (Fato_Venda, Base Inteligencia, dados desde 2015)
# ---------------------------------------------------------------------------

VENDA_LEGADO_DATA_COLS = {"data_captacao", "data_venda", "entradalead"}
VENDA_LEGADO_BOOL_COLS = {"foco"}


def migrar_venda_legado(session, report: Report):
    ja_existe = session.query(VendaLegado).first()
    if ja_existe:
        report.warn("vendas_legado ja tem dados - import historico e feito uma vez so, pulando")
        return

    df = ler_aba(ARQ_BASE_INTELIGENCIA, "Fato_Venda")
    colunas_modelo = set(VendaLegado.__table__.columns.keys())
    slug_por_header = {v.strip(): k for k, v in VENDA_LEGADO_HEADER_POR_SLUG.items()}

    linhas = []
    for _, row in df.iterrows():
        linha = {}
        for header, valor in row.items():
            nome_slug = slug_por_header.get(str(header).strip())
            if not nome_slug or nome_slug not in colunas_modelo:
                continue
            if nome_slug in VENDA_LEGADO_DATA_COLS:
                linha[nome_slug] = to_date(valor)
            elif nome_slug in VENDA_LEGADO_BOOL_COLS:
                linha[nome_slug] = to_bool(valor)
            else:
                linha[nome_slug] = to_str(valor)
        linhas.append(linha)

    colunas_copy = [s for s in VENDA_LEGADO_HEADER_POR_SLUG.keys() if s in colunas_modelo]
    copy_insert(session, "vendas_legado", colunas_copy, linhas)
    for _ in linhas:
        report.bump("vendas_legado", "inserido")



# ---------------------------------------------------------------------------
# Fase 6 - tabelas legado diversas (Dim_*/Fato_* pequenas, Recebido,
# Relatorio_Imovel, Sessao_Usuario, App_Admins, Menu_*)
# ---------------------------------------------------------------------------

TABELAS_LEGADO_DIVERSAS = [
    (ClienteLegado, "clientes_legado", ARQ_BASE_INTELIGENCIA, "Dim_Cliente", [("CPF", "cpf", "texto"), ("Nome", "nome", "texto"), ("IdContrato", "id_contrato", "texto"), ("Link_Drive", "link_drive", "texto")]),
    (NichoLegado, "nichos_legado", ARQ_BASE_INTELIGENCIA, "Dim_Nicho", [("Corretor", "corretor", "texto"), ("Nome", "nome", "texto"), ("Equipe", "equipe", "texto"), ("Gerente", "gerente", "texto"), ("Região", "regiao", "texto"), ("Bairro", "bairro", "texto"), ("Valor_min", "valor_min", "texto"), ("Valor_max", "valor_max", "texto"), ("Tipologia_1", "tipologia_1", "texto"), ("Tipologia_2", "tipologia_2", "texto"), ("Tipologia_3", "tipologia_3", "texto"), ("Tipologia_4", "tipologia_4", "texto"), ("Vaga", "vaga", "texto"), ("N_Cap_Nicho", "n_cap_nicho", "texto"), ("Estoque_Nicho", "estoque_nicho", "texto"), ("N_Estoque_total", "n_estoque_total", "texto"), ("VGV_Venda", "vgv_venda", "texto")]),
    (TipoImovelLegado, "tipos_imovel_legado", ARQ_BASE_INTELIGENCIA, "Dim_Tipo", [("IdTipo", "id_tipo", "texto"), ("Nome", "nome", "texto")]),
    (BairroLegado, "bairros_legado", ARQ_BASE_INTELIGENCIA, "Dim_Bairro", [("IdBairro", "id_bairro", "texto"), ("Nome", "nome", "texto")]),
    (ImovelLegado, "imoveis_legado", ARQ_BASE_INTELIGENCIA, "Dim_Imovel", [("Código", "codigo", "texto"), ("Tipo", "tipo", "texto"), ("Valor", "valor", "texto"), ("Bairro", "bairro", "texto"), ("Foco PP", "foco_pp", "bool"), ("Foco AC", "foco_ac", "bool")]),
    (DiretorLegado, "diretores_legado", ARQ_BASE_INTELIGENCIA, "Dim_Diretor", [("IdDiretor", "id_diretor", "texto"), ("Nome", "nome", "texto")]),
    (AnuncioImovelLegado, "anuncios_imovel_legado", ARQ_BASE_INTELIGENCIA, "Dim_AnuncioImóvel", [("IdAnuncio", "id_anuncio", "texto"), ("Cod", "cod", "texto")]),
    (PortalLegado, "portais_legado", ARQ_BASE_INTELIGENCIA, "Dim_Portal", [("Categoria", "categoria", "texto"), ("Limite", "limite", "texto")]),
    (FonteLegado, "fontes_legado", ARQ_BASE_INTELIGENCIA, "Dim_Fonte", [("Codigo", "codigo", "texto"), ("Nome", "nome", "texto")]),
    (AtendimentoLegado, "atendimentos_legado", ARQ_BASE_INTELIGENCIA, "Dim_Atendimento", [("Codigo", "codigo", "texto"), ("Nome", "nome", "texto")]),
    (CampanhaLegado, "campanhas_legado", ARQ_BASE_INTELIGENCIA, "Fato_Campanhas", [("Nome da campanha", "nome_campanha", "texto"), ("Nome do conjunto de anúncios", "nome_conjunto_anuncios", "texto"), ("Nome do anúncio", "nome_anuncio", "texto"), ("Dia", "dia", "data"), ("Alcance", "alcance", "texto"), ("Impressões", "impressoes", "texto"), ("Frequência", "frequencia", "texto"), ("Montante gasto (BRL)", "montante_gasto_brl", "texto"), ("Definição de atribuição", "definicao_atribuicao", "texto"), ("Começa a", "comeca_a", "data"), ("Termina a", "termina_a", "data"), ("Tipo de resultado", "tipo_resultado", "texto"), ("Resultados", "resultados", "texto"), ("Custo por resultado", "custo_por_resultado", "texto"), ("Início dos relatórios", "inicio_relatorios", "data"), ("Fim dos relatórios", "fim_relatorios", "data"), ("IdAnuncio", "id_anuncio", "texto")]),
    (MetaMensalLegado, "metas_mensais_legado", ARQ_BASE_INTELIGENCIA, "Fato_Meta_Mensal", [("Mes", "mes", "data"), ("IdGerente", "id_gerente", "texto"), ("Equipe", "equipe", "texto"), ("Meta_Cap", "meta_cap", "texto"), ("Meta_VGV", "meta_vgv", "texto"), ("Super_Meta_Cap", "super_meta_cap", "texto"), ("Super_Meta_Vgv", "super_meta_vgv", "texto")]),
    (RecebidoLegado, "recebidos_legado", ARQ_CONTRATOS, "Recebido", [("Data", "data", "data"), ("Contrato", "contrato", "texto"), ("Valor Recebido", "valor_recebido", "texto")]),
    (RelatorioImovelLegado, "relatorios_imovel_legado", ARQ_VISITAS, "Relatorio_Imovel", [("Id_Relatorio", "id_relatorio", "texto"), ("Id_Imovel", "id_imovel", "texto")]),
    (SessaoUsuarioLegado, "sessoes_usuario_legado", ARQ_VISITAS, "Sessao_Usuario", [("IdSessao", "id_sessao", "texto"), ("IdCorretor", "id_corretor", "texto")]),
    (AdminLegado, "admins_legado", ARQ_VISITAS, "App_Admins", [("Email", "email", "texto")]),
]


def _migrar_tabela_legado_generica(session, report, classe, tabela, arquivo, aba, cols):
    ja_existe = session.query(classe).first()
    if ja_existe:
        report.warn(f"{tabela} ja tem dados - import historico e feito uma vez so, pulando")
        return

    df = ler_aba(arquivo, aba)
    linhas = []
    for _, row in df.iterrows():
        linha = {}
        for header, slug, tipo in cols:
            valor = row.get(header)
            if tipo == "data":
                linha[slug] = to_date(valor)
            elif tipo == "bool":
                linha[slug] = to_bool(valor)
            else:
                linha[slug] = to_str(valor)
        linhas.append(linha)

    copy_insert(session, tabela, [slug for header, slug, tipo in cols], linhas)
    for _ in linhas:
        report.bump(tabela, "inserido")


def migrar_legado_diversos(session, report: Report):
    for classe, tabela, arquivo, aba, cols in TABELAS_LEGADO_DIVERSAS:
        _migrar_tabela_legado_generica(session, report, classe, tabela, arquivo, aba, cols)

    # Menu_Corretor / Menu_Gerente / Menu_Sem_Cadastro -> 1 tabela so (menus_legado)
    ja_existe_menu = session.query(MenuLegado).first()
    if ja_existe_menu:
        report.warn("menus_legado ja tem dados - import historico e feito uma vez so, pulando")
        return

    menu_abas = [
        ("Menu_Corretor", "corretor"),
        ("Menu_Gerente", "gerente"),
        ("Menu_Sem_Cadastro", "sem_cadastro"),
    ]
    menu_linhas = []
    for aba, tipo_menu in menu_abas:
        df = ler_aba(ARQ_VISITAS, aba)
        for _, row in df.iterrows():
            linha = {"tipo_menu": tipo_menu}
            linha["id_item"] = to_str(row.get("Id"))
            linha["titulo"] = to_str(row.get("Titulo"))
            linha["subtitulo"] = to_str(row.get("Subtitulo"))
            linha["icone"] = to_str(row.get("Icone"))
            linha["deep_link"] = to_str(row.get("DeepLink"))
            linha["ordem"] = to_str(row.get("Ordem"))
            menu_linhas.append(linha)

    copy_insert(session, "menus_legado",
                ["tipo_menu", "id_item", "titulo", "subtitulo", "icone", "deep_link", "ordem"],
                menu_linhas)
    for _ in menu_linhas:
        report.bump("menus_legado", "inserido")


# ---------------------------------------------------------------------------
# Fase 7 - estoque_legado / leads_legado (Fato_Estoque ~159k, Fato_Lead ~63k)
# ---------------------------------------------------------------------------

def migrar_leads_legado(session, report: Report):
    ja_existe = session.query(LeadLegado).first()
    if ja_existe:
        report.warn("leads_legado ja tem dados - import historico e feito uma vez so, pulando")
        return

    df = ler_aba(ARQ_BASE_INTELIGENCIA, "Fato_Lead")
    cols = ["data", "fonte", "contato", "relatorio", "cliente", "telefone",
            "codigo_imovel", "atendimento", "equipe", "observacao", "san_observacao"]
    df.columns = cols

    linhas = []
    for _, row in df.iterrows():
        linhas.append({
            "data": to_date(row.get("data")),
            "fonte": to_str(row.get("fonte")),
            "contato": to_str(row.get("contato")),
            "relatorio": to_str(row.get("relatorio")),
            "cliente": to_str(row.get("cliente")),
            "telefone": to_str(row.get("telefone")),
            "codigo_imovel": to_str(row.get("codigo_imovel")),
            "atendimento": to_str(row.get("atendimento")),
            "equipe": to_str(row.get("equipe")),
            "observacao": to_str(row.get("observacao")),
            "san_observacao": to_str(row.get("san_observacao")),
        })

    copy_insert(session, "leads_legado", cols, linhas)
    for _ in linhas:
        report.bump("leads_legado", "inserido")


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------

FASES = {
    "usuarios": migrar_usuarios,
    "visitas": migrar_visitas,
    "contratos": migrar_contratos,
    "eventos_imovel_legado": migrar_eventos_imovel_legado,
    "venda_legado": migrar_venda_legado,
    "legado_diversos": migrar_legado_diversos,
    "leads_legado": migrar_leads_legado,
}
ORDEM = ["usuarios", "visitas", "contratos", "eventos_imovel_legado", "venda_legado", "legado_diversos", "leads_legado"]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true", help="Comita de fato. Sem essa flag roda em dry-run (rollback no final).")
    parser.add_argument("--only", choices=ORDEM, help="Roda so uma fase (ainda assim respeita a ordem se vier sozinha).")
    args = parser.parse_args()

    fases = [args.only] if args.only else ORDEM

    engine = create_engine(Config.SQLALCHEMY_DATABASE_URI)
    Session = sessionmaker(bind=engine)
    session = Session()
    report = Report()

    try:
        for nome_fase in fases:
            print(f"\n--- fase: {nome_fase} ---")
            FASES[nome_fase](session, report)
            session.flush()

        if args.apply:
            session.commit()
            print("\nCOMMIT realizado.")
        else:
            session.rollback()
            print("\nDRY-RUN: rollback realizado, nada foi salvo. Rode com --apply para persistir.")

    except Exception as e:
        session.rollback()
        print(f"\nERRO, rollback realizado: {e}")
        raise
    finally:
        session.close()
        report.print_summary(dry_run=not args.apply)


if __name__ == "__main__":
    main()
