# app/services/visita_service.py
# OAuth (usuário real) para gravar no "Meu Drive" + gravar no Google Sheets
#
# 1) Crie credenciais OAuth (Desktop app) no Google Cloud Console e baixe o JSON.
# 2) Salve como: ./app/utils/asserts/oauth_client.json
# 3) Rode UMA VEZ localmente: python -c "from app.services.visita_service import ensure_oauth_token; ensure_oauth_token()"
#    -> vai abrir o navegador para autorizar e gerar ./app/utils/asserts/token.json
# 4) Em produção: leve o token.json junto (ou rode o passo 3 na máquina que vai rodar o backend).
#
# Requisitos:
#   pip install google-api-python-client google-auth google-auth-oauthlib google-auth-httplib2

import os
import uuid
import re
import datetime as dt
from typing import Any, Dict

from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload

from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow


SPREADSHEET_ID = "1isFLYaYbaKEZrsPDbU1Bc0cswyFUgTElcQf2CNXx0Hc"

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # app/
OAUTH_CLIENT_FILE = os.path.join(BASE_DIR, "utils", "asserts", "oauth.json")
TOKEN_FILE = os.path.join(BASE_DIR, "utils", "asserts", "token.json")

# Onde salvar PDFs no seu Drive:
# - Se for "Meu Drive", pode deixar só o nome da pasta e o sistema cria/usa.
DRIVE_PARENT_FOLDER_NAME = "61_Visitas"       # pasta raiz no seu Drive
DRIVE_SUBFOLDER_NAME = "Fato_Visitas_PDF"     # subpasta para os PDFs

SCOPES = [
    "https://www.googleapis.com/auth/drive.file",
    "https://www.googleapis.com/auth/spreadsheets",
]

_sheets = None
_drive_files = None
_drive = None


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


def _get_oauth_creds() -> Credentials:
    """
    Carrega token.json (OAuth do usuário).
    Se expirado, faz refresh.
    Se não existir, inicia fluxo (abre navegador) - usar UMA VEZ no setup.
    """
    creds = None

    if os.path.exists(TOKEN_FILE):
        creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)

    if creds and creds.expired and creds.refresh_token:
        creds.refresh(Request())
        with open(TOKEN_FILE, "w", encoding="utf-8") as f:
            f.write(creds.to_json())

    return creds


def ensure_oauth_token() -> None:
    """
    Rode UMA VEZ para gerar o token.json.
    """
    if os.path.exists(TOKEN_FILE):
        return

    if not os.path.exists(OAUTH_CLIENT_FILE):
        raise FileNotFoundError(f"OAuth client não encontrado: {OAUTH_CLIENT_FILE}")

    flow = InstalledAppFlow.from_client_secrets_file(OAUTH_CLIENT_FILE, SCOPES)
    creds = flow.run_local_server(port=0)

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
            "token.json não encontrado/ inválido. Rode ensure_oauth_token() uma vez para autorizar."
        )

    _sheets = build("sheets", "v4", credentials=creds).spreadsheets()
    _drive = build("drive", "v3", credentials=creds)
    _drive_files = _drive.files()
    return _sheets, _drive_files, _drive


