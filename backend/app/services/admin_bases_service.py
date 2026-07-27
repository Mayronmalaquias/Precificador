"""Service da gestao de bases pelo site.

Porta a logica dos scripts Bases/registrarCapitacao.py, registrarSaida.py e
tratamento_estoque.py para o banco. Em vez de ler/escrever no Google Sheets:
- le o arquivo (CSV / XLSX / XLS-HTML do Imoview) enviado pelo admin;
- resolve dimensoes/pessoas a partir do proprio banco (usuarios, tipos/bairros_legado);
- grava nas tabelas correntes fato_captacao/fato_saida/fato_estoque/fato_destaque;
- upsert em imoveis_legado e auto-cria bairro em bairros_legado (igual ao script).
"""

import io
import re
from datetime import date, datetime
from typing import Any, List, Optional, Tuple

import pandas as pd

from app.database import SessionLocal
from app.models.captacao import Captacao
from app.models.contrato import Contrato
from app.models.fato_bases import FatoCaptacao, FatoDestaque, FatoEstoque, FatoSaida
from app.models.legado_diversos import BairroLegado, ImovelLegado, TipoImovelLegado
from app.models.usuarios import Usuarios


# =========================
# Regras de foco (de registrarCapitacao.py)
# =========================
BAIRROS_PP_RAW = {
    "PLANO PILOTO", "ASA SUL", "ASA NORTE", "NOROESTE", "SUDOESTE",
    "JARDIM BOTANICO", "LAGO NORTE", "LAGO SUL", "SETOR SUDOESTE",
}
BAIRROS_AC_RAW = {
    "Águas Claras Norte", "Águas Claras Sul", "Norte (Águas Claras)",
    "Sul (Águas Claras)", "Águas Claras",
}
MIN_COMISSAO = 3.5
MIN_VALOR_PP = 1_000_000
MIN_VALOR_AC = 600_000
TIPOS_NAO_RESIDENCIAIS = {"T7", "T8", "T9", "T10", "T11"}


# =========================
# Helpers de normalizacao (de registrarCapitacao.py / registrarSaida.py)
# =========================
def norm(s: Any) -> str:
    if s is None:
        return ""
    s = str(s).strip().upper()
    s = (
        s.replace("Á", "A").replace("À", "A").replace("Ã", "A").replace("Â", "A")
        .replace("É", "E").replace("Ê", "E")
        .replace("Í", "I")
        .replace("Ó", "O").replace("Õ", "O").replace("Ô", "O")
        .replace("Ú", "U")
        .replace("Ç", "C")
        .replace("Ä", "A").replace("Ë", "E").replace("Ï", "I").replace("Ö", "O").replace("Ü", "U")
    )
    return re.sub(r"\s+", " ", s)


BAIRROS_PP = {norm(x) for x in BAIRROS_PP_RAW}
BAIRROS_AC = {norm(x) for x in BAIRROS_AC_RAW}


def to_float(x: Any) -> float:
    if x is None or (isinstance(x, float) and pd.isna(x)):
        return 0.0
    if isinstance(x, bool):
        return 1.0 if x else 0.0
    if isinstance(x, (int, float)):
        return float(x)
    s = str(x).strip().replace("'", "")
    if not s:
        return 0.0
    s = re.sub(r"[^\d,.\-]", "", s)
    if not s or s in {"-", ".", ","}:
        return 0.0
    if "." in s and "," in s:
        s = s.replace(".", "").replace(",", ".")
    elif "," in s:
        s = s.replace(",", ".")
    try:
        return float(s)
    except Exception:
        return 0.0


def to_str(x: Any) -> str:
    if x is None or (isinstance(x, float) and pd.isna(x)):
        return ""
    s = str(x).strip()
    if s.startswith("'"):
        s = s[1:]
    if s.lower() in {"nan", "none", "null"}:
        return ""
    return s


def normalize_codigo(x: Any) -> Optional[str]:
    if x is None or (isinstance(x, float) and pd.isna(x)):
        return None
    s = str(x).strip().replace("'", "")
    if not s or s.lower() == "nan":
        return None
    if re.fullmatch(r"\d+(\.0+)?", s):
        s = str(int(float(s)))
    return s


def parse_date_any(x: Any) -> Optional[date]:
    if x is None or (isinstance(x, float) and pd.isna(x)):
        return None
    if isinstance(x, datetime):
        return x.date()
    if isinstance(x, date):
        return x
    s = str(x).strip().replace("'", "")
    if not s:
        return None
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%Y/%m/%d",
                "%d/%m/%Y %H:%M", "%d/%m/%Y %H:%M:%S", "%Y-%m-%d %H:%M:%S"):
        try:
            return datetime.strptime(s, fmt).date()
        except ValueError:
            pass
    try:
        dt = pd.to_datetime(s, dayfirst=True, errors="coerce")
        return None if pd.isna(dt) else dt.date()
    except Exception:
        return None


def split_captadores(raw: Any) -> List[str]:
    if raw is None or (isinstance(raw, float) and pd.isna(raw)):
        return []
    s = str(raw).strip()
    if not s:
        return []
    partes = re.split(r"\s*\|\s*|\s*;\s*|\s*,\s*|/\s*", s)
    seen, out = set(), []
    for p in partes:
        p = p.strip()
        if p and p.lower() != "nan" and p not in seen:
            seen.add(p)
            out.append(p)
    return out[:3]


def classificar_foco(bairro_nome: str, valor: float, comissao_pct: float, is_residencial: bool) -> Tuple[bool, bool]:
    b = norm(bairro_nome)
    v = float(valor or 0)
    c = float(comissao_pct or 0)
    foco_pp = (b in BAIRROS_PP) and (v >= MIN_VALOR_PP) and (c >= MIN_COMISSAO) and is_residencial
    foco_ac = (b in BAIRROS_AC) and (v >= MIN_VALOR_AC) and (c >= MIN_COMISSAO) and is_residencial
    return foco_pp, foco_ac


