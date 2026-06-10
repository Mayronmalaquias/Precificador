from app.database import SessionLocal
from app.models.gerente_visita_visualizada import GerenteVisitaVisualizada


def marcar_visita_vista(id_gerente: str, id_visita: str) -> None:
    session = SessionLocal()
    try:
        exists = session.query(GerenteVisitaVisualizada).filter_by(
            id_gerente=id_gerente, id_visita=id_visita
        ).first()
        if not exists:
            session.add(GerenteVisitaVisualizada(id_gerente=id_gerente, id_visita=id_visita))
            session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def listar_visitas_vistas(id_gerente: str) -> list:
    session = SessionLocal()
    try:
        rows = (
            session.query(GerenteVisitaVisualizada.id_visita)
            .filter_by(id_gerente=id_gerente)
            .all()
        )
        return [r.id_visita for r in rows]
    finally:
        session.close()
