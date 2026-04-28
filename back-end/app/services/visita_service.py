# app/services/visita_service.py
# OAuth (usuário real) para gravar no "Meu Drive" + gravar no Google Sheets
#
# 1) Crie credenciais OAuth (Desktop app) no Google Cloud Console e baixe o JSON.
# 2) Salve como: ./app/utils/asserts/oauth.json
# 3) Rode UMA VEZ localmente:
#    python -c "from app.services.visita_service import ensure_oauth_token; ensure_oauth_token(force=True)"
#    -> vai abrir o navegador para autorizar e gerar ./app/utils/asserts/token.json
# 4) Em produção: leve o token.json junto.
#
# Requisitos:
#   pip install google-api-python-client google-auth google-auth-oauthlib google-auth-httplib2

from __future__ import annotations

import io
import os
import uuid
import re
import datetime as dt
import mimetypes
from typing import Any, Dict, List

from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload

from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.exceptions import RefreshError


# =========================
# CONFIG
# =========================
# Use o mesmo ID lido pelo Apps Script
SPREADSHEET_ID = "1we1qAVRBqAWaXmOfnLnFJzCi8WPt-ZEhxKb0Ab9DiQU"

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # app/
OAUTH_CLIENT_FILE = os.path.join(BASE_DIR, "utils", "asserts", "oauth.json")
TOKEN_FILE = os.path.join(BASE_DIR, "utils", "asserts", "token.json")

# Onde salvar PDFs/anexos no Drive
DRIVE_PARENT_FOLDER_NAME = "61_Visitas"
DRIVE_SUBFOLDER_NAME = "Fato_Visitas_PDF"
DRIVE_VISITA_REPORTS_SUBFOLDER_NAME="Relatorios_Visita_Gerados"

SCOPES = [
    "https://www.googleapis.com/auth/drive.file",
    "https://www.googleapis.com/auth/spreadsheets",
]



# =========================
# Utils
# =========================
def _safe_str(v: Any) -> str:
    return "" if v is None else str(v).strip()
def _to_ddmmyyyy(date_str: str) -> str:
    if not date_str:
        return dt.date.today().strftime("%d/%m/%Y")
    try:
        return dt.datetime.strptime(date_str, "%Y-%m-%d").strftime("%d/%m/%Y")
    except Exception:
        return date_str


def _now_ddmmyyyy_hhmmss() -> str:
    return dt.datetime.now().strftime("%d/%m/%Y %H:%M:%S")


def _is_true(value: Any) -> bool:
    if value is None:
        return False
    s = str(value).strip().upper()
    return s in {"SIM", "TRUE", "1", "YES", "Y"}


def _sanitize_filename(s: str) -> str:
    s = (s or "").strip()
    s = re.sub(r"[^\w\-\. ]+", "", s, flags=re.UNICODE)
    s = s.replace(" ", "_")
    return s[:120] if len(s) > 120 else s


def _norm_key(s: str) -> str:
    return re.sub(r"\s+", " ", (s or "").strip().lower())


def _norm_phone(s: str) -> str:
    digits = re.sub(r"\D+", "", s or "")
    if len(digits) > 11:
        digits = digits[-11:]
    return digits


def _parse_ddmmyyyy_safe(s: str) -> dt.date:
    try:
        return dt.datetime.strptime((s or "").strip(), "%d/%m/%Y").date()
    except Exception:
        return dt.date.min


# =========================
# OAuth
# =========================
def _get_oauth_creds() -> Credentials | None:
    """
    Carrega token.json.
    Se expirado, tenta refresh.
    Se o refresh falhar, força o usuário a regenerar o token.
    """
    creds = None

    if os.path.exists(TOKEN_FILE):
        try:
            creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)
        except Exception as e:
            raise RuntimeError(
                f"Não foi possível ler o token OAuth em {TOKEN_FILE}. "
                f"Apague o arquivo e gere outro. Detalhe: {e}"
            ) from e

    if not creds:
        return None

    if creds.valid:
        return creds

    if creds.expired and creds.refresh_token:
        try:
            creds.refresh(Request())
            with open(TOKEN_FILE, "w", encoding="utf-8") as f:
                f.write(creds.to_json())
            return creds
        except RefreshError as e:
            raise RuntimeError(
                "O token OAuth expirou, foi revogado ou ficou inválido. "
                f"Apague o arquivo '{TOKEN_FILE}' e rode novamente:\n"
                'python -c "from app.services.visita_service import ensure_oauth_token; ensure_oauth_token(force=True)"'
            ) from e

    return None


def ensure_oauth_token(force: bool = False) -> None:
    """
    Gera um novo token.json.
    Use force=True para apagar o token anterior e autorizar novamente.
    """
    if force and os.path.exists(TOKEN_FILE):
        os.remove(TOKEN_FILE)

    if os.path.exists(TOKEN_FILE) and not force:
        return

    if not os.path.exists(OAUTH_CLIENT_FILE):
        raise FileNotFoundError(f"OAuth client não encontrado: {OAUTH_CLIENT_FILE}")

    flow = InstalledAppFlow.from_client_secrets_file(OAUTH_CLIENT_FILE, SCOPES)
    creds = flow.run_local_server(port=0, prompt="consent")

    os.makedirs(os.path.dirname(TOKEN_FILE), exist_ok=True)
    with open(TOKEN_FILE, "w", encoding="utf-8") as f:
        f.write(creds.to_json())


def _get_services():
    """
    Cria novas instâncias dos serviços Sheets e Drive a cada chamada.
    Evita reutilização de conexão HTTP entre requests do Flask.
    """
    creds = _get_oauth_creds()
    if not creds:
        raise RuntimeError(
            "token.json não encontrado ou inválido. "
            "Rode ensure_oauth_token(force=True) para autorizar novamente."
        )

    sheets_service = build("sheets", "v4", credentials=creds, cache_discovery=False)
    drive_service = build("drive", "v3", credentials=creds, cache_discovery=False)

    sheets = sheets_service.spreadsheets()
    drive_files = drive_service.files()

    return sheets, drive_files, drive_service


# =========================
# Drive helpers
# =========================
def _find_or_create_folder(folder_name: str, parent_id: str | None = None) -> str:
    """
    Procura uma pasta por nome (no parent, se informado). Se não achar, cria.
    Retorna folderId.
    """
    _, drive_files, _ = _get_services()

    safe_folder_name = folder_name.replace("'", "\\'")
    q_parts = [
        "mimeType='application/vnd.google-apps.folder'",
        f"name='{safe_folder_name}'",
        "trashed=false",
    ]
    if parent_id:
        q_parts.append(f"'{parent_id}' in parents")

    q = " and ".join(q_parts)

    res = drive_files.list(
        q=q,
        spaces="drive",
        fields="files(id,name)",
        pageSize=10,
    ).execute()

    files = res.get("files", [])
    if files:
        return files[0]["id"]

    body = {
        "name": folder_name,
        "mimeType": "application/vnd.google-apps.folder",
    }
    if parent_id:
        body["parents"] = [parent_id]

    created = drive_files.create(body=body, fields="id").execute()
    return created["id"]


def upload_pdf_to_drive(file_storage, id_corretor: str, imovel_id: str, data_visita: str) -> Dict[str, str]:
    if not file_storage:
        return {"drivePath": "", "driveLink": ""}

    _, drive_files, _ = _get_services()

    filename_original = (file_storage.filename or "").lower()
    ext = os.path.splitext(filename_original)[1]
    mime = mimetypes.guess_type(filename_original)[0] or "application/octet-stream"

    safe_id = _sanitize_filename(id_corretor)
    safe_imovel = _sanitize_filename(imovel_id)
    safe_data = _sanitize_filename(data_visita)

    base = "_".join([p for p in [safe_id, safe_imovel, safe_data, "anexo"] if p])
    filename = f"{base}{ext}"

    root_folder_id = _find_or_create_folder(DRIVE_PARENT_FOLDER_NAME, parent_id=None)
    sub_folder_id = _find_or_create_folder(DRIVE_SUBFOLDER_NAME, parent_id=root_folder_id)

    try:
        file_storage.stream.seek(0)
    except Exception:
        pass

    media = MediaIoBaseUpload(
        file_storage.stream,
        mimetype=mime,
        resumable=True,
    )

    metadata = {"name": filename, "parents": [sub_folder_id]}

    created = drive_files.create(
        body=metadata,
        media_body=media,
        fields="id,name,webViewLink",
    ).execute()

    drive_path = f"{DRIVE_SUBFOLDER_NAME}/{created['name']}"
    drive_link = created.get("webViewLink", "") or ""

    return {"drivePath": drive_path, "driveLink": drive_link}


