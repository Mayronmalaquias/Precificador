# captacao_csv_to_sheets.py
# ============================================================
# Automação 100% em Python -> Google Sheets
# Lendo os imóveis a partir de CSV, e não mais da API
# ============================================================

import os
import re
from datetime import datetime, date
from typing import Dict, List, Any, Optional, Tuple

import pandas as pd
from dateutil.parser import parse as dateparse

from google.oauth2 import service_account
from googleapiclient.discovery import build


# =========================
# CONFIG (EDITE AQUI)
# =========================

# --- Google Sheets ---
CREDENTIALS_JSON = r"../cred.json"
SPREADSHEET_ID = "1HQDdcbUMj276hnIbPs-WwdWHiUPzMhPRWt4HHRyYGnw"

# --- CSV de entrada ---
CSV_PATH = r"./cap-19-06.csv"
CSV_SEP = ";"
CSV_ENCODING = "utf-8-sig"

# --- Filtros opcionais do CSV ---
FILTRAR_FINALIDADE = "Venda"    # ex: "Venda" / "Aluguel" / "" para não filtrar
FILTRAR_DESTINACAO = ""         # ex: "Residencial" / "Comercial" / "" para não filtrar

# --- Como o script vai filtrar os imóveis? ---
CODES_LIST: List[int] = []      # ex: [11854, 11870]
CODES_XLSX_PATH = ""            # ex: "./entrada.xlsx"
CODES_XLSX_SHEET = "Página1"

# --- Se quiser filtrar por data do CSV, descomente ---
# DATE_FROM = "01/03/2026"
# DATE_TO = "06/03/2026"


# =========================
# CONFIG REGRAS FOCO
# =========================
BAIRROS_PP_RAW = {
    "PLANO PILOTO",
    "ASA SUL",
    "ASA NORTE",
    "NOROESTE",
    "SUDOESTE",
    "JARDIM BOTANICO",
    "LAGO NORTE",
    "LAGO SUL",
    "SETOR SUDOESTE",
}

BAIRROS_AC_RAW = {
    "Águas Claras Norte",
    "Águas Claras Sul",
    "Norte (Águas Claras)",
    "Sul (Águas Claras)",
    "Águas Claras",
}

MIN_COMISSAO = 3.5
MIN_VALOR_PP = 1_000_000
MIN_VALOR_AC = 600_000


# =========================
# UTIL
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
    s = re.sub(r"\s+", " ", s)
    return s


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


def to_int(x: Any) -> Optional[int]:
    try:
        if x is None or (isinstance(x, float) and pd.isna(x)):
            return None

        s = str(x).strip().replace("'", "")
        if not s:
            return None

        return int(float(s))
    except Exception:
        return None


def parse_date_any(x: Any) -> Optional[date]:
    if x is None or (isinstance(x, float) and pd.isna(x)):
        return None

    if isinstance(x, date) and not isinstance(x, datetime):
        return x

    if isinstance(x, datetime):
        return x.date()

    s = str(x).strip().replace("'", "")
    if not s:
        return None

    try:
        d = dateparse(s, dayfirst=True, fuzzy=True)
        return d.date()
    except Exception:
        return None


def parse_bool_any(x: Any) -> bool:
    if isinstance(x, bool):
        return x

    if x is None or (isinstance(x, float) and pd.isna(x)):
        return False

    s = str(x).strip().replace("'", "").upper()

    if s in {"TRUE", "VERDADEIRO", "1", "SIM"}:
        return True
    if s in {"FALSE", "FALSO", "0", "NAO", "NÃO", ""}:
        return False

    return False


def unique_keep_order(lst: List[str]) -> List[str]:
    seen = set()
    out = []
    for x in lst:
        x = str(x).strip()
        if x and x.lower() != "nan" and x not in seen:
            seen.add(x)
            out.append(x)
    return out


