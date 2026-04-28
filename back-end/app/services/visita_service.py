"""
app/services/visita_service.py
OAuth (usuário real) para gravar no "Meu Drive" + gravar no Google Sheets

Setup:
1. Crie credenciais OAuth (Desktop app) no Google Cloud Console e baixe o JSON.
2. Salve como: ./app/utils/asserts/oauth.json
3. Rode UMA VEZ localmente:
   python -c "from app.services.visita_service import ensure_oauth_token; ensure_oauth_token(force=True)"
4. Em produção: leve o token.json junto.

Requisitos:
  pip install google-api-python-client google-auth google-auth-oauthlib google-auth-httplib2 reportlab
"""

from __future__ import annotations

import io
import logging
import mimetypes
import os
import re
import time
import uuid
import datetime as dt
from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation
from typing import Any, Dict, List, Optional, Tuple

from google.auth.exceptions import RefreshError
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import Resource, build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaIoBaseUpload

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Configuração
# ---------------------------------------------------------------------------
SPREADSHEET_ID = "1we1qAVRBqAWaXmOfnLnFJzCi8WPt-ZEhxKb0Ab9DiQU"

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OAUTH_CLIENT_FILE = os.path.join(BASE_DIR, "utils", "asserts", "oauth.json")
TOKEN_FILE = os.path.join(BASE_DIR, "utils", "asserts", "token.json")

DRIVE_PARENT_FOLDER_NAME = "61_Visitas"
DRIVE_SUBFOLDER_NAME = "Fato_Visitas_PDF"
DRIVE_VISITA_REPORTS_SUBFOLDER_NAME = "Relatorios_Visita_Gerados"
DRIVE_CLIENTE_REPORTS_SUBFOLDER_NAME = "Relatorios_Cliente_Gerados"

SCOPES = [
    "https://www.googleapis.com/auth/drive.file",
    "https://www.googleapis.com/auth/spreadsheets",
]

# Critérios de avaliação em ordem canônica
CRITERIOS_AVALIACAO = [
    "Localização",
    "Tamanho",
    "Planta",
    "Acabamento",
    "Conservação",
    "Condomínio",
    "Preço",
    "Nota Geral",
    "Preço Nota 10",
]

# Mapeamento: nome display → chave na sheet
CRITERIOS_KEY_MAP: Dict[str, str] = {
    "Localização": "Localizacao",
    "Tamanho": "Tamanho",
    "Planta": "Planta_Imovel",
    "Acabamento": "Qualidade_Acabamento",
    "Conservação": "Estado_Conservacao",
    "Condomínio": "Condominio_AreaComun",
    "Preço": "Preco",
    "Nota Geral": "Nota_Geral",
    "Preço Nota 10": "Preco_N10",
}

# ---------------------------------------------------------------------------
# Schemas das sheets (evita "magic strings" espalhadas)
# ---------------------------------------------------------------------------
@dataclass
class VisitaRow:
    id_visita: str
    id_imovel: str
    data_visita: str
    id_corretor: str
    anexo_ficha: str = ""
    audio_desc: str = ""
    link_audio: str = ""
    link_imagem: str = ""
    visita_com_parceiro: str = ""
    tipo_captacao: str = ""
    endereco_externo: str = ""
    proposta: str = ""
    created_at: str = ""
    created_by: str = ""
    assinatura: str = ""
    id_cliente_assinante: str = ""
    id_parceiro: str = ""
    imovel_nao_captado: str = ""

    def to_list(self) -> List[Any]:
        return [
            self.id_visita, self.id_imovel, self.data_visita, self.id_corretor,
            self.anexo_ficha, self.audio_desc, self.link_audio, self.link_imagem,
            self.visita_com_parceiro, self.tipo_captacao, self.endereco_externo,
            self.proposta, self.created_at, self.created_by, self.assinatura,
            self.id_cliente_assinante, self.id_parceiro, self.imovel_nao_captado,
        ]


@dataclass
class AvaliacaoRow:
    id_avaliacao: str
    id_visita: str
    id_cliente: str
    localizacao: str = ""
    tamanho: str = ""
    planta_imovel: str = ""
    qualidade_acabamento: str = ""
    estado_conservacao: str = ""
    condominio_area_comun: str = ""
    preco: str = ""
    nota_geral: str = ""
    preco_n10: str = ""
    created_by: str = ""
    id_parceiro: str = ""

    def to_list(self) -> List[Any]:
        return [
            self.id_avaliacao, self.id_visita, self.id_cliente,
            self.localizacao, self.tamanho, self.planta_imovel,
            self.qualidade_acabamento, self.estado_conservacao,
            self.condominio_area_comun, self.preco, self.nota_geral,
            self.preco_n10, self.created_by, self.id_parceiro,
        ]


# ---------------------------------------------------------------------------
# Utilitários
# ---------------------------------------------------------------------------
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
    return str(value).strip().upper() in {"SIM", "TRUE", "1", "YES", "Y"}


def _sanitize_filename(s: str) -> str:
    s = re.sub(r"[^\w\-\. ]+", "", (s or "").strip(), flags=re.UNICODE)
    s = s.replace(" ", "_")
    return s[:120]


def _norm_key(s: str) -> str:
    return re.sub(r"\s+", " ", (s or "").strip().lower())


def _parse_ddmmyyyy_safe(s: str) -> dt.date:
    try:
        return dt.datetime.strptime((s or "").strip(), "%d/%m/%Y").date()
    except Exception:
        return dt.date.min


def _fmt_money_brl(v: Any) -> str:
    if v in (None, ""):
        return ""
    try:
        num = Decimal(str(v).replace(".", "").replace(",", "."))
        formatted = f"{num:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
        return f"R$ {formatted}"
    except InvalidOperation:
        return str(v)


def _fmt_datetime_br(v: Any) -> str:
    if v in (None, ""):
        return ""
    if isinstance(v, dt.datetime):
        return v.strftime("%d/%m/%Y %H:%M:%S")
    s = str(v).strip()
    for fmt in ("%d/%m/%Y %H:%M:%S", "%d/%m/%Y", "%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d"):
        try:
            return dt.datetime.strptime(s, fmt).strftime("%d/%m/%Y %H:%M:%S")
        except Exception:
            continue
    return s


def _display(v: Any, default: str = "—") -> str:
    s = _safe_str(v)
    return s if s else default


def _num_or_none(v: Any) -> Optional[float]:
    s = _safe_str(v)
    if not s:
        return None
    try:
        return float(s.replace(".", "").replace(",", "."))
    except Exception:
        return None


