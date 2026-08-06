"""Rotas do lançamento de imóvel pelos assistentes (Imoview + Trello).

- GET  /assistente/imoview/listas   → listas p/ os dropdowns do form.
- POST /assistente/incluir-imovel    → inclui no Imoview + cria cartão no Trello.

Auth: passa pelo middleware global (X-API-KEY/JWT). A restrição "só assistente" é de
UX (a página no front é assistente-only); as rotas ficam disponíveis a quem está logado.
"""
from flask import current_app, request
from flask_restx import Namespace, Resource

from app.services import admin_bases_service, imoview_service, lancamento_service

assistente_ns = Namespace("assistente", description="Lançamento de imóvel (assistentes): Imoview + Trello")


@assistente_ns.route("/assistente/imoview/listas")
class ImoviewListas(Resource):
    @assistente_ns.doc(description="Listas do Imoview p/ popular os dropdowns do formulário.")
    def get(self):
        try:
            bairros_resultado = admin_bases_service.listar_bairros()
            nomes_bairros = {
                str(item.get("nome") or "").strip()
                for item in bairros_resultado.get("items", [])
                if str(item.get("nome") or "").strip()
            }
            bairros = [
                {"value": nome, "label": nome}
                for nome in sorted(nomes_bairros, key=str.casefold)
            ]
            return {
                "ok": True,
                "unidades": imoview_service.listar_unidades(),
                "finalidades": imoview_service.listar_finalidades(),
                "destinacoes": imoview_service.listar_destinacoes(),
                "tipos": imoview_service.listar_tipos(),
                "localchaves": imoview_service.listar_localchaves(),
                "bairros": bairros,
            }, 200
        except Exception as e:
            current_app.logger.exception("Erro ao carregar listas do Imoview")
            return {"ok": False, "error": str(e)}, 502


@assistente_ns.route("/assistente/incluir-imovel")
class IncluirImovel(Resource):
    @assistente_ns.doc(description="Inclui um imóvel no Imoview e cria o cartão no Trello. "
                                   "multipart/form-data: campos do imóvel + fotos[].")
    def post(self):
        # Aceita multipart (com fotos) ou JSON puro.
        if request.form:
            dados = request.form.to_dict()
        else:
            dados = request.get_json(silent=True) or {}

        if not dados.get("codigousuario"):
            return {"ok": False, "error": "codigousuario (corretor) é obrigatório"}, 400
        if not dados.get("rua"):
            return {"ok": False, "error": "endereço (rua) é obrigatório"}, 400
        # Imoview exige proprietário (sem ele o IncluirImovel dá null-reference).
        if not dados.get("prop_nome") or not dados.get("prop_cpf") or not dados.get("prop_telefone"):
            return {"ok": False, "error": "Proprietário (nome, CPF e telefone) é obrigatório"}, 400

        fotos = request.files.getlist("fotos") if request.files else []
        criar_trello = str(dados.get("criar_trello", "true")).lower() != "false"

        try:
            resultado = lancamento_service.lancar_imovel(dados, fotos=fotos, criar_trello=criar_trello)
            return resultado, 200
        except RuntimeError as e:  # erro do Imoview (validação/HTTP)
            return {"ok": False, "error": str(e)}, 502
        except Exception as e:
            current_app.logger.exception("Erro ao lançar imóvel")
            return {"ok": False, "error": str(e)}, 500