def split_captadores(raw: Any) -> List[str]:
    """
    Exemplos de conteúdo da coluna Captadores:
    - "Luana Salvinski"
    - "Fernando Borges | Filipe Brandão"
    - "Nome 1; Nome 2"
    """
    if raw is None or (isinstance(raw, float) and pd.isna(raw)):
        return []

    s = str(raw).strip()
    if not s:
        return []

    partes = re.split(r"\s*\|\s*|\s*;\s*|\s*,\s*|/\s*", s)
    partes = [p.strip() for p in partes if p and p.strip()]
    return unique_keep_order(partes)[:3]


def normalize_date_for_sheets(x: Any) -> str:
    d = parse_date_any(x)
    if d:
        return d.strftime("%d/%m/%Y")
    return ""


def cell_to_sheet_value(x: Any):
    if x is None:
        return ""

    if isinstance(x, float) and pd.isna(x):
        return ""

    if isinstance(x, (datetime, date)):
        return x.strftime("%d/%m/%Y")

    if isinstance(x, str):
        # remove apóstrofo inicial que pode contaminar a planilha
        if x.startswith("'"):
            x = x[1:]
        return x

    return x


# =========================
# CSV
# =========================
def load_csv_as_df(csv_path: str) -> pd.DataFrame:
    if not os.path.exists(csv_path):
        raise RuntimeError(f"CSV não encontrado: {csv_path}")

    df = pd.read_csv(
        csv_path,
        sep=CSV_SEP,
        encoding=CSV_ENCODING,
        engine="python"
    )

    df.columns = [str(c).replace("\ufeff", "").strip() for c in df.columns]
    return df


def load_codes_from_xlsx(xlsx_path: str, sheet_name: str) -> List[int]:
    df = pd.read_excel(xlsx_path, sheet_name=sheet_name)

    col = None
    for c in df.columns:
        if norm(c) in {"CODIGO", "CÓDIGO"}:
            col = c
            break

    if col is None:
        raise RuntimeError("No XLSX, a aba indicada precisa ter uma coluna 'Código'.")

    df[col] = pd.to_numeric(df[col], errors="coerce").astype("Int64")
    df = df.dropna(subset=[col])
    return sorted(df[col].astype(int).unique().tolist())