# =========================
# Sheets helpers
# =========================
def _get_column_values(sheet_name: str, col_letter: str, start_row: int = 2) -> List[str]:
    sheets, _, _ = _get_services()
    res = sheets.values().get(
        spreadsheetId=SPREADSHEET_ID,
        range=f"{sheet_name}!{col_letter}{start_row}:{col_letter}",
    ).execute()
    return [r[0] for r in res.get("values", []) if r and r[0] is not None]


def _append_row(sheet_name: str, values: List[Any]) -> None:
    sheets, _, _ = _get_services()
    sheets.values().append(
        spreadsheetId=SPREADSHEET_ID,
        range=f"{sheet_name}!A:Z",
        valueInputOption="USER_ENTERED",
        insertDataOption="INSERT_ROWS",
        body={"values": [values]},
    ).execute()


def _find_id_by_name_in_dim(dim_sheet: str, id_col_letter: str, name_col_letter: str, name: str) -> str:
    """
    Procura (case-insensitive) pelo nome na coluna de nome e retorna o ID da coluna de ID.
    Ex: Dim_Parceiro_Visita: ID=A, Nome=B
    """
    if not name:
        return ""

    names = _get_column_values(dim_sheet, name_col_letter, start_row=2)
    key = _norm_key(name)

    for i, n in enumerate(names):
        if _norm_key(str(n)) == key:
            row_number = 2 + i
            sheets, _, _ = _get_services()
            got = sheets.values().get(
                spreadsheetId=SPREADSHEET_ID,
                range=f"{dim_sheet}!{id_col_letter}{row_number}:{id_col_letter}{row_number}",
            ).execute().get("values", [])
            return (got[0][0] if got and got[0] else "") or ""

    return ""


def ensure_parceiro_id(nome_parceiro: str, imobiliaria: str, id_corretor: str) -> str:
    """
    Dim_Parceiro_Visita
      A Id_Parceiro
      B Nome_Parceiro
      C Imobiliaria
      D Id_Corretor
    """
    nome_parceiro = (nome_parceiro or "").strip()
    imobiliaria = (imobiliaria or "").strip()

    if not nome_parceiro:
        return ""

    found = _find_id_by_name_in_dim("Dim_Parceiro_Visita", "A", "B", nome_parceiro)
    if found:
        return found

    new_id = f"P{uuid.uuid4().hex[:7].upper()}"
    _append_row("Dim_Parceiro_Visita", [new_id, nome_parceiro, imobiliaria, id_corretor or ""])
    return new_id


def ensure_cliente_id(nome_cliente: str, telefone: str, email: str, created_by: str, id_corretor: str) -> str:
    """
    Dim_Cliente_Visita
      A Id_Cliente
      B Nome_Cliente
      C Telefone_Cliente
      D Email_Cliente
      E CreatedBy
      F Id_Corretor
    """
    nome_cliente = (nome_cliente or "").strip()
    telefone = (telefone or "").strip()
    email = (email or "").strip()

    if not nome_cliente:
        return ""

    found = _find_id_by_name_in_dim("Dim_Cliente_Visita", "A", "B", nome_cliente)
    if found:
        return found

    new_id = f"CL{uuid.uuid4().hex[:6].upper()}"
    _append_row("Dim_Cliente_Visita", [new_id, nome_cliente, telefone, email, created_by or "", id_corretor or ""])
    return new_id


# =========================
# Main: registrar_visita
# =========================
def registrar_visita(payload: Dict[str, Any]) -> str:
    """
    Grava em:
    - Fato_Visitas (A:R)
    - Fato_Avaliacao (A:N)
    - Fato_Cliente_Visita (A:D)
    - Fato_Parceiro_Visita (A:C)
    """
    sheets, _, _ = _get_services()

    id_visita = uuid.uuid4().hex[:8]
    id_avaliacao = uuid.uuid4().hex[:8]
    id_cliente_visita = uuid.uuid4().hex[:8]
    id_parceiro_visita = uuid.uuid4().hex[:8]

    data_visita = _to_ddmmyyyy(payload.get("dataVisita"))
    imovel_id = (payload.get("imovelId") or "").strip()
    id_corretor = (payload.get("idCorretor") or payload.get("corretorId") or "").strip()

    parceiro_externo = payload.get("parceiroExterno", "NAO")
    situacao_imovel = payload.get("situacaoImovel", "CAPTACAO_PROPRIA")
    proposta = payload.get("proposta", "")
    papel_visita = payload.get("papelVisita", "")

    aval = payload.get("avaliacoes", {}) or {}
    preco_nota10 = payload.get("precoNota10") or ""

    created_at = _now_ddmmyyyy_hhmmss()
    created_by = payload.get("corretorEmail") or ""

    visita_com_parceiro = "TRUE" if _is_true(parceiro_externo) else "FALSE"

    tipo_captacao = ""
    imovel_nao_captado = ""
    if situacao_imovel == "CAPTACAO_PROPRIA":
        tipo_captacao = "Captação Própria"
    elif situacao_imovel == "CAPTACAO_PARCEIRO":
        tipo_captacao = "Captação Parceiro"
    elif situacao_imovel == "IMOVEL_NAO_CAPTADO":
        imovel_nao_captado = "TRUE"

    anexo_ficha = payload.get("anexoFichaVisita", "")
    audio_desc = payload.get("audioDescricaoClienteVisita", "")
    link_audio = payload.get("linkAudio", "")
    link_imagem = payload.get("linkImagem", "")
    endereco_externo = payload.get("enderecoExterno", "")
    assinatura = payload.get("assinatura", "")

    parceiro_nome = (payload.get("parceiroNome") or "").strip()
    parceiro_imobiliaria = (payload.get("parceiroImobiliaria") or "").strip()

    cliente_nome = (payload.get("clienteNome") or "").strip()
    cliente_tel = (
        payload.get("clienteTelefone")
        or payload.get("clienteAssinanteTelefone")
        or ""
    ).strip()
    cliente_email = (
        payload.get("clienteEmail")
        or payload.get("clienteAssinanteEmail")
        or ""
    ).strip()

    cliente_assinante_nome = (payload.get("clienteAssinanteNome") or "").strip()
    cliente_assinante_tel = (payload.get("clienteAssinanteTelefone") or "").strip()
    cliente_assinante_email = (payload.get("clienteAssinanteEmail") or "").strip()

    id_parceiro = ensure_parceiro_id(parceiro_nome, parceiro_imobiliaria, id_corretor)

    id_cliente = ensure_cliente_id(
        cliente_nome,
        cliente_tel,
        cliente_email,
        created_by,
        id_corretor,
    )

    if cliente_assinante_nome and _norm_key(cliente_assinante_nome) != _norm_key(cliente_nome):
        id_cliente_assinante = ensure_cliente_id(
            cliente_assinante_nome,
            cliente_assinante_tel,
            cliente_assinante_email,
            created_by,
            id_corretor,
        )
    else:
        id_cliente_assinante = id_cliente

    visita_row = [
        id_visita,            # A Id_Visita
        imovel_id,            # B Id_Imovel
        data_visita,          # C Data_Visita
        id_corretor,          # D Id_Corretor
        anexo_ficha,          # E Anexo_Ficha_Visita
        audio_desc,           # F AudiodescricaoClienteVisita
        link_audio,           # G Link_Audio
        link_imagem,          # H Link_Imagem
        visita_com_parceiro,  # I Visita_Com_Parceiro
        tipo_captacao,        # J Tipo_Captacao
        endereco_externo,     # K Endereco_Externo
        proposta,             # L Proposta
        created_at,           # M CreatedAt
        created_by,           # N CreatedBy
        assinatura,           # O Assinatura
        id_cliente_assinante, # P Id_Cliente_Assinante
        id_parceiro,          # Q Id_Parceiro
        imovel_nao_captado,   # R Imovel_Nao_Captado
    ]

    start_row = 2
    col_a = sheets.values().get(
        spreadsheetId=SPREADSHEET_ID,
        range=f"Fato_Visitas!A{start_row}:A",
    ).execute().get("values", [])
    next_row = start_row + len(col_a)

    sheets.values().update(
        spreadsheetId=SPREADSHEET_ID,
        range=f"Fato_Visitas!A{next_row}:R{next_row}",
        valueInputOption="USER_ENTERED",
        body={"values": [visita_row]},
    ).execute()

    created_by_avaliacao = created_by or (payload.get("corretor") or "")

    # Fato_Avaliacao
    # A id_Avaliacao
    # B Id_Visita
    # C Id_Cliente
    # D Localizacao
    # E Tamanho
    # F Planta_Imovel
    # G Qualidade_Acabamento
    # H Estado_Conservacao
    # I Condominio_AreaComun
    # J Preco
    # K Nota_Geral
    # L Preco_N10
    # M CreatedBy
    # N Id_Parceiro
    avaliacao_row = [
        id_avaliacao,
        id_visita,
        id_cliente,
        aval.get("localizacao", ""),
        aval.get("tamanho", ""),
        aval.get("planta", ""),
        aval.get("acabamento", ""),
        aval.get("conservacao", ""),
        aval.get("condominio", ""),
        aval.get("preco", ""),
        aval.get("notaGeral", ""),
        preco_nota10,
        created_by_avaliacao,
        id_parceiro,
    ]

    sheets.values().append(
        spreadsheetId=SPREADSHEET_ID,
        range="Fato_Avaliacao!A:N",
        valueInputOption="USER_ENTERED",
        insertDataOption="INSERT_ROWS",
        body={"values": [avaliacao_row]},
    ).execute()

    # Fato_Cliente_Visita
    # A id_relacao
    # B Id_Visita
    # C Id_Cliente
    # D Papel_Visita
    cliente_visita_row = [
        id_cliente_visita,
        id_visita,
        id_cliente,
        papel_visita,
    ]

    sheets.values().append(
        spreadsheetId=SPREADSHEET_ID,
        range="Fato_Cliente_Visita!A:D",
        valueInputOption="USER_ENTERED",
        insertDataOption="INSERT_ROWS",
        body={"values": [cliente_visita_row]},
    ).execute()

    # Fato_Parceiro_Visita
    # A id_relacao
    # B Id_Visita
    # C Id_Parceiro
    if id_parceiro:
        parceiro_visita_row = [
            id_parceiro_visita,
            id_visita,
            id_parceiro,
        ]

        sheets.values().append(
            spreadsheetId=SPREADSHEET_ID,
            range="Fato_Parceiro_Visita!A:C",
            valueInputOption="USER_ENTERED",
            insertDataOption="INSERT_ROWS",
            body={"values": [parceiro_visita_row]},
        ).execute()

    return id_visita