def _pick_from_row(row: Optional[Dict[str, Any]], *keys: str) -> str:
    if not row:
        return ""
    for key in keys:
        val = _safe_str(row.get(key))
        if val:
            return val
    return ""


def _find_first_by_key(rows: List[Dict[str, Any]], key: str, value: Any) -> Optional[Dict[str, Any]]:
    val = _safe_str(value)
    return next((r for r in rows if _safe_str(r.get(key)) == val), None)


def _find_all_by_key(rows: List[Dict[str, Any]], key: str, value: Any) -> List[Dict[str, Any]]:
    val = _safe_str(value)
    return [r for r in rows if _safe_str(r.get(key)) == val]


# ---------------------------------------------------------------------------
# OAuth
# ---------------------------------------------------------------------------
def _get_oauth_creds() -> Optional[Credentials]:
    """Carrega e refresca credenciais OAuth. Retorna None se token não existe."""
    if not os.path.exists(TOKEN_FILE):
        return None

    try:
        creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)
    except Exception as e:
        raise RuntimeError(
            f"Não foi possível ler o token OAuth em {TOKEN_FILE}. "
            f"Apague o arquivo e gere outro. Detalhe: {e}"
        ) from e

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
                "Execute ensure_oauth_token(force=True) para reautorizar."
            ) from e

    return None


def ensure_oauth_token(force: bool = False) -> None:
    """Gera token.json interativamente. Use force=True para reautorizar."""
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


def _get_services() -> Tuple[Resource, Resource, Resource]:
    """
    Cria novas instâncias dos serviços Sheets e Drive.
    Retorna: (sheets_resource, drive_files_resource, drive_service)
    """
    creds = _get_oauth_creds()
    if not creds:
        raise RuntimeError(
            "token.json não encontrado ou inválido. "
            "Execute ensure_oauth_token() para gerar."
        )

    sheets_svc = build("sheets", "v4", credentials=creds, cache_discovery=False)
    drive_svc = build("drive", "v3", credentials=creds, cache_discovery=False)
    return sheets_svc.spreadsheets(), drive_svc.files(), drive_svc


# ---------------------------------------------------------------------------
# Retry decorator para chamadas de API
# ---------------------------------------------------------------------------
def _with_retry(fn, retries: int = 3, backoff: float = 2.0):
    """Executa fn com retry exponencial em erros transientes do Google."""
    for attempt in range(retries):
        try:
            return fn()
        except HttpError as e:
            if e.resp.status in (429, 500, 503) and attempt < retries - 1:
                wait = backoff * (attempt + 1)
                logger.warning("HTTP %s — tentativa %d/%d, aguardando %.1fs", e.resp.status, attempt + 1, retries, wait)
                time.sleep(wait)
                continue
            raise
    return None  # nunca alcançado


# ---------------------------------------------------------------------------
# Drive helpers
# ---------------------------------------------------------------------------
def _find_or_create_folder(folder_name: str, parent_id: Optional[str] = None) -> str:
    """Procura pasta por nome (e parent). Cria se não existir. Retorna folderId."""
    _, drive_files, _ = _get_services()

    safe_name = folder_name.replace("'", "\\'")
    q_parts = [
        "mimeType='application/vnd.google-apps.folder'",
        f"name='{safe_name}'",
        "trashed=false",
    ]
    if parent_id:
        q_parts.append(f"'{parent_id}' in parents")

    res = _with_retry(lambda: drive_files.list(
        q=" and ".join(q_parts),
        spaces="drive",
        fields="files(id,name)",
        pageSize=10,
    ).execute())

    files = res.get("files", [])
    if files:
        return files[0]["id"]

    body: Dict[str, Any] = {
        "name": folder_name,
        "mimeType": "application/vnd.google-apps.folder",
    }
    if parent_id:
        body["parents"] = [parent_id]

    created = _with_retry(lambda: drive_files.create(body=body, fields="id").execute())
    return created["id"]


def _resolve_folder_path(folder_names: List[str]) -> str:
    """
    Percorre/cria uma hierarquia de pastas e retorna o ID da última.
    Ex: ["61_Visitas", "Relatorios_Visita_Gerados", visita_id]
    """
    parent_id: Optional[str] = None
    for name in folder_names:
        parent_id = _find_or_create_folder(name, parent_id=parent_id)
    return parent_id  # type: ignore[return-value]


def _trash_same_name_files_in_folder(folder_id: str, file_name: str) -> None:
    _, drive_files, _ = _get_services()
    safe_name = file_name.replace("'", "\\'")
    q = f"name='{safe_name}' and '{folder_id}' in parents and trashed=false"

    res = _with_retry(lambda: drive_files.list(q=q, spaces="drive", fields="files(id,name)", pageSize=50).execute())
    for f in res.get("files", []):
        _with_retry(lambda fid=f["id"]: drive_files.update(fileId=fid, body={"trashed": True}).execute())


def _upload_pdf_bytes_to_drive(
    pdf_bytes: bytes,
    file_name: str,
    folder_path: List[str],
    make_public: bool = True,
) -> Dict[str, str]:
    """Faz upload de bytes como PDF numa hierarquia de pastas do Drive."""
    folder_id = _resolve_folder_path(folder_path)
    _trash_same_name_files_in_folder(folder_id, file_name)

    _, drive_files, drive_svc = _get_services()
    media = MediaIoBaseUpload(io.BytesIO(pdf_bytes), mimetype="application/pdf", resumable=False)

    created = _with_retry(lambda: drive_files.create(
        body={"name": file_name, "parents": [folder_id]},
        media_body=media,
        fields="id,name,webViewLink",
    ).execute())

    if make_public:
        try:
            _with_retry(lambda: drive_svc.permissions().create(
                fileId=created["id"],
                body={"type": "anyone", "role": "reader"},
                fields="id",
            ).execute())
        except Exception as e:
            logger.warning("Falha ao tornar arquivo público no Drive: %s", e)

    return {
        "file_id": created["id"],
        "file_name": created["name"],
        "drive_url": created.get("webViewLink", "") or "",
        "drive_path": "/".join(folder_path + [file_name]),
    }


