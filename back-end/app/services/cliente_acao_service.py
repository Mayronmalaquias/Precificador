from __future__ import annotations

from datetime import date, datetime
from typing import Any, Dict, Iterable, List, Optional

from app.database import SessionLocal
from app.models.cliente_acao import ClienteAcao


STATUS_VALIDOS = {"pendente", "a_fazer", "feita"}


def _safe_str(value: Any) -> str:
    return "" if value is None else str(value).strip()


def _parse_date(value: Any) -> date:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    text = _safe_str(value)
    if not text:
        raise ValueError("data_acao e obrigatoria")
    for fmt in ("%Y-%m-%d", "%d/%m/%Y"):
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            continue
    raise ValueError("data_acao invalida")


def _normalizar_status(value: Any) -> str:
    status = _safe_str(value) or "a_fazer"
    if status not in STATUS_VALIDOS:
        raise ValueError("status invalido")
    return status


def _status_por_data(status: str, data_acao: date | None) -> str:
    if status == "feita":
        return "feita"
    if data_acao and data_acao < date.today():
        return "pendente"
    return "a_fazer"


def _serialize(acao: ClienteAcao) -> Dict[str, Any]:
    status = _status_por_data(acao.status, acao.data_acao)
    return {
        "id": acao.id,
        "id_cliente": acao.id_cliente,
        "id_corretor": acao.id_corretor or "",
        "criado_por": acao.criado_por or "",
        "titulo": acao.titulo,
        "descricao": acao.descricao or "",
        "data_acao": acao.data_acao.isoformat() if acao.data_acao else "",
        "status": status,
        "created_at": acao.created_at.isoformat() if acao.created_at else "",
        "updated_at": acao.updated_at.isoformat() if acao.updated_at else "",
    }


def listar_acoes_clientes(ids_cliente: Iterable[str]) -> Dict[str, List[Dict[str, Any]]]:
    ids = sorted({_safe_str(item) for item in ids_cliente if _safe_str(item)})
    if not ids:
        return {}

    session = SessionLocal()
    try:
        rows = (
            session.query(ClienteAcao)
            .filter(ClienteAcao.id_cliente.in_(ids))
            .order_by(ClienteAcao.data_acao.asc(), ClienteAcao.id.asc())
            .all()
        )
        out: Dict[str, List[Dict[str, Any]]] = {id_cliente: [] for id_cliente in ids}
        for row in rows:
            out.setdefault(row.id_cliente, []).append(_serialize(row))
        return out
    finally:
        session.close()


def criar_acao_cliente(payload: Dict[str, Any]) -> Dict[str, Any]:
    id_cliente = _safe_str(payload.get("id_cliente"))
    titulo = _safe_str(payload.get("titulo"))
    if not id_cliente:
        raise ValueError("id_cliente e obrigatorio")
    if not titulo:
        raise ValueError("titulo e obrigatorio")

    data_acao = _parse_date(payload.get("data_acao"))
    status = _status_por_data(_normalizar_status(payload.get("status")), data_acao)
    acao = ClienteAcao(
        id_cliente=id_cliente,
        id_corretor=_safe_str(payload.get("id_corretor")),
        criado_por=_safe_str(payload.get("criado_por")),
        titulo=titulo,
        descricao=_safe_str(payload.get("descricao")),
        data_acao=data_acao,
        status=status,
    )

    session = SessionLocal()
    try:
        session.add(acao)
        session.commit()
        session.refresh(acao)
        return _serialize(acao)
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def atualizar_acao_cliente(acao_id: int, payload: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    session = SessionLocal()
    try:
        acao = session.get(ClienteAcao, acao_id)
        if not acao:
            return None

        if "titulo" in payload:
            titulo = _safe_str(payload.get("titulo"))
            if not titulo:
                raise ValueError("titulo e obrigatorio")
            acao.titulo = titulo
        if "descricao" in payload:
            acao.descricao = _safe_str(payload.get("descricao"))
        if "data_acao" in payload:
            acao.data_acao = _parse_date(payload.get("data_acao"))
        if "status" in payload:
            acao.status = _normalizar_status(payload.get("status"))
        acao.status = _status_por_data(acao.status, acao.data_acao)

        session.commit()
        session.refresh(acao)
        return _serialize(acao)
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
