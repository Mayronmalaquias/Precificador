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
SPREADSHEET_ID = "1isFLYaYbaKEZrsPDbU1Bc0cswyFUgTElcQf2CNXx0Hc"

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # app/
OAUTH_CLIENT_FILE = os.path.join(BASE_DIR, "utils", "asserts", "oauth.json")
TOKEN_FILE = os.path.join(BASE_DIR, "utils", "asserts", "token.json")

# Onde salvar PDFs/anexos no Drive
DRIVE_PARENT_FOLDER_NAME = "61_Visitas"
DRIVE_SUBFOLDER_NAME = "Fato_Visitas_PDF"

SCOPES = [
    "https://www.googleapis.com/auth/drive.file",
    "https://www.googleapis.com/auth/spreadsheets",
]

_sheets = None
_drive_files = None
_drive = None


# =========================
# Utils
# =========================
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
    Inicializa serviços Sheets e Drive com OAuth.
    """
    global _sheets, _drive_files, _drive
    if _sheets and _drive_files and _drive:
        return _sheets, _drive_files, _drive

    creds = _get_oauth_creds()
    if not creds:
        raise RuntimeError(
            "token.json não encontrado ou inválido. "
            "Rode ensure_oauth_token(force=True) para autorizar novamente."
        )

    _sheets = build("sheets", "v4", credentials=creds).spreadsheets()
    _drive = build("drive", "v3", credentials=creds)
    _drive_files = _drive.files()
    return _sheets, _drive_files, _drive


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