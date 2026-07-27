"""CRUD dos corretores ocultados do ranking (persistente)."""

from typing import Set, Tuple

from app.database import SessionLocal
from app.models.ranking_oculto import RankingOculto


def listar_ocultos() -> list:
    session = SessionLocal()
    try:
        return [
            {"id_corretor": o.id_corretor, "nome": o.nome}
            for o in session.query(RankingOculto).order_by(RankingOculto.nome).all()
        ]
    finally:
        session.close()


def ids_e_nomes_ocultos() -> Tuple[Set[str], Set[str]]:
    """Sets UPPER (id_corretor, nome) p/ o RankingService mesclar em _is_excluded."""
    session = SessionLocal()
    try:
        ids, nomes = set(), set()
        for o in session.query(RankingOculto).all():
            if o.id_corretor:
                ids.add(str(o.id_corretor).strip().upper())
            if o.nome:
                nomes.add(str(o.nome).strip().upper())
        return ids, nomes
    finally:
        session.close()


def ocultar(id_corretor: str, nome: str = "") -> dict:
    id_corretor = (id_corretor or "").strip()
    if not id_corretor:
        return {"ok": False, "error": "id_corretor obrigatorio"}
    session = SessionLocal()
    try:
        existe = session.query(RankingOculto).filter(RankingOculto.id_corretor == id_corretor).first()
        if existe:
            if nome and not existe.nome:
                existe.nome = nome
        else:
            session.add(RankingOculto(id_corretor=id_corretor, nome=(nome or None)))
        session.commit()
        return {"ok": True}
    except Exception as e:
        session.rollback()
        return {"ok": False, "error": str(e)}
    finally:
        session.close()


def mostrar(id_corretor: str) -> dict:
    id_corretor = (id_corretor or "").strip()
    if not id_corretor:
        return {"ok": False, "error": "id_corretor obrigatorio"}
    session = SessionLocal()
    try:
        session.query(RankingOculto).filter(RankingOculto.id_corretor == id_corretor).delete()
        session.commit()
        return {"ok": True}
    except Exception as e:
        session.rollback()
        return {"ok": False, "error": str(e)}
    finally:
        session.close()
