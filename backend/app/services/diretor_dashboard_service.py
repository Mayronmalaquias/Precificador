from datetime import date, datetime, timedelta
from decimal import Decimal, InvalidOperation
from functools import lru_cache
from pathlib import Path
import re

import pandas as pd
from sqlalchemy import and_, func, or_

from app.database import SessionLocal
from app.extensions import cache
from app.models.captacao import Captacao
from app.models.captacao_historico import CaptacaoHistorico
from app.models.contrato import Contrato
from app.models.dfimoveis_acesso import DfImoveisAcesso
from app.models.equipe import Equipe
from app.models.estoque_legado import LeadLegado
from app.models.gerente_visita_visualizada import GerenteVisitaVisualizada
from app.models.legado_diversos import CampanhaLegado
from app.models.usuarios import Usuarios
from app.models.visita import Visita


def _date(value, default):
    try:
        return datetime.strptime(str(value)[:10], "%Y-%m-%d").date()
    except (TypeError, ValueError):
        return default


def _number(value):
    if value in (None, ""):
        return 0.0
    text = str(value).strip().replace("R$", "").replace(" ", "")
    if "," in text:
        text = text.replace(".", "").replace(",", ".")
    try:
        return float(Decimal(text))
    except (InvalidOperation, ValueError):
        return 0.0


def _norm_proposta(value):
    value = str(value or "").strip().lower()
    if value in {"sim", "s", "aceita", "aceito"}:
        return "sim"
    if value in {"não", "nao", "n", "recusada", "recusado"}:
        return "nao"
    if value in {"talvez", "negociação", "negociacao"}:
        return "talvez"
    return None


def _pct(current, previous):
    if not previous:
        return None
    return round((current - previous) / previous * 100, 1)


def _period_query(query, column, start, end):
    return query.filter(column >= start, column <= end)


def _team_maps(session):
    teams = session.query(Equipe).filter(Equipe.ativo.is_(True)).order_by(Equipe.nome).all()
    managers = session.query(Usuarios).filter(
        Usuarios.ativo.is_(True), func.lower(Usuarios.permissao) == "gerente"
    ).all()
    manager_by_team = {str(u.team or ""): u for u in managers}
    result = []
    for team in teams:
        manager = manager_by_team.get(team.id_equipe)
        result.append({
            "id": team.id_equipe,
            "nome": team.nome or team.id_equipe,
            "gerente": manager.nome if manager else "Sem gerente cadastrado",
            "gerente_id": manager.id_usuarios if manager else None,
        })
    return result


def _team_user_ids(session, team):
    query = session.query(Usuarios.id_usuarios).filter(Usuarios.ativo.is_(True))
    if team:
        query = query.filter(Usuarios.team == team)
    return [row[0] for row in query.all() if row[0]]


def _visit_metrics(session, teams, start, end, selected_team=None):
    selected = [t for t in teams if not selected_team or t["id"] == selected_team]
    selected_ids = {team["id"] for team in selected}
    counts_by_team = {team["id"]: {"visitas": 0, "sim": 0, "nao": 0, "talvez": 0} for team in selected}
    proposals = {"sim": 0, "nao": 0, "talvez": 0}
    query = session.query(Visita.proposta, Usuarios.team).join(
        Usuarios, Usuarios.id_usuarios == Visita.id_corretor
    ).filter(Visita.data_visita >= start, Visita.data_visita <= end)
    if selected_team:
        query = query.filter(Usuarios.team == selected_team)
    for proposal, team_id in query.all():
        if team_id not in selected_ids:
            continue
        counts_by_team[team_id]["visitas"] += 1
        status = _norm_proposta(proposal)
        if status:
            counts_by_team[team_id][status] += 1
            proposals[status] += 1
    rows = [{**team, **counts_by_team[team["id"]]} for team in selected]
    return rows, proposals


