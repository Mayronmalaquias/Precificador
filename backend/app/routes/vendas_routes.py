from flask import current_app, request
from flask_restx import Namespace, Resource

from app.services import vendas_dash_service as svc

vendas_ns = Namespace("vendas", description="Dashboard e detalhe de vendas (contratos)")


def _filtros():
    return {
        "ano": request.args.get("ano"),
        "mes": request.args.get("mes"),
        "bairro": request.args.get("bairro"),
        "tipo": request.args.get("tipo"),
        "fonte": request.args.get("fonte"),
        "q": request.args.get("q"),
    }


@vendas_ns.route("/vendas/resumo")
class VendasResumo(Resource):
    def get(self):
        try:
            return svc.resumo(_filtros()), 200
        except Exception as e:
            current_app.logger.exception("Erro no resumo de vendas")
            return {"ok": False, "error": str(e)}, 500


@vendas_ns.route("/vendas")
class VendasLista(Resource):
    def get(self):
        try:
            page = int(request.args.get("page", 1))
            per_page = int(request.args.get("per_page", 50))
            return svc.listar(_filtros(), page, per_page), 200
        except Exception as e:
            current_app.logger.exception("Erro na lista de vendas")
            return {"ok": False, "error": str(e)}, 500


@vendas_ns.route("/vendas/<path:id_contrato>")
class VendaDetalhe(Resource):
    def get(self, id_contrato):
        try:
            res = svc.detalhe(id_contrato)
            return res, (200 if res.get("ok") else 404)
        except Exception as e:
            current_app.logger.exception("Erro no detalhe de venda")
            return {"ok": False, "error": str(e)}, 500