def situacao_eh_vago_disponivel(situacao: Any) -> bool:
    return norm(situacao) in {"VAGO/DISPONIVEL", "VAGO / DISPONIVEL", "VAGO", "DISPONIVEL"}


# --- Destaque: categorias dos portais (de Trasfer_Destaque.gs) ---
def filtra_portal(valor: Any) -> str:
    if not valor:
        return ""
    s = str(valor).lower()
    if "desativado" in s:
        return "Simples"
    if "super destaque" in s:
        return "Super destaque"
    if "destaque" in s:
        return "Destaque"
    if "simples" in s:
        return "Simples"
    return ""


def checar_publicacao(portal_olx: Any, portal_iw: Any, publicacao: Any) -> str:
    olx = str(portal_olx or "").lower()
    iw = str(portal_iw or "").lower()
    if "desativado" in olx and "desativado" in iw:
        return "Não liberada"
    return to_str(publicacao)


# =========================
# Leitura de arquivo (CSV / XLSX / XLS-HTML do Imoview)
# =========================
def get_col(df: pd.DataFrame, accepted_names: List[str]) -> Optional[str]:
    accepted = {norm(x) for x in accepted_names}
    for c in df.columns:
        if norm(c) in accepted:
            return c
    return None


def ler_arquivo(file_storage) -> pd.DataFrame:
    filename = (getattr(file_storage, "filename", "") or "").lower()
    raw = file_storage.read()
    bio = io.BytesIO(raw)

    df = None
    if filename.endswith(".csv"):
        for sep in (";", ","):
            bio.seek(0)
            try:
                tmp = pd.read_csv(bio, sep=sep, encoding="utf-8-sig", engine="python")
                if tmp.shape[1] > 1 or sep == ",":
                    df = tmp
                    break
            except Exception:
                continue
    elif filename.endswith(".xlsx"):
        df = pd.read_excel(bio)
    elif filename.endswith(".xls"):
        # Imoview exporta HTML disfarcado de .xls
        try:
            bio.seek(0)
            tables = pd.read_html(bio)
            df = max(tables, key=lambda t: t.shape[0] * t.shape[1])
        except Exception:
            bio.seek(0)
            df = pd.read_excel(bio)
    else:
        # fallback: tenta csv
        bio.seek(0)
        df = pd.read_csv(bio, sep=None, encoding="utf-8-sig", engine="python")

    if df is None or df.empty:
        raise ValueError("Nao foi possivel ler dados do arquivo (vazio ou formato invalido).")

    df.columns = [str(c).replace("﻿", "").strip() for c in df.columns]
    return df


# =========================
# Mapas / dimensoes a partir do banco
# =========================
def carregar_mapas(session) -> dict:
    nome_to_idcorretor = {}
    idcorretor_to_gerente = {}
    for u in session.query(Usuarios.id_usuarios, Usuarios.nome, Usuarios.username, Usuarios.team).all():
        idc = to_str(u.id_usuarios)
        nome = to_str(u.nome) or to_str(u.username)
        team = to_str(u.team)
        if idc and nome:
            nome_to_idcorretor[norm(nome)] = idc
        if idc and team:
            idcorretor_to_gerente[idc] = team

    tipo_name_to_id = {}
    for t in session.query(TipoImovelLegado.id_tipo, TipoImovelLegado.nome).all():
        nm = norm(t.nome)
        if nm:
            tipo_name_to_id[nm] = to_str(t.id_tipo)

    bairro_name_to_id = {}
    bairro_max = 0
    for b in session.query(BairroLegado.id_bairro, BairroLegado.nome).all():
        nm = norm(b.nome)
        idb = to_str(b.id_bairro)
        if nm:
            bairro_name_to_id[nm] = idb
        if idb.upper().startswith("B"):
            try:
                bairro_max = max(bairro_max, int(idb[1:]))
            except ValueError:
                pass

    return {
        "nome_to_idcorretor": nome_to_idcorretor,
        "idcorretor_to_gerente": idcorretor_to_gerente,
        "tipo_name_to_id": tipo_name_to_id,
        "bairro_name_to_id": bairro_name_to_id,
        "_bairro_max": bairro_max,
    }


def ensure_bairro(session, mapas: dict, bairro_nome: str) -> Tuple[str, bool]:
    key = norm(bairro_nome)
    if not key:
        return "", False
    if key in mapas["bairro_name_to_id"]:
        return mapas["bairro_name_to_id"][key], False
    mapas["_bairro_max"] += 1
    new_id = f"B{mapas['_bairro_max']}"
    session.add(BairroLegado(id_bairro=new_id, nome=to_str(bairro_nome)))
    session.flush()  # disponibiliza o id pra FK de imoveis_legado
    mapas["bairro_name_to_id"][key] = new_id
    return new_id, True


def map_tipo(mapas: dict, tipo_nome: str) -> Optional[str]:
    return mapas["tipo_name_to_id"].get(norm(tipo_nome)) or None


def is_residencial(tipo_id: Optional[str]) -> bool:
    if not tipo_id:
        return True
    return str(tipo_id).strip().upper() not in TIPOS_NAO_RESIDENCIAIS


def resolver_captadores(mapas: dict, nomes: List[str]) -> List[str]:
    out = []
    for nome in nomes:
        out.append(mapas["nome_to_idcorretor"].get(norm(nome), nome))
    return [c for c in (to_str(x) for x in out) if c][:3]


