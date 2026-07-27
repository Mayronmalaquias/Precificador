"""Dashboard de Vendas — le da base unica `contratos` (2015 -> hoje).

resumo() : KPIs + series por mes/ano + top bairros/tipos.
listar() : lista paginada com filtros (campos-chave).
detalhe(): contrato completo (todas as colunas) agrupado p/ a tela de detalhe.
"""

from datetime import date, datetime

from sqlalchemy import func

from app.database import SessionLocal
from app.models.contrato import Contrato

_COLS = list(Contrato.__table__.columns)


def _v(val):
    if val is None:
        return None
    if isinstance(val, (date, datetime)):
        return val.isoformat()
    try:
        from decimal import Decimal
        if isinstance(val, Decimal):
            return float(val)
    except Exception:
        pass
    return val


def _aplicar_filtros(q, f):
    ano = f.get("ano")
    mes = f.get("mes")
    bairro = (f.get("bairro") or "").strip()
    tipo = (f.get("tipo") or "").strip()
    fonte = (f.get("fonte") or "").strip()
    busca = (f.get("q") or "").strip()
    if ano:
        q = q.filter(func.extract("year", Contrato.data_contrato) == int(ano))
    if mes:
        q = q.filter(func.extract("month", Contrato.data_contrato) == int(mes))
    if bairro:
        q = q.filter(Contrato.bairro.ilike(f"%{bairro}%"))
    if tipo:
        q = q.filter(Contrato.tipo.ilike(f"%{tipo}%"))
    if fonte:
        q = q.filter(Contrato.fonte == fonte)
    if busca:
        like = f"%{busca}%"
        q = q.filter(
            (Contrato.id_contrato.ilike(like))
            | (Contrato.codigo_imovel.ilike(like))
            | (Contrato.bairro.ilike(like))
            | (Contrato.corretor_venda_1_nome.ilike(like))
            | (Contrato.corretor_captador_1_nome.ilike(like))
            | (Contrato.gerente_venda_nome.ilike(like))
        )
    return q


def resumo(filtros: dict) -> dict:
    session = SessionLocal()
    try:
        base = _aplicar_filtros(session.query(Contrato), filtros)

        tot = base.with_entities(
            func.count(Contrato.id_contrato),
            func.coalesce(func.sum(Contrato.valor_negocio), 0),
            func.coalesce(func.sum(Contrato.valor_comissao), 0),
            func.coalesce(func.sum(Contrato.valor_total_61), 0),
        ).one()
        n = int(tot[0] or 0)
        vgv = float(tot[1] or 0)
        comissao = float(tot[2] or 0)
        total_61 = float(tot[3] or 0)

        mes_col = func.to_char(Contrato.data_contrato, "YYYY-MM")
        por_mes = [
            {"mes": r[0], "contratos": int(r[1]), "vgv": float(r[2] or 0), "comissao": float(r[3] or 0)}
            for r in _aplicar_filtros(session.query(
                mes_col, func.count(Contrato.id_contrato),
                func.coalesce(func.sum(Contrato.valor_negocio), 0),
                func.coalesce(func.sum(Contrato.valor_comissao), 0),
            ), filtros).filter(Contrato.data_contrato.isnot(None)).group_by(mes_col).order_by(mes_col).all()
        ]

        ano_col = func.extract("year", Contrato.data_contrato)
        por_ano = [
            {"ano": int(r[0]), "contratos": int(r[1]), "vgv": float(r[2] or 0), "comissao": float(r[3] or 0)}
            for r in _aplicar_filtros(session.query(
                ano_col, func.count(Contrato.id_contrato),
                func.coalesce(func.sum(Contrato.valor_negocio), 0),
                func.coalesce(func.sum(Contrato.valor_comissao), 0),
            ), filtros).filter(Contrato.data_contrato.isnot(None)).group_by(ano_col).order_by(ano_col).all()
        ]

        def _top(col, limite=10):
            rows = _aplicar_filtros(session.query(
                col, func.count(Contrato.id_contrato),
                func.coalesce(func.sum(Contrato.valor_negocio), 0),
            ), filtros).filter(col.isnot(None), col != "").group_by(col).order_by(
                func.count(Contrato.id_contrato).desc()
            ).limit(limite).all()
            return [{"nome": r[0], "contratos": int(r[1]), "vgv": float(r[2] or 0)} for r in rows]

        return {
            "ok": True,
            "totais": {
                "contratos": n, "vgv": vgv, "comissao": comissao, "total_61": total_61,
                "ticket_medio": (vgv / n if n else 0),
                "comissao_media_pct": (comissao / vgv * 100 if vgv else 0),
            },
            "por_mes": por_mes,
            "por_ano": por_ano,
            "por_bairro": _top(Contrato.bairro),
            "por_tipo": _top(Contrato.tipo),
        }
    finally:
        session.close()


