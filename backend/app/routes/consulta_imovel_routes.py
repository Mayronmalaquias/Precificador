"""Consulta consolidada de imóvel (tela de apoio do estagiário/assistente).

Três rotas: listar/buscar, detalhar e editar o que é nosso. O escopo de acesso é
resolvido no service a partir do cadastro — a rota não confia no que a tela mandou.
"""
from flask import current_app, request
from flask_restx import Namespace, Resource

from app.services import consulta_imovel_service as servico
from app.services.consulta_imovel_service import ConsultaErro

consulta_imovel_ns = Namespace(
    "consulta-imoveis",
    description="Consulta de imóvel: dados do Imoview + bases internas (foco, captação, mídia, visitas)",
)


def _solicitante():
    return request.args.get("solicitante_id") or (request.get_json(silent=True) or {}).get("solicitante_id")


def _erro(exc, contexto):
    if isinstance(exc, ConsultaErro):
        return {"ok": False, "error": exc.mensagem}, exc.status
    current_app.logger.exception(contexto)
    return {"ok": False, "error": str(exc)}, 500


@consulta_imovel_ns.route("/imoveis/consulta")
class ConsultaLista(Resource):
    @consulta_imovel_ns.doc(params={
        "solicitante_id": "Id do usuário (obrigatório).",
        "busca": "Código, endereço, bairro ou tipo. Vazio lista tudo.",
        "page": "Página (padrão 1).",
        "per_page": "Itens por página (padrão 24, máx 100).",
        "situacao": "disponivel (padrão) | vendido | todos.",
        "meus": "1 para ver só os imóveis cuja captação o solicitante lançou.",
    })
    def get(self):
        try:
            return servico.buscar(
                _solicitante(),
                termo=request.args.get("busca", ""),
                page=request.args.get("page", 1),
                per_page=request.args.get("per_page", 24),
                situacao=request.args.get("situacao", "disponivel"),
                apenas_meus=str(request.args.get("meus", "")).lower() in {"1", "true", "sim"},
            ), 200
        except Exception as e:
            return _erro(e, "Erro na busca de imóveis")


@consulta_imovel_ns.route("/imoveis/consulta/<string:codigo>")
class ConsultaDetalhe(Resource):
    @consulta_imovel_ns.doc(description="Dados do Imoview (só leitura) + dados internos do imóvel.")
    def get(self, codigo):
        try:
            return servico.detalhe(_solicitante(), codigo), 200
        except Exception as e:
            return _erro(e, "Erro no detalhe do imóvel")

    @consulta_imovel_ns.doc(description=(
        "Edita os dados internos, um ou vários por chamada: `foco` "
        "(nao_foco|pp|ac|pp_ac), `matricula` e `inscricao_iptu`."
    ))
    def put(self, codigo):
        dados = request.get_json(silent=True) or {}
        try:
            return servico.atualizar_interno(_solicitante(), codigo, dados), 200
        except Exception as e:
            return _erro(e, "Erro ao atualizar dados internos do imóvel")
