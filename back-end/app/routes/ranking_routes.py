# app/routes/ranking_routes.py
from flask import request, send_file
from flask_restx import Namespace, Resource, fields
from app.services.ranking_service import RankingService
from app.services.corretor_pdf_service import gerar_pdf_corretor, gerar_pdf_todos

ranking_ns = Namespace("ranking", description="Rankings (VGV, VGC, Captação, Visitas)")

ranking_item = ranking_ns.model("RankingItem", {
    "posicao": fields.Integer,
    "id_corretor": fields.String,
    "corretor": fields.String,
    "total": fields.Float,
})

ranking_response = ranking_ns.model("RankingResponse", {
    "vgv": fields.List(fields.Nested(ranking_item)),
    "vgc": fields.List(fields.Nested(ranking_item)),

    "vgv_geral": fields.List(fields.Nested(ranking_item)),
    "vgc_geral": fields.List(fields.Nested(ranking_item)),

    "captacao": fields.List(fields.Nested(ranking_item)),
    "visitas": fields.List(fields.Nested(ranking_item)),
    "meta": fields.Raw,
})


@ranking_ns.route("/rankings")
class Rankings(Resource):
    @ranking_ns.doc(
        params={
            "start": "Data inicial (YYYY-MM-DD). Opcional.",
            "end": "Data final (YYYY-MM-DD). Opcional.",
            "include_pending": "Se true, inclui vendas sem divisão de comissão. Padrão: false.",
            "apply_factor": "Se true, divide Valor_Total_61 por 0.06 no VGC. Padrão: false.",
        }
    )
    @ranking_ns.marshal_with(ranking_response)
    def get(self):
        start = request.args.get("start")
        end = request.args.get("end")
        include_pending = request.args.get("include_pending", "false").lower() == "true"
        apply_factor = request.args.get("apply_factor", "false").lower() == "true"

        svc = RankingService()
        result = svc.get_all_rankings(start=start, end=end, include_pending=include_pending, apply_factor=apply_factor)
        return result, 200


@ranking_ns.route("/rankings/<string:kind>")
class RankingsByKind(Resource):
    @ranking_ns.doc(
        params={
            "start": "Data inicial (YYYY-MM-DD). Opcional.",
            "end": "Data final (YYYY-MM-DD). Opcional.",
            "include_pending": "Mesma regra do endpoint geral. Padrão: false.",
            "apply_factor": "Se true, divide Valor_Total_61 por 0.06 no VGC. Padrão: false.",
        }
    )
    @ranking_ns.marshal_list_with(ranking_item)
    def get(self, kind: str):
        kind = (kind or "").lower().strip()
        if kind not in {"vgv_geral", "vgc_geral", "captacao", "visitas"}:
            ranking_ns.abort(400, "kind inválido. Use: vgv_geral, vgc_geral, captacao, visitas")

        start = request.args.get("start")
        end = request.args.get("end")
        include_pending = request.args.get("include_pending", "false").lower() == "true"
        apply_factor = request.args.get("apply_factor", "false").lower() == "true"

        svc = RankingService()
        ranking = svc.get_ranking(kind=kind, start=start, end=end, include_pending=include_pending, apply_factor=apply_factor)
        return ranking, 200


@ranking_ns.route("/rankings/todos/pdf")
class TodosPdf(Resource):
    @ranking_ns.doc(
        params={
            "kind": "vgc_geral ou vgv_geral.",
            "start": "Data inicial (YYYY-MM-DD).",
            "end": "Data final (YYYY-MM-DD).",
            "apply_factor": "Divide Valor_Total_61 por 0.06 (só VGC). Padrão: false.",
        }
    )
    def get(self):
        kind = (request.args.get("kind", "vgc_geral") or "vgc_geral").lower().strip()
        if kind not in {"vgc_geral", "vgv_geral"}:
            return {"error": "kind inválido."}, 400

        start = request.args.get("start")
        end = request.args.get("end")
        apply_factor = request.args.get("apply_factor", "false").lower() == "true"

        svc = RankingService()
        corretores = svc.get_ranking(kind=kind, start=start, end=end, apply_factor=apply_factor)

        detalhes = []
        for item in corretores:
            nome = item.get("corretor", "")
            if not nome:
                continue
            detalhe = svc.get_corretor_detalhe(
                nome_corretor=nome,
                kind=kind,
                start=start,
                end=end,
                apply_factor=apply_factor,
            )
            if detalhe.get("negociacoes"):
                detalhes.append(detalhe)

        if not detalhes:
            return {"error": "Nenhum dado encontrado para os filtros informados."}, 404

        buf = gerar_pdf_todos(detalhes)
        kind_label = "vgc" if kind == "vgc_geral" else "vgv"
        nome_arquivo = f"relatorio_{kind_label}_{start}_{end}.pdf"
        return send_file(buf, as_attachment=True, download_name=nome_arquivo, mimetype="application/pdf")