def _sales(session, start, end, selected_team, teams):
    query = _period_query(session.query(Contrato), Contrato.data_contrato, start, end)
    recent_query = session.query(Contrato).filter(Contrato.data_contrato.isnot(None))
    selected = next((t for t in teams if t["id"] == selected_team), None)
    if selected and selected["gerente"] != "Sem gerente cadastrado":
        manager = selected["gerente"]
        query = query.filter(or_(Contrato.gerente_venda_nome.ilike(manager), Contrato.gerente_captacao_nome.ilike(manager)))
        recent_query = recent_query.filter(or_(Contrato.gerente_venda_nome.ilike(manager), Contrato.gerente_captacao_nome.ilike(manager)))
    rows = recent_query.order_by(Contrato.data_contrato.desc(), Contrato.created_at.desc()).limit(8).all()
    total = float(query.with_entities(func.coalesce(func.sum(Contrato.valor_negocio), 0)).scalar() or 0)
    manager_team = {str(item["gerente"] or "").strip().casefold(): item["nome"] for item in teams}
    items = [{
        "id": row.id_contrato,
        "imovel": " · ".join(v for v in (row.bairro, row.tipo) if v) or "Imóvel sem descrição",
        "codigo": row.codigo_imovel or row.id_contrato,
        "equipe": selected["nome"] if selected else manager_team.get(str(row.gerente_venda_nome or row.gerente_captacao_nome or "").strip().casefold(), "Não identificada"),
        "gerente": row.gerente_venda_nome or row.gerente_captacao_nome or "Não informado",
        "valor": float(row.valor_negocio or 0),
        "valor_total_61": float(row.valor_total_61 or 0),
        "data": row.data_contrato.isoformat() if row.data_contrato else None,
    } for row in rows]
    return total, query.count(), items


def _captation(session, start, end, selected_team):
    base = session.query(Captacao)
    if selected_team:
        base = base.filter(Captacao.team == selected_team)
    worked = base.filter(Captacao.updated_at >= datetime.combine(start, datetime.min.time()), Captacao.updated_at <= datetime.combine(end, datetime.max.time())).count()
    captured = base.filter(Captacao.captou_imovel.is_(True), Captacao.updated_at >= datetime.combine(start, datetime.min.time()), Captacao.updated_at <= datetime.combine(end, datetime.max.time())).count()
    ids = [row[0] for row in base.with_entities(Captacao.id).all()]
    stages = []
    for key, label in (("prospeccao", "Prospecção"), ("interacao", "Interação"), ("apresentacao", "Apresentação"), ("captacao", "Captação")):
        count = 0
        if ids:
            movement_date = func.coalesce(CaptacaoHistorico.data_acao, func.date(CaptacaoHistorico.created_at))
            count = session.query(CaptacaoHistorico).filter(
                CaptacaoHistorico.captacao_id.in_(ids), CaptacaoHistorico.tipo == "avanco",
                CaptacaoHistorico.etapa == key, movement_date >= start,
                movement_date <= end,
            ).count()
        stages.append({"etapa": key, "label": label, "total": count})
    return {"trabalhados": worked, "captados": captured, "etapas": stages}


def _leads(session, start, end, selected_team, teams):
    query = _period_query(session.query(LeadLegado), LeadLegado.data, start, end)
    selected = next((t for t in teams if t["id"] == selected_team), None)
    if selected:
        query = query.filter(or_(LeadLegado.equipe.ilike(selected["id"]), LeadLegado.equipe.ilike(selected["nome"])))
    return query.count()


@lru_cache(maxsize=4)
def _read_dfimoveis_report(file_path, modified_ns):
    del modified_ns  # faz parte da chave e invalida o cache quando o arquivo muda
    df = pd.read_excel(file_path, sheet_name="Relatório")
    return df


