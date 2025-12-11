# app/routes/visita_routes.py
from flask import request, current_app
from flask_restx import Namespace, Resource

from app.services.visita_service import registrar_visita

visita_ns = Namespace("visitas", description="Lançamento de visitas")


@visita_ns.route("")
class LancaVisita(Resource):
    @visita_ns.doc(description="Lança uma nova visita nas abas da planilha")
    def post(self):
        payload = request.get_json() or {}

        try:
            id_visita = registrar_visita(payload)
            return {"ok": True, "id_visita": id_visita}, 201
        except Exception as e:
            current_app.logger.exception("Erro ao registrar visita")
            return {"ok": False, "error": str(e)}, 500
