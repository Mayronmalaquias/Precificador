# app/services/visita_service.py
import os
import uuid
import datetime as dt

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


def registrar_visita(payload: dict) -> str:
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
    data_visita = payload.get("dataVisita") or dt.date.today().isoformat()
    imovel_id = payload.get("imovelId", "")
    corretor_nome = payload.get("corretor", "")
    telefone_corretor = payload.get("telefoneCorretor", "")
    parceiro_externo = payload.get("parceiroExterno", "NAO")
    situacao_imovel = payload.get("situacaoImovel", "CAPTACAO_PROPRIA")
    proposta = payload.get("proposta", "")
    cliente_nome = payload.get("clienteNome", "")
    papel_visita = payload.get("papelVisita", "")

    aval = payload.get("avaliacoes", {})
    preco_nota10 = payload.get("precoNota10") or ""

    # ----------------- Derivações para a folha -----------------
    visita_com_parceiro = "Sim" if parceiro_externo == "SIM" else "Não"

    tipo_captacao = ""
    imovel_nao_captado = ""
    if situacao_imovel == "CAPTACAO_PROPRIA":
        tipo_captacao = "Captação Própria"
    elif situacao_imovel == "CAPTACAO_PARCEIRO":
        tipo_captacao = "Captação Parceiro"
    elif situacao_imovel == "IMOVEL_NAO_CAPTADO":
        imovel_nao_captado = "Sim"

    # ===========================================================
    # 1) Fato_Visitas  (A:R)  -> vê os nomes das colunas no xlsx
    # ===========================================================
    visita_row = [
        id_visita,           # A Id_Visita
        imovel_id,           # B Id_Imovel
        data_visita,         # C Data_Visita
        telefone_corretor,   # D Id_Corretor (aqui estamos usando o telefone)
        "",                  # E Anexo_Ficha_Visita
        "",                  # F link_ficha_visita
        "",                  # G Imóvel visitado?
        "",                  # H Id_Usuario
        visita_com_parceiro, # I Visita_Com_Parceiro
        tipo_captacao,       # J Tipo_Captacao
        "",                  # K Tipo_Visita
        proposta,            # L Proposta
        "",                  # M Observações
        "",                  # N Origem_Captacao
        "",                  # O Tipo_Imóvel
        "",                  # P Id_Parceria
        "",                  # Q IdAnuncio
        imovel_nao_captado,  # R Imovel_Nao_Captado
    ]

    _sheets.values().append(
        spreadsheetId=SPREADSHEET_ID,
        range="Fato_Visitas!A:R",
        valueInputOption="USER_ENTERED",
        insertDataOption="INSERT_ROWS",
        body={"values": [visita_row]},
    ).execute()

    # ===========================================================
    # 2) Fato_Avaliacao
    # Colunas:
    # Id_Avaliacao, Id_Visita, Id_Cliente, Localizacao, Tamanho,
    # Planta, Qualidade_acabamento, Estado_conservacao,
    # Condominio_area_comum, Preco_Pedido, Nota_Imovel,
    # Preco_Nota10, CreatedBy, Id_Parceiro
    # ===========================================================
    avaliacao_row = [
        id_avaliacao,
        id_visita,
        cliente_nome,                       # aqui você pode colocar o Id_Cliente real se tiver
        aval.get("localizacao", ""),
        aval.get("tamanho", ""),
        aval.get("planta", ""),
        aval.get("acabamento", ""),
        aval.get("conservacao", ""),
        aval.get("condominio", ""),
        "",                                  # Preco_Pedido (se quiser mandar depois)
        aval.get("notaGeral", ""),
        preco_nota10,
        corretor_nome,                       # CreatedBy
        "",                                  # Id_Parceiro
    ]

    _sheets.values().append(
        spreadsheetId=SPREADSHEET_ID,
        range="Fato_Avaliacao!A:N",
        valueInputOption="USER_ENTERED",
        insertDataOption="INSERT_ROWS",
        body={"values": [avaliacao_row]},
    ).execute()

    # ===========================================================
    # 3) Fato_Cliente_Visita  (Id_ClienteVisita, Id_Visita, Id_Cliente, Papel_na_Visita)
    # ===========================================================
    cliente_visita_row = [
        id_cliente_visita,
        id_visita,
        cliente_nome,    # Id_Cliente (ou o código real se você tiver)
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