def upload_pdf_to_drive(file_storage, id_corretor: str, imovel_id: str, data_visita: str) -> Dict[str, str]:
    """Faz upload de um anexo de visita para o Drive."""
    if not file_storage:
        return {"drivePath": "", "driveLink": ""}

    _, drive_files, _ = _get_services()

    filename_original = (file_storage.filename or "").lower()
    ext = os.path.splitext(filename_original)[1]
    mime = mimetypes.guess_type(filename_original)[0] or "application/octet-stream"

    base = "_".join(filter(None, [
        _sanitize_filename(id_corretor),
        _sanitize_filename(imovel_id),
        _sanitize_filename(data_visita),
        "anexo",
    ]))
    filename = f"{base}{ext}"

    folder_id = _resolve_folder_path([DRIVE_PARENT_FOLDER_NAME, DRIVE_SUBFOLDER_NAME])

    try:
        file_storage.stream.seek(0)
    except Exception:
        pass

    media = MediaIoBaseUpload(file_storage.stream, mimetype=mime, resumable=True)
    created = _with_retry(lambda: drive_files.create(
        body={"name": filename, "parents": [folder_id]},
        media_body=media,
        fields="id,name,webViewLink",
    ).execute())

    return {
        "drivePath": f"{DRIVE_SUBFOLDER_NAME}/{created['name']}",
        "driveLink": created.get("webViewLink", "") or "",
    }


# ---------------------------------------------------------------------------
# Sheets helpers
# ---------------------------------------------------------------------------
def _batch_get_sheet_rows(ranges: List[str]) -> Dict[str, List[Dict[str, Any]]]:
    """batchGet com header automático. Retorna dict sheet_name → list[dict]."""
    sheets, _, _ = _get_services()

    res = _with_retry(lambda: sheets.values().batchGet(
        spreadsheetId=SPREADSHEET_ID,
        ranges=ranges,
        majorDimension="ROWS",
    ).execute())

    out: Dict[str, List[Dict[str, Any]]] = {}
    for rg, vr in zip(ranges, res.get("valueRanges", [])):
        sheet_name = rg.split("!")[0]
        values = vr.get("values", [])

        if not values or len(values) < 1:
            out[sheet_name] = []
            continue

        header = [str(c).strip() for c in values[0]]
        if not any(header):
            logger.warning("Sheet '%s' sem cabeçalho válido.", sheet_name)
            out[sheet_name] = []
            continue

        out[sheet_name] = [
            {header[i]: (raw[i] if i < len(raw) else "") for i in range(len(header))}
            for raw in values[1:]
        ]

    return out


def _append_row(sheets: Resource, sheet_name: str, values: List[Any]) -> None:
    _with_retry(lambda: sheets.values().append(
        spreadsheetId=SPREADSHEET_ID,
        range=f"{sheet_name}!A:Z",
        valueInputOption="USER_ENTERED",
        insertDataOption="INSERT_ROWS",
        body={"values": [values]},
    ).execute())


def _read_two_columns(sheets: Resource, sheet_name: str, id_col: str, name_col: str) -> List[Tuple[str, str]]:
    """
    Lê duas colunas de uma só vez para evitar N+1 queries.
    Retorna lista de (id, nome).
    """
    cols = f"{min(id_col, name_col)}:{max(id_col, name_col)}"
    res = _with_retry(lambda: sheets.values().get(
        spreadsheetId=SPREADSHEET_ID,
        range=f"{sheet_name}!{cols}",
    ).execute())

    rows_raw = res.get("values", [])
    # Determina qual coluna é id e qual é nome pelo índice
    id_idx = 0 if id_col <= name_col else 1
    name_idx = 1 - id_idx

    result = []
    for r in rows_raw[1:]:  # skip header
        if len(r) > max(id_idx, name_idx):
            result.append((r[id_idx].strip(), r[name_idx].strip()))
    return result


def _find_id_by_name(sheets: Resource, dim_sheet: str, id_col: str, name_col: str, name: str) -> str:
    """Busca ID pelo nome (case-insensitive) em uma única query."""
    if not name:
        return ""

    pairs = _read_two_columns(sheets, dim_sheet, id_col, name_col)
    key = _norm_key(name)

    for pair_id, pair_name in pairs:
        if _norm_key(pair_name) == key:
            return pair_id

    return ""


# ---------------------------------------------------------------------------
# Dim helpers: ensure_* (busca ou cria)
# ---------------------------------------------------------------------------
def ensure_parceiro_id(sheets: Resource, nome_parceiro: str, imobiliaria: str, id_corretor: str) -> str:
    """
    Dim_Parceiro_Visita: A=Id_Parceiro, B=Nome_Parceiro, C=Imobiliaria, D=Id_Corretor
    Retorna ID existente ou cria novo.
    """
    nome_parceiro = (nome_parceiro or "").strip()
    if not nome_parceiro:
        return ""

    found = _find_id_by_name(sheets, "Dim_Parceiro_Visita", "A", "B", nome_parceiro)
    if found:
        return found

    new_id = f"P{uuid.uuid4().hex[:7].upper()}"
    _append_row(sheets, "Dim_Parceiro_Visita", [new_id, nome_parceiro, (imobiliaria or "").strip(), id_corretor or ""])
    return new_id


def ensure_cliente_id(sheets: Resource, nome_cliente: str, telefone: str, email: str, created_by: str, id_corretor: str) -> str:
    """
    Dim_Cliente_Visita: A=Id_Cliente, B=Nome, C=Telefone, D=Email, E=CreatedBy, F=Id_Corretor
    Retorna ID existente ou cria novo.
    """
    nome_cliente = (nome_cliente or "").strip()
    if not nome_cliente:
        return ""

    found = _find_id_by_name(sheets, "Dim_Cliente_Visita", "A", "B", nome_cliente)
    if found:
        return found

    new_id = f"CL{uuid.uuid4().hex[:6].upper()}"
    _append_row(sheets, "Dim_Cliente_Visita", [new_id, nome_cliente, telefone or "", email or "", created_by or "", id_corretor or ""])
    return new_id


