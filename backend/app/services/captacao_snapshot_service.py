"""Snapshot diario da Jornada de Captacao + series de evolucao p/ o dashboard.

- gerar_snapshot(dia): grava o estado atual de todas as captacoes no dia.
- backfill(): reconstroi snapshots historicos a partir de created_at/data_fechamento
  (volume/equipe/corretor/bairro/endereco corretos por dia; etapa = atual, aprox p/ passado).
- evolucao(dimensao, filtros): serie temporal p/ grafico de linha.
"""

import unicodedata
from datetime import date, timedelta

from sqlalchemy import func, or_

from app.database import SessionLocal, engine
from app.models.captacao import Captacao
from app.models.captacao_snapshot import CaptacaoSnapshot

DIM_COL = {
    "equipe": CaptacaoSnapshot.team,
    "corretor": CaptacaoSnapshot.nome_corretor,
    "bairro": CaptacaoSnapshot.bairro,
    "endereco": CaptacaoSnapshot.endereco,
    "categoria": CaptacaoSnapshot.etapa_atual,
}


def _norm_key(v) -> str:
    """Chave canonica p/ agrupar variantes: trim, colapsa espacos, sem acento, MAIUSCULA."""
    s = " ".join(str(v or "").strip().split())
    if not s:
        return "—"
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode("ascii")
    return s.upper()


def _titlecase(s) -> str:
    return " ".join(w.capitalize() for w in str(s).split())


# normalizacao equivalente em SQL (upper + sem acento + colapsa espacos)
_ACENTOS = "ÁÀÂÃÄÉÈÊËÍÌÎÏÓÒÔÕÖÚÙÛÜÇáàâãäéèêëíìîïóòôõöúùûüç"
_SEM_ACENTO = "AAAAAEEEEIIIIOOOOOUUUUCaaaaaeeeeiiiiooooouuuuc"


def _sql_norm(col):
    return func.upper(func.btrim(func.regexp_replace(func.translate(func.coalesce(col, ""), _ACENTOS, _SEM_ACENTO), r"\s+", " ", "g")))


def _d(v):
    if v is None:
        return None
    if hasattr(v, "date"):
        try:
            return v.date()
        except Exception:
            pass
    return v


def gerar_snapshot(dia: date = None) -> dict:
    """Grava (idempotente) o estado atual de todas as captacoes no 'dia'."""
    dia = dia or date.today()
    session = SessionLocal()
    try:
        session.query(CaptacaoSnapshot).filter(CaptacaoSnapshot.data_snapshot == dia).delete()
        linhas = []
        for c in session.query(Captacao).all():
            linhas.append(CaptacaoSnapshot(
                data_snapshot=dia, captacao_id=c.id, team=c.team,
                id_corretor=c.id_corretor, nome_corretor=c.nome_corretor,
                bairro=c.bairro, endereco=c.endereco,
                etapa_atual=c.etapa_atual, status=c.status,
            ))
        session.add_all(linhas)
        session.commit()
        return {"ok": True, "dia": dia.isoformat(), "linhas": len(linhas)}
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def backfill() -> dict:
    """REBUILD completo dos snapshots historicos (created_at -> hoje).
    Reconstroi a ETAPA real de cada dia via captacao_historico (etapa vigente =
    ultimo evento com data <= dia). status via data_fechamento. TRUNCATE antes.
    Rodar 1x pra popular o historico; depois o cron diario mantem atualizado."""
    from app.models.captacao_historico import CaptacaoHistorico

    session = SessionLocal()
    try:
        caps = session.query(Captacao).all()
        hist = {}
        for h in (session.query(CaptacaoHistorico)
                  .order_by(CaptacaoHistorico.created_at).all()):
            if h.etapa:
                hist.setdefault(h.captacao_id, []).append((_d(h.created_at), h.etapa))
    finally:
        session.close()

    hoje = date.today()
    registros = []
    for c in caps:
        ini = _d(c.created_at) or hoje
        fim_fech = _d(c.data_fechamento)
        eventos = hist.get(c.id, [])  # [(data, etapa)] asc por created_at
        dia = ini
        while dia <= hoje:
            # etapa vigente no dia = etapa do ultimo evento com data <= dia
            etapa = None
            for ed, et in eventos:
                if ed and ed <= dia:
                    etapa = et
                elif ed and ed > dia:
                    break
            if not etapa:
                etapa = c.etapa_atual or "escolha"
            status = "fechado" if (fim_fech and dia >= fim_fech) else (
                c.status if (c.status and c.status != "fechado") else "ativo")
            registros.append((dia, c.id, c.team, c.id_corretor, c.nome_corretor,
                              c.bairro, c.endereco, etapa, status))
            dia += timedelta(days=1)

    with engine.begin() as conn:
        conn.exec_driver_sql("TRUNCATE TABLE captacao_snapshot RESTART IDENTITY")

    if not registros:
        return {"ok": True, "linhas": 0}

    raw = engine.raw_connection()
    try:
        from psycopg2.extras import execute_values
        cur = raw.cursor()
        execute_values(
            cur,
            """INSERT INTO captacao_snapshot
               (data_snapshot, captacao_id, team, id_corretor, nome_corretor,
                bairro, endereco, etapa_atual, status)
               VALUES %s
               ON CONFLICT (data_snapshot, captacao_id) DO NOTHING""",
            registros,
            page_size=1000,
        )
        raw.commit()
    finally:
        raw.close()
    return {"ok": True, "linhas": len(registros)}