def filter_df_by_config(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()

    if FILTRAR_FINALIDADE and "Finalidade" in out.columns:
        out = out[
            out["Finalidade"].astype(str).str.strip().str.upper() ==
            FILTRAR_FINALIDADE.strip().upper()
        ]

    if FILTRAR_DESTINACAO and "Destinacao" in out.columns:
        out = out[
            out["Destinacao"].astype(str).str.strip().str.upper() ==
            FILTRAR_DESTINACAO.strip().upper()
        ]

    if "DATE_FROM" in globals() and "DATE_TO" in globals():
        d1 = parse_date_any(globals()["DATE_FROM"])
        d2 = parse_date_any(globals()["DATE_TO"])

        if "DataCadastro" in out.columns and d1 and d2:
            out["_data_csv"] = out["DataCadastro"].apply(parse_date_any)
            out = out[(out["_data_csv"] >= d1) & (out["_data_csv"] <= d2)]
            out = out.drop(columns=["_data_csv"], errors="ignore")

    return out


def extract_fields_from_csv_row(row: pd.Series) -> dict:
    codigo = to_int(row.get("Codigo")) or 0
    bairro_nome = row.get("Bairro", "") or ""
    valor = row.get("Valor", 0)
    tipo_nome = row.get("Tipo", "") or ""
    comissao_pct = row.get("ComissaoVenda", 0)

    data_entrada = (
        row.get("DataCadastro")
        or row.get("DataHoraUltimaAlteracao")
        or row.get("DataHoraUltimaSituacao")
        or None
    )

    captadores_raw = row.get("Captadores", "")
    captador_nomes = split_captadores(captadores_raw)

    return {
        "codigo": codigo,
        "bairro_nome": str(bairro_nome),
        "valor": to_float(valor),
        "tipo_nome": str(tipo_nome),
        "comissao_pct": to_float(comissao_pct),
        "data_entrada": parse_date_any(data_entrada),
        "captador_ids": [],
        "captador_nomes": captador_nomes,
    }


def build_imoveis_from_csv(df: pd.DataFrame) -> Dict[int, dict]:
    out: Dict[int, dict] = {}

    for _, row in df.iterrows():
        codigo = to_int(row.get("Codigo"))
        if codigo is None:
            continue
        out[int(codigo)] = row.to_dict()

    return out


# =========================
# REGRAS FOCO
# =========================
def classificar_foco(bairro_nome: str, valor: float, comissao_pct: float, is_residencial: bool) -> Tuple[bool, bool]:
    b = norm(bairro_nome)
    v = float(valor or 0)
    c = float(comissao_pct or 0)

    foco_pp = (b in BAIRROS_PP) and (v >= MIN_VALOR_PP) and (c >= MIN_COMISSAO) and is_residencial
    foco_ac = (b in BAIRROS_AC) and (v >= MIN_VALOR_AC) and (c >= MIN_COMISSAO) and is_residencial

    return foco_pp, foco_ac


# =========================
# GOOGLE SHEETS
# =========================
def sheets_service(credentials_json: str):
    scopes = ["https://www.googleapis.com/auth/spreadsheets"]
    creds = service_account.Credentials.from_service_account_file(credentials_json, scopes=scopes)
    return build("sheets", "v4", credentials=creds)


def read_sheet_as_df(svc, spreadsheet_id: str, sheet_name: str) -> pd.DataFrame:
    rng = f"{sheet_name}!A:Z"
    res = svc.spreadsheets().values().get(
        spreadsheetId=spreadsheet_id,
        range=rng
    ).execute()

    values = res.get("values", [])
    if not values:
        return pd.DataFrame()

    header = values[0]
    rows = values[1:]
    fixed = [r + [""] * (len(header) - len(r)) for r in rows]
    return pd.DataFrame(fixed, columns=header)


def normalize_dim_imovel_types(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()

    if "Código" in df.columns:
        df["Código"] = df["Código"].apply(lambda x: to_int(x) if str(x).strip() != "" else "")

    if "Valor" in df.columns:
        df["Valor"] = df["Valor"].apply(lambda x: to_float(x) if str(x).strip() != "" else "")

    if "Foco PP" in df.columns:
        df["Foco PP"] = df["Foco PP"].apply(parse_bool_any)

    if "Foco AC" in df.columns:
        df["Foco AC"] = df["Foco AC"].apply(parse_bool_any)

    return df


def normalize_fato_captacao_types(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()

    if "Código" in df.columns:
        df["Código"] = df["Código"].apply(lambda x: to_int(x) if str(x).strip() != "" else "")

    if "DataEntrada" in df.columns:
        df["DataEntrada"] = df["DataEntrada"].apply(normalize_date_for_sheets)

    return df


def write_df_over_sheet(svc, spreadsheet_id: str, sheet_name: str, df: pd.DataFrame):
    df = df.copy()

    if sheet_name == "Dim_Imovel":
        df = normalize_dim_imovel_types(df)
    elif sheet_name == "Fato_Captacao":
        df = normalize_fato_captacao_types(df)

    values = [list(df.columns)]
    for _, row in df.iterrows():
        values.append([cell_to_sheet_value(v) for v in row.tolist()])

    svc.spreadsheets().values().update(
        spreadsheetId=spreadsheet_id,
        range=f"{sheet_name}!A1",
        valueInputOption="USER_ENTERED",
        body={"values": values},
    ).execute()


# =========================
# MAPAS DAS DIMENSÕES
# =========================
def load_dim_maps(svc, spreadsheet_id: str):
    df_bairro = read_sheet_as_df(svc, spreadsheet_id, "Dim_Bairro")
    df_tipo = read_sheet_as_df(svc, spreadsheet_id, "Dim_Tipo")
    df_corr = read_sheet_as_df(svc, spreadsheet_id, "Dim_Corretor")
    df_imovel = read_sheet_as_df(svc, spreadsheet_id, "Dim_Imovel")
    df_fato = read_sheet_as_df(svc, spreadsheet_id, "Fato_Captacao")

    bairro_name_to_id: Dict[str, str] = {}
    if not df_bairro.empty and "Nome" in df_bairro.columns and "IdBairro" in df_bairro.columns:
        for _, r in df_bairro.iterrows():
            bairro_name_to_id[norm(r.get("Nome", ""))] = str(r.get("IdBairro", "")).strip()

    tipo_name_to_id: Dict[str, str] = {}
    if not df_tipo.empty and "Nome" in df_tipo.columns and "IdTipo" in df_tipo.columns:
        for _, r in df_tipo.iterrows():
            tipo_name_to_id[norm(r.get("Nome", ""))] = str(r.get("IdTipo", "")).strip()

    nome_to_idcorretor: Dict[str, str] = {}
    corretor_to_gerente: Dict[str, str] = {}

    if not df_corr.empty:
        col_idcor = None
        col_nome = None
        col_ger = None

        for c in df_corr.columns:
            nc = norm(c)
            if nc in {"IDCORRETOR", "ID_CORRETOR"}:
                col_idcor = c
            elif nc in {"NOME", "NOMECORRETOR", "CORRETOR"}:
                col_nome = c
            elif nc in {"IDGERENTE", "ID_GERENTE", "GERENTE"}:
                col_ger = c

        if col_idcor is None and "IdCorretor" in df_corr.columns:
            col_idcor = "IdCorretor"

        if col_nome is None:
            if "Nome" in df_corr.columns:
                col_nome = "Nome"
            elif "Corretor" in df_corr.columns:
                col_nome = "Corretor"

        if col_ger is None:
            if "IdGerente" in df_corr.columns:
                col_ger = "IdGerente"
            elif "Gerente" in df_corr.columns:
                col_ger = "Gerente"

        for _, r in df_corr.iterrows():
            idcor = str(r.get(col_idcor, "")).strip() if col_idcor else ""
            nome = str(r.get(col_nome, "")).strip() if col_nome else ""
            ger = str(r.get(col_ger, "")).strip() if col_ger else ""

            if idcor and nome and nome.lower() != "nan":
                nome_to_idcorretor[norm(nome)] = idcor

            if idcor and ger and ger.lower() != "nan":
                corretor_to_gerente[idcor] = ger

    return {
        "df_bairro": df_bairro,
        "df_tipo": df_tipo,
        "df_imovel": df_imovel,
        "df_fato": df_fato,
        "bairro_name_to_id": bairro_name_to_id,
        "tipo_name_to_id": tipo_name_to_id,
        "nome_to_idcorretor": nome_to_idcorretor,
        "corretor_to_gerente": corretor_to_gerente,
    }


def next_dim_id(existing_ids: List[str], prefix: str) -> str:
    nums = []

    for x in existing_ids:
        if isinstance(x, str) and x.startswith(prefix):
            try:
                nums.append(int(x[len(prefix):]))
            except Exception:
                pass

    n = max(nums) + 1 if nums else 1
    return f"{prefix}{n}"


def ensure_bairro(dim: dict, bairro_nome: str) -> Tuple[str, bool]:
    key = norm(bairro_nome)
    if not key:
        return "", False

    if key in dim["bairro_name_to_id"]:
        return dim["bairro_name_to_id"][key], False

    df_bairro = dim["df_bairro"]
    if df_bairro.empty:
        df_bairro = pd.DataFrame(columns=["IdBairro", "Nome"])

    if "IdBairro" not in df_bairro.columns:
        df_bairro["IdBairro"] = ""

    if "Nome" not in df_bairro.columns:
        df_bairro["Nome"] = ""

    existing = df_bairro["IdBairro"].astype(str).tolist()
    new_id = next_dim_id(existing, "B")

    new_row = pd.DataFrame([{"IdBairro": new_id, "Nome": bairro_nome}])
    dim["df_bairro"] = pd.concat([df_bairro, new_row], ignore_index=True)
    dim["bairro_name_to_id"][key] = new_id

    return new_id, True


def map_tipo(dim: dict, tipo_nome: str) -> str:
    key = norm(tipo_nome)
    if not key:
        return ""
    return dim["tipo_name_to_id"].get(key, "")


def is_residencial_from_tipo_id(tipo_id: str) -> bool:
    non_res = {"T7", "T8", "T9", "T10", "T11"}
    return str(tipo_id).strip().upper() not in non_res if tipo_id else True


# =========================
# UPSERT / APPEND
# =========================
def upsert_dim_imovel(
    dim: dict,
    codigo: int,
    tipo_id: str,
    valor: float,
    bairro_id: str,
    foco_pp: bool,
    foco_ac: bool
):
    df = dim["df_imovel"]

    if df.empty:
        df = pd.DataFrame(columns=["Código", "Tipo", "Valor", "Bairro", "Foco PP", "Foco AC"])

    for col in ["Código", "Tipo", "Valor", "Bairro", "Foco PP", "Foco AC"]:
        if col not in df.columns:
            df[col] = ""

    df["Código_num"] = pd.to_numeric(df["Código"], errors="coerce")
    mask = (df["Código_num"] == codigo)

    if mask.any():
        idx = df.index[mask][0]
        df.at[idx, "Tipo"] = tipo_id
        df.at[idx, "Valor"] = float(valor)
        df.at[idx, "Bairro"] = bairro_id
        df.at[idx, "Foco PP"] = bool(foco_pp)
        df.at[idx, "Foco AC"] = bool(foco_ac)
    else:
        df = pd.concat(
            [
                df,
                pd.DataFrame([{
                    "Código": int(codigo),
                    "Tipo": tipo_id,
                    "Valor": float(valor),
                    "Bairro": bairro_id,
                    "Foco PP": bool(foco_pp),
                    "Foco AC": bool(foco_ac),
                }])
            ],
            ignore_index=True
        )

    df = df.drop(columns=["Código_num"], errors="ignore")
    dim["df_imovel"] = df


def append_fato_captacao(dim: dict, codigo: int, captadores: List[str], gerente: str, data_entrada: date):
    df = dim["df_fato"]

    if df.empty:
        df = pd.DataFrame(columns=["Código", "Captador1", "Captador2", "Captador3", "Gerente", "DataEntrada"])

    for col in ["Código", "Captador1", "Captador2", "Captador3", "Gerente", "DataEntrada"]:
        if col not in df.columns:
            df[col] = ""

    capt1 = captadores[0] if len(captadores) > 0 else ""
    capt2 = captadores[1] if len(captadores) > 1 else ""
    capt3 = captadores[2] if len(captadores) > 2 else ""

    df_tmp = df.copy()
    df_tmp["Código_num"] = pd.to_numeric(df_tmp["Código"], errors="coerce")
    df_tmp["DataEntrada_date"] = df_tmp["DataEntrada"].apply(parse_date_any)
    df_tmp["Captador1_str"] = df_tmp["Captador1"].astype(str)

    if ((df_tmp["Código_num"] == codigo) &
        (df_tmp["DataEntrada_date"] == data_entrada) &
        (df_tmp["Captador1_str"] == str(capt1))).any():
        dim["df_fato"] = df
        return

    df = pd.concat(
        [
            df,
            pd.DataFrame([{
                "Código": int(codigo),
                "Captador1": capt1,
                "Captador2": capt2,
                "Captador3": capt3,
                "Gerente": gerente,
                "DataEntrada": data_entrada,   # agora fica como data, não string
            }])
        ],
        ignore_index=True
    )

    dim["df_fato"] = df


# =========================
# MAIN
# =========================
def main():
    if not CREDENTIALS_JSON or not os.path.exists(CREDENTIALS_JSON):
        raise RuntimeError(f"Credenciais do Google não encontradas: {CREDENTIALS_JSON}")

    if not SPREADSHEET_ID or "COLE_AQUI" in SPREADSHEET_ID:
        raise RuntimeError("Defina SPREADSHEET_ID na seção CONFIG.")

    svc = sheets_service(CREDENTIALS_JSON)
    dim = load_dim_maps(svc, SPREADSHEET_ID)

    # 1) Ler CSV
    df_csv = load_csv_as_df(CSV_PATH)
    df_csv = filter_df_by_config(df_csv)

    if df_csv.empty:
        print("CSV vazio após os filtros. Encerrando.")
        return

    # 2) Se houver lista de códigos/XLSX, filtra o CSV por eles
    codes: List[int] = []

    if CODES_XLSX_PATH:
        if not os.path.exists(CODES_XLSX_PATH):
            raise RuntimeError(f"XLSX não encontrado: {CODES_XLSX_PATH}")
        codes = load_codes_from_xlsx(CODES_XLSX_PATH, CODES_XLSX_SHEET)
    elif CODES_LIST:
        codes = sorted(set([int(x) for x in CODES_LIST]))

    if codes:
        df_csv["Codigo_num"] = pd.to_numeric(df_csv["Codigo"], errors="coerce")
        df_csv_filtrado = df_csv[df_csv["Codigo_num"].isin(codes)].copy()

        returned_set = set(df_csv_filtrado["Codigo_num"].dropna().astype(int).tolist())
        codes_set = set(codes)
        missing = sorted(codes_set - returned_set)
        returned_sorted = sorted(returned_set)

        print(f"Total lista/planilha: {len(codes)} | Encontrados no CSV: {len(returned_set)} | Faltantes: {len(missing)}")

        pd.DataFrame({"codigo_encontrado_csv": returned_sorted}).to_csv(
            "codigos_encontrados_csv.csv",
            index=False,
            encoding="utf-8-sig"
        )
        pd.DataFrame({"codigo_faltante_csv": missing}).to_csv(
            "codigos_faltantes_csv.csv",
            index=False,
            encoding="utf-8-sig"
        )

        df_csv = df_csv_filtrado.drop(columns=["Codigo_num"], errors="ignore")

    # 3) Montar estrutura semelhante ao retorno anterior
    imoveis = build_imoveis_from_csv(df_csv)

    if not imoveis:
        print("Nenhum imóvel válido encontrado no CSV.")
        return

    # 4) Processar e atualizar Sheets
    novos_bairros_criados = False

    for codigo, item in imoveis.items():
        data = extract_fields_from_csv_row(pd.Series(item))

        codigo = int(data["codigo"])
        bairro_nome = data["bairro_nome"]
        valor = float(data["valor"])
        tipo_nome = data["tipo_nome"]
        comissao = float(data["comissao_pct"])

        captadores_csv_nomes = data["captador_nomes"]

        captadores: List[str] = []
        for nome in captadores_csv_nomes:
            mapped = dim["nome_to_idcorretor"].get(norm(nome), "")
            captadores.append(mapped if mapped else nome)

        captadores = [str(x).strip() for x in captadores if str(x).strip()][:3]
        data_entrada = data["data_entrada"] or date.today()

        bairro_id, created = ensure_bairro(dim, bairro_nome)
        if created:
            novos_bairros_criados = True

        tipo_id = map_tipo(dim, tipo_nome) or ""
        residencial = is_residencial_from_tipo_id(tipo_id)

        foco_pp, foco_ac = classificar_foco(bairro_nome, valor, comissao, residencial)

        capt1 = captadores[0] if captadores else ""
        gerente = dim["corretor_to_gerente"].get(str(capt1), "")

        upsert_dim_imovel(dim, codigo, tipo_id, valor, bairro_id, foco_pp, foco_ac)
        append_fato_captacao(dim, codigo, captadores, gerente, data_entrada)

        print(
            f"[OK] {codigo} | {bairro_nome} | valor={valor:.0f} | com={comissao} | "
            f"capt(csv_nomes)={captadores_csv_nomes} -> capt(final)={captadores} | "
            f"ger={gerente} | PP={foco_pp} AC={foco_ac}"
        )

    # 5) Persistir no Google Sheets
    if novos_bairros_criados:
        write_df_over_sheet(svc, SPREADSHEET_ID, "Dim_Bairro", dim["df_bairro"])

    write_df_over_sheet(svc, SPREADSHEET_ID, "Dim_Imovel", dim["df_imovel"])
    write_df_over_sheet(svc, SPREADSHEET_ID, "Fato_Captacao", dim["df_fato"])

    print("\nFinalizado: Dim_Imovel e Fato_Captacao atualizados no Google Sheet.")


if __name__ == "__main__":
    main()