def upsert_imovel_legado(session, codigo: str, tipo_id, valor: float, bairro_id, foco_pp: bool, foco_ac: bool):
    codigo = to_str(codigo)
    if not codigo:
        return
    row = session.query(ImovelLegado).filter(ImovelLegado.codigo == codigo).first()
    if row is None:
        row = ImovelLegado(codigo=codigo)
        session.add(row)
    row.tipo = tipo_id or None
    row.valor = str(valor) if valor else row.valor
    row.bairro = bairro_id or None
    row.foco_pp = bool(foco_pp)
    row.foco_ac = bool(foco_ac)


# =========================
# Insercao unitaria (compartilhada entre upload e manual)
# =========================
def _inserir_captacao(session, mapas, dados: dict, origem: str, arquivo: Optional[str], criado_por: Optional[str]) -> Tuple[str, bool]:
    codigo = normalize_codigo(dados.get("codigo"))
    if not codigo:
        return "erro", False

    bairro_nome = to_str(dados.get("bairro"))
    valor = to_float(dados.get("valor"))
    tipo_nome = to_str(dados.get("tipo"))
    comissao = to_float(dados.get("comissao"))
    data_entrada = parse_date_any(dados.get("data_entrada")) or date.today()
    captadores = resolver_captadores(mapas, dados.get("captadores") or [])

    bairro_id, criou_bairro = ensure_bairro(session, mapas, bairro_nome)
    tipo_id = map_tipo(mapas, tipo_nome)
    foco_pp, foco_ac = classificar_foco(bairro_nome, valor, comissao, is_residencial(tipo_id))
    capt1 = captadores[0] if captadores else ""
    gerente = mapas["idcorretor_to_gerente"].get(capt1, "")

    upsert_imovel_legado(session, codigo, tipo_id, valor, bairro_id, foco_pp, foco_ac)

    # dedup: (codigo, data_entrada, captador1)
    existe = session.query(FatoCaptacao.id).filter(
        FatoCaptacao.codigo_imovel == codigo,
        FatoCaptacao.data_entrada == data_entrada,
        FatoCaptacao.captador1 == (capt1 or None),
    ).first()
    if existe:
        return "duplicado", criou_bairro

    session.add(FatoCaptacao(
        codigo_imovel=codigo,
        captador1=captadores[0] if len(captadores) > 0 else None,
        captador2=captadores[1] if len(captadores) > 1 else None,
        captador3=captadores[2] if len(captadores) > 2 else None,
        id_gerente=gerente or None,
        data_entrada=data_entrada,
        bairro_id=bairro_id or None,
        bairro_nome=bairro_nome or None,
        tipo_id=tipo_id,
        tipo_nome=tipo_nome or None,
        valor=valor or None,
        comissao_pct=comissao or None,
        foco_pp=foco_pp,
        foco_ac=foco_ac,
        finalidade=to_str(dados.get("finalidade")) or None,
        origem=origem,
        arquivo_origem=arquivo,
        criado_por=criado_por,
    ))
    return "inserido", criou_bairro


def _ultima_captacao_por_codigo(session, codigo: str):
    return (
        session.query(FatoCaptacao)
        .filter(FatoCaptacao.codigo_imovel == codigo)
        .order_by(FatoCaptacao.data_entrada.desc(), FatoCaptacao.id.desc())
        .first()
    )


def _ultima_jornada_captacao_por_codigo(session, codigo: str):
    codigo = normalize_codigo(codigo)
    if not codigo:
        return None
    query = (
        session.query(Captacao)
        .filter(Captacao.numero_imovel.isnot(None))
        .filter((Captacao.captou_imovel.is_(True)) | (Captacao.status.in_(("captado", "exclusividade"))))
        .order_by(Captacao.updated_at.desc(), Captacao.id.desc())
    )
    for captacao in query.all():
        if normalize_codigo(captacao.numero_imovel) == codigo:
            return captacao
    return None


def _inserir_saida(session, mapas, dados: dict, origem: str, arquivo: Optional[str], criado_por: Optional[str]) -> str:
    codigo = normalize_codigo(dados.get("codigo"))
    if not codigo:
        return "erro"
    data_saida = parse_date_any(dados.get("data_saida")) or date.today()
    motivo = to_str(dados.get("motivo"))

    captadores = resolver_captadores(mapas, dados.get("captadores") or [])
    gerente = to_str(dados.get("id_gerente"))
    if not captadores:
        cap = _ultima_captacao_por_codigo(session, codigo)
        if cap:
            captadores = [c for c in (cap.captador1, cap.captador2, cap.captador3) if c]
            gerente = gerente or to_str(cap.id_gerente)
    if not gerente and captadores:
        gerente = mapas["idcorretor_to_gerente"].get(captadores[0], "")

    existe = session.query(FatoSaida.id).filter(
        FatoSaida.codigo_imovel == codigo,
        FatoSaida.data_saida == data_saida,
    ).first()
    if existe:
        return "duplicado"

    session.add(FatoSaida(
        codigo_imovel=codigo,
        captador1=captadores[0] if len(captadores) > 0 else None,
        captador2=captadores[1] if len(captadores) > 1 else None,
        captador3=captadores[2] if len(captadores) > 2 else None,
        id_gerente=gerente or None,
        motivo=motivo or None,
        data_saida=data_saida,
        origem=origem,
        arquivo_origem=arquivo,
        criado_por=criado_por,
    ))
    return "inserido"