# =========================
# Consulta: visitas do corretor
# =========================
def buscar_visitas_do_corretor(id_corretor: str, q: str = "", limit: int = 30) -> List[Dict[str, Any]]:
    """
    Retorna lista de visitas do corretor com:
      - cliente (nome vindo da Dim_Cliente_Visita a partir do Id_Cliente)
      - id_visita
      - dataVisita
      - imovelId
      - label
    """
    id_corretor = (id_corretor or "").strip()
    qn = _norm_key(q)

    if not id_corretor:
        return []

    sheets, _, _ = _get_services()

    res = sheets.values().batchGet(
        spreadsheetId=SPREADSHEET_ID,
        ranges=[
            "Fato_Visitas!A2:R",
            "Fato_Cliente_Visita!A2:D",
            "Dim_Cliente_Visita!A2:B",
        ],
    ).execute()

    ranges = res.get("valueRanges", [])
    fato_rows = (ranges[0].get("values", []) if len(ranges) > 0 else [])
    fato_cli_rows = (ranges[1].get("values", []) if len(ranges) > 1 else [])
    dim_rows = (ranges[2].get("values", []) if len(ranges) > 2 else [])

    cliente_map: Dict[str, str] = {}
    for r in dim_rows:
        cid = (r[0] if len(r) > 0 else "").strip()
        nome = (r[1] if len(r) > 1 else "").strip()
        if cid:
            cliente_map[cid] = nome

    clientes_por_visita: Dict[str, List[str]] = {}
    for r in fato_cli_rows:
        id_visita = (r[1] if len(r) > 1 else "").strip()
        id_cliente_fato = (r[2] if len(r) > 2 else "").strip()

        if not id_visita or not id_cliente_fato:
            continue

        nome_cli = (cliente_map.get(id_cliente_fato, "") or "").strip()
        if not nome_cli:
            continue

        clientes_por_visita.setdefault(id_visita, [])
        if nome_cli not in clientes_por_visita[id_visita]:
            clientes_por_visita[id_visita].append(nome_cli)

    itens: List[Dict[str, Any]] = []

    for idx, r in enumerate(fato_rows):
        row_number = 2 + idx

        id_visita = (r[0] if len(r) > 0 else "").strip()
        id_imovel = (r[1] if len(r) > 1 else "").strip()
        data_visita = (r[2] if len(r) > 2 else "").strip()
        id_cor_row = (r[3] if len(r) > 3 else "").strip()

        if not id_visita:
            continue
        if id_cor_row != id_corretor:
            continue

        nomes = clientes_por_visita.get(id_visita, [])
        if nomes:
            cliente_nome = nomes[0] if len(nomes) == 1 else f"{nomes[0]} (+{len(nomes)-1})"
        else:
            id_cliente_assinante = (r[15] if len(r) > 15 else "").strip()
            cliente_nome = (cliente_map.get(id_cliente_assinante, "") or "").strip()

        label = " - ".join(
            [p for p in [cliente_nome, data_visita, f"#{id_imovel}" if id_imovel else ""] if p]
        ).strip() or id_visita

        if qn:
            hay = " ".join([cliente_nome, data_visita, id_imovel, id_visita, label])
            if qn not in _norm_key(hay):
                continue

        itens.append(
            {
                "id_visita": id_visita,
                "cliente": cliente_nome,
                "dataVisita": data_visita,
                "imovelId": id_imovel,
                "label": label,
                "row": row_number,
            }
        )

    itens.sort(
        key=lambda it: (_parse_ddmmyyyy_safe(it.get("dataVisita", "")), int(it.get("row", 0))),
        reverse=True
    )

    return itens[: max(1, int(limit or 30))]

# =========================
# PDF da Visita
# =========================
def _batch_get_sheet_rows(ranges: List[str]) -> Dict[str, List[Dict[str, Any]]]:
    sheets, _, _ = _get_services()

    res = sheets.values().batchGet(
        spreadsheetId=SPREADSHEET_ID,
        ranges=ranges,
        majorDimension="ROWS",
    ).execute()

    value_ranges = res.get("valueRanges", [])
    out: Dict[str, List[Dict[str, Any]]] = {}

    for rg, vr in zip(ranges, value_ranges):
        values = vr.get("values", [])
        sheet_name = rg.split("!")[0]

        if not values:
            out[sheet_name] = []
            continue

        header = [str(c).strip() for c in values[0]]
        rows = []

        for raw in values[1:]:
            row = {}
            for i, h in enumerate(header):
                row[h] = raw[i] if i < len(raw) else ""
            rows.append(row)

        out[sheet_name] = rows

    return out


