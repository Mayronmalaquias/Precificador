"""Popula usuarios.id_imoview a partir da aba 'Corretores' do xlsx do AppSheet.

Casa por nome normalizado (sem acento/minúsculo). Idempotente: só grava se mudou.
Rodar (raiz do backend): PYTHONPATH=. python seed_id_imoview.py
"""
import unicodedata

import pandas as pd

from app.database import SessionLocal
from app.models.usuarios import Usuarios

XLSX = "../legado/appsheet/Estoque - Geral.xlsx"


def _norm(s) -> str:
    return unicodedata.normalize("NFKD", str(s or "")).encode("ascii", "ignore").decode().lower().strip()


def _codigo(v) -> str:
    try:
        f = float(v)
        return str(int(f)) if f.is_integer() else str(v)
    except (TypeError, ValueError):
        return str(v).strip()


def main() -> None:
    df = pd.read_excel(XLSX, sheet_name="Corretores")
    col_nome = next(c for c in df.columns if "corretor" in _norm(c))
    col_cod = next(c for c in df.columns if "imoview" in _norm(c) or "codigo" in _norm(c))

    # Código 1 (e 0/vazio) é PLACEHOLDER no xlsx ("sem Imoview ainda") — ignora.
    PLACEHOLDERS = {"", "0", "1"}
    mapa = {}
    for _, r in df.iterrows():
        nome, cod = r[col_nome], r[col_cod]
        if pd.notna(nome) and pd.notna(cod):
            c = _codigo(cod)
            if c not in PLACEHOLDERS:
                mapa[_norm(nome)] = c

    session = SessionLocal()
    atualizados, ja_ok, sem_match = [], 0, []
    try:
        for u in session.query(Usuarios).all():
            chave = _norm(u.nome) or _norm(u.username)
            cod = mapa.get(chave)
            if not cod:
                if _norm(u.permissao) == "corretor":
                    sem_match.append(u.nome or u.username)
                continue
            if str(u.id_imoview or "") == cod:
                ja_ok += 1
                continue
            u.id_imoview = cod
            atualizados.append(f"{u.nome} -> {cod}")
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()

    print(f"Atualizados ({len(atualizados)}):")
    for a in atualizados:
        print("  ", a)
    print(f"Já corretos: {ja_ok}")
    print(f"Corretores sem match no xlsx ({len(sem_match)}):", ", ".join(sem_match[:25]) or "—")


if __name__ == "__main__":
    main()