def _media(session, start, end):
    latest_date = session.query(func.max(DfImoveisAcesso.data_relatorio)).scalar()
    if latest_date:
        base = session.query(DfImoveisAcesso).filter(DfImoveisAcesso.data_relatorio == latest_date)
        rows = base.all()
        grouped = session.query(
            DfImoveisAcesso.bairro,
            func.count(func.distinct(DfImoveisAcesso.codigo_busca)),
            func.coalesce(func.sum(DfImoveisAcesso.impressao), 0),
            func.coalesce(func.sum(DfImoveisAcesso.acesso), 0),
            func.coalesce(func.sum(
                DfImoveisAcesso.emails + DfImoveisAcesso.telefone +
                DfImoveisAcesso.whatsapp_emails_gerados + DfImoveisAcesso.visita +
                DfImoveisAcesso.proposta
            ), 0),
        ).filter(DfImoveisAcesso.data_relatorio == latest_date).group_by(
            DfImoveisAcesso.bairro
        ).order_by(func.sum(DfImoveisAcesso.acesso).desc()).limit(12).all()
        profiles = [{
            "id": bairro or "nao-identificado", "bairro": bairro or "Não identificado",
            "perfil": bairro or "Não identificado", "detalhe": f"{int(imoveis)} imóveis no relatório",
            "impressoes": int(impressions), "acessos": int(accesses), "leads": int(leads), "delta": None,
        } for bairro, imoveis, impressions, accesses, leads in grouped]
        first = rows[0]
        leads_total = sum(row.emails + row.telefone + row.whatsapp_emails_gerados + row.visita + row.proposta for row in rows)
        return {
            "disponivel": True, "fonte": "banco", "arquivo": first.arquivo_origem,
            "data_relatorio": latest_date.isoformat(), "impressoes": sum(row.impressao for row in rows),
            "acessos": sum(row.acesso for row in rows), "leads": leads_total,
            "imoveis": len({row.codigo_busca for row in rows}), "perfis": profiles,
            "mensagem": "Tipologia, faixa de valor e metragem não existem no arquivo exportado pelo DFImóveis.",
        }

    report_dir = Path(__file__).resolve().parents[3] / "legado"
    files = sorted(report_dir.glob("Relatorio-de-acesso-imoveis-*.xlsx"), key=lambda path: path.stat().st_mtime, reverse=True)
    if files:
        df = _read_dfimoveis_report(str(files[0]), files[0].stat().st_mtime_ns).copy()
        required = {"Endereco", "CodigoDeBusca", "Acesso", "Impressao"}
        if not required.issubset(df.columns):
            raise ValueError("Planilha DFImóveis sem as colunas obrigatórias: Endereco, CodigoDeBusca, Acesso e Impressao")
        numeric = ["Acesso", "Impressao", "Emails", "Telefone", "WhatsAppEmailsGerados", "Visita", "Proposta"]
        for column in numeric:
            if column not in df.columns:
                df[column] = 0
            df[column] = pd.to_numeric(df[column], errors="coerce").fillna(0)
        df["Leads"] = df[["Emails", "Telefone", "WhatsAppEmailsGerados", "Visita", "Proposta"]].sum(axis=1)

        def bairro(endereco):
            parts = [part.strip() for part in str(endereco or "").split("-") if part.strip()]
            if len(parts) >= 3 and parts[1].upper() == "BRASILIA":
                return parts[2]
            return parts[1] if len(parts) >= 2 else "Não identificado"

        df["Bairro"] = df["Endereco"].map(bairro)
        profiles = []
        grouped = df.groupby("Bairro", dropna=False).agg(
            impressoes=("Impressao", "sum"), acessos=("Acesso", "sum"), leads=("Leads", "sum"), imoveis=("CodigoDeBusca", "nunique")
        ).sort_values("acessos", ascending=False).head(12)
        for index, row in grouped.iterrows():
            profiles.append({
                "id": str(index), "bairro": str(index).title(), "perfil": str(index).title(),
                "detalhe": f"{int(row['imoveis'])} imóveis no relatório",
                "impressoes": int(row["impressoes"]), "acessos": int(row["acessos"]),
                "leads": int(row["leads"]), "delta": None,
            })
        match = re.search(r"(\d{2})_(\d{2})_(\d{4})", files[0].name)
        report_date = f"{match.group(3)}-{match.group(2)}-{match.group(1)}" if match else None
        return {
            "disponivel": True, "arquivo": files[0].name, "data_relatorio": report_date,
            "impressoes": int(df["Impressao"].sum()), "acessos": int(df["Acesso"].sum()),
            "leads": int(df["Leads"].sum()), "imoveis": int(df["CodigoDeBusca"].nunique()),
            "perfis": profiles,
            "mensagem": "Tipologia, faixa de valor e metragem não existem no arquivo exportado pelo DFImóveis.",
        }

    rows = _period_query(session.query(CampanhaLegado), CampanhaLegado.dia, start, end).all()
    return {
        "disponivel": bool(rows),
        "impressoes": int(sum(_number(row.impressoes) for row in rows)),
        "alcance": int(sum(_number(row.alcance) for row in rows)),
        "leads": int(sum(_number(row.resultados) for row in rows)),
        "acessos": None,
        "perfis": [],
        "mensagem": "Nenhum relatório de acesso do DFImóveis foi encontrado. Exibindo somente campanhas importadas.",
    }