# ---------------------------------------------------------------------------
# Main: registrar_visita
# ---------------------------------------------------------------------------
def registrar_visita(payload: Dict[str, Any]) -> str:
    """
    Grava em: Fato_Visitas, Fato_Avaliacao, Fato_Cliente_Visita, Fato_Parceiro_Visita.
    Retorna id_visita gerado.
    """
    # Uma única conexão para toda a operação
    sheets, _, _ = _get_services()

    id_visita = uuid.uuid4().hex[:8]
    id_avaliacao = uuid.uuid4().hex[:8]
    id_cliente_visita = uuid.uuid4().hex[:8]
    id_parceiro_visita = uuid.uuid4().hex[:8]

    data_visita = _to_ddmmyyyy(payload.get("dataVisita", ""))
    imovel_id = _safe_str(payload.get("imovelId"))
    id_corretor = _safe_str(payload.get("idCorretor") or payload.get("corretorId"))

    parceiro_externo = payload.get("parceiroExterno", "NAO")
    situacao_imovel = payload.get("situacaoImovel", "CAPTACAO_PROPRIA")
    created_at = _now_ddmmyyyy_hhmmss()
    created_by = payload.get("corretorEmail") or ""

    # Tipo de captação
    tipo_captacao = ""
    imovel_nao_captado = ""
    if situacao_imovel == "CAPTACAO_PROPRIA":
        tipo_captacao = "Captação Própria"
    elif situacao_imovel == "CAPTACAO_PARCEIRO":
        tipo_captacao = "Captação Parceiro"
    elif situacao_imovel == "IMOVEL_NAO_CAPTADO":
        imovel_nao_captado = "TRUE"

    # Parceiro
    parceiro_nome = _safe_str(payload.get("parceiroNome"))
    parceiro_imobiliaria = _safe_str(payload.get("parceiroImobiliaria"))
    id_parceiro = ensure_parceiro_id(sheets, parceiro_nome, parceiro_imobiliaria, id_corretor)

    # Clientes
    cliente_nome = _safe_str(payload.get("clienteNome"))
    cliente_tel = _safe_str(payload.get("clienteTelefone") or payload.get("clienteAssinanteTelefone"))
    cliente_email = _safe_str(payload.get("clienteEmail") or payload.get("clienteAssinanteEmail"))
    id_cliente = ensure_cliente_id(sheets, cliente_nome, cliente_tel, cliente_email, created_by, id_corretor)

    cliente_assinante_nome = _safe_str(payload.get("clienteAssinanteNome"))
    if cliente_assinante_nome and _norm_key(cliente_assinante_nome) != _norm_key(cliente_nome):
        id_cliente_assinante = ensure_cliente_id(
            sheets,
            cliente_assinante_nome,
            _safe_str(payload.get("clienteAssinanteTelefone")),
            _safe_str(payload.get("clienteAssinanteEmail")),
            created_by,
            id_corretor,
        )
    else:
        id_cliente_assinante = id_cliente

    # --- Fato_Visitas ---
    visita = VisitaRow(
        id_visita=id_visita,
        id_imovel=imovel_id,
        data_visita=data_visita,
        id_corretor=id_corretor,
        anexo_ficha=_safe_str(payload.get("anexoFichaVisita")),
        audio_desc=_safe_str(payload.get("audioDescricaoClienteVisita")),
        link_audio=_safe_str(payload.get("linkAudio")),
        link_imagem=_safe_str(payload.get("linkImagem")),
        visita_com_parceiro="TRUE" if _is_true(parceiro_externo) else "FALSE",
        tipo_captacao=tipo_captacao,
        endereco_externo=_safe_str(payload.get("enderecoExterno")),
        proposta=_safe_str(payload.get("proposta")),
        created_at=created_at,
        created_by=created_by,
        assinatura=_safe_str(payload.get("assinatura")),
        id_cliente_assinante=id_cliente_assinante,
        id_parceiro=id_parceiro,
        imovel_nao_captado=imovel_nao_captado,
    )

    # Encontra próxima linha disponível
    col_a = _with_retry(lambda: sheets.values().get(
        spreadsheetId=SPREADSHEET_ID,
        range="Fato_Visitas!A2:A",
    ).execute().get("values", []))
    next_row = 2 + len(col_a)

    _with_retry(lambda: sheets.values().update(
        spreadsheetId=SPREADSHEET_ID,
        range=f"Fato_Visitas!A{next_row}:R{next_row}",
        valueInputOption="USER_ENTERED",
        body={"values": [visita.to_list()]},
    ).execute())

    # --- Fato_Avaliacao ---
    aval = payload.get("avaliacoes") or {}
    avaliacao = AvaliacaoRow(
        id_avaliacao=id_avaliacao,
        id_visita=id_visita,
        id_cliente=id_cliente,
        localizacao=_safe_str(aval.get("localizacao")),
        tamanho=_safe_str(aval.get("tamanho")),
        planta_imovel=_safe_str(aval.get("planta")),
        qualidade_acabamento=_safe_str(aval.get("acabamento")),
        estado_conservacao=_safe_str(aval.get("conservacao")),
        condominio_area_comun=_safe_str(aval.get("condominio")),
        preco=_safe_str(aval.get("preco")),
        nota_geral=_safe_str(aval.get("notaGeral")),
        preco_n10=_safe_str(payload.get("precoNota10")),
        created_by=created_by or _safe_str(payload.get("corretor")),
        id_parceiro=id_parceiro,
    )
    _append_row(sheets, "Fato_Avaliacao", avaliacao.to_list())

    # --- Fato_Cliente_Visita ---
    _append_row(sheets, "Fato_Cliente_Visita", [
        id_cliente_visita,
        id_visita,
        id_cliente,
        _safe_str(payload.get("papelVisita")),
    ])

    # --- Fato_Parceiro_Visita ---
    if id_parceiro:
        _append_row(sheets, "Fato_Parceiro_Visita", [id_parceiro_visita, id_visita, id_parceiro])

    return id_visita


# ---------------------------------------------------------------------------
# Consulta: visitas do corretor
# ---------------------------------------------------------------------------
def buscar_visitas_do_corretor(id_corretor: str, q: str = "", limit: int = 30) -> List[Dict[str, Any]]:
    """Retorna visitas do corretor com nome do cliente, data e imóvel."""
    id_corretor = (id_corretor or "").strip()
    if not id_corretor:
        return []

    qn = _norm_key(q)
    data = _batch_get_sheet_rows([
        "Fato_Visitas!A1:R",
        "Fato_Cliente_Visita!A1:D",
        "Dim_Cliente_Visita!A1:B",
    ])

    # Índice de clientes: id → nome
    cliente_map: Dict[str, str] = {
        _safe_str(r.get("Id_Cliente")): _safe_str(r.get("Nome_Cliente"))
        for r in data.get("Dim_Cliente_Visita", [])
        if r.get("Id_Cliente")
    }

    # Clientes por visita
    clientes_por_visita: Dict[str, List[str]] = {}
    for r in data.get("Fato_Cliente_Visita", []):
        vid = _safe_str(r.get("Id_Visita"))
        cid = _safe_str(r.get("Id_Cliente"))
        nome = cliente_map.get(cid, "")
        if vid and nome:
            clientes_por_visita.setdefault(vid, [])
            if nome not in clientes_por_visita[vid]:
                clientes_por_visita[vid].append(nome)

    itens: List[Dict[str, Any]] = []
    for idx, r in enumerate(data.get("Fato_Visitas", [])):
        id_visita = _safe_str(r.get("Id_Visita"))
        id_imovel = _safe_str(r.get("Id_Imovel"))
        data_visita = _safe_str(r.get("Data_Visita"))
        id_cor_row = _safe_str(r.get("Id_Corretor"))

        if not id_visita or id_cor_row != id_corretor:
            continue

        nomes = clientes_por_visita.get(id_visita, [])
        if nomes:
            cliente_nome = nomes[0] if len(nomes) == 1 else f"{nomes[0]} (+{len(nomes)-1})"
        else:
            cliente_nome = cliente_map.get(_safe_str(r.get("Id_Cliente_Assinante")), "")

        label = " - ".join(filter(None, [cliente_nome, data_visita, f"#{id_imovel}" if id_imovel else ""])) or id_visita

        if qn and qn not in _norm_key(" ".join([cliente_nome, data_visita, id_imovel, id_visita, label])):
            continue

        itens.append({
            "id_visita": id_visita,
            "cliente": cliente_nome,
            "dataVisita": data_visita,
            "imovelId": id_imovel,
            "label": label,
            "row": 2 + idx,
        })

    itens.sort(key=lambda it: (_parse_ddmmyyyy_safe(it["dataVisita"]), int(it["row"])), reverse=True)
    return itens[:max(1, int(limit or 30))]