def _inserir_estoque(session, mapas, dados: dict, origem: str, arquivo: Optional[str], criado_por: Optional[str]) -> str:
    codigo = normalize_codigo(dados.get("codigo"))
    if not codigo:
        return "erro"
    data_estoque = parse_date_any(dados.get("data_estoque")) or date.today()
    captadores = resolver_captadores(mapas, dados.get("captadores") or [])
    gerente = to_str(dados.get("id_gerente"))
    if not captadores:
        cap = _ultima_captacao_por_codigo(session, codigo)
        if cap:
            captadores = [c for c in (cap.captador1, cap.captador2, cap.captador3) if c]
            gerente = gerente or to_str(cap.id_gerente)
    if not captadores:
        jornada = _ultima_jornada_captacao_por_codigo(session, codigo)
        if jornada:
            captadores = [to_str(jornada.id_corretor) or to_str(jornada.nome_corretor)]
            gerente = gerente or to_str(jornada.team)
    if not gerente and captadores:
        gerente = mapas["idcorretor_to_gerente"].get(captadores[0], "")

    existe = session.query(FatoEstoque.id).filter(
        FatoEstoque.codigo_imovel == codigo,
        FatoEstoque.data_estoque == data_estoque,
    ).first()
    if existe:
        return "duplicado"

    session.add(FatoEstoque(
        codigo_imovel=codigo,
        captador1=captadores[0] if len(captadores) > 0 else None,
        captador2=captadores[1] if len(captadores) > 1 else None,
        captador3=captadores[2] if len(captadores) > 2 else None,
        id_gerente=gerente or None,
        data_estoque=data_estoque,
        publicacao_na_internet=to_str(dados.get("publicacao_na_internet")) or None,
        exclusivo=to_str(dados.get("exclusivo")) or None,
        categoria_df=to_str(dados.get("categoria_df")) or None,
        categoria_df_seguro=to_str(dados.get("categoria_df_seguro")) or None,
        categoria_wi=to_str(dados.get("categoria_wi")) or None,
        id_anuncio_meta=to_str(dados.get("id_anuncio_meta")) or None,
        origem=origem,
        arquivo_origem=arquivo,
        criado_por=criado_por,
    ))
    return "inserido"


# =========================
# Processamento de arquivo (substitui os 3 scripts)
# =========================
def processar_captacao(file_storage, criado_por=None, finalidade="Venda") -> dict:
    df = ler_arquivo(file_storage)
    arquivo = getattr(file_storage, "filename", None)

    col_cod = get_col(df, ["Codigo", "Código", "Code"])
    if not col_cod:
        raise ValueError("Arquivo de captacao sem coluna de codigo (Codigo/Código).")
    col_bairro = get_col(df, ["Bairro"])
    col_valor = get_col(df, ["Valor"])
    col_tipo = get_col(df, ["Tipo"])
    col_com = get_col(df, ["ComissaoVenda", "Comissao", "Comissão", "% comissão", "ComissaoVenda%"])
    col_capt = get_col(df, ["Captadores", "Captador"])
    col_data = get_col(df, ["DataCadastro", "DataHoraUltimaAlteracao", "DataHoraUltimaSituacao", "DataEntrada", "Data"])
    col_fin = get_col(df, ["Finalidade"])

    resumo = {"inseridos": 0, "ignorados_duplicados": 0, "bairros_criados": 0, "erros": [], "preview": []}
    session = SessionLocal()
    try:
        mapas = carregar_mapas(session)
        for i, row in df.iterrows():
            if finalidade and col_fin and norm(row.get(col_fin)) != norm(finalidade):
                continue
            dados = {
                "codigo": row.get(col_cod),
                "bairro": row.get(col_bairro) if col_bairro else "",
                "valor": row.get(col_valor) if col_valor else 0,
                "tipo": row.get(col_tipo) if col_tipo else "",
                "comissao": row.get(col_com) if col_com else 0,
                "captadores": split_captadores(row.get(col_capt)) if col_capt else [],
                "data_entrada": row.get(col_data) if col_data else None,
                "finalidade": row.get(col_fin) if col_fin else finalidade,
            }
            try:
                status, criou_bairro = _inserir_captacao(session, mapas, dados, "upload", arquivo, criado_por)
            except Exception as e:  # erro numa linha nao derruba o arquivo todo
                resumo["erros"].append(f"linha {i}: {e}")
                continue
            if criou_bairro:
                resumo["bairros_criados"] += 1
            if status == "inserido":
                resumo["inseridos"] += 1
                if len(resumo["preview"]) < 10:
                    resumo["preview"].append(normalize_codigo(dados["codigo"]))
            elif status == "duplicado":
                resumo["ignorados_duplicados"] += 1
            else:
                resumo["erros"].append(f"linha {i}: codigo invalido")
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
    return resumo


def processar_saida(file_storage, criado_por=None, finalidade="Venda") -> dict:
    df = ler_arquivo(file_storage)
    arquivo = getattr(file_storage, "filename", None)

    col_cod = get_col(df, ["Codigo", "Código", "Code"])
    if not col_cod:
        raise ValueError("Arquivo de saida sem coluna de codigo (Codigo/Código).")
    col_sit = get_col(df, ["Situacao", "Situação"])
    col_data = get_col(df, ["DataHoraUltimaSituacao", "DataUltimaSituacao", "DataSaida", "Data"])
    col_motivo = get_col(df, ["MotivoDesativacao", "Motivo", "MotivoSaida"])
    col_fin = get_col(df, ["Finalidade"])

    resumo = {"inseridos": 0, "ignorados_duplicados": 0, "erros": [], "preview": []}
    session = SessionLocal()
    try:
        mapas = carregar_mapas(session)
        for i, row in df.iterrows():
            if finalidade and col_fin and norm(row.get(col_fin)) != norm(finalidade):
                continue
            # regra: tudo que NAO for vago/disponivel e saida
            if col_sit and situacao_eh_vago_disponivel(row.get(col_sit)):
                continue
            motivo = to_str(row.get(col_motivo)) if col_motivo else ""
            if not motivo and col_sit:
                motivo = to_str(row.get(col_sit))
            dados = {
                "codigo": row.get(col_cod),
                "data_saida": row.get(col_data) if col_data else None,
                "motivo": motivo,
                "captadores": [],
            }
            try:
                status = _inserir_saida(session, mapas, dados, "upload", arquivo, criado_por)
            except Exception as e:
                resumo["erros"].append(f"linha {i}: {e}")
                continue
            if status == "inserido":
                resumo["inseridos"] += 1
                if len(resumo["preview"]) < 10:
                    resumo["preview"].append(normalize_codigo(dados["codigo"]))
            elif status == "duplicado":
                resumo["ignorados_duplicados"] += 1
            else:
                resumo["erros"].append(f"linha {i}: codigo invalido")
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
    return resumo


