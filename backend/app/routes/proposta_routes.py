"""Rotas das propostas efetivas (lançadas pelos gerentes).

O `solicitante_id` define escopo e permissão de escrita — a validação toda mora no
service (`escopo_do_solicitante`), então nenhuma rota aqui confia no que a tela mandou.
"""
from flask import current_app, request
from flask_restx import Namespace, Resource

from app.services import proposta_service
from app.services.proposta_service import PropostaErro

proposta_ns = Namespace("propostas", description="Propostas efetivas lançadas pelos gerentes")


def _solicitante():
    return request.args.get("solicitante_id") or (request.get_json(silent=True) or {}).get("solicitante_id")


def _erro(exc, contexto):
    if isinstance(exc, PropostaErro):
        return {"ok": False, "error": exc.mensagem}, exc.status
    current_app.logger.exception(contexto)
    return {"ok": False, "error": str(exc)}, 500


@proposta_ns.route("/propostas")
class Propostas(Resource):
    def get(self):
        try:
            return proposta_service.listar(_solicitante(), {
                "situacao": request.args.get("situacao"),
                "team": request.args.get("team"),
                "forma_pagamento": request.args.get("forma_pagamento"),
                "busca": request.args.get("busca"),
                "somente_abertas": request.args.get("somente_abertas"),
                # Recorte de periodo pela data de lancamento (usado no Relatorio do Gerente).
                "corretor": request.args.get("corretor"),
                "inicio": request.args.get("inicio"),
                "fim": request.args.get("fim"),
            }), 200
        except Exception as e:
            return _erro(e, "Erro ao listar propostas efetivas")

    def post(self):
        dados = request.get_json(silent=True) or {}
        try:
            return proposta_service.criar(_solicitante(), dados), 201
        except Exception as e:
            return _erro(e, "Erro ao criar proposta efetiva")


@proposta_ns.route("/propostas/corretores")
class PropostaCorretores(Resource):
    @proposta_ns.doc(description="Corretores em nome de quem o solicitante pode lançar.")
    def get(self):
        try:
            return proposta_service.corretores_disponiveis(_solicitante()), 200
        except Exception as e:
            return _erro(e, "Erro ao listar corretores para proposta")


@proposta_ns.route("/propostas/visitas")
class PropostaVisitas(Resource):
    @proposta_ns.doc(description="Visitas candidatas a origem da proposta (restritas à equipe).")
    def get(self):
        try:
            return proposta_service.visitas_relacionadas(_solicitante(), {
                "corretor": request.args.get("corretor"),
                "team": request.args.get("team"),
                "codigo": request.args.get("codigo"),
                "busca": request.args.get("busca"),
            }), 200
        except Exception as e:
            return _erro(e, "Erro ao listar visitas para proposta")


@proposta_ns.route("/propostas/<int:proposta_id>")
class PropostaItem(Resource):
    def get(self, proposta_id):
        try:
            return proposta_service.obter(_solicitante(), proposta_id), 200
        except Exception as e:
            return _erro(e, "Erro ao obter proposta efetiva")

    def put(self, proposta_id):
        dados = request.get_json(silent=True) or {}
        try:
            return proposta_service.atualizar(_solicitante(), proposta_id, dados), 200
        except Exception as e:
            return _erro(e, "Erro ao atualizar proposta efetiva")

    def delete(self, proposta_id):
        try:
            return proposta_service.excluir(_solicitante(), proposta_id), 200
        except Exception as e:
            return _erro(e, "Erro ao excluir proposta efetiva")


@proposta_ns.route("/propostas/<int:proposta_id>/acoes")
class PropostaAcoes(Resource):
    def post(self, proposta_id):
        dados = request.get_json(silent=True) or {}
        try:
            return proposta_service.registrar_acao(_solicitante(), proposta_id, dados), 201
        except Exception as e:
            return _erro(e, "Erro ao registrar ação da proposta")
