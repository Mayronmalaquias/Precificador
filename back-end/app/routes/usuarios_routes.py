from flask import request
from flask_restx import Resource, Namespace
from app.services.usuarios_service import retornar_lista, retornar_infos, alterar_ativo, _usuario_to_dict


corretor_ns = Namespace('corretor', description="Corretores e usuários")


def _parse_bool(value):
    if value is None:
        return None

    value = str(value).strip().lower()

    if value in {"true", "1", "sim", "s"}:
        return True

    if value in {"false", "0", "nao", "não", "n"}:
        return False

    return None


@corretor_ns.route('/corretor/retornar-lista')
class RetornarListaCorretor(Resource):
    @corretor_ns.doc(description="Retorna lista de corretores por gerente e/ou ativos")
    def get(self):
        gerente = request.args.get("gerente")
        ativo_raw = request.args.get("ativo")
        ativo = _parse_bool(ativo_raw)

        if ativo_raw is not None and ativo is None:
            return {"error": "Parâmetro 'ativo' inválido. Use true ou false."}, 400

        lista = retornar_lista(id_gerente=gerente, ativo=ativo)
        return {"ok": True, "lista": lista}, 200


@corretor_ns.route('/corretor/retornar-informacao')
class RetornarInfoCorretor(Resource):
    @corretor_ns.doc(description="Retorna informações sobre corretor específico")
    def get(self):
        username = request.args.get("username")
        id_corretor = request.args.get("id_corretor")

        if not username and not id_corretor:
            return {"error": "Username ou id_corretor precisa ser passado"}, 400

        resultado = retornar_infos(id_corretor=id_corretor, username=username)

        if "error" in resultado:
            return resultado, 404

        return {"ok": True, "usuario": resultado}, 200


@corretor_ns.route('/corretor/alterar-ativo')
class AlterarCorretorAtivo(Resource):
    @corretor_ns.doc(description="Altera se o corretor está ativo ou não")
    def post(self):
        data = request.get_json() or {}
        id_corretor = data.get("id_corretor")
        novo_ativo = data.get("new_ativo")

        if id_corretor is None or novo_ativo is None:
            return {"error": "id_corretor e new_ativo precisam ser passados!"}, 400

        if not isinstance(novo_ativo, bool):
            return {"error": "new_ativo precisa ser booleano"}, 400

        resultado = alterar_ativo(id_corretor, novo_ativo)

        if "error" in resultado:
            return resultado, 404

        return resultado, 200

from app.services.usuarios_service import retornar_corretor_nome

@corretor_ns.route('/corretor/retornar-nome')
class RetornarCorretorNome(Resource):

    @corretor_ns.doc(description='Retorna corretores por nome')
    def get(self):
        nome = request.args.get("nome")

        if not nome:
            return {"error": "Nome não passado"}, 400

        resultado = retornar_corretor_nome(nome)

        return {
            "ok": True,
            "lista": [_usuario_to_dict(u) for u in resultado]
        }, 200