def processar_estoque(file_storage, criado_por=None, data_estoque=None) -> dict:
    df = ler_arquivo(file_storage)
    arquivo = getattr(file_storage, "filename", None)
    data_ref = parse_date_any(data_estoque) or date.today()

    col_cod = get_col(df, ["Codigo", "Código", "Code"])
    if not col_cod:
        raise ValueError("Arquivo de estoque sem coluna de codigo (Codigo/Código).")
    col_capt = get_col(df, ["Captadores", "Captador"])
    col_data = get_col(df, ["DataEstoque", "Data"])
    col_pub = get_col(df, ["PublicacaoNaInternet", "Publicacao na Internet", "Publicado"])
    col_exc = get_col(df, ["Exclusivo", "Exclusividade"])

    resumo = {"inseridos": 0, "ignorados_duplicados": 0, "erros": [], "preview": []}
    session = SessionLocal()
    try:
        mapas = carregar_mapas(session)
        for i, row in df.iterrows():
            dados = {
                "codigo": row.get(col_cod),
                "captadores": split_captadores(row.get(col_capt)) if col_capt else [],
                "data_estoque": row.get(col_data) if col_data else data_ref,
                "publicacao_na_internet": row.get(col_pub) if col_pub else "",
                "exclusivo": row.get(col_exc) if col_exc else "",
            }
            try:
                status = _inserir_estoque(session, mapas, dados, "upload", arquivo, criado_por)
            except Exception as e:
                resumo["erros"].append(f"linha {i}: {e}")
                continue
            if status == "inserido":
                resumo["inseridos"] += 1
                if len(resumo["preview"]) < 10:
                    resumo["preview"].append(normalize_codigo(dados["codigo"]))
            elif status == "duplicado":
                resumo["ignorados_duplicados"] += 1
            else:
                resumo["erros"].append(f"linha {i}: codigo invalido")
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
    return resumo


def _ler_codigos_posicional(file_storage, col_codigo=2, skip=2, col_situacao=None, excluir_situacoes=None) -> set:
    """Le os relatorios auxiliares de Destaque (Seguros/Assinados) por POSICAO de coluna,
    igual ao Trasfer_Destaque.gs (codigo na 3a coluna, dados a partir da 3a linha)."""
    raw = file_storage.read()
    bio = io.BytesIO(raw)
    fn = (getattr(file_storage, "filename", "") or "").lower()
    if fn.endswith(".csv"):
        bio.seek(0)
        df = pd.read_csv(bio, header=None, sep=None, engine="python", encoding="utf-8-sig")
    else:
        df = pd.read_excel(bio, header=None)

    excluir = {norm(x) for x in (excluir_situacoes or set())}
    out = set()
    for i in range(skip, len(df)):
        row = df.iloc[i]
        if col_codigo >= len(row):
            continue
        cod = normalize_codigo(row.iloc[col_codigo])
        if not cod:
            continue
        if col_situacao is not None and col_situacao < len(row):
            if norm(row.iloc[col_situacao]) in excluir:
                continue
        out.add(cod)
    return out


def processar_destaque(imoveis_file, seguros_file, assinados_file, criado_por=None) -> dict:
    """Importa os 3 arquivos de Destaque (imoveis + seguros + assinados) e faz
    FULL REPLACE de fato_destaque (igual ao Trasfer_Destaque.gs, que limpava a aba)."""
    df = ler_arquivo(imoveis_file)
    arquivo = getattr(imoveis_file, "filename", None)

    col_cod = get_col(df, ["Codigo", "Código", "Code"])
    if not col_cod:
        raise ValueError("Arquivo de imoveis sem coluna de codigo (Codigo/Código).")
    col_capt = get_col(df, ["Captadores", "Captador"])
    col_end = get_col(df, ["Endereco", "Endereço"])
    col_valor = get_col(df, ["Valor"])
    col_bairro = get_col(df, ["Bairro"])
    col_pub = get_col(df, ["PublicacaoNaInternet", "Publicacao na Internet", "PublicacaoInternet"])
    col_olx = get_col(df, ["PortalOlxBrasil", "PortalOlx", "OLX", "DFImoveis", "PortalDFImoveis"])
    col_iw = get_col(df, ["PortalImovelWeb", "ImovelWeb", "WImoveis", "PortalWImoveis"])

    seguros = _ler_codigos_posicional(seguros_file, col_codigo=2, skip=2, col_situacao=5,
                                      excluir_situacoes={"Cadastrado", "Com Pendência", "Com Pendencia"})
    assinados = _ler_codigos_posicional(assinados_file, col_codigo=2, skip=2)

    resumo = {"inseridos": 0, "removidos": 0, "erros": [], "preview": []}
    session = SessionLocal()
    try:
        mapas = carregar_mapas(session)
        resumo["removidos"] = session.query(FatoDestaque).delete()  # full replace
        for i, row in df.iterrows():
            codigo = normalize_codigo(row.get(col_cod))
            if not codigo:
                continue
            try:
                captadores = resolver_captadores(mapas, split_captadores(row.get(col_capt)) if col_capt else [])
                gerente = mapas["idcorretor_to_gerente"].get(captadores[0], "") if captadores else ""
                olx = row.get(col_olx) if col_olx else ""
                iw = row.get(col_iw) if col_iw else ""
                session.add(FatoDestaque(
                    codigo_imovel=codigo,
                    captador1=captadores[0] if len(captadores) > 0 else None,
                    captador2=captadores[1] if len(captadores) > 1 else None,
                    captador3=captadores[2] if len(captadores) > 2 else None,
                    id_gerente=gerente or None,
                    data_destaque=date.today(),
                    endereco=to_str(row.get(col_end)) if col_end else None,
                    bairro=to_str(row.get(col_bairro)) if col_bairro else None,
                    publicacao_web=checar_publicacao(olx, iw, row.get(col_pub) if col_pub else "") or None,
                    categoria_df=filtra_portal(olx) or None,
                    categoria_wi=filtra_portal(iw) or None,
                    categoria_df_seguro=("Sim" if codigo in seguros else "Não"),
                    categoria_df_assinado=("Sim" if codigo in assinados else "Não"),
                    valor=to_float(row.get(col_valor)) or None if col_valor else None,
                    origem="upload",
                    arquivo_origem=arquivo,
                    criado_por=criado_por,
                ))
                resumo["inseridos"] += 1
                if len(resumo["preview"]) < 10:
                    resumo["preview"].append(codigo)
            except Exception as e:
                resumo["erros"].append(f"linha {i}: {e}")
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
    return resumo


