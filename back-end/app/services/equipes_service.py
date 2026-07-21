from app.database import SessionLocal
from app.models.equipe import Equipe


def _to_dict(e: Equipe) -> dict:
    return {
        "id_equipe": e.id_equipe,
        "nome": e.nome,
        "email": e.email,
        "ativo": bool(e.ativo),
    }


def listar_equipes(incluir_inativas: bool = False) -> list:
    session = SessionLocal()
    try:
        query = session.query(Equipe)
        if not incluir_inativas:
            query = query.filter(Equipe.ativo.is_(True))
        itens = query.order_by(Equipe.nome.asc()).all()
        return [_to_dict(e) for e in itens]
    finally:
        session.close()


def criar_equipe(id_equipe: str, nome: str, email: str = None) -> dict:
    """Cria a equipe; se já existir (mesmo id), reativa e atualiza o nome."""
    session = SessionLocal()
    try:
        id_equipe = str(id_equipe or "").strip()
        nome = (nome or "").strip()
        if not id_equipe:
            raise ValueError("id_equipe é obrigatório")

        e = session.query(Equipe).filter_by(id_equipe=id_equipe).first()
        if e:
            if nome:
                e.nome = nome
            if email is not None:
                e.email = email
            e.ativo = True
        else:
            e = Equipe(id_equipe=id_equipe, nome=nome or id_equipe, email=email, ativo=True)
            session.add(e)

        session.commit()
        session.refresh(e)
        return _to_dict(e)
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def atualizar_equipe(id_equipe: str, nome=None, email=None, ativo=None) -> dict:
    session = SessionLocal()
    try:
        e = session.query(Equipe).filter_by(id_equipe=str(id_equipe or "").strip()).first()
        if not e:
            return {"ok": False, "error": "Equipe não encontrada"}

        if nome is not None:
            e.nome = nome
        if email is not None:
            e.email = email
        if ativo is not None:
            e.ativo = bool(ativo)

        session.commit()
        session.refresh(e)
        return {"ok": True, "equipe": _to_dict(e)}
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