# ---------------------------------------------------------------------------
# Clientes do corretor
# ---------------------------------------------------------------------------
def listar_clientes_do_corretor(id_corretor: str) -> List[Dict[str, Any]]:
    """Retorna clientes vinculados ao corretor (leitura simples da Dim)."""
    sheets, _, _ = _get_services()

    res = _with_retry(lambda: sheets.values().get(
        spreadsheetId=SPREADSHEET_ID,
        range="Dim_Cliente_Visita!A2:F",
    ).execute())

    clientes = []
    for r in res.get("values", []):
        if (r[5] if len(r) > 5 else "").strip() == id_corretor:
            clientes.append({
                "id_cliente": r[0] if len(r) > 0 else "",
                "nome": r[1] if len(r) > 1 else "",
                "telefone": r[2] if len(r) > 2 else "",
                "email": r[3] if len(r) > 3 else "",
            })

    clientes.sort(key=lambda x: x["nome"].lower())
    return clientes


def criar_cliente_manual(nome: str, telefone: str, email: str, created_by: str, id_corretor: str) -> str:
    """Cria cliente manualmente (via formulário), reutilizando ensure_cliente_id."""
    sheets, _, _ = _get_services()
    return ensure_cliente_id(sheets, nome, telefone, email, created_by, id_corretor)


def buscar_clientes_do_corretor_com_historico(id_corretor: str, q: str = "", limit: int = 200) -> List[Dict[str, Any]]:
    """Retorna clientes do corretor com qtd de visitas, última data e imóveis visitados."""
    id_corretor = (id_corretor or "").strip()
    if not id_corretor:
        return []

    qn = _norm_key(q)
    data = _batch_get_sheet_rows([
        "Dim_Cliente_Visita!A1:F",
        "Fato_Cliente_Visita!A1:D",
        "Fato_Visitas!A1:R",
    ])

    # Índice: id_visita → {imovelId, dataVisita} — apenas visitas do corretor
    visitas_map: Dict[str, Dict[str, str]] = {
        _safe_str(r.get("Id_Visita")): {
            "imovelId": _safe_str(r.get("Id_Imovel")),
            "dataVisita": _safe_str(r.get("Data_Visita")),
        }
        for r in data.get("Fato_Visitas", [])
        if _safe_str(r.get("Id_Visita")) and _safe_str(r.get("Id_Corretor")) == id_corretor
    }

    # Stats por cliente
    cliente_stats: Dict[str, Dict[str, Any]] = {
        _safe_str(r.get("Id_Cliente")): {
            "id_cliente": _safe_str(r.get("Id_Cliente")),
            "nome": _safe_str(r.get("Nome_Cliente")),
            "telefone": _safe_str(r.get("Telefone_Cliente")),
            "email": _safe_str(r.get("Email_Cliente")),
            "qtd_visitas": 0,
            "ultima_data": "",
            "imoveis": [],
            "visitas_ids": [],
        }
        for r in data.get("Dim_Cliente_Visita", [])
        if _safe_str(r.get("Id_Cliente")) and _safe_str(r.get("Id_Corretor")) == id_corretor
    }

    for r in data.get("Fato_Cliente_Visita", []):
        vid = _safe_str(r.get("Id_Visita"))
        cid = _safe_str(r.get("Id_Cliente"))

        if not vid or not cid or cid not in cliente_stats:
            continue

        visita = visitas_map.get(vid)
        if not visita:
            continue

        stats = cliente_stats[cid]
        stats["qtd_visitas"] += 1
        stats["visitas_ids"].append(vid)

        imovel_id = visita["imovelId"]
        if imovel_id and imovel_id not in stats["imoveis"]:
            stats["imoveis"].append(imovel_id)

        data_visita = visita["dataVisita"]
        if data_visita and _parse_ddmmyyyy_safe(data_visita) > _parse_ddmmyyyy_safe(stats["ultima_data"]):
            stats["ultima_data"] = data_visita

    itens = list(cliente_stats.values())
    for item in itens:
        item["label"] = " - ".join([
            item.get("nome", ""),
            f"Visitas: {item.get('qtd_visitas', 0)}",
            f"Última: {item.get('ultima_data', '-')}",
        ])

    if qn:
        itens = [
            it for it in itens
            if qn in _norm_key(" ".join([
                it.get("id_cliente", ""), it.get("nome", ""), it.get("telefone", ""),
                it.get("email", ""), it.get("ultima_data", ""),
                " ".join(it.get("imoveis", [])), it.get("label", ""),
            ]))
        ]

    itens.sort(
        key=lambda it: (_parse_ddmmyyyy_safe(it.get("ultima_data", "")), it.get("qtd_visitas", 0), it.get("nome", "").lower()),
        reverse=True,
    )
    return itens[:max(1, int(limit or 200))]


# ---------------------------------------------------------------------------
# Contexto para PDFs
# ---------------------------------------------------------------------------
def _avg_scores(avaliacoes: List[Dict[str, Any]]) -> Dict[str, str]:
    """Calcula médias dos critérios de avaliação."""
    out: Dict[str, str] = {}
    for label, key in CRITERIOS_KEY_MAP.items():
        if key == "Preco_N10":
            continue
        nums = [_num_or_none(a.get(key)) for a in avaliacoes]
        nums = [n for n in nums if n is not None]
        out[label] = f"{sum(nums)/len(nums):.1f}" if nums else "—"

    preco_n10_vals = [_num_or_none(a.get("Preco_N10")) for a in avaliacoes]
    preco_n10_vals = [n for n in preco_n10_vals if n is not None]
    out["Preço Nota 10"] = _fmt_money_brl(sum(preco_n10_vals) / len(preco_n10_vals)) if preco_n10_vals else "—"

    return out