def _find_first_by_key(rows: List[Dict[str, Any]], key: str, value: Any) -> Dict[str, Any] | None:
    val = _safe_str(value)
    for row in rows:
        if _safe_str(row.get(key)) == val:
            return row
    return None


def _find_all_by_key(rows: List[Dict[str, Any]], key: str, value: Any) -> List[Dict[str, Any]]:
    val = _safe_str(value)
    return [row for row in rows if _safe_str(row.get(key)) == val]


def _fmt_money_brl(v: Any) -> str:
    if v in (None, ""):
        return ""
    try:
        num = float(str(v).replace(".", "").replace(",", "."))
        return f"R$ {num:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    except Exception:
        return str(v)


def _fmt_datetime_br(v: Any) -> str:
    if v in (None, ""):
        return ""

    if isinstance(v, dt.datetime):
        return v.strftime("%d/%m/%Y %H:%M:%S")

    s = str(v).strip()
    if not s:
        return ""

    formatos = [
        "%d/%m/%Y %H:%M:%S",
        "%d/%m/%Y",
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%d",
    ]
    for fmt in formatos:
        try:
            d = dt.datetime.strptime(s, fmt)
            return d.strftime("%d/%m/%Y %H:%M:%S")
        except Exception:
            continue

    return s


def _pick_from_row(row: Dict[str, Any] | None, *keys: str) -> str:
    if not row:
        return ""
    for key in keys:
        val = _safe_str(row.get(key))
        if val:
            return val
    return ""


def _display(v: Any, default: str = "—") -> str:
    s = _safe_str(v)
    return s if s else default


def _num_or_none(v: Any) -> float | None:
    s = _safe_str(v)
    if not s:
        return None
    try:
        return float(s.replace(".", "").replace(",", "."))
    except Exception:
        return None


def _avg_scores(avaliacoes: List[Dict[str, Any]]) -> Dict[str, str]:
    campos = [
        ("Localizacao", "Localização"),
        ("Tamanho", "Tamanho"),
        ("Planta_Imovel", "Planta"),
        ("Qualidade_Acabamento", "Acabamento"),
        ("Estado_Conservacao", "Conservação"),
        ("Condominio_AreaComun", "Condomínio"),
        ("Preco", "Preço"),
        ("Nota_Geral", "Nota Geral"),
    ]

    out: Dict[str, str] = {}
    for key, label in campos:
        nums = [_num_or_none(a.get(key)) for a in avaliacoes]
        nums = [n for n in nums if n is not None]
        if nums:
            out[label] = f"{sum(nums)/len(nums):.1f}"
        else:
            out[label] = "—"

    preco_n10_vals = [_num_or_none(a.get("Preco_N10")) for a in avaliacoes]
    preco_n10_vals = [n for n in preco_n10_vals if n is not None]
    out["Preço Nota 10"] = _fmt_money_brl(sum(preco_n10_vals)/len(preco_n10_vals)) if preco_n10_vals else "—"

    return out


def _find_corretor_row(visita: Dict[str, Any], dim_corretor: List[Dict[str, Any]]) -> Dict[str, Any] | None:
    id_corretor = _pick_from_row(visita, "Id_Corretor")
    created_by = _pick_from_row(visita, "CreatedBy")

    corretor = None
    if id_corretor:
        corretor = _find_first_by_key(dim_corretor, "IdCorretor", id_corretor)

    if not corretor and created_by:
        corretor = _find_first_by_key(dim_corretor, "Email", created_by)

    return corretor


def _trash_same_name_files_in_folder(folder_id: str, file_name: str) -> None:
    _, drive_files, _ = _get_services()

    safe_name = file_name.replace("'", "\\'")
    q = (
        f"name='{safe_name}' and "
        f"'{folder_id}' in parents and "
        "trashed=false"
    )

    res = drive_files.list(
        q=q,
        spaces="drive",
        fields="files(id,name)",
        pageSize=50,
    ).execute()

    for f in res.get("files", []):
        drive_files.update(fileId=f["id"], body={"trashed": True}).execute()


