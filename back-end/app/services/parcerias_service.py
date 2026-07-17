"""CRUD das parcerias da 61 com imobiliarias/corretores (persistente)."""

from datetime import datetime

from app.database import SessionLocal
from app.models.parceria import Parceria


def _norm_bool(v, default=False):
    if v is None:
        return default
    if isinstance(v, bool):
        return v
    return str(v).strip().lower() in ("1", "true", "sim", "yes", "on")


def _norm_txt(v):
    s = (str(v).strip() if v is not None else "")
    return s or None


def listar():
    session = SessionLocal()
    try:
        rows = session.query(Parceria).order_by(Parceria.nome).all()
        return [p.to_dict() for p in rows]
    finally:
        session.close()


def criar(payload: dict) -> dict:
    nome = (payload.get("nome") or "").strip()
    if not nome:
        return {"ok": False, "error": "nome é obrigatório"}

    session = SessionLocal()
    try:
        existe = session.query(Parceria).filter(Parceria.nome.ilike(nome)).first()
        if existe:
            return {"ok": False, "error": f'Já existe parceria "{nome}".'}

        p = Parceria(
            nome=nome,
            percentual=_norm_txt(payload.get("percentual")),
            faz_parceria=_norm_bool(payload.get("faz_parceria"), default=True),
            tem_contrato=_norm_bool(payload.get("tem_contrato"), default=False),
            observacao=_norm_txt(payload.get("observacao")),
        )
        session.add(p)
        session.commit()
        return {"ok": True, "parceria": p.to_dict()}
    except Exception as e:
        session.rollback()
        return {"ok": False, "error": str(e)}
    finally:
        session.close()


def atualizar(parceria_id: int, payload: dict) -> dict:
    session = SessionLocal()
    try:
        p = session.query(Parceria).filter(Parceria.id == parceria_id).first()
        if not p:
            return {"ok": False, "error": "parceria não encontrada"}

        if "nome" in payload:
            novo_nome = (payload.get("nome") or "").strip()
            if not novo_nome:
                return {"ok": False, "error": "nome não pode ser vazio"}
            conflito = (
                session.query(Parceria)
                .filter(Parceria.nome.ilike(novo_nome), Parceria.id != parceria_id)
                .first()
            )
            if conflito:
                return {"ok": False, "error": f'Já existe parceria "{novo_nome}".'}
            p.nome = novo_nome

        if "percentual" in payload:
            p.percentual = _norm_txt(payload.get("percentual"))
        if "faz_parceria" in payload:
            p.faz_parceria = _norm_bool(payload.get("faz_parceria"), default=p.faz_parceria)
        if "tem_contrato" in payload:
            p.tem_contrato = _norm_bool(payload.get("tem_contrato"), default=p.tem_contrato)
        if "observacao" in payload:
            p.observacao = _norm_txt(payload.get("observacao"))

        p.atualizado_em = datetime.utcnow()
        session.commit()
        return {"ok": True, "parceria": p.to_dict()}
    except Exception as e:
        session.rollback()
        return {"ok": False, "error": str(e)}
    finally:
        session.close()


def remover(parceria_id: int) -> dict:
    session = SessionLocal()
    try:
        n = session.query(Parceria).filter(Parceria.id == parceria_id).delete()
        session.commit()
        if not n:
            return {"ok": False, "error": "parceria não encontrada"}
        return {"ok": True}
    except Exception as e:
        session.rollback()
        return {"ok": False, "error": str(e)}
    finally:
        session.close()