def _aplicar_filtros(q, f):
    if f.get("equipe"):
        q = q.filter(CaptacaoSnapshot.team == f["equipe"])
    if f.get("corretor"):
        # valor vem do dropdown ja normalizado (_norm_key)
        q = q.filter(_sql_norm(CaptacaoSnapshot.nome_corretor) == _norm_key(f["corretor"]))
    if f.get("bairro"):
        q = q.filter(_sql_norm(CaptacaoSnapshot.bairro) == _norm_key(f["bairro"]))
    if f.get("endereco"):
        q = q.filter(CaptacaoSnapshot.endereco.ilike(f"%{f['endereco']}%"))
    if f.get("categoria"):
        q = q.filter(CaptacaoSnapshot.etapa_atual == f["categoria"])
    if f.get("status"):
        q = q.filter(CaptacaoSnapshot.status == f["status"])
    if f.get("data_de"):
        q = q.filter(CaptacaoSnapshot.data_snapshot >= f["data_de"])
    if f.get("data_ate"):
        q = q.filter(CaptacaoSnapshot.data_snapshot <= f["data_ate"])
    return q


def evolucao(dimensao: str, filtros: dict, max_series: int = 12, por_estado: bool = False) -> dict:
    dimensao = (dimensao or "equipe").lower()
    col = DIM_COL.get(dimensao, CaptacaoSnapshot.team)
    # "por_estado" quebra cada grupo por etapa (linha "GRUPO — etapa"); irrelevante se ja e categoria
    split = por_estado and dimensao != "categoria"

    session = SessionLocal()
    try:
        cols = [CaptacaoSnapshot.data_snapshot, col.label("grupo")]
        group_cols = [CaptacaoSnapshot.data_snapshot, col]
        if split:
            cols.append(CaptacaoSnapshot.etapa_atual.label("etapa"))
            group_cols.append(CaptacaoSnapshot.etapa_atual)
        cols.append(func.count(func.distinct(CaptacaoSnapshot.captacao_id)))

        q = session.query(*cols)
        q = _aplicar_filtros(q, filtros)
        # Esconde equipes desativadas (ativo=False) do grafico por equipe — mesma regra do opcoes().
        if dimensao == "equipe":
            from app.models.equipe import Equipe
            inativas = [
                row[0]
                for row in session.query(Equipe.id_equipe).filter(Equipe.ativo.is_(False)).all()
            ]
            if inativas:
                q = q.filter(or_(
                    CaptacaoSnapshot.team.is_(None),
                    CaptacaoSnapshot.team.notin_(inativas),
                ))
        q = q.group_by(*group_cols).order_by(CaptacaoSnapshot.data_snapshot)
        rows = q.all()
    finally:
        session.close()

    datas = sorted({r[0].isoformat() for r in rows})

    totais = {}
    valores = {}
    votos_label = {}
    etapa_de = {}
    for r in rows:
        if split:
            data_s, grupo, etapa, qtd = r
        else:
            data_s, grupo, qtd = r
            etapa = None
        base_k = _norm_key(grupo)
        k = f"{base_k}|{etapa}" if split else base_k
        orig = " ".join(str(grupo or "").strip().split()) or "—"
        qtd = int(qtd)
        d = data_s.isoformat()
        totais[k] = totais.get(k, 0) + qtd
        valores[(k, d)] = valores.get((k, d), 0) + qtd
        vl = votos_label.setdefault(k, {})
        vl[orig] = vl.get(orig, 0) + qtd
        if split:
            etapa_de[k] = etapa or "—"

    labels = {}
    for k, v in votos_label.items():
        base = k.split("|")[0]
        nome = f"(sem {dimensao})" if base == "—" else _titlecase(max(v, key=v.get))
        labels[k] = f"{nome} — {etapa_de[k]}" if split else nome
    ordenados = sorted(totais, key=lambda k: -totais[k])
    principais = ordenados[:max_series]
    outros = ordenados[max_series:]

    series = []
    for k in principais:
        series.append({"nome": labels.get(k, k), "pontos": [valores.get((k, d), 0) for d in datas]})
    if outros:
        pontos = [sum(valores.get((k, d), 0) for k in outros) for d in datas]
        series.append({"nome": "Outros", "pontos": pontos})

    return {"ok": True, "dimensao": dimensao, "datas": datas, "series": series}


def opcoes(equipe: str = None) -> dict:
    """Listas distintas p/ os dropdowns de filtro (equipe, corretor, bairro).
    Se 'equipe' for passada (gerente), restringe corretores/bairros a essa equipe."""
    equipe = (equipe or "").strip() or None
    session = SessionLocal()
    try:
        if equipe:
            equipes = [equipe]
        else:
            equipes = sorted({
                (r[0] or "").strip()
                for r in session.query(CaptacaoSnapshot.team).distinct().all()
                if r[0] and str(r[0]).strip()
            })

        def _dedup(col):
            porkey = {}
            q = session.query(col).distinct()
            if equipe:
                q = q.filter(CaptacaoSnapshot.team == equipe)
            for (val,) in q.all():
                if not val or not str(val).strip():
                    continue
                k = _norm_key(val)
                porkey.setdefault(k, str(val).strip())
            return sorted(
                [{"value": k, "label": _titlecase(v)} for k, v in porkey.items()],
                key=lambda x: x["label"],
            )

        # Esconde equipes desativadas (ativo=False no cadastro de equipes).
        from app.models.equipe import Equipe
        inativas = {
            row[0]
            for row in session.query(Equipe.id_equipe).filter(Equipe.ativo.is_(False)).all()
        }
        equipes = [e for e in equipes if e not in inativas]

        return {
            "ok": True,
            "equipes": [{"value": e, "label": e} for e in equipes],
            "corretores": _dedup(CaptacaoSnapshot.nome_corretor),
            "bairros": _dedup(CaptacaoSnapshot.bairro),
        }
    finally:
        session.close()
