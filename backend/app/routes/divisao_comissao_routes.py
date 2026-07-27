# app/routes/divisao_comissao_routes.py
from flask import request
from flask_restx import Namespace, Resource, fields
from app.services.ranking_service import RankingService

divisao_ns = Namespace("divisao", description="Divisão de comissão (manual)")

linha_model = divisao_ns.model("DivisaoLinha", {
    "papel": fields.String(required=True, description="VENDA ou CAPTACAO"),
    "id_corretor": fields.String(required=False, description="Opcional"),
    "nome_corretor": fields.String(required=True, description="Nome do corretor"),
    "percentual": fields.Float(required=True, description="Percentual (0-100)"),
    "observacao": fields.String(required=False, description="Opcional"),
})

payload_model = divisao_ns.model("DivisaoPayload", {
    "id_contrato": fields.String(required=True, description="Id_Contrato da venda/contrato"),
    "linhas": fields.List(fields.Nested(linha_model), required=True),
})


@divisao_ns.route("/contratos-2026")
class Contratos2026(Resource):
    def get(self):
        """
        Lista contratos apenas de 2026 para seleção no front (dropdown/autocomplete).
        """
        svc = RankingService()
        try:
            contratos = svc.get_contratos_2026()
            return {"ok": True, "contratos": contratos}, 200
        except Exception as e:
            return {"ok": False, "error": str(e)}, 500


@divisao_ns.route("/corretores")
class Corretores(Resource):
    def get(self):
        """
        Lista corretores com seus respectivos IDs para dropdown no front.
        Origem: aba Dim_Corretores (ou outra definida em ENV).
        """
        svc = RankingService()
        try:
            corretores = svc.get_corretores()
            return {"ok": True, "corretores": corretores}, 200
        except Exception as e:
            return {"ok": False, "error": str(e)}, 500


@divisao_ns.route("/divisao-comissao")
class DivisaoComissao(Resource):
    @divisao_ns.expect(payload_model)
    def post(self):
        """
        Adiciona linhas na aba Divisao_Comissao (N corretores por contrato).
        """
        payload = request.get_json() or {}
        svc = RankingService()

        try:
            result = svc.add_divisao_comissao(payload)
            return result, 201
        except ValueError as e:
            return {"ok": False, "error": str(e)}, 400
        except Exception as e:
            return {"ok": False, "error": f"Erro interno: {str(e)}"}, 500