# =========================
# Lancamento manual
# =========================
def criar_captacao_manual(dados: dict, criado_por=None) -> dict:
    session = SessionLocal()
    try:
        mapas = carregar_mapas(session)
        if isinstance(dados.get("captadores"), str):
            dados["captadores"] = split_captadores(dados["captadores"])
        status, criou_bairro = _inserir_captacao(session, mapas, dados, "manual", None, criado_por)
        if status == "erro":
            return {"ok": False, "error": "codigo obrigatorio"}
        session.commit()
        return {"ok": True, "status": status, "bairro_criado": criou_bairro}
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def criar_saida_manual(dados: dict, criado_por=None) -> dict:
    session = SessionLocal()
    try:
        mapas = carregar_mapas(session)
        if isinstance(dados.get("captadores"), str):
            dados["captadores"] = split_captadores(dados["captadores"])
        status = _inserir_saida(session, mapas, dados, "manual", None, criado_por)
        if status == "erro":
            return {"ok": False, "error": "codigo obrigatorio"}
        session.commit()
        return {"ok": True, "status": status}
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def criar_estoque_manual(dados: dict, criado_por=None) -> dict:
    session = SessionLocal()
    try:
        mapas = carregar_mapas(session)
        if isinstance(dados.get("captadores"), str):
            dados["captadores"] = split_captadores(dados["captadores"])
        status = _inserir_estoque(session, mapas, dados, "manual", None, criado_por)
        if status == "erro":
            return {"ok": False, "error": "codigo obrigatorio"}
        session.commit()
        return {"ok": True, "status": status}
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def criar_destaque_manual(dados: dict, criado_por=None) -> dict:
    session = SessionLocal()
    try:
        mapas = carregar_mapas(session)
        caps = dados.get("captadores")
        if isinstance(caps, str):
            caps = split_captadores(caps)
        captadores = resolver_captadores(mapas, caps or [])
        gerente = to_str(dados.get("id_gerente"))
        if not gerente and captadores:
            gerente = mapas["idcorretor_to_gerente"].get(captadores[0], "")
        session.add(FatoDestaque(
            codigo_imovel=normalize_codigo(dados.get("codigo")),
            captador1=captadores[0] if len(captadores) > 0 else None,
            captador2=captadores[1] if len(captadores) > 1 else None,
            captador3=captadores[2] if len(captadores) > 2 else None,
            id_gerente=gerente or None,
            data_destaque=parse_date_any(dados.get("data_destaque")) or date.today(),
            endereco=to_str(dados.get("endereco")) or None,
            bairro=to_str(dados.get("bairro")) or None,
            publicacao_web=to_str(dados.get("publicacao_web")) or None,
            categoria_df=to_str(dados.get("categoria_df")) or None,
            categoria_wi=to_str(dados.get("categoria_wi")) or None,
            categoria_df_seguro=to_str(dados.get("categoria_df_seguro")) or None,
            categoria_df_assinado=to_str(dados.get("categoria_df_assinado")) or None,
            valor=to_float(dados.get("valor")) or None,
            origem="manual",
            criado_por=criado_por,
        ))
        session.commit()
        return {"ok": True}
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


# =========================
# Serializacao + consultas paginadas
# =========================
def _d(v):
    if v is None:
        return None
    if isinstance(v, (date, datetime)):
        return v.isoformat()
    return v


def _num(v):
    return float(v) if v is not None else None


def _captacao_dict(c: FatoCaptacao) -> dict:
    return {
        "id": c.id, "codigo_imovel": c.codigo_imovel,
        "captador1": c.captador1, "captador2": c.captador2, "captador3": c.captador3,
        "id_gerente": c.id_gerente, "data_entrada": _d(c.data_entrada),
        "bairro_id": c.bairro_id, "bairro_nome": c.bairro_nome,
        "tipo_id": c.tipo_id, "tipo_nome": c.tipo_nome,
        "valor": _num(c.valor), "comissao_pct": _num(c.comissao_pct),
        "foco_pp": c.foco_pp, "foco_ac": c.foco_ac, "finalidade": c.finalidade,
        "origem": c.origem, "arquivo_origem": c.arquivo_origem, "criado_por": c.criado_por,
        "created_at": _d(c.created_at),
    }


