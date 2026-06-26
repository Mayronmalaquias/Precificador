import os
import re
from datetime import datetime, date
from typing import Dict, List, Tuple, Optional, Any

import pandas as pd
from google.oauth2 import service_account
from googleapiclient.discovery import build


# =========================
# CONFIG
# =========================
CREDENTIALS_JSON = r"../cred.json"
SPREADSHEET_ID = "1HQDdcbUMj276hnIbPs-WwdWHiUPzMhPRWt4HHRyYGnw"

INPUT_CSV_PATH = "./saida-19-06.csv"
CSV_SEP = ";"
CSV_ENCODING = "utf-8-sig"

SHEET_SAIDA_NAME = "Fato_Saida"
SHEET_CAPTACAO_NAME = "Fato_Captacao"

DEFAULT_MOTIVO = ""   # se não vier motivo no CSV, usa isso
USAR_SITUACAO_COMO_MOTIVO_SE_VAZIO = True

# filtros opcionais
FILTRAR_FINALIDADE = "Venda"      # ex: "Venda", "Aluguel" ou "" para não filtrar
FILTRAR_DESTINACAO = ""           # ex: "Residencial", "Comercial" ou "" para não filtrar

# se quiser limitar a uma lista específica de códigos
CODES_LIST: List[int] = []

# se quiser filtrar por data de saída
# DATE_FROM = "01/03/2026"
# DATE_TO = "06/03/2026"


# =========================
# Utils
# =========================
def build_sheets_service(credentials_json: str):
    scopes = ["https://www.googleapis.com/auth/spreadsheets"]
    creds = service_account.Credentials.from_service_account_file(
        credentials_json,
        scopes=scopes
    )
    return build("sheets", "v4", credentials=creds, cache_discovery=False)


def norm_text(x: Any) -> str:
    if x is None or (isinstance(x, float) and pd.isna(x)):
        return ""
    s = str(x).strip().upper()
    s = (
        s.replace("Á", "A").replace("À", "A").replace("Ã", "A").replace("Â", "A")
         .replace("É", "E").replace("Ê", "E")
         .replace("Í", "I")
         .replace("Ó", "O").replace("Õ", "O").replace("Ô", "O")
         .replace("Ú", "U")
         .replace("Ç", "C")
    )
    s = re.sub(r"\s+", " ", s)
    return s


def normalize_codigo(x) -> Optional[str]:
    if x is None or (isinstance(x, float) and pd.isna(x)):
        return None

    s = str(x).strip().replace("'", "")
    if not s:
        return None

    if re.fullmatch(r"\d+(\.0+)?", s):
        s = str(int(float(s)))

    return s


def parse_date_any(x) -> Optional[date]:
    if x is None or (isinstance(x, float) and pd.isna(x)) or pd.isna(x):
        return None

    if isinstance(x, date) and not isinstance(x, datetime):
        return x

    if isinstance(x, datetime):
        return x.date()

    s = str(x).strip().replace("'", "")
    if not s:
        return None

    for fmt in (
        "%Y-%m-%d",
        "%d/%m/%Y",
        "%d-%m-%Y",
        "%Y/%m/%d",
        "%d/%m/%Y %H:%M",
        "%d/%m/%Y %H:%M:%S",
        "%Y-%m-%d %H:%M:%S",
    ):
        try:
            return datetime.strptime(s, fmt).date()
        except ValueError:
            pass

    try:
        dt = pd.to_datetime(s, dayfirst=True, errors="coerce")
        if pd.isna(dt):
            return None
        return dt.date()
    except Exception:
        return None


def date_to_sheet_str(x) -> str:
    d = parse_date_any(x)
    if d:
        return d.strftime("%d/%m/%Y")
    return date.today().strftime("%d/%m/%Y")


def sheet_get_values(service, spreadsheet_id: str, range_a1: str) -> List[List[str]]:
    resp = service.spreadsheets().values().get(
        spreadsheetId=spreadsheet_id,
        range=range_a1
    ).execute()
    return resp.get("values", [])


def sheet_append_rows(service, spreadsheet_id: str, sheet_name: str, rows: List[List[str]]):
    if not rows:
        return

    body = {"values": rows}
    service.spreadsheets().values().append(
        spreadsheetId=spreadsheet_id,
        range=f"{sheet_name}!A1",
        valueInputOption="USER_ENTERED",
        insertDataOption="INSERT_ROWS",
        body=body
    ).execute()


