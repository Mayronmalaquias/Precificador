from datetime import date, datetime

from app.database import SessionLocal
from app.models.captacao import Captacao


def _d(val):
    if val is None:
        return None
    if isinstance(val, (date, datetime)):
        return val.isoformat()
    return val


def _to_dict(c: Captacao) -> dict:
    return {
        "id": c.id,
        "id_corretor": c.id_corretor,
        "nome_corretor": c.nome_corretor,
        "team": c.team,
        "endereco": c.endereco,
        "bairro": c.bairro,
        "bloco": c.bloco,
        "etapa_atual": c.etapa_atual,
        "status": c.status,
        "motivo_fechamento": c.motivo_fechamento,
        "data_fechamento": _d(c.data_fechamento),
        "data_entrada_etapa": _d(c.data_entrada_etapa),
        "tem_numero": c.tem_numero,
        "acao_sem_numero": c.acao_sem_numero,
        "data_acao_sem_numero": _d(c.data_acao_sem_numero),
        "acao_escolha_realizada": c.acao_escolha_realizada,
        "nome_cliente": c.nome_cliente,
        "telefone_cliente": c.telefone_cliente,
        "numero_imovel": c.numero_imovel,
        "book_enviado": c.book_enviado,
        "link_anuncio": c.link_anuncio,
        "falou_proprietario": c.falou_proprietario,
        "motivo_nao_interacao": c.motivo_nao_interacao,
        "proxima_acao_interacao": c.proxima_acao_interacao,
        "data_proxima_acao_interacao": _d(c.data_proxima_acao_interacao),
        "acao_interacao_realizada": c.acao_interacao_realizada,
        "visitou_imovel": c.visitou_imovel,
        "motivo_nao_apresentacao": c.motivo_nao_apresentacao,
        "proxima_acao_apresentacao": c.proxima_acao_apresentacao,
        "data_proxima_acao_apresentacao": _d(c.data_proxima_acao_apresentacao),
        "acao_apresentacao_realizada": c.acao_apresentacao_realizada,
        "captou_imovel": c.captou_imovel,
        "objecao_captacao": c.objecao_captacao,
        "proxima_acao_captacao": c.proxima_acao_captacao,
        "data_proxima_acao_captacao": _d(c.data_proxima_acao_captacao),
        "acao_captacao_realizada": c.acao_captacao_realizada,
        "created_at": _d(c.created_at),
        "updated_at": _d(c.updated_at),
    }


def _set_val(obj, campo, val):
    setattr(obj, campo, val if val != "" else None)


def criar_captacao(data: dict) -> dict:
    session = SessionLocal()
    try:
        c = Captacao(
            id_corretor=data["id_corretor"],
            nome_corretor=data.get("nome_corretor"),
            team=data.get("team") or None,
            endereco=data["endereco"],
            bairro=data.get("bairro") or None,
            bloco=data.get("bloco") or None,
            etapa_atual=data.get("etapa_atual", "escolha"),
            data_entrada_etapa=datetime.now(),
            tem_numero=data.get("tem_numero"),
            acao_sem_numero=data.get("acao_sem_numero") or None,
            data_acao_sem_numero=data.get("data_acao_sem_numero") or None,
            numero_imovel=data.get("numero_imovel") or None,
        )
        session.add(c)
        session.commit()
        session.refresh(c)
        return {"ok": True, "captacao": _to_dict(c)}
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def listar_captacoes_corretor(id_corretor: str) -> dict:
    session = SessionLocal()
    try:
        items = (
            session.query(Captacao)
            .filter_by(id_corretor=id_corretor)
            .order_by(Captacao.updated_at.desc())
            .all()
        )
        return {"ok": True, "captacoes": [_to_dict(c) for c in items]}
    finally:
        session.close()


def listar_captacoes_gerente(team: str = None) -> dict:
    session = SessionLocal()
    try:
        q = session.query(Captacao)
        if team:
            q = q.filter_by(team=team)
        items = q.order_by(Captacao.updated_at.desc()).all()
        return {"ok": True, "captacoes": [_to_dict(c) for c in items]}
    finally:
        session.close()


def obter_captacao(captacao_id: int) -> dict:
    session = SessionLocal()
    try:
        c = session.query(Captacao).filter_by(id=captacao_id).first()
        if not c:
            return {"ok": False, "error": "Captacao nao encontrada"}
        return {"ok": True, "captacao": _to_dict(c)}
    finally:
        session.close()


def atualizar_captacao(captacao_id: int, data: dict) -> dict:
    session = SessionLocal()
    try:
        c = session.query(Captacao).filter_by(id=captacao_id).first()
        if not c:
            return {"ok": False, "error": "Captacao nao encontrada"}

        etapa_anterior = c.etapa_atual

        campos = [
            "status", "endereco", "bairro", "bloco",
            "tem_numero", "acao_sem_numero", "data_acao_sem_numero", "acao_escolha_realizada",
            "nome_cliente", "telefone_cliente", "numero_imovel", "book_enviado", "link_anuncio",
            "falou_proprietario", "motivo_nao_interacao", "proxima_acao_interacao",
            "data_proxima_acao_interacao", "acao_interacao_realizada",
            "visitou_imovel", "motivo_nao_apresentacao", "proxima_acao_apresentacao",
            "data_proxima_acao_apresentacao", "acao_apresentacao_realizada",
            "captou_imovel", "objecao_captacao", "proxima_acao_captacao",
            "data_proxima_acao_captacao", "acao_captacao_realizada",
        ]
        for campo in campos:
            if campo in data:
                _set_val(c, campo, data[campo])

        # etapa_atual separado: se mudou, atualiza data_entrada_etapa
        if "etapa_atual" in data:
            nova_etapa = data["etapa_atual"]
            _set_val(c, "etapa_atual", nova_etapa)
            if nova_etapa != etapa_anterior:
                c.data_entrada_etapa = datetime.now()

        c.updated_at = datetime.now()
        session.commit()
        session.refresh(c)
        return {"ok": True, "captacao": _to_dict(c)}
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def fechar_captacao(captacao_id: int, motivo: str) -> dict:
    session = SessionLocal()
    try:
        c = session.query(Captacao).filter_by(id=captacao_id).first()
        if not c:
            return {"ok": False, "error": "Captacao nao encontrada"}
        c.status = "fechado"
        c.motivo_fechamento = motivo
        c.data_fechamento = date.today()
        c.updated_at = datetime.now()
        session.commit()
        session.refresh(c)
        return {"ok": True, "captacao": _to_dict(c)}
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
