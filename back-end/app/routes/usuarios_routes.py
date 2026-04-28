from flask import request
from flask_restx import Resource, Namespace
from app.services.usuarios_service import (
    retornar_lista,
    retornar_infos,
    alterar_ativo,
    _usuario_to_dict,
    alterar_gerente,
    retornar_corretor_nome,
)

corretor_ns = Namespace("corretor", description="Corretores e usuários")


def _parse_bool(value):
    if value is None:
        return None
    value = str(value).strip().lower()
    if value in {"true", "1", "sim", "s"}:
        return True
    if value in {"false", "0", "nao", "não", "n"}:
        return False
    return None


@corretor_ns.route("/corretor/retornar-lista")
class RetornarListaCorretor(Resource):
    @corretor_ns.doc(
        description="Retorna lista paginada de corretores por gerente e/ou status ativo",
        params={
            "gerente":   "ID do gerente para filtrar a equipe",
            "ativo":     "true | false",
            "page":      "Página (padrão 1)",
            "per_page":  "Registros por página (padrão 50, máx 200)",
        },
    )
    def get(self):
        gerente     = request.args.get("gerente")
        ativo_raw   = request.args.get("ativo")
        ativo       = _parse_bool(ativo_raw)
        page        = int(request.args.get("page", 1))
        per_page    = min(int(request.args.get("per_page", 1000)), 1000)
        per_page    = 1000
        if ativo_raw is not None and ativo is None:
            return {"error": "Parâmetro 'ativo' inválido. Use true ou false."}, 400

        resultado = retornar_lista(
            id_gerente=gerente, ativo=ativo, page=page, per_page=per_page
        )
        return {"ok": True, **resultado}, 200


@corretor_ns.route("/corretor/retornar-informacao")
class RetornarInfoCorretor(Resource):
    @corretor_ns.doc(description="Retorna informações de um corretor específico")
    def get(self):
        username    = request.args.get("username")
        id_corretor = request.args.get("id_corretor")

        if not username and not id_corretor:
            return {"error": "Username ou id_corretor precisa ser passado"}, 400

        resultado = retornar_infos(id_corretor=id_corretor, username=username)

        if "error" in resultado:
            return resultado, 404

        return {"ok": True, "usuario": resultado}, 200


@corretor_ns.route("/corretor/alterar-ativo")
class AlterarCorretorAtivo(Resource):
    @corretor_ns.doc(description="Altera se o corretor está ativo ou não")
    def post(self):
        data        = request.get_json() or {}
        id_corretor = data.get("id_corretor")
        novo_ativo  = data.get("new_ativo")

        if id_corretor is None or novo_ativo is None:
            return {"error": "id_corretor e new_ativo precisam ser passados!"}, 400

        if not isinstance(novo_ativo, bool):
            return {"error": "new_ativo precisa ser booleano"}, 400

        resultado = alterar_ativo(id_corretor, novo_ativo)

        if "error" in resultado:
            return resultado, 404

        return resultado, 200


@corretor_ns.route("/corretor/retornar-nome")
class RetornarCorretorNome(Resource):
    @corretor_ns.doc(description="Retorna corretores por nome (busca parcial, máx 10)")
    def get(self):
        nome = request.args.get("nome")

        if not nome:
            return {"error": "Nome não passado"}, 400

        resultado = retornar_corretor_nome(nome)
        return {"ok": True, "lista": resultado}, 200


@corretor_ns.route("/corretor/alterar-gerente")
class AlterarGerenteCorretor(Resource):
    @corretor_ns.doc(description="Altera o gerente relacionado ao corretor")
    def post(self):
        data        = request.get_json() or {}
        newmanager  = data.get("manager")
        id_corretor = data.get("corretor")

        if not all([newmanager, id_corretor]):
            return {"error": "Gerente e Corretor precisam ser passados"}, 400

        message = alterar_gerente(newmanager, id_corretor)

        if "error" in message:
            return message, 404

        return message, 200