def _montar_contexto_pdf_visita(visita_id: str) -> Dict[str, Any]:
    data = _batch_get_sheet_rows([
        "Fato_Visitas!A1:R",
        "Fato_Avaliacao!A1:N",
        "Dim_Cliente_Visita!A1:F",
        "Fato_Cliente_Visita!A1:D",
        "Dim_Corretor!A1:I",
        "Dim_Parceiro_Visita!A1:D",
        "Fato_Parceiro_Visita!A1:D",
    ])

    visita = _find_first_by_key(data["Fato_Visitas"], "Id_Visita", visita_id)
    if not visita:
        raise ValueError(f"Visita {visita_id} não encontrada.")

    cliente_map = {_safe_str(r.get("Id_Cliente")): r for r in data["Dim_Cliente_Visita"] if r.get("Id_Cliente")}
    parceiro_map = {_safe_str(r.get("Id_Parceiro")): r for r in data["Dim_Parceiro_Visita"] if r.get("Id_Parceiro")}

    # Corretor
    id_corretor = _pick_from_row(visita, "Id_Corretor")
    created_by = _pick_from_row(visita, "CreatedBy")
    corretor = (
        _find_first_by_key(data["Dim_Corretor"], "IdCorretor", id_corretor) or
        _find_first_by_key(data["Dim_Corretor"], "Email", created_by)
    )

    # Clientes
    clientes: List[Dict[str, Any]] = []
    for fc in _find_all_by_key(data["Fato_Cliente_Visita"], "Id_Visita", visita_id):
        cli = cliente_map.get(_safe_str(fc.get("Id_Cliente")))
        if cli:
            clientes.append({
                "Id_Cliente": _pick_from_row(cli, "Id_Cliente"),
                "Nome_Cliente": _pick_from_row(cli, "Nome_Cliente", "Nome"),
                "Telefone_Cliente": _pick_from_row(cli, "Telefone_Cliente", "Telefone"),
                "Email_Cliente": _pick_from_row(cli, "Email_Cliente", "Email"),
                "Papel_na_Visita": _pick_from_row(fc, "Papel_na_Visita", "Papel_Visita", "Papel"),
            })

    # Fallback: cliente assinante direto na visita
    if not clientes:
        cli = cliente_map.get(_pick_from_row(visita, "Id_Cliente_Assinante"))
        if cli:
            clientes.append({
                "Id_Cliente": _pick_from_row(cli, "Id_Cliente"),
                "Nome_Cliente": _pick_from_row(cli, "Nome_Cliente", "Nome"),
                "Telefone_Cliente": _pick_from_row(cli, "Telefone_Cliente", "Telefone"),
                "Email_Cliente": _pick_from_row(cli, "Email_Cliente", "Email"),
                "Papel_na_Visita": "Assinante",
            })

    # Parceiros
    parceiros: List[Dict[str, Any]] = []
    for fp in _find_all_by_key(data["Fato_Parceiro_Visita"], "Id_Visita", visita_id):
        par = parceiro_map.get(_safe_str(fp.get("Id_Parceiro")))
        if par:
            parceiros.append({
                "Id_Parceiro": _pick_from_row(par, "Id_Parceiro"),
                "Nome_Parceiro": _pick_from_row(par, "Nome_Parceiro", "Nome"),
                "Imobiliaria": _pick_from_row(par, "Imobiliaria"),
                "Papel_na_Visita": _pick_from_row(fp, "Papel_na_Visita", "Papel_Visita", "Papel"),
            })

    if not parceiros:
        par = parceiro_map.get(_pick_from_row(visita, "Id_Parceiro"))
        if par:
            parceiros.append({
                "Id_Parceiro": _pick_from_row(par, "Id_Parceiro"),
                "Nome_Parceiro": _pick_from_row(par, "Nome_Parceiro", "Nome"),
                "Imobiliaria": _pick_from_row(par, "Imobiliaria"),
                "Papel_na_Visita": "Parceiro",
            })

    # Avaliações
    avals = _find_all_by_key(data["Fato_Avaliacao"], "Id_Visita", visita_id)
    avaliacoes = [
        {
            "Nome_Cliente": _pick_from_row(cliente_map.get(_safe_str(a.get("Id_Cliente"))), "Nome_Cliente", "Nome"),
            **{key: _pick_from_row(a, key) for key in CRITERIOS_KEY_MAP.values()},
        }
        for a in avals
    ]

    data_visita_raw = _pick_from_row(visita, "Data_Visita")
    return {
        "Id_Visita": _pick_from_row(visita, "Id_Visita"),
        "CreatedAt": _fmt_datetime_br(_pick_from_row(visita, "CreatedAt")),
        "Data_Visita": _fmt_datetime_br(data_visita_raw).split(" ")[0] if data_visita_raw else "",
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
        "CorretorEmail": _pick_from_row(corretor, "Email") or created_by,
        "CorretorDescricao": _pick_from_row(corretor, "Descricao", "Descrição", "Bio"),
        "Clientes": clientes,
        "Parceiros": parceiros,
        "Avaliacoes": avaliacoes,
        "TotAval": len(avaliacoes),
    }


