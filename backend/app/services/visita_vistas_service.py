from app.database import SessionLocal
from app.models.gerente_visita_visualizada import GerenteVisitaVisualizada

# Flags de revisao do gerente por visita (alem do "visto"). Monotonicas: uma vez True,
# nunca voltam a False.
_FLAGS = ("viu_anexo", "viu_notas", "add_motivo")


def marcar_visita_vista(
    id_gerente: str,
    id_visita: str,
    viu_anexo: bool = False,
    viu_notas: bool = False,
    add_motivo: bool = False,
) -> None:
    """Upsert do registro (gerente, visita). Sempre marca como visto; liga as flags
    passadas (True) sem nunca desligar as ja ligadas."""
    novas = {"viu_anexo": bool(viu_anexo), "viu_notas": bool(viu_notas), "add_motivo": bool(add_motivo)}
    session = SessionLocal()
    try:
        row = session.query(GerenteVisitaVisualizada).filter_by(
            id_gerente=id_gerente, id_visita=id_visita
        ).first()
        if row is None:
            session.add(GerenteVisitaVisualizada(
                id_gerente=id_gerente, id_visita=id_visita, **novas
            ))
        else:
            for flag, valor in novas.items():
                if valor and not getattr(row, flag):
                    setattr(row, flag, True)
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def listar_visitas_vistas(ids_gerente: list) -> list:
    """Compat: lista de id_visita marcadas como vistas por qualquer um dos gerentes."""
    session = SessionLocal()
    try:
        rows = (
            session.query(GerenteVisitaVisualizada.id_visita)
            .filter(GerenteVisitaVisualizada.id_gerente.in_(ids_gerente))
            .all()
        )
        return list({r.id_visita for r in rows})
    finally:
        session.close()


def mapa_visitas_vistas(ids_gerente: list) -> dict:
    """{id_visita: {visto, viu_anexo, viu_notas, add_motivo}} agregando os gerentes
    informados (OR das flags). Usado pelo front p/ badges e pelo diretor."""
    session = SessionLocal()
    try:
        rows = (
            session.query(GerenteVisitaVisualizada)
            .filter(GerenteVisitaVisualizada.id_gerente.in_(ids_gerente))
            .all()
        )
    finally:
        session.close()

    mapa: dict = {}
    for r in rows:
        item = mapa.setdefault(
            r.id_visita,
            {"visto": True, "viu_anexo": False, "viu_notas": False, "add_motivo": False},
        )
        for flag in _FLAGS:
            if getattr(r, flag):
                item[flag] = True
    return mapa


def mapa_flags_por_visitas(ids_visita: list) -> dict:
    """{id_visita: {visto, viu_anexo, viu_notas, add_motivo}} pelas visitas (agrega OR
    de qualquer gerente). Usado onde o filtro natural e por visita (gestao de clientes)."""
    ids = [i for i in (ids_visita or []) if i]
    if not ids:
        return {}
    session = SessionLocal()
    try:
        rows = (
            session.query(GerenteVisitaVisualizada)
            .filter(GerenteVisitaVisualizada.id_visita.in_(ids))
            .all()
        )
    finally:
        session.close()

    mapa: dict = {}
    for r in rows:
        item = mapa.setdefault(
            r.id_visita,
            {"visto": True, "viu_anexo": False, "viu_notas": False, "add_motivo": False},
        )
        for flag in _FLAGS:
            if getattr(r, flag):
                item[flag] = True
    return mapa