def _saida_dict(s: FatoSaida) -> dict:
    return {
        "id": s.id, "codigo_imovel": s.codigo_imovel,
        "captador1": s.captador1, "captador2": s.captador2, "captador3": s.captador3,
        "id_gerente": s.id_gerente, "motivo": s.motivo, "data_saida": _d(s.data_saida),
        "origem": s.origem, "arquivo_origem": s.arquivo_origem, "criado_por": s.criado_por,
        "created_at": _d(s.created_at),
    }


def _estoque_dict(e: FatoEstoque) -> dict:
    return {
        "id": e.id, "codigo_imovel": e.codigo_imovel,
        "captador1": e.captador1, "captador2": e.captador2, "captador3": e.captador3,
        "id_gerente": e.id_gerente, "data_estoque": _d(e.data_estoque),
        "publicacao_na_internet": e.publicacao_na_internet, "exclusivo": e.exclusivo,
        "categoria_df": e.categoria_df, "categoria_df_seguro": e.categoria_df_seguro,
        "categoria_wi": e.categoria_wi, "id_anuncio_meta": e.id_anuncio_meta,
        "origem": e.origem, "arquivo_origem": e.arquivo_origem, "criado_por": e.criado_por,
        "created_at": _d(e.created_at),
    }


def _aplicar_filtros_evento(query, model, filtros: dict, col_data):
    codigo = (filtros.get("codigo") or "").strip()
    captador = (filtros.get("captador") or "").strip()
    data_de = parse_date_any(filtros.get("data_de"))
    data_ate = parse_date_any(filtros.get("data_ate"))
    if codigo:
        query = query.filter(model.codigo_imovel == normalize_codigo(codigo))
    if captador:
        like = f"%{captador}%"
        query = query.filter(
            (model.captador1.ilike(like)) | (model.captador2.ilike(like)) | (model.captador3.ilike(like))
        )
    if data_de:
        query = query.filter(col_data >= data_de)
    if data_ate:
        query = query.filter(col_data <= data_ate)
    return query


def _listar(model, col_data, to_dict, filtros: dict, page: int, per_page: int, extra=None) -> dict:
    page = max(1, int(page or 1))
    per_page = min(max(1, int(per_page or 50)), 500)
    session = SessionLocal()
    try:
        query = session.query(model)
        query = _aplicar_filtros_evento(query, model, filtros, col_data)
        if extra:
            query = extra(query)
        total = query.count()
        rows = query.order_by(col_data.desc(), model.id.desc()) \
                    .offset((page - 1) * per_page).limit(per_page).all()
        return {"ok": True, "total": total, "page": page, "per_page": per_page,
                "items": [to_dict(r) for r in rows]}
    finally:
        session.close()


def listar_captacoes(filtros: dict, page=1, per_page=50) -> dict:
    def extra(q):
        bairro = (filtros.get("bairro") or "").strip()
        if bairro:
            q = q.filter(FatoCaptacao.bairro_nome.ilike(f"%{bairro}%"))
        return q
    return _listar(FatoCaptacao, FatoCaptacao.data_entrada, _captacao_dict, filtros, page, per_page, extra)


def listar_saidas(filtros: dict, page=1, per_page=50) -> dict:
    return _listar(FatoSaida, FatoSaida.data_saida, _saida_dict, filtros, page, per_page)


def listar_estoque(filtros: dict, page=1, per_page=50) -> dict:
    return _listar(FatoEstoque, FatoEstoque.data_estoque, _estoque_dict, filtros, page, per_page)


# =========================
# CRUD de dimensoes (Tipo / Bairro)
# =========================
def listar_tipos() -> dict:
    session = SessionLocal()
    try:
        rows = session.query(TipoImovelLegado).order_by(TipoImovelLegado.id_tipo).all()
        return {"ok": True, "items": [{"id": r.id, "id_tipo": r.id_tipo, "nome": r.nome} for r in rows]}
    finally:
        session.close()


def _next_dim_id(session, model, col, prefix: str) -> str:
    maxn = 0
    for (val,) in session.query(col).all():
        v = to_str(val)
        if v.upper().startswith(prefix):
            try:
                maxn = max(maxn, int(v[len(prefix):]))
            except ValueError:
                pass
    return f"{prefix}{maxn + 1}"


def criar_tipo(nome: str, id_tipo=None) -> dict:
    nome = to_str(nome)
    if not nome:
        return {"ok": False, "error": "nome obrigatorio"}
    session = SessionLocal()
    try:
        if session.query(TipoImovelLegado).filter(TipoImovelLegado.nome.ilike(nome)).first():
            return {"ok": False, "error": "tipo ja existe"}
        novo_id = to_str(id_tipo) or _next_dim_id(session, TipoImovelLegado, TipoImovelLegado.id_tipo, "T")
        row = TipoImovelLegado(id_tipo=novo_id, nome=nome)
        session.add(row)
        session.commit()
        return {"ok": True, "id": row.id, "id_tipo": novo_id, "nome": nome}
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def atualizar_tipo(id_: int, nome: str) -> dict:
    session = SessionLocal()
    try:
        row = session.query(TipoImovelLegado).get(id_)
        if not row:
            return {"ok": False, "error": "tipo nao encontrado"}
        row.nome = to_str(nome)
        session.commit()
        return {"ok": True}
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def excluir_tipo(id_: int) -> dict:
    session = SessionLocal()
    try:
        row = session.query(TipoImovelLegado).get(id_)
        if not row:
            return {"ok": False, "error": "tipo nao encontrado"}
        session.delete(row)
        session.commit()
        return {"ok": True}
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def listar_bairros() -> dict:
    session = SessionLocal()
    try:
        rows = session.query(BairroLegado).order_by(BairroLegado.nome).all()
        return {"ok": True, "items": [{"id": r.id, "id_bairro": r.id_bairro, "nome": r.nome} for r in rows]}
    finally:
        session.close()