def _montar_contexto_pdf_cliente(id_cliente: str) -> Dict[str, Any]:
    data = _batch_get_sheet_rows([
        "Dim_Cliente_Visita!A1:F",
        "Fato_Cliente_Visita!A1:D",
        "Fato_Visitas!A1:R",
        "Fato_Avaliacao!A1:N",
        "Dim_Parceiro_Visita!A1:D",
        "Fato_Parceiro_Visita!A1:C",
    ])

    cliente = _find_first_by_key(data["Dim_Cliente_Visita"], "Id_Cliente", id_cliente)
    if not cliente:
        raise ValueError(f"Cliente {id_cliente} não encontrado.")

    visitas_map = {_pick_from_row(v, "Id_Visita"): v for v in data["Fato_Visitas"] if _pick_from_row(v, "Id_Visita")}
    parceiro_map = {_pick_from_row(p, "Id_Parceiro"): p for p in data["Dim_Parceiro_Visita"] if _pick_from_row(p, "Id_Parceiro")}

    parceiros_por_visita: Dict[str, List[str]] = {}
    for fp in data["Fato_Parceiro_Visita"]:
        vid = _pick_from_row(fp, "Id_Visita")
        pid = _pick_from_row(fp, "Id_Parceiro")
        if vid and pid:
            parceiros_por_visita.setdefault(vid, []).append(pid)

    visita_ids = [_pick_from_row(v, "Id_Visita") for v in _find_all_by_key(data["Fato_Cliente_Visita"], "Id_Cliente", id_cliente)]

    visitas_detalhadas = []
    for vid in visita_ids:
        visita = visitas_map.get(vid)
        if not visita:
            continue

        avals = [
            a for a in data["Fato_Avaliacao"]
            if _pick_from_row(a, "Id_Visita") == vid and _pick_from_row(a, "Id_Cliente") == id_cliente
        ]
        avaliacao = avals[0] if avals else {}

        parceiros_nomes = [
            _pick_from_row(parceiro_map.get(pid), "Nome_Parceiro", "Nome")
            for pid in parceiros_por_visita.get(vid, [])
            if parceiro_map.get(pid)
        ]

        visitas_detalhadas.append({
            "id_visita": vid,
            "data_visita": _pick_from_row(visita, "Data_Visita"),
            "id_imovel": _pick_from_row(visita, "Id_Imovel"),
            "proposta": _pick_from_row(visita, "Proposta"),
            "tipo_captacao": _pick_from_row(visita, "Tipo_Captacao"),
            "endereco_externo": _pick_from_row(visita, "Endereco_Externo"),
            "parceiros": [n for n in parceiros_nomes if n],
            "avaliacao": {
                label: _pick_from_row(avaliacao, key)
                for label, key in {**CRITERIOS_KEY_MAP, "Proposta": "Proposta"}.items()
            },
        })

    visitas_detalhadas.sort(key=lambda x: _parse_ddmmyyyy_safe(x.get("data_visita", "")), reverse=True)
    ultima_data = visitas_detalhadas[0]["data_visita"] if visitas_detalhadas else ""

    criterios_pdf = CRITERIOS_AVALIACAO + ["Proposta"]
    resumo_headers = ["Critérios"] + [
        f"Visita {i}\n{_display(v.get('data_visita'))}"
        for i, v in enumerate(visitas_detalhadas, start=1)
    ]

    resumo_rows = []
    for criterio in criterios_pdf:
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


# ---------------------------------------------------------------------------
# PDF Builder (compartilhado)
# ---------------------------------------------------------------------------
def _get_reportlab():
    """Importa ReportLab uma vez e levanta erro claro se não instalado."""
    try:
        from reportlab.lib import colors
        from reportlab.lib.pagesizes import A4, landscape
        from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
        from reportlab.lib.units import mm
        from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
        return colors, A4, landscape, ParagraphStyle, getSampleStyleSheet, mm, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
    except ImportError as e:
        raise RuntimeError("reportlab não instalado. Execute: pip install reportlab") from e


def _make_styles(styles, ParagraphStyle):
    """Retorna dict com os estilos de parágrafo utilizados nos PDFs."""
    base = {
        "title": ParagraphStyle("title", parent=styles["Title"], fontName="Helvetica-Bold", fontSize=19, textColor="#0f172a", spaceAfter=4),
        "subtitle": ParagraphStyle("subtitle", parent=styles["BodyText"], fontName="Helvetica", fontSize=9.5, textColor="#64748b", spaceAfter=10),
        "section": ParagraphStyle("section", parent=styles["Heading2"], fontName="Helvetica-Bold", fontSize=11, textColor="#0f172a", spaceBefore=8, spaceAfter=6),
        "body": ParagraphStyle("body", parent=styles["BodyText"], fontName="Helvetica", fontSize=9.2, leading=12, textColor="#111827"),
        "small": ParagraphStyle("small", parent=styles["BodyText"], fontName="Helvetica", fontSize=8.2, leading=10.5, textColor="#4b5563"),
    }
    return base


def _make_info_table(rows, mm, colors, Table, TableStyle, col_widths=(42, 130)):
    tbl = Table(rows, colWidths=[w * mm for w in col_widths])
    tbl.setStyle(TableStyle([
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
    ]))
    return tbl


def _make_grid_table(data, widths_mm, mm, colors, Table, TableStyle):
    tbl = Table(data, colWidths=[w * mm for w in widths_mm], repeatRows=1)
    tbl.setStyle(TableStyle([
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
    ]))
    return tbl


