from flask import request, current_app
from flask_restx import Namespace, Resource

from app.services.captacao_service import (
    criar_captacao,
    listar_captacoes_corretor,
    listar_captacoes_gerente,
    obter_captacao,
    atualizar_captacao,
    fechar_captacao,
    listar_historico,
)

captacao_ns = Namespace("captacao", description="Jornada de captacao de imoveis")


@captacao_ns.route("/captacoes")
class Captacoes(Resource):
    def get(self):
        gerente = request.args.get("gerente", "false").lower() == "true"
        if gerente:
            team = (request.args.get("team") or "").strip() or None
            try:
                return listar_captacoes_gerente(team=team), 200
            except Exception as e:
                current_app.logger.exception("Erro ao listar captacoes gerente")
                return {"ok": False, "error": str(e)}, 500

        id_corretor = (request.args.get("id_corretor") or "").strip()
        if not id_corretor:
            return {"ok": False, "error": "id_corretor ou gerente=true sao obrigatorios"}, 400
        try:
            return listar_captacoes_corretor(id_corretor), 200
        except Exception as e:
            current_app.logger.exception("Erro ao listar captacoes")
            return {"ok": False, "error": str(e)}, 500

    def post(self):
        data = request.get_json() or {}
        if not data.get("id_corretor") or not data.get("endereco"):
            return {"ok": False, "error": "id_corretor e endereco sao obrigatorios"}, 400
        try:
            return criar_captacao(data), 201
        except Exception as e:
            current_app.logger.exception("Erro ao criar captacao")
            return {"ok": False, "error": str(e)}, 500


@captacao_ns.route("/captacoes/<int:captacao_id>")
class CaptacaoDetalhe(Resource):
    def get(self, captacao_id):
        try:
            result = obter_captacao(captacao_id)
            return result, 200 if result.get("ok") else 404
        except Exception as e:
            current_app.logger.exception("Erro ao obter captacao")
            return {"ok": False, "error": str(e)}, 500

    def put(self, captacao_id):
        data = request.get_json() or {}
        try:
            result = atualizar_captacao(captacao_id, data)
            return result, 200 if result.get("ok") else 404
        except Exception as e:
            current_app.logger.exception("Erro ao atualizar captacao")
            return {"ok": False, "error": str(e)}, 500


@captacao_ns.route("/captacoes/<int:captacao_id>/historico")
class HistoricoCaptacao(Resource):
    def get(self, captacao_id):
        try:
            return listar_historico(captacao_id), 200
        except Exception as e:
            current_app.logger.exception("Erro ao listar historico")
            return {"ok": False, "error": str(e)}, 500


@captacao_ns.route("/captacoes/<int:captacao_id>/fechar")
class FecharCaptacao(Resource):
    def post(self, captacao_id):
        data = request.get_json() or {}
        motivo = (data.get("motivo") or "").strip()
        if not motivo:
            return {"ok": False, "error": "Motivo e obrigatorio"}, 400
        try:
            result = fechar_captacao(captacao_id, motivo)
            return result, 200 if result.get("ok") else 404
        except Exception as e:
            current_app.logger.exception("Erro ao fechar captacao")
            return {"ok": False, "error": str(e)}, 500