def _montar_contexto_pdf_visita(visita_id: str) -> Dict[str, Any]:
    data = _batch_get_sheet_rows(
        [
            "Fato_Visitas!A1:R",
            "Fato_Avaliacao!A1:N",
            "Dim_Cliente_Visita!A1:F",
            "Fato_Cliente_Visita!A1:D",
            "Dim_Corretor!A1:I",
            "Dim_Parceiro_Visita!A1:D",
            "Fato_Parceiro_Visita!A1:D",
        ]
    )

    fato_visitas = data.get("Fato_Visitas", [])
    fato_avaliacao = data.get("Fato_Avaliacao", [])
    dim_cliente = data.get("Dim_Cliente_Visita", [])
    fato_cliente_visita = data.get("Fato_Cliente_Visita", [])
    dim_corretor = data.get("Dim_Corretor", [])
    dim_parceiro = data.get("Dim_Parceiro_Visita", [])
    fato_parceiro_visita = data.get("Fato_Parceiro_Visita", [])

    visita = _find_first_by_key(fato_visitas, "Id_Visita", visita_id)
    if not visita:
        raise ValueError(f"Visita {visita_id} não encontrada.")

    corretor = _find_corretor_row(visita, dim_corretor)

    cliente_map = {
        _safe_str(r.get("Id_Cliente")): r
        for r in dim_cliente
        if _safe_str(r.get("Id_Cliente"))
    }

    parceiro_map = {
        _safe_str(r.get("Id_Parceiro")): r
        for r in dim_parceiro
        if _safe_str(r.get("Id_Parceiro"))
    }

    clientes: List[Dict[str, Any]] = []
    fatos_cliente = _find_all_by_key(fato_cliente_visita, "Id_Visita", visita_id)

    for fc in fatos_cliente:
        id_cliente = _safe_str(fc.get("Id_Cliente"))
        cli = cliente_map.get(id_cliente)
        if not cli:
            continue

        clientes.append(
            {
                "Id_Cliente": id_cliente,
                "Nome_Cliente": _pick_from_row(cli, "Nome_Cliente", "Nome"),
                "Telefone_Cliente": _pick_from_row(cli, "Telefone_Cliente", "Telefone"),
                "Email_Cliente": _pick_from_row(cli, "Email_Cliente", "Email"),
                "Papel_na_Visita": _pick_from_row(fc, "Papel_na_Visita", "Papel_Visita", "Papel"),
            }
        )

    if not clientes and _pick_from_row(visita, "Id_Cliente_Assinante"):
        cli = cliente_map.get(_pick_from_row(visita, "Id_Cliente_Assinante"))
        if cli:
            clientes.append(
                {
                    "Id_Cliente": _pick_from_row(cli, "Id_Cliente"),
                    "Nome_Cliente": _pick_from_row(cli, "Nome_Cliente", "Nome"),
                    "Telefone_Cliente": _pick_from_row(cli, "Telefone_Cliente", "Telefone"),
                    "Email_Cliente": _pick_from_row(cli, "Email_Cliente", "Email"),
                    "Papel_na_Visita": "Assinante",
                }
            )

    parceiros: List[Dict[str, Any]] = []
    fatos_parceiro = _find_all_by_key(fato_parceiro_visita, "Id_Visita", visita_id)

    for fp in fatos_parceiro:
        id_parceiro = _safe_str(fp.get("Id_Parceiro"))
        par = parceiro_map.get(id_parceiro)
        if not par:
            continue

        parceiros.append(
            {
                "Id_Parceiro": id_parceiro,
                "Nome_Parceiro": _pick_from_row(par, "Nome_Parceiro", "Nome"),
                "Imobiliaria": _pick_from_row(par, "Imobiliaria"),
                "Papel_na_Visita": _pick_from_row(fp, "Papel_na_Visita", "Papel_Visita", "Papel"),
            }
        )

    if not parceiros and _pick_from_row(visita, "Id_Parceiro"):
        par = parceiro_map.get(_pick_from_row(visita, "Id_Parceiro"))
        if par:
            parceiros.append(
                {
                    "Id_Parceiro": _pick_from_row(par, "Id_Parceiro"),
                    "Nome_Parceiro": _pick_from_row(par, "Nome_Parceiro", "Nome"),
                    "Imobiliaria": _pick_from_row(par, "Imobiliaria"),
                    "Papel_na_Visita": "Parceiro",
                }
            )

    avals = _find_all_by_key(fato_avaliacao, "Id_Visita", visita_id)

    def _deref_cliente_nome(id_cliente: Any) -> str:
        cli = cliente_map.get(_safe_str(id_cliente))
        if cli:
            return _pick_from_row(cli, "Nome_Cliente", "Nome")
        return ""

    avaliacoes = []
    for a in avals:
        avaliacoes.append(
            {
                "Nome_Cliente": _deref_cliente_nome(a.get("Id_Cliente")),
                "Localizacao": _pick_from_row(a, "Localizacao"),
                "Tamanho": _pick_from_row(a, "Tamanho"),
                "Planta_Imovel": _pick_from_row(a, "Planta_Imovel"),
                "Qualidade_Acabamento": _pick_from_row(a, "Qualidade_Acabamento"),
                "Estado_Conservacao": _pick_from_row(a, "Estado_Conservacao"),
                "Condominio_AreaComun": _pick_from_row(a, "Condominio_AreaComun"),
                "Preco": _pick_from_row(a, "Preco"),
                "Preco_N10": _pick_from_row(a, "Preco_N10"),
                "Nota_Geral": _pick_from_row(a, "Nota_Geral"),
            }
        )

    return {
        "Id_Visita": _pick_from_row(visita, "Id_Visita"),
        "CreatedAt": _fmt_datetime_br(_pick_from_row(visita, "CreatedAt")),
        "Data_Visita": _fmt_datetime_br(_pick_from_row(visita, "Data_Visita")).split(" ")[0] if _pick_from_row(visita, "Data_Visita") else "",
        "Proposta": _pick_from_row(visita, "Proposta"),
        "Id_Imovel": _pick_from_row(visita, "Id_Imovel"),
        "Tipo_Captacao": _pick_from_row(visita, "Tipo_Captacao"),
        "Endereco_Externo": _pick_from_row(visita, "Endereco_Externo"),
        "Visita_Com_Parceiro": _pick_from_row(visita, "Visita_Com_Parceiro"),
        "Imovel_Nao_Captado": _pick_from_row(visita, "Imovel_Nao_Captado"),
        "Anexo_Ficha_Visita": _pick_from_row(visita, "Anexo_Ficha_Visita"),
        "AudiodescricaoClienteVisita": _pick_from_row(visita, "AudiodescricaoClienteVisita"),
        "Link_Audio": _pick_from_row(visita, "Link_Audio"),
        "Link_Imagem": _pick_from_row(visita, "Link_Imagem"),
        "Assinatura": _pick_from_row(visita, "Assinatura"),
        "CorretorNome": _pick_from_row(corretor, "Nome", "Nome_Corretor", "NomeCompleto"),
        "CorretorTelefone": _pick_from_row(corretor, "Telefone", "Telefone_Corretor", "Celular", "WhatsApp"),
        "CorretorInstagram": _pick_from_row(corretor, "Instragram", "Instagram", "Instagram_Corretor"),
        "CorretorEmail": _pick_from_row(corretor, "Email") or _pick_from_row(visita, "CreatedBy"),
        "CorretorDescricao": _pick_from_row(corretor, "Descricao", "Descrição", "Bio"),
        "Clientes": clientes,
        "Parceiros": parceiros,
        "Avaliacoes": avaliacoes,
        "TotAval": len(avaliacoes),
    }


def _build_pdf_visita_bytes(ctx: Dict[str, Any]) -> bytes:
    try:
        from reportlab.lib import colors
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
        from reportlab.lib.units import mm
        from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
    except ImportError as e:
        raise RuntimeError(
            "A biblioteca reportlab não está instalada. Instale com: pip install reportlab"
        ) from e

    buffer = io.BytesIO()

    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=14 * mm,
        rightMargin=14 * mm,
        topMargin=14 * mm,
        bottomMargin=12 * mm,
        title=f"Relatorio_Visita_{ctx['Id_Visita']}",
    )

    styles = getSampleStyleSheet()

    style_title = ParagraphStyle(
        "custom_title",
        parent=styles["Title"],
        fontName="Helvetica-Bold",
        fontSize=19,
        textColor=colors.HexColor("#0f172a"),
        spaceAfter=4,
    )

    style_subtitle = ParagraphStyle(
        "custom_subtitle",
        parent=styles["BodyText"],
        fontName="Helvetica",
        fontSize=9.5,
        textColor=colors.HexColor("#64748b"),
        spaceAfter=10,
    )

    style_section = ParagraphStyle(
        "custom_section",
        parent=styles["Heading2"],
        fontName="Helvetica-Bold",
        fontSize=11,
        textColor=colors.HexColor("#0f172a"),
        spaceBefore=8,
        spaceAfter=6,
    )

    style_body = ParagraphStyle(
        "custom_body",
        parent=styles["BodyText"],
        fontName="Helvetica",
        fontSize=9.2,
        leading=12,
        textColor=colors.HexColor("#111827"),
    )

    style_small = ParagraphStyle(
        "custom_small",
        parent=styles["BodyText"],
        fontName="Helvetica",
        fontSize=8.2,
        leading=10.5,
        textColor=colors.HexColor("#4b5563"),
    )

    def make_info_table(rows, col_widths=(42 * mm, 130 * mm)):
        tbl = Table(rows, colWidths=list(col_widths))
        tbl.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, -1), colors.white),
                    ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#e5e7eb")),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("LEFTPADDING", (0, 0), (-1, -1), 8),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                    ("TOPPADDING", (0, 0), (-1, -1), 6),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                    ("TEXTCOLOR", (0, 0), (0, -1), colors.HexColor("#475569")),
                    ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
                    ("TEXTCOLOR", (1, 0), (1, -1), colors.HexColor("#111827")),
                ]
            )
        )
        return tbl

    def make_grid_table(data, widths):
        tbl = Table(data, colWidths=widths, repeatRows=1)
        tbl.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0f172a")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#e5e7eb")),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("FONTSIZE", (0, 0), (-1, -1), 8.5),
                    ("LEADING", (0, 0), (-1, -1), 10),
                    ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f8fafc")]),
                    ("LEFTPADDING", (0, 0), (-1, -1), 6),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                    ("TOPPADDING", (0, 0), (-1, -1), 6),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                ]
            )
        )
        return tbl

    story = []

    story.append(Paragraph("Relatório de Visita", style_title))
    story.append(
        Paragraph(
            "Documento consolidado da visita, com corretor, clientes, parceiros e resumo das avaliações.",
            style_subtitle,
        )
    )

    resumo_rows = [
        ["Id da visita", _display(ctx.get("Id_Visita"))],
        ["Data da visita", _display(ctx.get("Data_Visita"))],
        ["Criado em", _display(ctx.get("CreatedAt"))],
        ["Imóvel", _display(ctx.get("Id_Imovel"))],
        ["Proposta", _display(ctx.get("Proposta"))],
        ["Tipo de captação", _display(ctx.get("Tipo_Captacao"))],
    ]
    story.append(make_info_table(resumo_rows))
    story.append(Spacer(1, 10))

    story.append(Paragraph("Corretor", style_section))
    story.append(
        make_info_table(
            [
                ["Nome", _display(ctx.get("CorretorNome"))],
                ["Telefone", _display(ctx.get("CorretorTelefone"))],
                ["Instagram", _display(ctx.get("CorretorInstagram"))],
                ["E-mail", _display(ctx.get("CorretorEmail"))],
                ["Descrição", _display(ctx.get("CorretorDescricao"))],
            ]
        )
    )
    story.append(Spacer(1, 10))

    story.append(Paragraph("Detalhes da visita", style_section))
    detalhes_rows = [
        ["Endereço externo", _display(ctx.get("Endereco_Externo"))],
        ["Visita com parceiro", _display(ctx.get("Visita_Com_Parceiro"))],
        ["Imóvel não captado", _display(ctx.get("Imovel_Nao_Captado"))],
        ["Áudio descrição", _display(ctx.get("AudiodescricaoClienteVisita"))],
    ]
    story.append(make_info_table(detalhes_rows))
    story.append(Spacer(1, 10))

    story.append(Paragraph("Clientes", style_section))
    clientes_data = [["Cliente", "Telefone", "E-mail", "Papel"]]
    if ctx["Clientes"]:
        for c in ctx["Clientes"]:
            clientes_data.append(
                [
                    _display(c.get("Nome_Cliente")),
                    _display(c.get("Telefone_Cliente")),
                    _display(c.get("Email_Cliente")),
                    _display(c.get("Papel_na_Visita")),
                ]
            )
    else:
        clientes_data.append(["Sem clientes vinculados", "—", "—", "—"])

    story.append(
        make_grid_table(
            clientes_data,
            [52 * mm, 34 * mm, 62 * mm, 26 * mm],
        )
    )
    story.append(Spacer(1, 10))

    if ctx["Parceiros"]:
        story.append(Paragraph("Parceiros", style_section))
        parceiros_data = [["Parceiro", "Imobiliária", "Papel"]]
        for p in ctx["Parceiros"]:
            parceiros_data.append(
                [
                    _display(p.get("Nome_Parceiro")),
                    _display(p.get("Imobiliaria")),
                    _display(p.get("Papel_na_Visita")),
                ]
            )

        story.append(
            make_grid_table(
                parceiros_data,
                [65 * mm, 75 * mm, 34 * mm],
            )
        )
        story.append(Spacer(1, 10))

    story.append(Paragraph("Resumo das avaliações", style_section))
    medias = _avg_scores(ctx["Avaliacoes"])

    resumo_avaliacao = [["Critério", "Resultado"]]
    for label, value in medias.items():
        resumo_avaliacao.append([label, value])

    story.append(
        make_grid_table(
            resumo_avaliacao,
            [95 * mm, 79 * mm],
        )
    )
    story.append(Spacer(1, 10))

    if ctx["Avaliacoes"]:
        respondentes = sorted(
            {a.get("Nome_Cliente", "").strip() for a in ctx["Avaliacoes"] if a.get("Nome_Cliente")}
        )
        if respondentes:
            story.append(
                Paragraph(
                    f"<b>Respondentes:</b> {', '.join(respondentes)}",
                    style_body,
                )
            )
            story.append(Spacer(1, 6))

    links_disponiveis = []
    if _safe_str(ctx.get("Link_Audio")):
        links_disponiveis.append(f"<b>Link do áudio:</b> {ctx['Link_Audio']}")
    if _safe_str(ctx.get("Link_Imagem")):
        links_disponiveis.append(f"<b>Link da imagem:</b> {ctx['Link_Imagem']}")
    if _safe_str(ctx.get("Anexo_Ficha_Visita")):
        links_disponiveis.append(f"<b>Anexo da ficha:</b> {ctx['Anexo_Ficha_Visita']}")
    if _safe_str(ctx.get("Assinatura")):
        links_disponiveis.append(f"<b>Assinatura:</b> {ctx['Assinatura']}")

    if links_disponiveis:
        story.append(Paragraph("Links e anexos", style_section))
        for linha in links_disponiveis:
            story.append(Paragraph(linha, style_small))
            story.append(Spacer(1, 4))

    doc.build(story)
    return buffer.getvalue()