def criar_bairro(nome: str) -> dict:
    nome = to_str(nome)
    if not nome:
        return {"ok": False, "error": "nome obrigatorio"}
    session = SessionLocal()
    try:
        if session.query(BairroLegado).filter(BairroLegado.nome.ilike(nome)).first():
            return {"ok": False, "error": "bairro ja existe"}
        novo_id = _next_dim_id(session, BairroLegado, BairroLegado.id_bairro, "B")
        row = BairroLegado(id_bairro=novo_id, nome=nome)
        session.add(row)
        session.commit()
        return {"ok": True, "id": row.id, "id_bairro": novo_id, "nome": nome}
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def atualizar_bairro(id_: int, nome: str) -> dict:
    session = SessionLocal()
    try:
        row = session.query(BairroLegado).get(id_)
        if not row:
            return {"ok": False, "error": "bairro nao encontrado"}
        row.nome = to_str(nome)
        session.commit()
        return {"ok": True}
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def excluir_bairro(id_: int) -> dict:
    session = SessionLocal()
    try:
        row = session.query(BairroLegado).get(id_)
        if not row:
            return {"ok": False, "error": "bairro nao encontrado"}
        session.delete(row)
        session.commit()
        return {"ok": True}
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


# =========================
# Venda (cadastro enxuto em contratos)
# =========================
VENDA_CAMPOS_TEXTO = [
    "contrato", "codigo_imovel", "bairro", "tipo", "origem_lead",
    "gerente_venda_nome", "gerente_captacao_nome", "diretor_nome",
    "corretor_venda_1_nome", "corretor_venda_2_nome",
    "corretor_captador_1_nome", "corretor_captador_2_nome",
]
VENDA_CAMPOS_NUM = [
    "valor_negocio", "valor_comissao", "valor_total_61", "percentual_comissao_61",
    "valor_gerente_venda", "valor_gerente_captacao", "valor_diretor",
    "valor_corretor_venda_1", "valor_corretor_venda_2",
    "valor_corretor_captador_1", "valor_corretor_captador_2",
    "percentual_gerente_venda", "percentual_gerente_captacao", "percentual_diretor",
    "percentual_corretor_venda_1", "percentual_corretor_venda_2",
    "percentual_corretor_captacao_1", "percentual_corretor_captacao_2",
]
VENDA_CAMPOS_DATA = ["data_contrato", "data_assinatura"]


def criar_venda(dados: dict, criado_por=None) -> dict:
    id_contrato = to_str(dados.get("id_contrato"))
    if not id_contrato:
        return {"ok": False, "error": "id_contrato obrigatorio"}
    session = SessionLocal()
    try:
        if session.query(Contrato).get(id_contrato):
            return {"ok": False, "error": "id_contrato ja existe"}
        c = Contrato(id_contrato=id_contrato)
        for campo in VENDA_CAMPOS_TEXTO:
            if dados.get(campo) is not None:
                setattr(c, campo, to_str(dados.get(campo)) or None)
        for campo in VENDA_CAMPOS_NUM:
            if dados.get(campo) not in (None, ""):
                setattr(c, campo, to_float(dados.get(campo)))
        for campo in VENDA_CAMPOS_DATA:
            if dados.get(campo):
                setattr(c, campo, parse_date_any(dados.get(campo)))
        session.add(c)
        session.commit()
        return {"ok": True, "id_contrato": id_contrato}
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def listar_vendas(filtros: dict, page=1, per_page=50) -> dict:
    page = max(1, int(page or 1))
    per_page = min(max(1, int(per_page or 50)), 500)
    session = SessionLocal()
    try:
        query = session.query(Contrato)
        codigo = (filtros.get("codigo") or "").strip()
        if codigo:
            query = query.filter(Contrato.codigo_imovel == codigo)
        data_de = parse_date_any(filtros.get("data_de"))
        data_ate = parse_date_any(filtros.get("data_ate"))
        if data_de:
            query = query.filter(Contrato.data_contrato >= data_de)
        if data_ate:
            query = query.filter(Contrato.data_contrato <= data_ate)
        total = query.count()
        rows = query.order_by(Contrato.data_contrato.desc()) \
                    .offset((page - 1) * per_page).limit(per_page).all()
        items = [{
            "id_contrato": r.id_contrato, "contrato": r.contrato,
            "data_contrato": _d(r.data_contrato), "codigo_imovel": r.codigo_imovel,
            "bairro": r.bairro, "tipo": r.tipo, "valor_negocio": _num(r.valor_negocio),
            "valor_comissao": _num(r.valor_comissao),
            "gerente_venda_nome": r.gerente_venda_nome,
            "corretor_venda_1_nome": r.corretor_venda_1_nome,
        } for r in rows]
        return {"ok": True, "total": total, "page": page, "per_page": per_page, "items": items}
    finally:
        session.close()


def listar_destaques(filtros: dict, page=1, per_page=50) -> dict:
    page = max(1, int(page or 1))
    per_page = min(max(1, int(per_page or 50)), 500)
    session = SessionLocal()
    try:
        query = session.query(FatoDestaque)
        codigo = (filtros.get("codigo") or "").strip()
        if codigo:
            query = query.filter(FatoDestaque.codigo_imovel == normalize_codigo(codigo))
        total = query.count()
        rows = query.order_by(FatoDestaque.data_destaque.desc(), FatoDestaque.id.desc()) \
                    .offset((page - 1) * per_page).limit(per_page).all()
        items = [{
            "id": r.id, "codigo_imovel": r.codigo_imovel, "endereco": r.endereco,
            "bairro": r.bairro, "valor": _num(r.valor), "data_destaque": _d(r.data_destaque),
            "captador1": r.captador1, "id_gerente": r.id_gerente,
        } for r in rows]
        return {"ok": True, "total": total, "page": page, "per_page": per_page, "items": items}
    finally:
        session.close()