def _find_or_create_folder(folder_name: str, parent_id: str | None = None) -> str:
    """
    Procura uma pasta por nome (no parent, se informado). Se não achar, cria.
    Retorna folderId.
    """
    _, drive_files, _ = _get_services()

    # query de pasta
    q_parts = [
        "mimeType='application/vnd.google-apps.folder'",
        f"name='{folder_name}'",
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
    """
    Envia o PDF para o MEU DRIVE (OAuth do usuário) e retorna:
      - drivePath: "Fato_Visitas_PDF/<nome>.pdf" (padrão que você quer gravar)
      - driveLink: webViewLink do Drive
    """
    if not file_storage:
        return {"drivePath": "", "driveLink": ""}

    _, drive_files, _ = _get_services()

    safe_id = _sanitize_filename(id_corretor)
    safe_imovel = _sanitize_filename(imovel_id)
    safe_data = _sanitize_filename(data_visita)

    base = "_".join([p for p in [safe_id, safe_imovel, safe_data, "ficha"] if p]) or "ficha_visita"
    filename = f"{base}.pdf"

    # garante pastas: Meu Drive / 61_Visitas / Fato_Visitas_PDF
    root_folder_id = _find_or_create_folder(DRIVE_PARENT_FOLDER_NAME, parent_id=None)
    sub_folder_id = _find_or_create_folder(DRIVE_SUBFOLDER_NAME, parent_id=root_folder_id)

    media = MediaIoBaseUpload(
        file_storage.stream,
        mimetype="application/pdf",
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


def registrar_visita(payload: Dict[str, Any]) -> str:
    """
    Grava em:
    - Fato_Visitas (A:R)
    - Fato_Avaliacao (A:N)
    - Fato_Cliente_Visita (A:D)
    """
    sheets, _, _ = _get_services()

    id_visita = uuid.uuid4().hex[:8]
    id_avaliacao = uuid.uuid4().hex[:8]
    id_cliente_visita = uuid.uuid4().hex[:8]

    data_visita = _to_ddmmyyyy(payload.get("dataVisita"))
    imovel_id = payload.get("imovelId", "")

    # CORRETO: id do corretor vem do login
    id_corretor = payload.get("idCorretor") or payload.get("corretorId") or ""

    parceiro_externo = payload.get("parceiroExterno", "NAO")
    situacao_imovel = payload.get("situacaoImovel", "CAPTACAO_PROPRIA")

    proposta = payload.get("proposta", "")
    cliente_nome = payload.get("clienteNome", "")
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

    # Campos do Sheets vindos do front
    anexo_ficha = payload.get("anexoFichaVisita", "")                # E (caminho)
    audio_desc = payload.get("audioDescricaoClienteVisita", "")      # F
    link_audio = payload.get("linkAudio", "")                        # G
    link_imagem = payload.get("linkImagem", "")                      # H (link do PDF no Drive)
    endereco_externo = payload.get("enderecoExterno", "")            # K
    assinatura = payload.get("assinatura", "")                       # O
    id_cliente_assinante = payload.get("idClienteAssinante", "")     # P
    id_parceiro = payload.get("idParceiro", "")                      # Q

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

    # modelo padrão: cabeçalho na linha 1, dados a partir da 2
    START_ROW = 2
    colA = sheets.values().get(
        spreadsheetId=SPREADSHEET_ID,
        range=f"Fato_Visitas!A{START_ROW}:A",
    ).execute().get("values", [])
    next_row = START_ROW + len(colA)

    sheets.values().update(
        spreadsheetId=SPREADSHEET_ID,
        range=f"Fato_Visitas!A{next_row}:R{next_row}",
        valueInputOption="USER_ENTERED",
        body={"values": [visita_row]},
    ).execute()

    created_by_avaliacao = created_by or (payload.get("corretor") or "")

    avaliacao_row = [
        id_avaliacao,                 # A
        id_visita,                    # B
        cliente_nome,                 # C (ideal: Id_Cliente real)
        aval.get("localizacao", ""),  # D
        aval.get("tamanho", ""),      # E
        aval.get("planta", ""),       # F
        aval.get("acabamento", ""),   # G
        aval.get("conservacao", ""),  # H
        aval.get("condominio", ""),   # I
        "",                           # J Preco_Pedido
        aval.get("notaGeral", ""),    # K Nota_Imovel
        preco_nota10,                 # L Preco_Nota10
        created_by_avaliacao,         # M CreatedBy
        id_parceiro,                  # N Id_Parceiro
    ]

    sheets.values().append(
        spreadsheetId=SPREADSHEET_ID,
        range="Fato_Avaliacao!A:N",
        valueInputOption="USER_ENTERED",
        insertDataOption="INSERT_ROWS",
        body={"values": [avaliacao_row]},
    ).execute()

    cliente_visita_row = [
        id_cliente_visita,
        id_visita,
        cliente_nome,
        papel_visita,
    ]

    sheets.values().append(
        spreadsheetId=SPREADSHEET_ID,
        range="Fato_Cliente_Visita!A:D",
        valueInputOption="USER_ENTERED",
        insertDataOption="INSERT_ROWS",
        body={"values": [cliente_visita_row]},
    ).execute()

    return id_visita