def gerar_pdf_visita_download(visita_id: str):
    ctx = _montar_contexto_pdf_visita(visita_id)
    pdf_bytes = _build_pdf_visita_bytes(ctx)
    file_name = f"Relatorio_Visita_{visita_id}.pdf"
    return io.BytesIO(pdf_bytes), file_name


def gerar_pdf_visita_publico(visita_id: str) -> Dict[str, str]:
    ctx = _montar_contexto_pdf_visita(visita_id)
    pdf_bytes = _build_pdf_visita_bytes(ctx)
    file_name = f"Relatorio_Visita_{visita_id}.pdf"

    root_folder_id = _find_or_create_folder(DRIVE_PARENT_FOLDER_NAME, parent_id=None)
    reports_folder_id = _find_or_create_folder(
        DRIVE_VISITA_REPORTS_SUBFOLDER_NAME,
        parent_id=root_folder_id,
    )
    visita_folder_id = _find_or_create_folder(visita_id, parent_id=reports_folder_id)

    _trash_same_name_files_in_folder(visita_folder_id, file_name)

    _, drive_files, drive = _get_services()

    media = MediaIoBaseUpload(
        io.BytesIO(pdf_bytes),
        mimetype="application/pdf",
        resumable=False,
    )

    created = drive_files.create(
        body={"name": file_name, "parents": [visita_folder_id]},
        media_body=media,
        fields="id,name,webViewLink",
    ).execute()

    try:
        drive.permissions().create(
            fileId=created["id"],
            body={"type": "anyone", "role": "reader"},
            fields="id",
        ).execute()
    except Exception:
        pass

    drive_path = (
        f"{DRIVE_PARENT_FOLDER_NAME}/"
        f"{DRIVE_VISITA_REPORTS_SUBFOLDER_NAME}/"
        f"{visita_id}/"
        f"{file_name}"
    )

    return {
        "file_id": created["id"],
        "file_name": created["name"],
        "drive_url": created.get("webViewLink", "") or "",
        "drive_path": drive_path,
    }


def listar_clientes_do_corretor(id_corretor: str) -> List[Dict[str, Any]]:
    """
    Lê a Dim_Cliente_Visita e retorna clientes vinculados ao ID do corretor.
    """
    sheets, _, _ = _get_services()
    # Lendo o intervalo que contém os dados dos clientes
    res = sheets.values().get(
        spreadsheetId=SPREADSHEET_ID,
        range="Dim_Cliente_Visita!A2:F",
    ).execute()
    
    rows = res.get("values", [])
    clientes = []
    
    for r in rows:
        # Estrutura: A:Id, B:Nome, C:Telefone, D:Email, E:CreatedBy, F:Id_Corretor
        row_id_corretor = (r[5] if len(r) > 5 else "").strip()
        
        if row_id_corretor == id_corretor:
            clientes.append({
                "id_cliente": r[0] if len(r) > 0 else "",
                "nome": r[1] if len(r) > 1 else "",
                "telefone": r[2] if len(r) > 2 else "",
                "email": r[3] if len(r) > 3 else "",
            })
            
    # Ordenar por nome para facilitar no front
    clientes.sort(key=lambda x: x["nome"].lower())
    return clientes

def criar_cliente_manual(nome: str, telefone: str, email: str, created_by: str, id_corretor: str) -> str:
    """
    Apenas chama a lógica de persistência que você já tem, 
    mas isolada para criação manual via formulário.
    """
    # A função ensure_cliente_id já verifica se existe e cria se não existir.
    # Como é uma criação manual, garantimos que ela rode.
    return ensure_cliente_id(
        nome_cliente=nome,
        telefone=telefone,
        email=email,
        created_by=created_by,
        id_corretor=id_corretor
    )