def _alerts(session, selected_team, today):
    query = session.query(Captacao)
    if selected_team:
        query = query.filter(Captacao.team == selected_team)
    alerts = []
    for row in query.filter(Captacao.status.in_(["ativo", "exclusividade"])).all():
        due = None
        done = False
        if row.etapa_atual == "escolha": due, done = row.data_acao_sem_numero, row.acao_escolha_realizada
        elif row.etapa_atual == "interacao": due, done = row.data_proxima_acao_interacao, row.acao_interacao_realizada
        elif row.etapa_atual == "apresentacao": due, done = row.data_proxima_acao_apresentacao, row.acao_apresentacao_realizada
        elif row.etapa_atual == "captacao": due, done = row.data_proxima_acao_captacao, row.acao_captacao_realizada
        if due and due < today and not done:
            days = (today - due).days
            alerts.append({"id": f"acao-{row.id}", "tipo": "Atividade atrasada", "descricao": row.endereco, "responsavel": row.nome_corretor or row.team or "Não informado", "atraso": f"{days} dia(s)", "nivel": "critical" if days >= 7 else "warning"})
        updated = row.updated_at.date() if row.updated_at else row.created_at.date() if row.created_at else None
        if updated and (today - updated).days >= 14:
            alerts.append({"id": f"stale-{row.id}", "tipo": "Imóvel sem atualização", "descricao": row.endereco, "responsavel": row.nome_corretor or row.team or "Não informado", "atraso": f"{(today - updated).days} dias", "nivel": "warning"})

    review_query = session.query(GerenteVisitaVisualizada, Visita).join(Visita, Visita.id_visita == GerenteVisitaVisualizada.id_visita).filter(
        Visita.data_visita >= today - timedelta(days=30),
        or_(GerenteVisitaVisualizada.viu_anexo.is_(False), GerenteVisitaVisualizada.viu_notas.is_(False), GerenteVisitaVisualizada.add_motivo.is_(False)),
    )
    if selected_team:
        review_query = review_query.filter(GerenteVisitaVisualizada.id_gerente == selected_team)
    for flags, visit in review_query.limit(50).all():
        pending = [label for value, label in ((flags.viu_anexo, "anexo"), (flags.viu_notas, "notas"), (flags.add_motivo, "motivo")) if not value]
        alerts.append({"id": f"visita-{visit.id_visita}", "tipo": "Revisão de visita pendente", "descricao": f"Pendente: {', '.join(pending)}", "responsavel": flags.id_gerente, "atraso": visit.data_visita.isoformat() if visit.data_visita else "—", "nivel": "critical"})
    return alerts[:30]


