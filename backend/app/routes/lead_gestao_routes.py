"""Leads na tela do gerente: listar/abrir com escopo e lançar no Contact2Sale.

O escopo é resolvido no service a partir do cadastro — a rota não confia no que a tela
mandou. Ver `lead_gestao_service`.
"""
from flask import current_app, g, request
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
    payload = getattr(g, "jwt_payload", None) or {}
    if payload.get("sub"):
        return payload["sub"]
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


@lead_gestao_ns.route("/leads/gestao/resumo")
class LeadsResumo(Resource):
    @lead_gestao_ns.doc(
        description=(
            "Distribuicoes dos leads do periodo para os graficos: serie diaria, fonte, "
            "equipe, corretor, canal de contato e motivos de nao agendar. Le da base "
            "interna (instantaneo), nao do Contact2Sale ao vivo."
        ),
        params={
            "solicitante_id": "Id do usuario (obrigatorio).",
            "inicio": "Data inicial (YYYY-MM-DD).",
            "fim": "Data final (YYYY-MM-DD).",
            "id_gerente": "Recorta por equipe. So tem efeito para quem enxerga tudo.",
            "corretor": "Nome ou id de quem atende.",
        },
    )
    def get(self):
        try:
            return servico.resumo(
                _solicitante(),
                inicio=request.args.get("inicio") or None,
                fim=request.args.get("fim") or None,
                equipe=request.args.get("id_gerente") or None,
                corretor=request.args.get("corretor") or None,
            ), 200
        except Exception as e:
            return _erro(e, "Erro ao resumir leads")


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

    @lead_gestao_ns.doc(description=(
        "Corrige os dados do lead na base interna: `cliente`, `telefone`, "
        "`codigo_imovel`, `fonte`, `observacao` e o repasse de dono (`atendimento`). "
        "Nao propaga para o Contact2Sale — la o valor antigo permanece. Gerente so "
        "repassa dentro da propria equipe."
    ))
    def patch(self, lead_id):
        dados = request.get_json(silent=True) or {}
        try:
            return servico.editar_lead(_solicitante(), lead_id, dados), 200
        except Exception as e:
            return _erro(e, "Erro ao editar lead")


@lead_gestao_ns.route("/leads/c2s/<string:id_c2s>")
class LeadEspelhoDetalhe(Resource):
    @lead_gestao_ns.doc(
        description=(
            "Detalhe do lead pelo id do Contact2Sale, lido do espelho local. Existe "
            "porque 26% dos leads nao tem linha em `leads_legado` (a importacao legada "
            "so aceita lead da recepcao ou de fonte Faixa/Indicacao) e por isso nao "
            "abriam pela rota /leads/gestao/<id>. Quando ha elo, vem o acompanhamento e "
            "`pode_editar` e verdadeiro; sem elo, o lead abre em leitura."
        ),
        params={"solicitante_id": "Id do usuario (obrigatorio)."},
    )
    def get(self, id_c2s):
        try:
            return servico.detalhe_espelho(_solicitante(), id_c2s), 200
        except Exception as e:
            return _erro(e, "Erro ao abrir lead do espelho")

    @lead_gestao_ns.doc(description=(
        "Grava o acompanhamento do lead pelo id do Contact2Sale: `contato_status` "
        "(sem_contato|whatsapp|telefone|email), `visita_agendada` (bool) e, quando ela "
        "for **false**, `motivo_sem_visita` (obrigatorio) e `proxima_acao`. Vale para "
        "TODO lead do espelho, inclusive os que nao tem registro em `leads_legado`."
    ))
    def put(self, id_c2s):
        dados = request.get_json(silent=True) or {}
        try:
            return servico.acompanhar_espelho(_solicitante(), id_c2s, dados), 200
        except Exception as e:
            return _erro(e, "Erro ao gravar acompanhamento do lead")

    @lead_gestao_ns.doc(description=(
        "Corrige os dados do lead (`cliente`, `telefone`, `codigo_imovel`, `fonte`, "
        "`observacao`) pelo id do Contact2Sale. Grava em `leads_legado`, porque no "
        "espelho o sync sobrescreveria — responde 409 quando o lead nao tem registro la."
    ))
    def patch(self, id_c2s):
        dados = request.get_json(silent=True) or {}
        try:
            return servico.editar_lead_espelho(_solicitante(), id_c2s, dados), 200
        except Exception as e:
            return _erro(e, "Erro ao editar lead")


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
            "bairro": "Bairro do imóvel citado (busca parcial, ignora acento).",
            "tipo": "Tipo do imóvel citado (busca parcial).",
            "quartos": "Número exato de quartos do imóvel citado.",
            "valor_min": "Valor mínimo do imóvel citado (R$).",
            "valor_max": "Valor máximo do imóvel citado (R$).",
            "area_min": "Área mínima do imóvel citado (m²).",
            "area_max": "Área máxima do imóvel citado (m²).",
            "origem_de": "Data mínima de ENTRADA do lead (AAAA-MM-DD). Vale mesmo com "
                         "a janela principal em 'atualizacao'.",
            "origem_ate": "Data máxima de entrada do lead (AAAA-MM-DD).",
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
                    # `bairro`, `tipo` e `quartos` nao sao do lead: recortam pelo imovel
                    # citado, casado com o catalogo pelo codigo.
                    for k in ("situacao", "fonte", "canal", "equipe", "funil", "corretor",
                              "motivo", "arquivado", "fechado", "com_motivo",
                              "sem_acompanhamento", "busca",
                              "bairro", "tipo", "quartos",
                              "valor_min", "valor_max", "area_min", "area_max",
                              # `origem_*` recorta a data de ENTRADA e e independente
                              # de `por` — ver comentario em `_aplicar_filtros`.
                              "origem_de", "origem_ate")
                },
            ), 200
        except Exception as e:
            return _erro(e, "Erro ao consultar leads no Contact2Sale")


@lead_gestao_ns.route("/leads/c2s/opcoes")
class LeadsC2SOpcoes(Resource):
    @lead_gestao_ns.doc(description=(
        "Opções dos filtros: motivo de arquivamento, situação e etapa do funil (catálogo "
        "fixo da C2S) mais bairro, tipo e quartos dos imóveis que os leads citam. "
        "Não consulta o Contact2Sale — responde na hora, então a tela pode montar os "
        "dropdowns antes da primeira busca."
    ))
    def get(self):
        try:
            return {"ok": True, **servico_c2s.catalogo_opcoes()}, 200
        except Exception as e:
            return _erro(e, "Erro ao listar opções de filtro de leads")
