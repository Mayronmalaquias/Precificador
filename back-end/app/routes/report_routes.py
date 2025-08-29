# app/routes/report_routes.py
from flask import request
from flask_restx import Resource, Namespace
from app.services.report_service import gerar_relatorio_imovel

report_ns = Namespace(
    "relatorio_imovel",
    description="Relatório específico de performance do imóvel"
)

@report_ns.route("/reporteImovel")  # endpoint final: /relatorio_imovel/reporteImovel
class GerarRelatorioImovel(Resource):
    @report_ns.doc(
        description="Gera o relatório PDF de performance do imóvel",
        produces=["application/pdf"]  # <- dica forte p/ RESTX escolher PDF
    )
    @report_ns.param("codigo", "Código do Imóvel", required=True)
    def get(self):
        codigo = request.args.get("codigo", type=str)
        return gerar_relatorio_imovel(codigo)

@report_ns.route("/health")
class Health(Resource):
    def get(self):
        return {"status": "ok"}, 200
