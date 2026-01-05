# app/services/visita_service.py
import os
import uuid
import datetime as dt
from typing import Any, Dict

from google.oauth2 import service_account
from googleapiclient.discovery import build

SPREADSHEET_ID = "1isFLYaYbaKEZrsPDbU1Bc0cswyFUgTElcQf2CNXx0Hc"  # <-- coloque o seu aqui

# Caminho absoluto para o credentials.json dentro do projeto
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # app/
CREDENTIALS_FILE = "./app/utils/asserts/credenciais.json"

SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]

credentials = service_account.Credentials.from_service_account_file(
    CREDENTIALS_FILE, scopes=SCOPES
)
_sheets = build("sheets", "v4", credentials=credentials).spreadsheets()


def _to_ddmmyyyy(date_str: str) -> str:
    """
    Converte 'YYYY-MM-DD' (React) para 'DD/MM/YYYY' (mais amigável no Sheets).
    Se vier vazio, usa hoje.
    Se vier em outro formato, retorna como está.
    """
    if not date_str:
        return dt.date.today().strftime("%d/%m/%Y")
    try:
        return dt.datetime.strptime(date_str, "%Y-%m-%d").strftime("%d/%m/%Y")
    except Exception:
        return date_str


def _now_ddmmyyyy_hhmmss() -> str:
    return dt.datetime.now().strftime("%d/%m/%Y %H:%M:%S")


def _is_true(value: Any) -> bool:
    """
    Aceita 'SIM/NAO' (React), 'TRUE/FALSE', 1/0, etc.
    """
    if value is None:
        return False
    s = str(value).strip().upper()
    return s in {"SIM", "TRUE", "1", "YES", "Y"}


def registrar_visita(payload: Dict[str, Any]) -> str:
    """
    Recebe o JSON enviado pelo React e grava nas abas:
    - Fato_Visitas
    - Fato_Avaliacao
    - Fato_Cliente_Visita

    Retorna o Id_Visita gerado.
    """

    # ----------------- IDs -----------------
    id_visita = uuid.uuid4().hex[:8]
    id_avaliacao = uuid.uuid4().hex[:8]
    id_cliente_visita = uuid.uuid4().hex[:8]

    # ----------------- Campos básicos -----------------
    data_visita = _to_ddmmyyyy(payload.get("dataVisita"))
    imovel_id = payload.get("imovelId", "")
    corretor_nome = payload.get("corretor", "")
    telefone_corretor = payload.get("telefoneCorretor", "")

    # React manda "SIM"/"NAO" (no seu componente)
    parceiro_externo = payload.get("parceiroExterno", "NAO")

    situacao_imovel = payload.get("situacaoImovel", "CAPTACAO_PROPRIA")
    proposta = payload.get("proposta", "")
    cliente_nome = payload.get("clienteNome", "")
    papel_visita = payload.get("papelVisita", "")

    aval = payload.get("avaliacoes", {}) or {}
    preco_nota10 = payload.get("precoNota10") or ""

    # ---- CreatedAt / CreatedBy ----
    created_at = _now_ddmmyyyy_hhmmss()
    created_by = payload.get("corretorEmail") or ""  # envie do React/localStorage

    # ----------------- Derivações para a folha -----------------
    visita_com_parceiro = "TRUE" if _is_true(parceiro_externo) else "FALSE"

    tipo_captacao = ""
    imovel_nao_captado = ""
    if situacao_imovel == "CAPTACAO_PROPRIA":
        tipo_captacao = "Captação Própria"
    elif situacao_imovel == "CAPTACAO_PARCEIRO":
        tipo_captacao = "Captação Parceiro"
    elif situacao_imovel == "IMOVEL_NAO_CAPTADO":
        imovel_nao_captado = "TRUE"

    # ----------------- Campos ainda não usados (deixa vazio) -----------------
    anexo_ficha = ""           # E Anexo_Ficha_Visita
    audio_desc = ""            # F AudiodescricaoClienteVisita
    link_audio = ""            # G Link_Audio
    link_imagem = ""           # H Link_Imagem
    endereco_externo = ""      # K Endereco_Externo
    assinatura = ""            # O Assinatura
    id_cliente_assinante = ""  # P Id_Cliente_Assinante
    id_parceiro = ""           # Q Id_Parceiro

    # ===========================================================
    # 1) Fato_Visitas  (A:R)  - ORDEM CERTA (18 colunas)
    # ===========================================================
    # A Id_Visita
    # B Id_Imovel
    # C Data_Visita
    # D Id_Corretor
    # E Anexo_Ficha_Visita
    # F AudiodescricaoClienteVisita
    # G Link_Audio
    # H Link_Imagem
    # I Visita_Com_Parceiro
    # J Tipo_Captacao
    # K Endereco_Externo
    # L Proposta
    # M CreatedAt
    # N CreatedBy
    # O Assinatura
    # P Id_Cliente_Assinante
    # Q Id_Parceiro
    # R Imovel_Nao_Captado
    visita_row = [
        id_visita,            # A
        imovel_id,            # B
        data_visita,          # C
        telefone_corretor,    # D
        anexo_ficha,          # E
        audio_desc,           # F
        link_audio,           # G
        link_imagem,          # H
        visita_com_parceiro,  # I
        tipo_captacao,        # J
        endereco_externo,     # K
        proposta,             # L
        created_at,           # M
        created_by,           # N (EMAIL)
        assinatura,           # O
        id_cliente_assinante, # P
        id_parceiro,          # Q
        imovel_nao_captado,   # R
    ]

    # Escreve sempre em A:R na próxima linha (evita cair na coluna S)
    START_ROW = 5  # ajuste se seus dados começarem em outra linha

    colA = _sheets.values().get(
        spreadsheetId=SPREADSHEET_ID,
        range=f"Fato_Visitas!A{START_ROW}:A",
    ).execute().get("values", [])

    next_row = START_ROW + len(colA)

    _sheets.values().update(
        spreadsheetId=SPREADSHEET_ID,
        range=f"Fato_Visitas!A{next_row}:R{next_row}",
        valueInputOption="USER_ENTERED",
        body={"values": [visita_row]},
    ).execute()

    # ===========================================================
    # 2) Fato_Avaliacao
    # Colunas (A:N):
    # Id_Avaliacao, Id_Visita, Id_Cliente, Localizacao, Tamanho,
    # Planta, Qualidade_acabamento, Estado_conservacao,
    # Condominio_area_comum, Preco_Pedido, Nota_Imovel,
    # Preco_Nota10, CreatedBy, Id_Parceiro
    # ===========================================================
    # Sugestão: manter CreatedBy como email (se tiver), senão cai no nome
    created_by_avaliacao = created_by or corretor_nome

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

    _sheets.values().append(
        spreadsheetId=SPREADSHEET_ID,
        range="Fato_Avaliacao!A:N",
        valueInputOption="USER_ENTERED",
        insertDataOption="INSERT_ROWS",
        body={"values": [avaliacao_row]},
    ).execute()

    # ===========================================================
    # 3) Fato_Cliente_Visita  (A:D)
    # (Id_ClienteVisita, Id_Visita, Id_Cliente, Papel_na_Visita)
    # ===========================================================
    cliente_visita_row = [
        id_cliente_visita,
        id_visita,
        cliente_nome,  # ideal: Id_Cliente real
        papel_visita,
    ]

    _sheets.values().append(
        spreadsheetId=SPREADSHEET_ID,
        range="Fato_Cliente_Visita!A:D",
        valueInputOption="USER_ENTERED",
        insertDataOption="INSERT_ROWS",
        body={"values": [cliente_visita_row]},
    ).execute()

    return id_visita