# ---------------------------------------------------------------------------
# PDF: Visita
# ---------------------------------------------------------------------------
def _build_pdf_visita_bytes(ctx: Dict[str, Any]) -> bytes:
    colors, A4, landscape, ParagraphStyle, getSampleStyleSheet, mm, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle = _get_reportlab()

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, leftMargin=14*mm, rightMargin=14*mm,
                            topMargin=14*mm, bottomMargin=12*mm,
                            title=f"Relatorio_Visita_{ctx['Id_Visita']}")

    st = _make_styles(getSampleStyleSheet(), ParagraphStyle)
    rl = (colors, mm, Table, TableStyle)

    story = [
        Paragraph("Relatório de Visita", st["title"]),
        Paragraph("Documento consolidado da visita, com corretor, clientes, parceiros e resumo das avaliações.", st["subtitle"]),
        _make_info_table([
            ["Id da visita", _display(ctx.get("Id_Visita"))],
            ["Data da visita", _display(ctx.get("Data_Visita"))],
            ["Criado em", _display(ctx.get("CreatedAt"))],
            ["Imóvel", _display(ctx.get("Id_Imovel"))],
            ["Proposta", _display(ctx.get("Proposta"))],
            ["Tipo de captação", _display(ctx.get("Tipo_Captacao"))],
        ], mm, colors, Table, TableStyle),
        Spacer(1, 10),
        Paragraph("Corretor", st["section"]),
        _make_info_table([
            ["Nome", _display(ctx.get("CorretorNome"))],
            ["Telefone", _display(ctx.get("CorretorTelefone"))],
            ["Instagram", _display(ctx.get("CorretorInstagram"))],
            ["E-mail", _display(ctx.get("CorretorEmail"))],
            ["Descrição", _display(ctx.get("CorretorDescricao"))],
        ], mm, colors, Table, TableStyle),
        Spacer(1, 10),
        Paragraph("Detalhes da visita", st["section"]),
        _make_info_table([
            ["Endereço externo", _display(ctx.get("Endereco_Externo"))],
            ["Visita com parceiro", _display(ctx.get("Visita_Com_Parceiro"))],
            ["Imóvel não captado", _display(ctx.get("Imovel_Nao_Captado"))],
            ["Áudio descrição", _display(ctx.get("AudiodescricaoClienteVisita"))],
        ], mm, colors, Table, TableStyle),
        Spacer(1, 10),
        Paragraph("Clientes", st["section"]),
    ]

    clientes_data = [["Cliente", "Telefone", "E-mail", "Papel"]]
    if ctx["Clientes"]:
        for c in ctx["Clientes"]:
            clientes_data.append([_display(c.get("Nome_Cliente")), _display(c.get("Telefone_Cliente")), _display(c.get("Email_Cliente")), _display(c.get("Papel_na_Visita"))])
    else:
        clientes_data.append(["Sem clientes vinculados", "—", "—", "—"])

    story += [_make_grid_table(clientes_data, [52, 34, 62, 26], mm, colors, Table, TableStyle), Spacer(1, 10)]

    if ctx["Parceiros"]:
        parceiros_data = [["Parceiro", "Imobiliária", "Papel"]] + [
            [_display(p.get("Nome_Parceiro")), _display(p.get("Imobiliaria")), _display(p.get("Papel_na_Visita"))]
            for p in ctx["Parceiros"]
        ]
        story += [Paragraph("Parceiros", st["section"]), _make_grid_table(parceiros_data, [65, 75, 34], mm, colors, Table, TableStyle), Spacer(1, 10)]

    medias = _avg_scores(ctx["Avaliacoes"])
    resumo_aval = [["Critério", "Resultado"]] + [[label, value] for label, value in medias.items()]
    story += [Paragraph("Resumo das avaliações", st["section"]), _make_grid_table(resumo_aval, [95, 79], mm, colors, Table, TableStyle), Spacer(1, 10)]

    respondentes = sorted({a.get("Nome_Cliente", "").strip() for a in ctx["Avaliacoes"] if a.get("Nome_Cliente")})
    if respondentes:
        story += [Paragraph(f"<b>Respondentes:</b> {', '.join(respondentes)}", st["body"]), Spacer(1, 6)]

    links = []
    for label, key in [("Link do áudio", "Link_Audio"), ("Link da imagem", "Link_Imagem"), ("Anexo da ficha", "Anexo_Ficha_Visita"), ("Assinatura", "Assinatura")]:
        if _safe_str(ctx.get(key)):
            links.append(f"<b>{label}:</b> {ctx[key]}")

    if links:
        story.append(Paragraph("Links e anexos", st["section"]))
        for linha in links:
            story += [Paragraph(linha, st["small"]), Spacer(1, 4)]

    doc.build(story)
    return buffer.getvalue()


# ---------------------------------------------------------------------------
# PDF: Cliente
# ---------------------------------------------------------------------------
def _build_pdf_cliente_bytes(ctx: Dict[str, Any]) -> bytes:
    colors, A4, landscape, ParagraphStyle, getSampleStyleSheet, mm, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle = _get_reportlab()

    buffer = io.BytesIO()
    total_visitas = len(ctx.get("Visitas") or [])
    page_size = landscape(A4) if total_visitas >= 4 else A4

    doc = SimpleDocTemplate(buffer, pagesize=page_size, leftMargin=14*mm, rightMargin=14*mm,
                            topMargin=14*mm, bottomMargin=12*mm,
                            title=f"Relatorio_Cliente_{ctx['Id_Cliente']}")

    st = _make_styles(getSampleStyleSheet(), ParagraphStyle)

    story = [
        Paragraph("Relatório Consolidado do Cliente", st["title"]),
        Paragraph("Resumo consolidado das visitas e avaliações registradas para o cliente.", st["subtitle"]),
        _make_info_table([
            ["Id do cliente", _display(ctx.get("Id_Cliente"))],
            ["Nome", _display(ctx.get("Nome_Cliente"))],
            ["Total de visitas", _display(ctx.get("Qtd_Visitas"))],
            ["Última visita", _display(ctx.get("Ultima_Visita"))],
        ], mm, colors, Table, TableStyle, col_widths=(48, 124)),
        Spacer(1, 10),
        Paragraph("Resumo das avaliações", st["section"]),
    ]

    headers = ctx.get("Resumo_Avaliacoes_Headers") or ["Critérios"]
    rows = ctx.get("Resumo_Avaliacoes_Rows") or []
    total_cols = len(headers)

    largura_total = 180 if page_size == A4 else 255
    largura_criterio = 38
    largura_visita = max((largura_total - largura_criterio) / max(total_cols - 1, 1), 20)
    col_widths = [largura_criterio] + [largura_visita] * (total_cols - 1)

    story.append(_make_grid_table([headers] + rows, col_widths, mm, colors, Table, TableStyle))
    doc.build(story)
    return buffer.getvalue()


# ---------------------------------------------------------------------------
# API pública: gerar PDFs
# ---------------------------------------------------------------------------
def gerar_pdf_visita_download(visita_id: str) -> Tuple[io.BytesIO, str]:
    ctx = _montar_contexto_pdf_visita(visita_id)
    pdf_bytes = _build_pdf_visita_bytes(ctx)
    return io.BytesIO(pdf_bytes), f"Relatorio_Visita_{visita_id}.pdf"


def gerar_pdf_visita_publico(visita_id: str) -> Dict[str, str]:
    ctx = _montar_contexto_pdf_visita(visita_id)
    pdf_bytes = _build_pdf_visita_bytes(ctx)
    file_name = f"Relatorio_Visita_{visita_id}.pdf"
    return _upload_pdf_bytes_to_drive(
        pdf_bytes, file_name,
        [DRIVE_PARENT_FOLDER_NAME, DRIVE_VISITA_REPORTS_SUBFOLDER_NAME, visita_id],
    )


def gerar_pdf_cliente_download(id_cliente: str) -> Tuple[io.BytesIO, str]:
    ctx = _montar_contexto_pdf_cliente(id_cliente)
    pdf_bytes = _build_pdf_cliente_bytes(ctx)
    return io.BytesIO(pdf_bytes), f"Relatorio_Cliente_{id_cliente}.pdf"


def gerar_pdf_cliente_publico(id_cliente: str) -> Dict[str, str]:
    ctx = _montar_contexto_pdf_cliente(id_cliente)
    pdf_bytes = _build_pdf_cliente_bytes(ctx)
    file_name = f"Relatorio_Cliente_{id_cliente}.pdf"
    return _upload_pdf_bytes_to_drive(
        pdf_bytes, file_name,
        [DRIVE_PARENT_FOLDER_NAME, DRIVE_CLIENTE_REPORTS_SUBFOLDER_NAME, id_cliente],
    )