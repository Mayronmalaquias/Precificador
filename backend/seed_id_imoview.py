"""Popula usuarios.id_imoview a partir da aba 'Corretores' da planilha de estoque.

Fonte padrão: o Google Sheet vivo (mesma planilha do lançamento de imóvel). Com --xlsx,
lê o export antigo do AppSheet — útil offline / sem service account.

Casa por nome normalizado (sem acento/minúsculo). Idempotente: só grava se mudou, e
nunca rouba um código que já é de outro usuário (o código é único).

Rodar (raiz do backend): PYTHONPATH=. python seed_id_imoview.py [--xlsx]
"""
import sys
import unicodedata

from app.database import SessionLocal
from app.models.usuarios import Usuarios
from app.services.lancamento_service import CODIGOS_PLACEHOLDER, codigo_imoview

XLSX = "../legado/appsheet/Estoque - Geral.xlsx"


def _norm(s) -> str:
    return unicodedata.normalize("NFKD", str(s or "")).encode("ascii", "ignore").decode().lower().strip()


def _mapa_do_sheet() -> dict:
    """{nome_normalizado: codigo} a partir da aba 'Corretores' do Google Sheet."""
    from app.services.lancamento_service import carregar_corretores_estoque

    return {_norm(nome): cod for cod, nome in carregar_corretores_estoque().items()}


def _mapa_do_xlsx() -> dict:
    """{nome_normalizado: codigo} a partir do export xlsx do AppSheet."""
    import pandas as pd

    df = pd.read_excel(XLSX, sheet_name="Corretores")
    col_nome = next(c for c in df.columns if "corretor" in _norm(c))
    col_cod = next(c for c in df.columns if "imoview" in _norm(c) or "codigo" in _norm(c))

    mapa = {}
    for _, r in df.iterrows():
        nome, cod = r[col_nome], r[col_cod]
        if pd.notna(nome) and pd.notna(cod):
            c = codigo_imoview(cod)
            if c not in CODIGOS_PLACEHOLDER:
                mapa[_norm(nome)] = c
    return mapa


def main() -> None:
    usar_xlsx = "--xlsx" in sys.argv
    if usar_xlsx:
        mapa = _mapa_do_xlsx()
        print(f"Fonte: xlsx ({XLSX}) — {len(mapa)} corretores.")
    else:
        mapa = _mapa_do_sheet()
        print(f"Fonte: Google Sheet (aba 'Corretores') — {len(mapa)} corretores.")

    session = SessionLocal()
    atualizados, ja_ok, sem_match, conflitos = [], 0, [], []
    try:
        usuarios = session.query(Usuarios).all()
        # Codigo -> quem ja usa, p/ nao duplicar de-para (Lancar Imovel casa pelo codigo).
        dono_do_codigo = {
            str(u.id_imoview): (u.nome or u.username)
            for u in usuarios
            if str(u.id_imoview or "") not in CODIGOS_PLACEHOLDER
        }

        for u in usuarios:
            chave = _norm(u.nome) or _norm(u.username)
            cod = mapa.get(chave)
            if not cod:
                if _norm(u.permissao) == "corretor":
                    sem_match.append(u.nome or u.username)
                continue
            if str(u.id_imoview or "") == cod:
                ja_ok += 1
                continue
            dono = dono_do_codigo.get(cod)
            if dono and dono != (u.nome or u.username):
                conflitos.append(f"{u.nome} -> {cod} (já é de {dono})")
                continue
            u.id_imoview = cod
            dono_do_codigo[cod] = u.nome or u.username
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
    print(f"Corretores sem match na aba ({len(sem_match)}):", ", ".join(sem_match[:25]) or "—")
    if conflitos:
        print(f"Conflitos de código ({len(conflitos)}):")
        for c in conflitos:
            print("  ", c)


if __name__ == "__main__":
    main()
