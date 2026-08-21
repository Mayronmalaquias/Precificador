"""Leads na tela do gerente: listar/abrir com escopo e lançar no Contact2Sale.

O escopo é resolvido no service a partir do cadastro — a rota não confia no que a tela
mandou. Ver `lead_gestao_service`.
"""
from flask import current_app, request
from flask_restx import Namespace, Resource

from app.services import lead_c2s_service as servico_c2s
from app.services import lead_gestao_service as servico
from app.services.lead_c2s_service import LeadC2SErro
from app.services.lead_gestao_service import LeadErro

lead_gestao_ns = Namespace(
    "leads-gestao",
    description="Leads do Contact2Sale: consulta com escopo por equipe e lançamento",
)


def _solicitante():
    return request.args.get("solicitante_id") or (request.get_json(silent=True) or {}).get("solicitante_id")


def _erro(exc, contexto):
    if isinstance(exc, (LeadErro, LeadC2SErro)):
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
        "nao_vistos": "1 para trazer só os leads sem acompanhamento registrado.",
        "corretor": "Nome (ou id) de quem atende — casa id, nome e username.",
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
                apenas_nao_vistos=str(request.args.get("nao_vistos", "")).lower() in {"1", "true", "sim"},
                corretor=request.args.get("corretor") or None,
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
    @lead_gestao_ns.doc(description=(
        "Detalhe do lead + dados do imóvel citado (endereço, valor, metragem, data da "
        "captação) + acompanhamento. 403 se for de outra equipe."
    ))
    def get(self, lead_id):
        try:
            return servico.detalhe(_solicitante(), lead_id), 200
        except Exception as e:
            return _erro(e, "Erro ao abrir lead")

    @lead_gestao_ns.doc(description=(
        "Grava o acompanhamento: `contato_status` (sem_contato|whatsapp|telefone|email), "
        "`visita_agendada` (bool) e, quando ela for **false**, `motivo_sem_visita` "
        "(obrigatório) e `proxima_acao`."
    ))
    def put(self, lead_id):
        dados = request.get_json(silent=True) or {}
        try:
            return servico.atualizar_acompanhamento(_solicitante(), lead_id, dados), 200
        except Exception as e:
            return _erro(e, "Erro ao gravar acompanhamento do lead")


@lead_gestao_ns.route("/leads/c2s")
class LeadsAoVivo(Resource):
    @lead_gestao_ns.doc(
        description=(
            "Leads lidos **ao vivo do Contact2Sale**, com a situação atual e o motivo do "
            "arquivamento — a base interna guarda o retrato do dia da importação. "
            "A API do C2S só honra janela de data e paginação; os demais filtros são "
            "aplicados no servidor, e nesse caso a resposta traz `varredura_completa=false` "
            "quando o período excedeu o teto de varredura."
        ),
        params={
            "solicitante_id": "Id do usuário (obrigatório).",
            "inicio": "Data inicial (YYYY-MM-DD, obrigatória).",
            "fim": "Data final (YYYY-MM-DD, obrigatória).",
            "por": "Campo de data da janela: 'criacao' (padrão) ou 'atualizacao'.",
            "page": "Página (padrão 1).",
            "per_page": "Itens por página (padrão 30, máx 100).",
            "situacao": "Situação do lead no C2S (ex.: Em negociação).",
            "fonte": "Portal de origem (ex.: Grupo Zap).",
            "canal": "Canal de contato (ex.: WhatsApp).",
            "equipe": "Nome da equipe. Só tem efeito para quem enxerga tudo.",
            "funil": "Etapa do funil no C2S.",
            "corretor": "Nome de quem atende (busca parcial).",
            "motivo": "Motivo do arquivamento (busca parcial).",
            "arquivado": "sim | nao",
            "fechado": "sim | nao (negócio fechado).",
            "com_motivo": "1 para trazer só quem tem motivo de arquivamento preenchido.",
            "busca": "Cliente, telefone, e-mail, código, imóvel, corretor ou motivo.",
        },
    )
    def get(self):
        try:
            por = request.args.get("por") or "criacao"
            return servico_c2s.listar(
                _solicitante(),
                inicio=request.args.get("inicio"),
                fim=request.args.get("fim"),
                page=request.args.get("page", 1),
                per_page=request.args.get("per_page", 30),
                campo_data="updated" if por == "atualizacao" else "created",
                filtros={
                    k: request.args.get(k, "")
                    for k in ("situacao", "fonte", "canal", "equipe", "funil", "corretor",
                              "motivo", "arquivado", "fechado", "com_motivo", "sem_acompanhamento", "busca")
                },
            ), 200
        except Exception as e:
            return _erro(e, "Erro ao consultar leads no Contact2Sale")


@lead_gestao_ns.route("/leads/c2s/opcoes")
class LeadsC2SOpcoes(Resource):
    @lead_gestao_ns.doc(description=(
        "Opções fixas dos filtros (motivo de arquivamento, situação, etapa do funil). "
        "Não consulta o Contact2Sale — responde na hora, então a tela pode montar os "
        "dropdowns antes da primeira busca."
    ))
    def get(self):
        try:
            return {"ok": True, **servico_c2s.catalogo_opcoes()}, 200
        except Exception as e:
            return _erro(e, "Erro ao listar opções de filtro de leads")