def listar(filtros: dict, page=1, per_page=50) -> dict:
    page = max(1, int(page or 1))
    per_page = min(max(1, int(per_page or 50)), 500)
    session = SessionLocal()
    try:
        q = _aplicar_filtros(session.query(Contrato), filtros)
        total = q.count()
        rows = q.order_by(Contrato.data_contrato.desc()).offset((page - 1) * per_page).limit(per_page).all()
        def _pct_empresa(c):
            vt61 = float(c.valor_total_61 or 0)
            if not vt61:
                return None
            atr = sum(float(getattr(c, k) or 0) for k in _CAMPOS_ATRIBUIDOS)
            return round((vt61 - atr) / vt61 * 100, 2)

        items = [{
            "id_contrato": c.id_contrato,
            "contrato": c.contrato,
            "data_contrato": _v(c.data_contrato),
            "codigo_imovel": c.codigo_imovel,
            "bairro": c.bairro, "tipo": c.tipo,
            "valor_negocio": _v(c.valor_negocio),
            "valor_comissao": _v(c.valor_comissao),
            "percentual_comissao_61": _v(c.percentual_comissao_61),
            # % de cada parte
            "percentual_corretor_venda_1": _v(c.percentual_corretor_venda_1),
            "percentual_corretor_venda_2": _v(c.percentual_corretor_venda_2),
            "percentual_corretor_captacao_1": _v(c.percentual_corretor_captacao_1),
            "percentual_corretor_captacao_2": _v(c.percentual_corretor_captacao_2),
            "percentual_gerente_venda": _v(c.percentual_gerente_venda),
            "percentual_gerente_captacao": _v(c.percentual_gerente_captacao),
            "percentual_diretor": _v(c.percentual_diretor),
            "percentual_empresa_61": _pct_empresa(c),
            "corretor_venda_1_nome": c.corretor_venda_1_nome,
            "corretor_captador_1_nome": c.corretor_captador_1_nome,
            "gerente_venda_nome": c.gerente_venda_nome,
            "fonte": c.fonte,
        } for c in rows]
        return {"ok": True, "total": total, "page": page, "per_page": per_page, "items": items}
    finally:
        session.close()


# Campos $ que somam o "total atribuido" (base do %_empresa_61, igual Pag_Controle.gs)
_CAMPOS_ATRIBUIDOS = [
    "valor_gerente_venda", "valor_gerente_captacao", "valor_diretor",
    "valor_corretor_venda_1", "valor_corretor_venda_2",
    "valor_corretor_captador_1", "valor_corretor_captador_2",
]

# agrupamento das colunas p/ a tela de detalhe — espelha o relatorio "Controle" (Pag_Controle.gs)
GRUPOS_DETALHE = [
    ("Contrato", ["contrato", "id_contrato", "fonte", "data_contrato", "codigo_imovel", "bairro", "tipo", "origem_lead", "finciamento", "imobiliaria_venda", "imobiliaria_cap"]),
    ("Resumo financeiro", ["valor_negocio", "valor_comissao", "valor_total_61", "percentual_comissao_61", "nf_61_imoveis", "liquido_61", "valor_empresa_61", "percentual_empresa_61"]),
    ("Controle de pagamento — Gerência / Diretoria", ["gerente_venda_nome", "percentual_gerente_venda", "valor_gerente_venda", "gerente_captacao_nome", "percentual_gerente_captacao", "valor_gerente_captacao", "diretor_nome", "percentual_diretor", "valor_diretor"]),
    ("Controle de pagamento — Corretores", ["corretor_venda_1_nome", "percentual_corretor_venda_1", "valor_corretor_venda_1", "corretor_venda_2_nome", "percentual_corretor_venda_2", "valor_corretor_venda_2", "corretor_captador_1_nome", "percentual_corretor_captacao_1", "valor_corretor_captador_1", "corretor_captador_2_nome", "percentual_corretor_captacao_2", "valor_corretor_captador_2"]),
    ("Datas", ["data_assinatura", "data_escritura", "data_quitacao", "data_posse", "data_pagamento_sinal", "data_vistoria", "data_envio_docs_financ"]),
    ("Comissao - Parcelas", ["parcelas_comissao", "data_parcela1_comissao", "valor_parcela_comissao_1", "data_parcela2_comissao", "valor_parcela_comissao_2", "data_parcela3_comissao", "valor_parcela_comissao_3"]),
]


def detalhe(id_contrato: str) -> dict:
    session = SessionLocal()
    try:
        c = session.get(Contrato, id_contrato)
        if not c:
            return {"ok": False, "error": "contrato nao encontrado"}
        full = {col.name: _v(getattr(c, col.name)) for col in _COLS}

        # %_empresa_61 = (Valor_Total_61 - total atribuido) / Valor_Total_61  (Pag_Controle.gs)
        vt61 = float(full.get("valor_total_61") or 0)
        atribuido = sum(float(full.get(k) or 0) for k in _CAMPOS_ATRIBUIDOS)
        empresa = vt61 - atribuido
        full["valor_empresa_61"] = round(empresa, 2)
        full["percentual_empresa_61"] = round(empresa / vt61 * 100, 2) if vt61 else None

        usados = {k for _, ks in GRUPOS_DETALHE for k in ks}
        grupos = [{"titulo": t, "campos": [{"campo": k, "valor": full.get(k)} for k in ks if k in full]}
                  for t, ks in GRUPOS_DETALHE]
        # tudo que sobrou (compradores/vendedores/anexos/protocolos...) num grupo "Outros"
        outros = [{"campo": k, "valor": v} for k, v in full.items()
                  if k not in usados and k not in ("created_at", "updated_at") and v not in (None, "")]
        if outros:
            grupos.append({"titulo": "Outros", "campos": outros})
        return {"ok": True, "id_contrato": id_contrato, "grupos": grupos, "full": full}
    finally:
        session.close()
