from flask import current_app, request
from flask_restx import Namespace, Resource

from app.services.equipes_service import atualizar_equipe, criar_equipe, listar_equipes

equipes_ns = Namespace("equipes", description="Gestão de equipes")


@equipes_ns.route("/equipes")
class Equipes(Resource):
    def get(self):
        incluir = (request.args.get("incluir_inativas") or "").lower() == "true"
        try:
            return {"ok": True, "equipes": listar_equipes(incluir_inativas=incluir)}, 200
        except Exception as e:
            current_app.logger.exception("Erro ao listar equipes")
            return {"ok": False, "error": str(e)}, 500

    def post(self):
        data = request.get_json() or {}
        id_equipe = (data.get("id_equipe") or "").strip()
        nome = (data.get("nome") or "").strip()
        if not id_equipe or not nome:
            return {"ok": False, "error": "id_equipe e nome são obrigatórios"}, 400
        try:
            equipe = criar_equipe(id_equipe, nome, data.get("email"))
            return {"ok": True, "equipe": equipe}, 201
        except ValueError as e:
            return {"ok": False, "error": str(e)}, 400
        except Exception as e:
            current_app.logger.exception("Erro ao criar equipe")
            return {"ok": False, "error": str(e)}, 500


@equipes_ns.route("/equipes/<string:id_equipe>")
class EquipeDetalhe(Resource):
    def put(self, id_equipe):
        data = request.get_json() or {}
        try:
            result = atualizar_equipe(
                id_equipe,
                nome=data.get("nome"),
                email=data.get("email"),
                ativo=data.get("ativo"),
            )
            return result, 200 if result.get("ok") else 404
        except Exception as e:
            current_app.logger.exception("Erro ao atualizar equipe")
            return {"ok": False, "error": str(e)}, 500
