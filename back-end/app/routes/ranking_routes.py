# app/routes/ranking_routes.py
from flask import request
from flask_restx import Namespace, Resource, fields
from app.services.ranking_service import RankingService

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
            "limit": "Quantidade máxima no ranking. Padrão: 100.",
            "include_pending": "Se true, inclui vendas sem divisão de comissão (apenas para VGV/Captação/Visitas; VGC depende da divisão). Padrão: false.",
        }
    )
    @ranking_ns.marshal_with(ranking_response)
    def get(self):
        start = request.args.get("start")
        end = request.args.get("end")
        limit = int(request.args.get("limit", "100"))
        include_pending = request.args.get("include_pending", "false").lower() == "true"

        svc = RankingService()
        result = svc.get_all_rankings(start=start, end=end, limit=limit, include_pending=include_pending)
        return result, 200


@ranking_ns.route("/rankings/<string:kind>")
class RankingsByKind(Resource):
    @ranking_ns.doc(
        params={
            "start": "Data inicial (YYYY-MM-DD). Opcional.",
            "end": "Data final (YYYY-MM-DD). Opcional.",
            "limit": "Quantidade máxima no ranking. Padrão: 100.",
            "include_pending": "Mesma regra do endpoint geral. Padrão: false.",
        }
    )
    @ranking_ns.marshal_with(fields.List(fields.Nested(ranking_item)))
    def get(self, kind: str):
        kind = (kind or "").lower().strip()
        if kind not in {"vgv", "vgc", "captacao", "visitas"}:
            ranking_ns.abort(400, "kind inválido. Use: vgv, vgc, captacao, visitas")

        start = request.args.get("start")
        end = request.args.get("end")
        limit = int(request.args.get("limit", "100"))
        include_pending = request.args.get("include_pending", "false").lower() == "true"

        svc = RankingService()
        all_rankings = svc.get_all_rankings(start=start, end=end, limit=limit, include_pending=include_pending)
        return all_rankings[kind], 200