@ranking_ns.route("/rankings/corretor/detalhe")
class CorretorDetalhe(Resource):
    @ranking_ns.doc(
        params={
            "nome": "Nome do corretor (exato, case-insensitive).",
            "kind": "vgc_geral ou vgv_geral.",
            "start": "Data inicial (YYYY-MM-DD).",
            "end": "Data final (YYYY-MM-DD).",
            "apply_factor": "Se true, divide Valor_Total_61 por 0.06 (só VGC). Padrão: false.",
        }
    )
    def get(self):
        nome = request.args.get("nome", "")
        kind = (request.args.get("kind", "vgc_geral") or "vgc_geral").lower().strip()
        if kind not in {"vgc_geral", "vgv_geral"}:
            return {"error": "kind inválido. Use: vgc_geral, vgv_geral"}, 400

        start = request.args.get("start")
        end = request.args.get("end")
        apply_factor = request.args.get("apply_factor", "false").lower() == "true"

        svc = RankingService()
        resultado = svc.get_corretor_detalhe(
            nome_corretor=nome,
            kind=kind,
            start=start,
            end=end,
            apply_factor=apply_factor,
        )
        return resultado, 200


@ranking_ns.route("/rankings/corretor/pdf")
class CorretorPdf(Resource):
    @ranking_ns.doc(
        params={
            "nome": "Nome do corretor.",
            "kind": "vgc_geral ou vgv_geral.",
            "start": "Data inicial (YYYY-MM-DD).",
            "end": "Data final (YYYY-MM-DD).",
            "apply_factor": "Divide Valor_Total_61 por 0.06 (só VGC). Padrão: false.",
        }
    )
    def get(self):
        nome = request.args.get("nome", "")
        kind = (request.args.get("kind", "vgc_geral") or "vgc_geral").lower().strip()
        if kind not in {"vgc_geral", "vgv_geral"}:
            return {"error": "kind inválido."}, 400

        start = request.args.get("start")
        end = request.args.get("end")
        apply_factor = request.args.get("apply_factor", "false").lower() == "true"

        svc = RankingService()
        detalhe = svc.get_corretor_detalhe(
            nome_corretor=nome,
            kind=kind,
            start=start,
            end=end,
            apply_factor=apply_factor,
        )

        buf = gerar_pdf_corretor(detalhe)
        nome_arquivo = f"comissoes_{nome.replace(' ', '_').lower()}_{start}_{end}.pdf"
        return send_file(buf, as_attachment=True, download_name=nome_arquivo, mimetype="application/pdf")


# app/routes/meta_gerente_routes.py
# app/routes/meta_gerente_routes.py# app/routes/meta_gerente_routes.py
from flask import Blueprint, request, send_file
from app.services.meta_service import MetaGerenteConfig, MetaGerenteService
from datetime import datetime

meta_gerente_bp = Blueprint("meta_gerente_bp", __name__)

@meta_gerente_bp.route("/relatorio/metas-gerentes", methods=["POST"])
def gerar_relatorio_metas_gerentes():
    body = request.get_json() or {}
    hoje = datetime.today()

    if hoje.month == 1:
        mes_relatorio_padrao = 12
    else:
        mes_relatorio_padrao = hoje.month - 1

    config = MetaGerenteConfig(
        ano_relatorio=body.get("ano_relatorio", 2026),
        mes_relatorio=body.get("mes_relatorio", mes_relatorio_padrao),
        sheet_id_contratos=body.get("sheet_id_contratos", "1I9Lnbf3Be6oz9YPlHFiA9PkFFb9svDWvDtIcHH5I2QY"),
        sheet_id_base_inteligencia=body.get("sheet_id_base_inteligencia", "1_GA3LfjgQDTR_oly9fw5-XwHHTMWaUJixdVZ4PIHPB8"),
        caminho_credencial=body.get("caminho_credencial", "./app/utils/asserts/credenciais.json")
    )

    service = MetaGerenteService(config)
    metas_mensais = body.get("metas_mensais", {})

    pdf_buffer = service.gerar_relatorio_pdf(metas_mensais)

    return send_file(
        pdf_buffer,
        as_attachment=True,
        download_name=config.nome_arquivo_pdf,
        mimetype="application/pdf"
    )
