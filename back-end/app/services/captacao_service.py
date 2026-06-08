from datetime import date, datetime

from app.database import SessionLocal
from app.models.captacao import Captacao
from app.models.captacao_historico import CaptacaoHistorico

ETAPA_LABELS = {
    "escolha":      "Escolha",
    "prospeccao":   "Prospecção",
    "interacao":    "Interação",
    "apresentacao": "Apresentação",
    "captacao":     "Captação",
}


def _d(val):
    if val is None:
        return None
    if isinstance(val, (date, datetime)):
        return val.isoformat()
    return val


def _parse_date(val):
    if val is None or val == "":
        return None
    if isinstance(val, datetime):
        return val.date()
    if isinstance(val, date):
        return val
    try:
        return datetime.strptime(str(val)[:10], "%Y-%m-%d").date()
    except (ValueError, TypeError):
        return None


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


def _hist_dict(h: CaptacaoHistorico) -> dict:
    return {
        "id": h.id,
        "captacao_id": h.captacao_id,
        "etapa": h.etapa,
        "tipo": h.tipo,
        "descricao": h.descricao,
        "data_acao": _d(h.data_acao),
        "created_at": _d(h.created_at),
    }


def _add_hist(session, captacao_id, etapa, tipo, descricao, data_acao=None):
    session.add(CaptacaoHistorico(
        captacao_id=captacao_id,
        etapa=etapa,
        tipo=tipo,
        descricao=descricao,
        data_acao=_parse_date(data_acao),
    ))


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
            link_anuncio=data.get("link_anuncio") or None,
            etapa_atual=data.get("etapa_atual", "escolha"),
            data_entrada_etapa=datetime.now(),
            tem_numero=data.get("tem_numero"),
            acao_sem_numero=data.get("acao_sem_numero") or None,
            data_acao_sem_numero=data.get("data_acao_sem_numero") or None,
            numero_imovel=data.get("numero_imovel") or None,
        )
        session.add(c)
        session.flush()

        _add_hist(session, c.id, "escolha", "inicio", "Imóvel lançado na jornada")

        if c.acao_sem_numero:
            _add_hist(session, c.id, "escolha", "acao",
                      c.acao_sem_numero, c.data_acao_sem_numero)

        if c.etapa_atual == "prospeccao":
            _add_hist(session, c.id, "prospeccao", "avanco",
                      "Avançou para Prospecção")

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


def listar_historico(captacao_id: int) -> dict:
    session = SessionLocal()
    try:
        items = (
            session.query(CaptacaoHistorico)
            .filter_by(captacao_id=captacao_id)
            .order_by(CaptacaoHistorico.created_at.asc(), CaptacaoHistorico.id.asc())
            .all()
        )
        return {"ok": True, "historico": [_hist_dict(h) for h in items]}
    finally:
        session.close()