def buscar_clientes_do_corretor_com_historico(id_corretor: str, q: str = "", limit: int = 200) -> List[Dict[str, Any]]:
    """
    Retorna clientes do corretor com resumo:
      - id_cliente
      - nome
      - telefone
      - email
      - qtd_visitas
      - ultima_data
      - imoveis
      - visitas_ids
      - label
    """
    id_corretor = (id_corretor or "").strip()
    qn = _norm_key(q)

    if not id_corretor:
        return []

    sheets, _, _ = _get_services()

    res = sheets.values().batchGet(
        spreadsheetId=SPREADSHEET_ID,
        ranges=[
            "Dim_Cliente_Visita!A2:F",
            "Fato_Cliente_Visita!A2:D",
            "Fato_Visitas!A2:R",
        ],
    ).execute()

    ranges = res.get("valueRanges", [])
    dim_rows = (ranges[0].get("values", []) if len(ranges) > 0 else [])
    fato_cli_rows = (ranges[1].get("values", []) if len(ranges) > 1 else [])
    fato_visita_rows = (ranges[2].get("values", []) if len(ranges) > 2 else [])

    visitas_map: Dict[str, Dict[str, str]] = {}
    for r in fato_visita_rows:
        id_visita = (r[0] if len(r) > 0 else "").strip()
        id_imovel = (r[1] if len(r) > 1 else "").strip()
        data_visita = (r[2] if len(r) > 2 else "").strip()
        id_cor_row = (r[3] if len(r) > 3 else "").strip()

        if id_visita and id_cor_row == id_corretor:
            visitas_map[id_visita] = {
                "imovelId": id_imovel,
                "dataVisita": data_visita,
            }

    cliente_stats: Dict[str, Dict[str, Any]] = {}

    for r in dim_rows:
        id_cliente = (r[0] if len(r) > 0 else "").strip()
        nome = (r[1] if len(r) > 1 else "").strip()
        telefone = (r[2] if len(r) > 2 else "").strip()
        email = (r[3] if len(r) > 3 else "").strip()
        row_id_corretor = (r[5] if len(r) > 5 else "").strip()

        if not id_cliente or row_id_corretor != id_corretor:
            continue

        cliente_stats[id_cliente] = {
            "id_cliente": id_cliente,
            "nome": nome,
            "telefone": telefone,
            "email": email,
            "qtd_visitas": 0,
            "ultima_data": "",
            "imoveis": [],
            "visitas_ids": [],
        }

    for r in fato_cli_rows:
        id_visita = (r[1] if len(r) > 1 else "").strip()
        id_cliente = (r[2] if len(r) > 2 else "").strip()

        if not id_visita or not id_cliente:
            continue

        if id_cliente not in cliente_stats:
            continue

        visita = visitas_map.get(id_visita)
        if not visita:
            continue

        cliente_stats[id_cliente]["qtd_visitas"] += 1
        cliente_stats[id_cliente]["visitas_ids"].append(id_visita)

        imovel_id = visita.get("imovelId", "")
        if imovel_id and imovel_id not in cliente_stats[id_cliente]["imoveis"]:
            cliente_stats[id_cliente]["imoveis"].append(imovel_id)

        data_visita = visita.get("dataVisita", "")
        atual = cliente_stats[id_cliente]["ultima_data"]

        if data_visita:
            if not atual or _parse_ddmmyyyy_safe(data_visita) > _parse_ddmmyyyy_safe(atual):
                cliente_stats[id_cliente]["ultima_data"] = data_visita

    itens = list(cliente_stats.values())

    for item in itens:
        item["label"] = " - ".join(
            [
                item.get("nome", ""),
                f"Visitas: {item.get('qtd_visitas', 0)}",
                f"Última: {item.get('ultima_data', '-')}",
            ]
        )

    if qn:
        filtrados = []
        for item in itens:
            hay = " ".join(
                [
                    item.get("id_cliente", ""),
                    item.get("nome", ""),
                    item.get("telefone", ""),
                    item.get("email", ""),
                    item.get("ultima_data", ""),
                    " ".join(item.get("imoveis", [])),
                    item.get("label", ""),
                ]
            )
            if qn in _norm_key(hay):
                filtrados.append(item)
        itens = filtrados

    itens.sort(
        key=lambda it: (
            _parse_ddmmyyyy_safe(it.get("ultima_data", "")),
            it.get("qtd_visitas", 0),
            it.get("nome", "").lower(),
        ),
        reverse=True,
    )

    return itens[: max(1, int(limit or 200))]



def _build_pdf_cliente_bytes(ctx: Dict[str, Any]) -> bytes:
    try:
        from reportlab.lib import colors
        from reportlab.lib.pagesizes import A4, landscape
        from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
        from reportlab.lib.units import mm
        from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
    except ImportError as e:
        raise RuntimeError(
            "A biblioteca reportlab não está instalada. Instale com: pip install reportlab"
        ) from e

    buffer = io.BytesIO()

    total_visitas = len(ctx.get("Visitas") or [])
    page_size = landscape(A4) if total_visitas >= 4 else A4

    doc = SimpleDocTemplate(
        buffer,
        pagesize=page_size,
        leftMargin=14 * mm,
        rightMargin=14 * mm,
        topMargin=14 * mm,
        bottomMargin=12 * mm,
        title=f"Relatorio_Cliente_{ctx['Id_Cliente']}",
    )

    styles = getSampleStyleSheet()

    style_title = ParagraphStyle(
        "cliente_title",
        parent=styles["Title"],
        fontName="Helvetica-Bold",
        fontSize=19,
        textColor=colors.HexColor("#0f172a"),
        spaceAfter=4,
    )

    style_subtitle = ParagraphStyle(
        "cliente_subtitle",
        parent=styles["BodyText"],
        fontName="Helvetica",
        fontSize=9.5,
        textColor=colors.HexColor("#64748b"),
        spaceAfter=10,
    )

    style_section = ParagraphStyle(
        "cliente_section",
        parent=styles["Heading2"],
        fontName="Helvetica-Bold",
        fontSize=11,
        textColor=colors.HexColor("#0f172a"),
        spaceBefore=8,
        spaceAfter=6,
    )

    def make_info_table(rows, col_widths=(48 * mm, 124 * mm)):
        tbl = Table(rows, colWidths=list(col_widths))
        tbl.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, -1), colors.white),
                    ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#e5e7eb")),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("LEFTPADDING", (0, 0), (-1, -1), 8),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                    ("TOPPADDING", (0, 0), (-1, -1), 6),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                    ("TEXTCOLOR", (0, 0), (0, -1), colors.HexColor("#475569")),
                    ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
                    ("TEXTCOLOR", (1, 0), (1, -1), colors.HexColor("#111827")),
                ]
            )
        )
        return tbl

    def make_grid_table(data, widths):
        tbl = Table(data, colWidths=widths, repeatRows=1)
        tbl.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0f172a")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#e5e7eb")),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("FONTSIZE", (0, 0), (-1, -1), 8.2),
                    ("LEADING", (0, 0), (-1, -1), 9.5),
                    ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f8fafc")]),
                    ("LEFTPADDING", (0, 0), (-1, -1), 5),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 5),
                    ("TOPPADDING", (0, 0), (-1, -1), 5),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                ]
            )
        )
        return tbl

    story = []

    story.append(Paragraph("Relatório Consolidado do Cliente", style_title))
    story.append(
        Paragraph(
            "Resumo consolidado das visitas e avaliações registradas para o cliente.",
            style_subtitle,
        )
    )

    story.append(
        make_info_table(
            [
                ["Id do cliente", _display(ctx.get("Id_Cliente"))],
                ["Nome", _display(ctx.get("Nome_Cliente"))],
                ["Total de visitas", _display(ctx.get("Qtd_Visitas"))],
                ["Última visita", _display(ctx.get("Ultima_Visita"))],
            ]
        )
    )
    story.append(Spacer(1, 10))

    story.append(Paragraph("Resumo das avaliações", style_section))

    headers = ctx.get("Resumo_Avaliacoes_Headers") or ["Critérios"]
    rows = ctx.get("Resumo_Avaliacoes_Rows") or []

    tabela_resumo = [headers] + rows

    total_cols = len(headers)
    if total_cols <= 1:
        col_widths = [172 * mm]
    else:
        largura_total = 180 * mm if page_size == A4 else 255 * mm
        largura_criterio = 38 * mm
        largura_restante = max(largura_total - largura_criterio, 40 * mm)
        largura_visita = largura_restante / (total_cols - 1)
        col_widths = [largura_criterio] + [largura_visita] * (total_cols - 1)

    story.append(make_grid_table(tabela_resumo, col_widths))
    doc.build(story)
    return buffer.getvalue()


