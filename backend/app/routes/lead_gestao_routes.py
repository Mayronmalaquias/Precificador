"""Leads na tela do gerente: listar/abrir com escopo e lançar no Contact2Sale.

O escopo é resolvido no service a partir do cadastro — a rota não confia no que a tela
mandou. Ver `lead_gestao_service`.
"""
from flask import current_app, request
from flask_restx import Namespace, Resource

from app.services import lead_gestao_service as servico
from app.services.lead_gestao_service import LeadErro

lead_gestao_ns = Namespace(
    "leads-gestao",
    description="Leads do Contact2Sale: consulta com escopo por equipe e lançamento",
)


def _solicitante():
    return request.args.get("solicitante_id") or (request.get_json(silent=True) or {}).get("solicitante_id")


def _erro(exc, contexto):
    if isinstance(exc, LeadErro):
        return {"ok": False, "error": exc.mensagem}, exc.status
    current_app.logger.exception(contexto)
    return {"ok": False, "error": str(exc)}, 500


@lead_gestao_ns.route("/leads/gestao")
class LeadsGestao(Resource):
    @lead_gestao_ns.doc(params={
        "solicitante_id": "Id do usuário (obrigatório).",
        "busca": "Cliente, telefone, código do imóvel ou fonte.",
        "inicio": "Data inicial (YYYY-MM-DD).",
        "fim": "Data final (YYYY-MM-DD).",
        "page": "Página (padrão 1).",
        "per_page": "Itens por página (padrão 30, máx 100).",
        "id_gerente": "Recorta por equipe. Só tem efeito para quem enxerga tudo.",
    })
    def get(self):
        try:
            return servico.listar(
                _solicitante(),
                busca=request.args.get("busca", ""),
                page=request.args.get("page", 1),
                per_page=request.args.get("per_page", 30),
                inicio=request.args.get("inicio") or None,
                fim=request.args.get("fim") or None,
                equipe=request.args.get("id_gerente") or None,
            ), 200
        except Exception as e:
            return _erro(e, "Erro ao listar leads")

    @lead_gestao_ns.doc(description=(
        "Cria o lead **no Contact2Sale**. Exige telefone ou e-mail (a API responde 423 sem "
        "os dois). Não grava na base interna: o lead volta na importação diária."
    ))
    def post(self):
        dados = request.get_json(silent=True) or {}
        try:
            return servico.criar_lead(_solicitante(), dados), 201
        except Exception as e:
            return _erro(e, "Erro ao criar lead no Contact2Sale")


@lead_gestao_ns.route("/leads/gestao/<int:lead_id>")
class LeadGestaoDetalhe(Resource):
    @lead_gestao_ns.doc(description="Detalhe do lead. 403 se for de outra equipe.")
    def get(self, lead_id):
        try:
            return servico.detalhe(_solicitante(), lead_id), 200
        except Exception as e:
            return _erro(e, "Erro ao abrir lead")
