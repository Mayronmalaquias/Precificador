from flask import current_app, request
from flask_restx import Namespace, Resource

from app.services.auth_service import cadastrar_usuario, login, registrar_nova_senha
from app.services.usuarios_service import CAMPOS_EDITAVEIS, retornar_infos
from app.utils.helpers import normalizar_user
from app.utils.security import validate_password_strength

auth_ns = Namespace("auth", description="Autenticacao de usuarios")


@auth_ns.route("/auth/cadastro")
class CadastroUsuario(Resource):
    @auth_ns.doc(description="Cadastro de novo usuario")
    def post(self):
        data = request.get_json() or {}

        username = normalizar_user(data.get("username") or "")
        password = data.get("password")
        team = data.get("team")

        if not all([username, password, team]):
            return {"error": "Campos username, password e team sao obrigatorios"}, 400

        if data.get("lgpd_assinada") is not True:
            return {"error": "É obrigatório aceitar os termos de LGPD para criar a conta."}, 400

        password_error = validate_password_strength(password)
        if password_error:
            return {"error": password_error}, 400

        try:
            dados_extras = {
                k: v
                for k, v in data.items()
                if k in CAMPOS_EDITAVEIS
                and k not in {
                    "nome", "email", "telefone", "instagram", "descricao",
                    "username", "permissao", "team",
                }
            }

            cadastrar_usuario(
                username=username,
                password=password,
                team=team,
                nome=data.get("nome"),
                email=data.get("email"),
                telefone=data.get("telefone"),
                instagram=data.get("instagram"),
                descricao=data.get("descricao"),
                permissao=data.get("permissao"),
                dados_extras=dados_extras,
            )
            return {"message": "Usuario cadastrado com sucesso"}, 201

        except ValueError as e:
            return {"error": str(e)}, 409

        except Exception:
            current_app.logger.exception("Erro interno ao cadastrar usuario")
            return {"error": "Erro interno ao cadastrar usuario"}, 500


@auth_ns.route("/auth/login")
class LoginUsuario(Resource):
    @auth_ns.doc(description="Login de usuario")
    def post(self):
        data = request.get_json() or {}

        username = normalizar_user(data.get("username") or "")
        password = data.get("password")

        if not all([username, password]):
            return {"error": "Usuario e senha sao obrigatorios"}, 400

        usuario = login(username, password)

        if isinstance(usuario, dict) and usuario.get("inactive"):
            return {"error": "Cadastro aguardando validação do RH."}, 403

        if usuario:
            return {
                "login": True,
                "message": "Login realizado com sucesso",
                "user": usuario,
            }, 200

        return {"error": "Usuario ou senha incorretos"}, 401


@auth_ns.route("/auth/switch-password")
class TrocarSenha(Resource):
    def post(self):
        data = request.get_json() or {}
        username = normalizar_user(data.get("username") or "")
        old_pass = data.get("old_pass")
        new_pass = data.get("new_pass")

        if not all([username, old_pass, new_pass]):
            return {"error": "username, old_pass e new_pass sao obrigatorios"}, 400

        password_error = validate_password_strength(new_pass)
        if password_error:
            return {"error": password_error}, 400

        if old_pass == new_pass:
            return {"error": "A nova senha deve ser diferente da senha atual"}, 400

        if not login(username, old_pass):
            return {"error": "Usuario ou senha incorretos"}, 401

        message = registrar_nova_senha(username, new_pass)
        if "error" in message:
            return {"ok": False, "message": message["error"]}, 400

        return {"ok": True, "message": message["ok"]}, 200


@auth_ns.route("/auth/recuperar-senha")
class RecuperarSenha(Resource):
    @auth_ns.doc(description="Recuperar senha por id do usuario")
    def post(self):
        data = request.get_json() or {}

        id_corretor = data.get("id_corretor")
        newpass = data.get("newpass")

        if not id_corretor or not newpass:
            return {"error": "id_corretor e newpass sao obrigatorios"}, 400

        password_error = validate_password_strength(newpass)
        if password_error:
            return {"error": password_error}, 400

        dados_corretor = retornar_infos(id_corretor=id_corretor)

        if not dados_corretor or "error" in dados_corretor:
            return {"error": "Usuario nao encontrado"}, 404

        username = normalizar_user(dados_corretor.get("username"))

        if not username:
            return {"error": "Username nao encontrado para este usuario"}, 404

        resultado = registrar_nova_senha(username, newpass)

        if "error" in resultado:
            return {"error": resultado["error"]}, 400

        return {"ok": "Senha alterada com sucesso"}, 200
