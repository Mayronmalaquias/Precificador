from flask import request, current_app
from flask_restx import Namespace, Resource

from app.services.captacao_service import (
    criar_captacao,
    listar_captacoes_corretor,
    listar_captacoes_gerente,
    obter_captacao,
    atualizar_captacao,
    fechar_captacao,
    marcar_exclusividade,
    excluir_captacao,
    listar_historico,
)

from app.services import captacao_snapshot_service as snap_svc

captacao_ns = Namespace("captacao", description="Jornada de captacao de imoveis")


@captacao_ns.route("/captacoes/snapshot")
class CaptacaoSnapshotEndpoint(Resource):
    def post(self):
        """Gera o snapshot do dia (usar via cron diario). ?backfill=true reconstroi historico."""
        try:
            if (request.args.get("backfill") or "").lower() == "true":
                return snap_svc.backfill(), 200
            return snap_svc.gerar_snapshot(), 200
        except Exception as e:
            current_app.logger.exception("Erro no snapshot de captacao")
            return {"ok": False, "error": str(e)}, 500


def _equipe_forcada():
    """Se o solicitante NAO for diretor, retorna a equipe dele (gerente ve so a propria)."""
    perm = (request.args.get("solicitante_permissao") or "").lower()
    team = (request.args.get("solicitante_team") or "").strip()
    if perm != "diretor" and team:
        return team
    return None


@captacao_ns.route("/captacoes/evolucao/opcoes")
class CaptacaoEvolucaoOpcoes(Resource):
    def get(self):
        try:
            return snap_svc.opcoes(equipe=_equipe_forcada()), 200
        except Exception as e:
            current_app.logger.exception("Erro nas opcoes de evolucao")
            return {"ok": False, "error": str(e)}, 500


@captacao_ns.route("/captacoes/evolucao")
class CaptacaoEvolucao(Resource):
    def get(self):
        """Serie temporal p/ o dashboard de evolucao. Params: dimensao + filtros."""
        forcada = _equipe_forcada()
        filtros = {
            "equipe": forcada or request.args.get("equipe"),
            "corretor": request.args.get("corretor"),
            "bairro": request.args.get("bairro"),
            "endereco": request.args.get("endereco"),
            "categoria": request.args.get("categoria"),
            "status": request.args.get("status"),
            "data_de": request.args.get("data_de"),
            "data_ate": request.args.get("data_ate"),
        }
        por_estado = (request.args.get("por_estado") or "").lower() == "true"
        try:
            return snap_svc.evolucao(request.args.get("dimensao", "equipe"), filtros, por_estado=por_estado), 200
        except Exception as e:
            current_app.logger.exception("Erro na evolucao de captacao")
            return {"ok": False, "error": str(e)}, 500


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


@captacao_ns.route("/captacoes/<int:captacao_id>/excluir")
class ExcluirCaptacao(Resource):
    def delete(self, captacao_id):
        try:
            result = excluir_captacao(captacao_id)
            return result, 200 if result.get("ok") else 404
        except Exception as e:
            current_app.logger.exception("Erro ao excluir captacao")
            return {"ok": False, "error": str(e)}, 500


@captacao_ns.route("/captacoes/<int:captacao_id>/exclusividade")
class ExclusividadeCaptacao(Resource):
    def post(self, captacao_id):
        data = request.get_json() or {}
        data_exclusividade = (data.get("data_exclusividade") or "").strip()
        if not data_exclusividade:
            return {"ok": False, "error": "data_exclusividade e obrigatoria"}, 400
        try:
            result = marcar_exclusividade(captacao_id, data_exclusividade)
            return result, 200 if result.get("ok") else 404
        except Exception as e:
            current_app.logger.exception("Erro ao marcar exclusividade")
            return {"ok": False, "error": str(e)}, 500