def read_input_csv(path: str) -> pd.DataFrame:
    if not os.path.exists(path):
        raise RuntimeError(f"CSV não encontrado: {path}")

    df = pd.read_csv(
        path,
        sep=CSV_SEP,
        encoding=CSV_ENCODING,
        engine="python"
    )

    df.columns = [str(c).replace("\ufeff", "").strip() for c in df.columns]

    if not isinstance(df, pd.DataFrame):
        raise RuntimeError(f"Falha ao ler CSV: retorno inesperado ({type(df)}).")

    return df


def get_col(df: pd.DataFrame, accepted_names: List[str]) -> Optional[str]:
    accepted = {norm_text(x) for x in accepted_names}
    for c in df.columns:
        if norm_text(c) in accepted:
            return c
    return None


def situacao_eh_vago_disponivel(situacao: Any) -> bool:
    s = norm_text(situacao)

    # o principal caso do seu CSV é "Vago/Disponível"
    if s in {
        "VAGO/DISPONIVEL",
        "VAGO / DISPONIVEL",
        "VAGO",
        "DISPONIVEL",
    }:
        return True

    return False


def filtrar_saidas_csv(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()

    col_codigo = get_col(out, ["Código", "Codigo", "Code"])
    if col_codigo is None:
        raise RuntimeError("Não encontrei coluna de código no CSV.")

    col_situacao = get_col(out, ["Situacao", "Situação"])
    if col_situacao is None:
        raise RuntimeError("Não encontrei a coluna 'Situacao' no CSV.")

    col_finalidade = get_col(out, ["Finalidade"])
    col_destinacao = get_col(out, ["Destinacao", "Destinação"])

    out["__codigo"] = out[col_codigo].apply(normalize_codigo)
    out = out[out["__codigo"].notna()].copy()

    if FILTRAR_FINALIDADE and col_finalidade:
        out = out[
            out[col_finalidade].astype(str).str.strip().str.upper()
            == FILTRAR_FINALIDADE.strip().upper()
        ]

    if FILTRAR_DESTINACAO and col_destinacao:
        out = out[
            out[col_destinacao].astype(str).str.strip().str.upper()
            == FILTRAR_DESTINACAO.strip().upper()
        ]

    # regra principal: tudo que NÃO for vago/disponível é saída
    out = out[~out[col_situacao].apply(situacao_eh_vago_disponivel)].copy()

    if CODES_LIST:
        codes_norm = {str(int(x)) for x in CODES_LIST}
        out = out[out["__codigo"].isin(codes_norm)].copy()

    # filtro opcional por data
    col_data_situacao = get_col(out, ["DataHoraUltimaSituacao", "DataUltimaSituacao", "DataSaida", "Data"])
    if "DATE_FROM" in globals() and "DATE_TO" in globals() and col_data_situacao:
        d1 = parse_date_any(globals()["DATE_FROM"])
        d2 = parse_date_any(globals()["DATE_TO"])
        if d1 and d2:
            out["__data_saida_dt"] = out[col_data_situacao].apply(parse_date_any)
            out = out[
                out["__data_saida_dt"].notna() &
                (out["__data_saida_dt"] >= d1) &
                (out["__data_saida_dt"] <= d2)
            ].copy()

    return out


# =========================
# Main
# =========================
def main():
    service = build_sheets_service(CREDENTIALS_JSON)

    # 1) Ler CSV e filtrar as saídas
    df_in = read_input_csv(INPUT_CSV_PATH)
    df_in = filtrar_saidas_csv(df_in)

    if df_in.empty:
        print("Nenhuma saída encontrada no CSV após aplicar os filtros.")
        return

    col_codigo = get_col(df_in, ["Código", "Codigo", "Code"])
    col_data = get_col(df_in, ["DataHoraUltimaSituacao", "DataUltimaSituacao", "DataSaida", "Data"])
    col_motivo = get_col(df_in, ["MotivoDesativacao", "Motivo", "MotivoSaida"])
    col_situacao = get_col(df_in, ["Situacao", "Situação"])

    # 2) Ler Fato_Captacao do Google Sheets para resolver Captadores/Gerente
    cap_values = sheet_get_values(service, SPREADSHEET_ID, f"{SHEET_CAPTACAO_NAME}!A:Z")
    if not cap_values:
        raise RuntimeError(f"Aba {SHEET_CAPTACAO_NAME} está vazia ou não encontrada.")

    cap_header = cap_values[0]
    cap_rows = cap_values[1:]

    def idx_cap(colname: str) -> int:
        try:
            return cap_header.index(colname)
        except ValueError:
            return -1

    i_cod = idx_cap("Código")
    i_c1 = idx_cap("Captador1")
    i_c2 = idx_cap("Captador2")
    i_c3 = idx_cap("Captador3")
    i_g = idx_cap("Gerente")
    i_dt = idx_cap("DataEntrada")

    if i_cod == -1:
        raise RuntimeError("Não encontrei a coluna 'Código' na aba Fato_Captacao.")

    # mapa do registro mais recente da captação por código
    cap_map: Dict[str, Tuple[str, str, str, str, str]] = {}
    cap_map_dt: Dict[str, datetime] = {}

    for r in cap_rows:
        if i_cod >= len(r):
            continue

        cod = normalize_codigo(r[i_cod])
        if not cod:
            continue

        c1 = r[i_c1] if (i_c1 != -1 and i_c1 < len(r)) else ""
        c2 = r[i_c2] if (i_c2 != -1 and i_c2 < len(r)) else ""
        c3 = r[i_c3] if (i_c3 != -1 and i_c3 < len(r)) else ""
        ge = r[i_g] if (i_g != -1 and i_g < len(r)) else ""

        dt_raw = r[i_dt] if (i_dt != -1 and i_dt < len(r)) else ""
        dt_parsed_date = parse_date_any(dt_raw)
        dt_key = datetime.combine(dt_parsed_date, datetime.min.time()) if dt_parsed_date else datetime.min

        if cod not in cap_map or dt_key >= cap_map_dt[cod]:
            cap_map[cod] = (c1, c2, c3, ge, str(dt_raw))
            cap_map_dt[cod] = dt_key

    # 3) Ler Fato_Saida para evitar duplicar (Código + DataSaida)
    saida_values = sheet_get_values(service, SPREADSHEET_ID, f"{SHEET_SAIDA_NAME}!A:Z")

    existing = set()
    if saida_values:
        saida_header = saida_values[0]
        saida_rows = saida_values[1:]

        try:
            s_cod = saida_header.index("Código")
        except ValueError:
            s_cod = 0

        try:
            s_dt = saida_header.index("DataSaida")
        except ValueError:
            s_dt = 6

        for r in saida_rows:
            cod = normalize_codigo(r[s_cod]) if s_cod < len(r) else None
            dts = date_to_sheet_str(r[s_dt]) if s_dt < len(r) else ""
            if cod:
                existing.add((cod, dts))

    # 4) Montar linhas a inserir
    # ordem: Código | Captador1 | Captador2 | Captador3 | Gerente | Motivo | DataSaida
    rows_to_append: List[List[str]] = []

    for _, row in df_in.iterrows():
        cod = row["__codigo"]

        data_saida = date_to_sheet_str(row[col_data]) if col_data else date.today().strftime("%d/%m/%Y")

        motivo = ""
        if col_motivo and not pd.isna(row[col_motivo]):
            motivo = str(row[col_motivo]).strip()

        if not motivo:
            if USAR_SITUACAO_COMO_MOTIVO_SE_VAZIO and col_situacao:
                motivo = str(row[col_situacao]).strip()
            else:
                motivo = DEFAULT_MOTIVO

        # evita duplicar
        if (cod, data_saida) in existing:
            continue

        c1 = c2 = c3 = ge = ""
        if cod in cap_map:
            c1, c2, c3, ge, _ = cap_map[cod]

        rows_to_append.append([cod, c1, c2, c3, ge, motivo, data_saida])

    if not rows_to_append:
        print("Nada para inserir em Fato_Saida (talvez já exista tudo).")
        return

    # 5) Append
    sheet_append_rows(service, SPREADSHEET_ID, SHEET_SAIDA_NAME, rows_to_append)
    print(f"Inseridos {len(rows_to_append)} registros em {SHEET_SAIDA_NAME}.")


if __name__ == "__main__":
    main()