def _visit_reviews(session, start, end, selected_team, teams):
    query = session.query(Visita, Usuarios, GerenteVisitaVisualizada).join(
        Usuarios, Usuarios.id_usuarios == Visita.id_corretor
    ).outerjoin(
        GerenteVisitaVisualizada,
        and_(
            GerenteVisitaVisualizada.id_visita == Visita.id_visita,
            GerenteVisitaVisualizada.id_gerente == Usuarios.team,
        ),
    ).filter(Visita.data_visita >= start, Visita.data_visita <= end)
    if selected_team:
        query = query.filter(Usuarios.team == selected_team)

    items = []
    for visit, broker, flags in query.order_by(Visita.data_visita.desc()).limit(500).all():
        viewed = flags is not None
        items.append({
            "id": visit.id_visita,
            "data": visit.data_visita.isoformat() if visit.data_visita else None,
            "imovel": visit.id_imovel or visit.endereco_externo or "Imóvel não informado",
            "corretor": broker.nome or broker.username or visit.id_corretor,
            "equipe_id": broker.team,
            "proposta": _norm_proposta(visit.proposta),
            "tem_nota": bool(visit.audiodescricao_cliente_visita or visit.link_audio),
            "tem_anexo": bool(visit.anexo_ficha_visita or visit.link_imagem),
            "viu_visita": viewed,
            "viu_nota": bool(flags.viu_notas) if flags else False,
            "viu_anexo": bool(flags.viu_anexo) if flags else False,
            "adicionou_motivo": bool(flags.add_motivo) if flags else False,
            "visualizado_em": flags.visualizado_em.isoformat() if flags and flags.visualizado_em else None,
        })

    totals = {
        "total": len(items),
        "viu_visita": sum(1 for item in items if item["viu_visita"]),
        "viu_nota": sum(1 for item in items if item["viu_nota"]),
        "viu_anexo": sum(1 for item in items if item["viu_anexo"]),
        "adicionou_motivo": sum(1 for item in items if item["adicionou_motivo"]),
    }
    team_names = {team["id"]: team for team in teams}
    grouped = {}
    for item in items:
        team_id = item["equipe_id"] or "sem-equipe"
        team_info = team_names.get(team_id, {})
        row = grouped.setdefault(team_id, {
            "equipe_id": team_id,
            "equipe": team_info.get("nome") or team_id,
            "gerente": team_info.get("gerente") or "Sem gerente cadastrado",
            "total_visitas": 0,
            "nao_viu_visita": 0,
            "notas_aplicaveis": 0,
            "nao_viu_nota": 0,
            "anexos_aplicaveis": 0,
            "nao_viu_anexo": 0,
            "motivos_aplicaveis": 0,
            "nao_adicionou_motivo": 0,
        })
        row["total_visitas"] += 1
        if not item["viu_visita"]:
            row["nao_viu_visita"] += 1
        if item["tem_nota"]:
            row["notas_aplicaveis"] += 1
            if not item["viu_nota"]:
                row["nao_viu_nota"] += 1
        if item["tem_anexo"]:
            row["anexos_aplicaveis"] += 1
            if not item["viu_anexo"]:
                row["nao_viu_anexo"] += 1
        if item["proposta"] in {"sim", "talvez"}:
            row["motivos_aplicaveis"] += 1
            if not item["adicionou_motivo"]:
                row["nao_adicionou_motivo"] += 1

    by_team = sorted(grouped.values(), key=lambda row: (
        -(row["nao_viu_visita"] + row["nao_viu_nota"] + row["nao_viu_anexo"] + row["nao_adicionou_motivo"]),
        row["equipe"],
    ))
    return {"totais": totals, "por_equipe": by_team}


@cache.memoize(timeout=180)
def executive_view(start_value=None, end_value=None, team=None):
    today = date.today()
    end = _date(end_value, today)
    start = _date(start_value, end.replace(day=1))
    if start > end:
        start, end = end, start
    length = (end - start).days + 1
    previous_end = start - timedelta(days=1)
    previous_start = previous_end - timedelta(days=length - 1)

    session = SessionLocal()
    try:
        teams = _team_maps(session)
        team = team if any(item["id"] == team for item in teams) else None
        team_rows, proposals = _visit_metrics(session, teams, start, end, team)
        previous_rows, previous_proposals = _visit_metrics(session, teams, previous_start, previous_end, team)
        sales_total, sales_count, recent_sales = _sales(session, start, end, team, teams)
        previous_sales, _, _ = _sales(session, previous_start, previous_end, team, teams)
        leads = _leads(session, start, end, team, teams)
        previous_leads = _leads(session, previous_start, previous_end, team, teams)
        visits = sum(row["visitas"] for row in team_rows)
        previous_visits = sum(row["visitas"] for row in previous_rows)
        proposal_total = sum(proposals.values())
        previous_proposal_total = sum(previous_proposals.values())
        return {
            "ok": True, "atualizado_em": datetime.now().isoformat(),
            "periodo": {"inicio": start.isoformat(), "fim": end.isoformat()},
            "equipes_opcoes": teams,
            "kpis": {
                "vendas": {"valor": sales_total, "quantidade": sales_count, "variacao_pct": _pct(sales_total, previous_sales)},
                "propostas": {"valor": proposal_total, "variacao_pct": _pct(proposal_total, previous_proposal_total)},
                "visitas": {"valor": visits, "variacao_pct": _pct(visits, previous_visits)},
                "leads": {"valor": leads, "variacao_pct": _pct(leads, previous_leads)},
            },
            "equipes": team_rows, "propostas": proposals,
            "captacao": _captation(session, start, end, team),
            "vendas_recentes": recent_sales, "midia": _media(session, start, end),
            "pendencias": _alerts(session, team, today),
            "revisao_visitas": _visit_reviews(session, start, end, team, teams),
        }
    finally:
        session.close()
