"""Consulta consolidada de imóvel (tela de apoio do estagiário/assistente).

Três rotas: listar/buscar, detalhar e editar o que é nosso. O escopo de acesso é
resolvido no service a partir do cadastro — a rota não confia no que a tela mandou.
"""
from flask import current_app, g, request
from flask_restx import Namespace, Resource

from app.services import consulta_imovel_service as servico
from app.services.consulta_imovel_service import ConsultaErro

consulta_imovel_ns = Namespace(
    "consulta-imoveis",
    description="Consulta de imóvel: dados do Imoview + bases internas (foco, captação, mídia, visitas)",
)


def _solicitante():
    payload = getattr(g, "jwt_payload", None) or {}
    if payload.get("sub"):
        return payload["sub"]
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
        "situacao": ("disponivel (padrão) | vendido | desativado | moderacao | reforma | "
                     "saiu (deixou o estoque: vendido, desativado ou em reforma) | todos."),
        "meus": "1 para ver só os imóveis cuja captação o solicitante lançou.",
        "bairro": "Bairro (busca parcial).",
        "tipo": "Tipo do imóvel (busca parcial).",
        "finalidade": "Venda | Aluguel.",
        "foco": "nao_foco | pp | ac | pp_ac | qualquer.",
        "valor_min": "Valor mínimo.",
        "valor_max": "Valor máximo.",
        "area_min": "Área mínima (m²).",
        "area_max": "Área máxima (m²).",
        "quartos_min": "Mínimo de quartos.",
        "vagas_min": "Mínimo de vagas.",
        "mudou_de": ("Data inicial da última mudança de situação (YYYY-MM-DD). Com "
                     "`situacao=vendido`, é o recorte de VENDIDOS NO PERÍODO."),
        "mudou_ate": "Data final da última mudança de situação (YYYY-MM-DD).",
        "captado_de": "Data inicial do cadastro do imóvel (YYYY-MM-DD).",
        "captado_ate": "Data final do cadastro do imóvel (YYYY-MM-DD).",
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
                filtros={
                    chave: request.args.get(chave)
                    for chave in servico.FILTROS_DE_CATALOGO
                },
            ), 200
        except Exception as e:
            return _erro(e, "Erro na busca de imóveis")


@consulta_imovel_ns.route("/imoveis/consulta/graficos")
class ConsultaGraficos(Resource):
    @consulta_imovel_ns.doc(
        description=(
            "Distribuicoes do estoque para os graficos, sobre o MESMO recorte da "
            "listagem: situacao, tipo, bairro, finalidade, faixa de valor, foco e o "
            "fluxo mensal de entradas x saidas. Aceita os mesmos filtros de "
            "/imoveis/consulta."
        ),
        params={
            "solicitante_id": "Id do usuario (obrigatorio).",
            "meses": "Tamanho da serie mensal (padrao 12, max 60).",
        },
    )
    def get(self):
        try:
            return servico.graficos(
                _solicitante(),
                termo=request.args.get("busca", ""),
                situacao=request.args.get("situacao", "disponivel"),
                apenas_meus=str(request.args.get("meus", "")).lower() in {"1", "true", "sim"},
                filtros={c: request.args.get(c) for c in servico.FILTROS_DE_CATALOGO},
                meses=request.args.get("meses", 12),
            ), 200
        except Exception as e:
            return _erro(e, "Erro ao montar graficos de imoveis")


@consulta_imovel_ns.route("/imoveis/consulta/opcoes")
class ConsultaOpcoes(Resource):
    @consulta_imovel_ns.doc(
        description=("Bairros, tipos, finalidades e situações presentes no catálogo, "
                     "para os dropdowns da Gestão de Imóveis."),
        params={"solicitante_id": "Id do usuário (obrigatório)."},
    )
    def get(self):
        try:
            return servico.opcoes_de_filtro(_solicitante()), 200
        except Exception as e:
            return _erro(e, "Erro ao listar opções de filtro")


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