def gerar_pdf_cliente_download(id_cliente: str):
    ctx = _montar_contexto_pdf_cliente(id_cliente)
    pdf_bytes = _build_pdf_cliente_bytes(ctx)
    file_name = f"Relatorio_Cliente_{id_cliente}.pdf"
    return io.BytesIO(pdf_bytes), file_name


def gerar_pdf_cliente_publico(id_cliente: str) -> Dict[str, str]:
    ctx = _montar_contexto_pdf_cliente(id_cliente)
    pdf_bytes = _build_pdf_cliente_bytes(ctx)
    file_name = f"Relatorio_Cliente_{id_cliente}.pdf"

    root_folder_id = _find_or_create_folder(DRIVE_PARENT_FOLDER_NAME, parent_id=None)
    reports_folder_id = _find_or_create_folder(
        "Relatorios_Cliente_Gerados",
        parent_id=root_folder_id,
    )
    cliente_folder_id = _find_or_create_folder(id_cliente, parent_id=reports_folder_id)

    _trash_same_name_files_in_folder(cliente_folder_id, file_name)

    _, drive_files, drive = _get_services()

    media = MediaIoBaseUpload(
        io.BytesIO(pdf_bytes),
        mimetype="application/pdf",
        resumable=False,
    )

    created = drive_files.create(
        body={"name": file_name, "parents": [cliente_folder_id]},
        media_body=media,
        fields="id,name,webViewLink",
    ).execute()

    try:
        drive.permissions().create(
            fileId=created["id"],
            body={"type": "anyone", "role": "reader"},
            fields="id",
        ).execute()
    except Exception:
        pass

    drive_path = (
        f"{DRIVE_PARENT_FOLDER_NAME}/Relatorios_Cliente_Gerados/{id_cliente}/{file_name}"
    )

    return {
        "file_id": created["id"],
        "file_name": created["name"],
        "drive_url": created.get("webViewLink", "") or "",
        "drive_path": drive_path,
    }

def _montar_contexto_pdf_cliente(id_cliente: str) -> Dict[str, Any]:
    data = _batch_get_sheet_rows(
        [
            "Dim_Cliente_Visita!A1:F",
            "Fato_Cliente_Visita!A1:D",
            "Fato_Visitas!A1:R",
            "Fato_Avaliacao!A1:N",
            "Dim_Parceiro_Visita!A1:D",
            "Fato_Parceiro_Visita!A1:C",
        ]
    )

    dim_cliente = data.get("Dim_Cliente_Visita", [])
    fato_cliente_visita = data.get("Fato_Cliente_Visita", [])
    fato_visitas = data.get("Fato_Visitas", [])
    fato_avaliacao = data.get("Fato_Avaliacao", [])
    dim_parceiro = data.get("Dim_Parceiro_Visita", [])
    fato_parceiro_visita = data.get("Fato_Parceiro_Visita", [])

    cliente = _find_first_by_key(dim_cliente, "Id_Cliente", id_cliente)
    if not cliente:
        raise ValueError(f"Cliente {id_cliente} não encontrado.")

    visitas_rel = _find_all_by_key(fato_cliente_visita, "Id_Cliente", id_cliente)
    visita_ids = [
        _pick_from_row(v, "Id_Visita")
        for v in visitas_rel
        if _pick_from_row(v, "Id_Visita")
    ]

    visitas_map = {
        _pick_from_row(v, "Id_Visita"): v
        for v in fato_visitas
        if _pick_from_row(v, "Id_Visita")
    }

    parceiro_map = {
        _pick_from_row(p, "Id_Parceiro"): p
        for p in dim_parceiro
        if _pick_from_row(p, "Id_Parceiro")
    }

    parceiros_por_visita = {}
    for fp in fato_parceiro_visita:
        vid = _pick_from_row(fp, "Id_Visita")
        pid = _pick_from_row(fp, "Id_Parceiro")
        if not vid or not pid:
            continue
        parceiros_por_visita.setdefault(vid, [])
        parceiros_por_visita[vid].append(pid)

    visitas_detalhadas = []

    for vid in visita_ids:
        visita = visitas_map.get(vid)
        if not visita:
            continue

        avals = [
            a for a in fato_avaliacao
            if _pick_from_row(a, "Id_Visita") == vid and _pick_from_row(a, "Id_Cliente") == id_cliente
        ]

        parceiros_nomes = []
        for pid in parceiros_por_visita.get(vid, []):
            par = parceiro_map.get(pid)
            if par:
                nome_parceiro = _pick_from_row(par, "Nome_Parceiro", "Nome")
                if nome_parceiro:
                    parceiros_nomes.append(nome_parceiro)

        avaliacao = avals[0] if avals else {}

        visitas_detalhadas.append({
            "id_visita": vid,
            "data_visita": _pick_from_row(visita, "Data_Visita"),
            "id_imovel": _pick_from_row(visita, "Id_Imovel"),
            "proposta": _pick_from_row(visita, "Proposta"),
            "tipo_captacao": _pick_from_row(visita, "Tipo_Captacao"),
            "endereco_externo": _pick_from_row(visita, "Endereco_Externo"),
            "parceiros": parceiros_nomes,
            "avaliacao": {
                "Localização": _pick_from_row(avaliacao, "Localizacao"),
                "Tamanho": _pick_from_row(avaliacao, "Tamanho"),
                "Planta": _pick_from_row(avaliacao, "Planta_Imovel"),
                "Acabamento": _pick_from_row(avaliacao, "Qualidade_Acabamento"),
                "Conservação": _pick_from_row(avaliacao, "Estado_Conservacao"),
                "Condomínio": _pick_from_row(avaliacao, "Condominio_AreaComun"),
                "Preço": _pick_from_row(avaliacao, "Preco"),
                "Nota Geral": _pick_from_row(avaliacao, "Nota_Geral"),
                "Preço Nota 10": _pick_from_row(avaliacao, "Preco_N10"),
            },
        })

    visitas_detalhadas.sort(
        key=lambda x: _parse_ddmmyyyy_safe(x.get("data_visita", "")),
        reverse=True
    )

    ultima_data = visitas_detalhadas[0]["data_visita"] if visitas_detalhadas else ""

    criterios = [
        "Localização",
        "Tamanho",
        "Planta",
        "Acabamento",
        "Conservação",
        "Condomínio",
        "Preço",
        "Nota Geral",
        "Preço Nota 10",
        "Proposta",
    ]

    resumo_headers = ["Critérios"]
    for i, visita in enumerate(visitas_detalhadas, start=1):
        data_label = _display(visita.get("data_visita"))
        resumo_headers.append(f"Visita {i}\n{data_label}")

    resumo_rows = []
    for criterio in criterios:
        linha = [criterio]
        for visita in visitas_detalhadas:
            if criterio == "Proposta":
                valor = _display(visita.get("proposta"))
            else:
                valor = _display((visita.get("avaliacao") or {}).get(criterio))
            linha.append(valor)
        resumo_rows.append(linha)

    return {
        "Id_Cliente": _pick_from_row(cliente, "Id_Cliente"),
        "Nome_Cliente": _pick_from_row(cliente, "Nome_Cliente", "Nome"),
        "CreatedBy": _pick_from_row(cliente, "CreatedBy"),
        "Id_Corretor": _pick_from_row(cliente, "Id_Corretor"),
        "Qtd_Visitas": len(visitas_detalhadas),
        "Ultima_Visita": ultima_data,
        "Visitas": visitas_detalhadas,
        "Resumo_Avaliacoes_Headers": resumo_headers,
        "Resumo_Avaliacoes_Rows": resumo_rows,
    }