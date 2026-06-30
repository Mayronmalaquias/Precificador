"""
Script: marcar visitas da equipe Lotus (Thais) como visualizadas até ontem,
excluindo os corretores Ronaldo e Antônia.

Rodar do diretório back-end:
    python marcar_visitas_lotus.py

O script imprime um resumo antes de gravar — confirme antes de inserir.
"""

import os
import sys
import datetime
from dotenv import load_dotenv

load_dotenv()

# ── Google Sheets ────────────────────────────────────────────────────────────
import os as _os
BASE_DIR = _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), "app")
TOKEN_FILE   = _os.path.join(BASE_DIR, "utils", "asserts", "token.json")
OAUTH_FILE   = _os.path.join(BASE_DIR, "utils", "asserts", "oauth.json")
SCOPES       = [
    "https://www.googleapis.com/auth/drive.file",
    "https://www.googleapis.com/auth/spreadsheets",
]
SPREADSHEET_ID = "1we1qAVRBqAWaXmOfnLnFJzCi8WPt-ZEhxKb0Ab9DiQU"

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build


def _get_creds():
    creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)
    if creds.expired and creds.refresh_token:
        from google.auth.transport.requests import Request
        creds.refresh(Request())
    return creds


def _read_sheet(service, range_name):
    result = service.spreadsheets().values().get(
        spreadsheetId=SPREADSHEET_ID, range=range_name
    ).execute()
    rows = result.get("values", [])
    if not rows:
        return []
    headers = rows[0]
    return [dict(zip(headers, row + [""] * (len(headers) - len(row)))) for row in rows[1:]]


# ── PostgreSQL ───────────────────────────────────────────────────────────────
sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
from app.database import SessionLocal
from app.models.gerente_visita_visualizada import GerenteVisitaVisualizada


def main():
    print("Conectando ao Google Sheets...")
    service = build("sheets", "v4", credentials=_get_creds())

    dim_gerente  = _read_sheet(service, "Dim_Gerente!A1:D")
    dim_corretor = _read_sheet(service, "Dim_Corretor!A1:I")
    fato_visitas = _read_sheet(service, "Fato_Visitas!A1:D")  # Id_Visita, Id_Imovel, Data_Visita, Id_Corretor

    # 1. Encontrar Thais na Dim_Gerente (equipe LOTUS ou nome contendo "thais")
    thais = next(
        (g for g in dim_gerente
         if "lotus" in (g.get("Equipe") or "").lower()
         or "thais" in (g.get("Nome") or "").lower()),
        None,
    )
    if not thais:
        print("ERRO: Gerente Thais / equipe Lotus não encontrada em Dim_Gerente.")
        print("Gerentes disponíveis:", [(g.get("Nome"), g.get("Equipe")) for g in dim_gerente])
        sys.exit(1)

    id_gerente_thais = thais["IdGerente"]
    print(f"Gerente encontrada: {thais['Nome']} (ID={id_gerente_thais}, Equipe={thais.get('Equipe')})")

    # 2. Corretores da equipe de Thais, excluindo Ronaldo e Antônia
    EXCLUIDOS = {"ronaldo", "antonia", "antônia"}
    corretores_equipe = [
        c for c in dim_corretor
        if c.get("IdGerente") == id_gerente_thais
        and not any(ex in (c.get("Nome") or "").lower() for ex in EXCLUIDOS)
    ]
    ids_corretores = {c["IdCorretor"] for c in corretores_equipe}

    print(f"\nCorretores incluídos ({len(corretores_equipe)}):")
    for c in corretores_equipe:
        print(f"  {c['IdCorretor']} — {c.get('Nome')}")

    excluidos_encontrados = [
        c for c in dim_corretor
        if c.get("IdGerente") == id_gerente_thais
        and any(ex in (c.get("Nome") or "").lower() for ex in EXCLUIDOS)
    ]
    if excluidos_encontrados:
        print(f"\nCorretores EXCLUÍDOS:")
        for c in excluidos_encontrados:
            print(f"  {c['IdCorretor']} — {c.get('Nome')}")

    # 3. Visitas desses corretores com Data_Visita < hoje
    ontem = datetime.date.today()  # "até ontem" = antes de hoje
    ids_visita = []
    for v in fato_visitas:
        if v.get("Id_Corretor") not in ids_corretores:
            continue
        raw_data = v.get("Data_Visita", "")
        if not raw_data:
            ids_visita.append(v["Id_Visita"])
            continue
        try:
            # Formato pode ser "dd/mm/yyyy", "yyyy-mm-dd" ou datetime string
            raw = str(raw_data).strip()
            if "/" in raw:
                partes = raw.split("/")
                if len(partes[2]) == 4:
                    data_v = datetime.date(int(partes[2]), int(partes[1]), int(partes[0]))
                else:
                    data_v = datetime.date(int(partes[0]), int(partes[1]), int(partes[2]))
            else:
                data_v = datetime.date.fromisoformat(raw[:10])
            if data_v < ontem:
                ids_visita.append(v["Id_Visita"])
        except Exception:
            ids_visita.append(v["Id_Visita"])  # data inválida → inclui por segurança

    ids_visita = [i for i in ids_visita if i]
    print(f"\nVisitas a marcar como vistas: {len(ids_visita)}")

    if not ids_visita:
        print("Nenhuma visita encontrada. Encerrando.")
        sys.exit(0)

    confirmar = input(f"\nInserir {len(ids_visita)} registros para id_gerente={id_gerente_thais}? [s/N] ").strip().lower()
    if confirmar != "s":
        print("Cancelado.")
        sys.exit(0)

    # 4. Inserir no banco, ignorando duplicatas
    session = SessionLocal()
    try:
        existentes = {
            r.id_visita
            for r in session.query(GerenteVisitaVisualizada.id_visita)
            .filter_by(id_gerente=id_gerente_thais)
            .all()
        }
        novos = [i for i in ids_visita if i not in existentes]
        print(f"Já existem {len(existentes)} registros. Inserindo {len(novos)} novos...")

        for id_visita in novos:
            session.add(GerenteVisitaVisualizada(
                id_gerente=id_gerente_thais,
                id_visita=id_visita,
            ))
        session.commit()
        print(f"✓ {len(novos)} registros inseridos com sucesso.")
    except Exception as e:
        session.rollback()
        print(f"ERRO ao inserir: {e}")
        raise
    finally:
        session.close()


if __name__ == "__main__":
    main()