def atualizar_captacao(captacao_id: int, data: dict) -> dict:
    session = SessionLocal()
    try:
        c = session.query(Captacao).filter_by(id=captacao_id).first()
        if not c:
            return {"ok": False, "error": "Captacao nao encontrada"}

        etapa_anterior = c.etapa_atual
        hist = []  # list of (etapa, tipo, descricao, data_acao)

        # ── Escolha ──
        nova_acao_escolha = data.get("acao_sem_numero")
        if nova_acao_escolha and nova_acao_escolha != c.acao_sem_numero:
            hist.append(("escolha", "acao", nova_acao_escolha,
                         data.get("data_acao_sem_numero")))

        if data.get("acao_escolha_realizada") is True and c.acao_escolha_realizada is not True:
            hist.append(("escolha", "realizada",
                         f"Ação realizada: {c.acao_sem_numero or ''}", None))

        # ── Prospecção ──
        nova_acao_int = data.get("proxima_acao_interacao")
        if nova_acao_int and nova_acao_int != c.proxima_acao_interacao:
            hist.append(("prospeccao", "acao", nova_acao_int,
                         data.get("data_proxima_acao_interacao")))

        if data.get("acao_interacao_realizada") is True and c.acao_interacao_realizada is not True:
            hist.append(("prospeccao", "realizada",
                         f"Ação realizada: {c.proxima_acao_interacao or ''}", None))

        novo_nome = data.get("nome_cliente")
        if novo_nome and novo_nome != c.nome_cliente:
            hist.append(("prospeccao", "dado", f"Proprietário: {novo_nome}", None))

        if "book_enviado" in data and data["book_enviado"] is not None and data["book_enviado"] != c.book_enviado:
            hist.append(("prospeccao", "book",
                         "Book enviado ao cliente" if data["book_enviado"] else "Book não enviado",
                         None))

        # ── Prospecção (motivo_nao_interacao vem do SecaoAvanco de prospecção) ──
        novo_motivo_int = data.get("motivo_nao_interacao")
        if novo_motivo_int and novo_motivo_int != c.motivo_nao_interacao:
            hist.append(("prospeccao", "objecao", novo_motivo_int, None))

        # ── Interação (proxima_acao_apresentacao + motivo_nao_apresentacao vêm do SecaoAvanco de interação) ──
        novo_motivo_apr = data.get("motivo_nao_apresentacao")
        if novo_motivo_apr and novo_motivo_apr != c.motivo_nao_apresentacao:
            hist.append(("interacao", "objecao", novo_motivo_apr, None))

        nova_acao_apr = data.get("proxima_acao_apresentacao")
        if nova_acao_apr and nova_acao_apr != c.proxima_acao_apresentacao:
            hist.append(("interacao", "acao", nova_acao_apr,
                         data.get("data_proxima_acao_apresentacao")))

        if data.get("acao_apresentacao_realizada") is True and c.acao_apresentacao_realizada is not True:
            hist.append(("interacao", "realizada",
                         f"Ação realizada: {c.proxima_acao_apresentacao or ''}", None))

        # ── Apresentação / Captação (proxima_acao_captacao e objecao_captacao) ──
        nova_acao_cap = data.get("proxima_acao_captacao")
        if nova_acao_cap and nova_acao_cap != c.proxima_acao_captacao:
            etapa_acao = etapa_anterior if etapa_anterior in ("apresentacao", "captacao") else "apresentacao"
            hist.append((etapa_acao, "acao", nova_acao_cap,
                         data.get("data_proxima_acao_captacao")))

        if data.get("acao_captacao_realizada") is True and c.acao_captacao_realizada is not True:
            etapa_real = etapa_anterior if etapa_anterior in ("apresentacao", "captacao") else "captacao"
            hist.append((etapa_real, "realizada",
                         f"Ação realizada: {c.proxima_acao_captacao or ''}", None))

        novo_obj_cap = data.get("objecao_captacao")
        if novo_obj_cap and novo_obj_cap != c.objecao_captacao:
            etapa_obj = etapa_anterior if etapa_anterior in ("apresentacao", "captacao") else "apresentacao"
            hist.append((etapa_obj, "objecao", novo_obj_cap, None))

        if data.get("captou_imovel") is True and c.captou_imovel is not True:
            hist.append(("captacao", "captado", "Imóvel captado com sucesso!", None))

        # ── Aplica todos os campos ──
        campos = [
            "status", "endereco", "bairro", "bloco", "link_anuncio",
            "tem_numero", "acao_sem_numero", "data_acao_sem_numero", "acao_escolha_realizada",
            "nome_cliente", "telefone_cliente", "numero_imovel", "book_enviado",
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

        if "etapa_atual" in data:
            nova_etapa = data["etapa_atual"]
            _set_val(c, "etapa_atual", nova_etapa)
            if nova_etapa != etapa_anterior:
                c.data_entrada_etapa = datetime.now()
                hist.append((nova_etapa, "avanco",
                             f"Avançou para {ETAPA_LABELS.get(nova_etapa, nova_etapa)}", None))

        c.updated_at = datetime.now()
        session.commit()
        session.refresh(c)

        for etapa, tipo, descricao, data_acao in hist:
            _add_hist(session, captacao_id, etapa, tipo, descricao, data_acao)
        if hist:
            session.commit()

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

        _add_hist(session, captacao_id, c.etapa_atual, "fechamento",
                  f"Encerrado: {motivo}", c.data_fechamento)
        session.commit()

        return {"ok": True, "captacao": _to_dict(c)}
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
