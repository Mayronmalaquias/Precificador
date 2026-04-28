# app/services/google_service.py
from __future__ import annotations

import os
from google.oauth2 import service_account
from googleapiclient.discovery import build

SCOPES = [
    "https://www.googleapis.com/auth/drive",
    "https://www.googleapis.com/auth/spreadsheets",
]

_cached = {"sheets": None, "drive": None, "drive_files": None}


def _get_sa_creds():
    """
    Lê o JSON do Service Account via caminho em env var.
    Ex: GOOGLE_SA_JSON=C:\\caminho\\service_account.json
    """
    sa_path = "app/utils/asserts/service_account.json"
    if not sa_path:
        raise RuntimeError("Env var GOOGLE_SA_JSON não configurada (caminho do service account).")
    if not os.path.exists(sa_path):
        raise RuntimeError(f"Arquivo de service account não encontrado: {sa_path}")

    return service_account.Credentials.from_service_account_file(sa_path, scopes=SCOPES)


def get_services():
    """
    Retorna (sheets, drive_files, drive)
    """
    if _cached["sheets"] and _cached["drive"] and _cached["drive_files"]:
        return _cached["sheets"], _cached["drive_files"], _cached["drive"]

    creds = _get_sa_creds()
    sheets = build("sheets", "v4", credentials=creds).spreadsheets()
    drive = build("drive", "v3", credentials=creds)
    drive_files = drive.files()

    _cached["sheets"] = sheets
    _cached["drive"] = drive
    _cached["drive_files"] = drive_files
    return sheets, drive_files, drive
