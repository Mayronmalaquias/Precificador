"""Sync da tabela `contratos` a partir da planilha Google (aba 'Vendas').

One-way: Sheet -> DB (a planilha e a fonte da verdade). Upsert por id_contrato:
insere novos, atualiza existentes. NAO apaga linhas que sumiram da planilha
(seguranca; ver `removidos_na_planilha` no resumo).

Reusa: google_service.get_services (auth SA), Contrato.HEADER_POR_SLUG (mapa
coluna-da-planilha -> atributo do model), parsers de admin_bases_service.
Headers da planilha vem com espaco extra -> comparacao sempre via strip().
"""

import os
from datetime import datetime

from app.database import SessionLocal
from app.models.contrato import Contrato, HEADER_POR_SLUG
from app.services.admin_bases_service import parse_date_any, to_float, to_str
from app.services.google_service import get_services

SHEET_ID = os.getenv("GSHEET_VENDAS_ID", "1GLYIVuOG0heAXKxL5MdtjNxlR7o9N8BaWuvwHF9Jb0Y")
ABA = os.getenv("GSHEET_ABA_VENDAS", "Vendas")
ID_HEADERS = ("Id_Contrato", "IdContrato", "ID_Contrato")

# tipo de cada coluna do model (pra parsear certo)
_COL_TYPE = {slug: type(Contrato.__table__.columns[slug].type).__name__ for slug in HEADER_POR_SLUG}


def _parse(slug, raw):
    t = _COL_TYPE.get(slug)
    if t == "Date":
        return parse_date_any(raw)
    if t in ("Numeric", "DECIMAL"):
        s = to_str(raw)
        return to_float(s) if s else None
    s = to_str(raw)
    return s or None


def _ler_planilha():
    sheets, _, _ = get_services()
    res = sheets.values().get(spreadsheetId=SHEET_ID, range=f"{ABA}!A1:ZZ").execute()
    return res.get("values", [])


def sync_contratos_from_sheet(criado_por=None) -> dict:
    valores = _ler_planilha()
    if not valores:
        return {"ok": False, "error": "Planilha vazia ou inacessivel"}

    header = [str(h).strip() for h in valores[0]]
    idx = {}
    for i, h in enumerate(header):
        idx.setdefault(h, i)  # primeira ocorrencia

    id_col = next((h for h in ID_HEADERS if h in idx), None)
    if not id_col:
        return {"ok": False, "error": f"Coluna de id nao encontrada (esperado um de {ID_HEADERS})"}
    id_i = idx[id_col]

    # mapa slug -> indice na planilha (via header normalizado)
    slug_idx = {slug: idx[h.strip()] for slug, h in HEADER_POR_SLUG.items() if h.strip() in idx}

    resumo = {"ok": True, "linhas_planilha": len(valores) - 1, "inseridos": 0,
              "atualizados": 0, "ignorados": 0, "erros": []}
    ncols = len(header)

    # monta registros dedupando por id_contrato (ultima ocorrencia vence)
    por_id = {}
    for n, row in enumerate(valores[1:], start=2):
        row = list(row) + [""] * (ncols - len(row))
        id_contrato = to_str(row[id_i]) if id_i < len(row) else ""
        if not id_contrato:
            resumo["ignorados"] += 1
            continue
        try:
            dados = {slug: _parse(slug, row[i]) for slug, i in slug_idx.items()}
            dados["id_contrato"] = id_contrato
            dados["fonte"] = "planilha"
            por_id[id_contrato] = dados
        except Exception as e:
            resumo["erros"].append(f"linha {n} ({id_contrato}): {e}")

    registros = list(por_id.values())
    ids_planilha = set(por_id.keys())

    session = SessionLocal()
    try:
        # ids ja existentes (p/ contar inseridos x atualizados e "removidos")
        existentes = {c.id_contrato: (c.fonte or "") for c in session.query(Contrato.id_contrato, Contrato.fonte).all()}

        if registros:
            from sqlalchemy.dialects.postgresql import insert as pg_insert
            cols_upd = [k for k in registros[0].keys() if k not in ("id_contrato", "created_at")]
            stmt = pg_insert(Contrato.__table__).values(registros)
            stmt = stmt.on_conflict_do_update(
                index_elements=["id_contrato"],
                set_={k: getattr(stmt.excluded, k) for k in cols_upd},
            )
            session.execute(stmt)
            session.commit()

        resumo["inseridos"] = sum(1 for i in ids_planilha if i not in existentes)
        resumo["atualizados"] = len(registros) - resumo["inseridos"]
        removidos = {i for i, f in existentes.items() if f == "planilha"} - ids_planilha
        resumo["removidos_na_planilha"] = sorted(removidos)[:50]
        resumo["qtd_removidos_na_planilha"] = len(removidos)
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()

    resumo["sincronizado_em"] = datetime.utcnow().isoformat()
    return resumo
