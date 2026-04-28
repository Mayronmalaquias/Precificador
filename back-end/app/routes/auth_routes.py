from flask import request
from flask_restx import Resource, Namespace
from app.services.auth_service import cadastrar_usuario, login, registrar_nova_senha
from app.services.usuarios_service import retornar_infos
from app.utils.helpers import normalizar_user

auth_ns = Namespace('auth', description="Autenticação de usuários")


@auth_ns.route('/auth/cadastro')
class CadastroUsuario(Resource):
    @auth_ns.doc(description='Cadastro de novo usuário')
    def post(self):
        data = request.get_json() or {}

        username = (data.get('username') or '')
        username = normalizar_user(username)
        password = data.get('password')
        team = data.get('team')

        nome = data.get('nome')
        email = data.get('email')
        telefone = data.get('telefone')
        instagram = data.get('instagram')
        descricao = data.get('descricao')
        id_usuarios = data.get('id_usuarios')
        permissao = data.get('permissao')

        if not all([username, password, team]):
            return {'error': 'Campos username, password e team são obrigatórios'}, 400

        if len(password) < 8:
            return {'error': 'A senha deve conter no mínimo 8 caracteres'}, 400

        try:
            cadastrar_usuario(
                username=username,
                password=password,
                team=team,
                nome=nome,
                email=email,
                telefone=telefone,
                instagram=instagram,
                descricao=descricao,
                id_usuarios=id_usuarios,
                permissao=permissao
            )
            return {'message': 'Usuário cadastrado com sucesso'}, 201

        except ValueError as e:
            return {'error': str(e)}, 409

        except Exception as e:
            return {'error': f'Erro interno ao cadastrar usuário: {str(e)}'}, 500


@auth_ns.route('/auth/login')
class LoginUsuario(Resource):
    @auth_ns.doc(description='Login de usuário')
    def post(self):
        data = request.get_json() or {}

        username = (data.get('username') or '')
        username = normalizar_user(username)
        password = data.get('password')

        if not all([username, password]):
            return {'error': 'Usuário e senha são obrigatórios'}, 400

        usuario = login(username, password)

        if usuario:
            return {
                "login": True,
                "message": "Login realizado com sucesso",
                "user": usuario
            }, 200

        return {"error": "Usuário ou senha incorretos"}, 401


@auth_ns.route('/auth/switch-password')
class TrocarSenha(Resource):
    def post(self):
        data = request.get_json() or {}
        username = (data.get('username') or '')
        username = normalizar_user(username)
        old_pass = data.get('old_pass')
        new_pass = data.get('new_pass')

        if not all([username, old_pass, new_pass]):
            return {"error": "username, old_pass e new_pass são obrigatórios"}, 400
        
        if len(new_pass) < 8:
            return {'error': 'A senha deve conter no mínimo 8 caracteres'}, 400

        if new_pass.lower() == new_pass or new_pass.upper() == new_pass:
            return {'error': 'A senha precisa ter letras maiúsculas e minúsculas'}, 400

        if not any(c.isalpha() for c in new_pass):
            return {'error': 'A senha precisa ter pelo menos uma letra'}, 400

        if not any(c.isdigit() for c in new_pass):
            return {'error': 'A senha precisa ter pelo menos um número'}, 400
        if old_pass == new_pass:
            return {'error': 'A nova senha deve ser diferente da senha atual'}, 400

        flag = login(username,old_pass)
        if flag:
            message = registrar_nova_senha(username,new_pass)
            if "error" in message:
                return {
                    "ok":False,
                    "message": message['error']
                },400
            return {
                "ok":True,
                "message": message['ok']
            },200
        else:
            return {"error": "Usuário ou senha incorretos"}, 401
    

@auth_ns.route('/auth/recuperar-senha')
class RecuperarSenha(Resource):
    @auth_ns.doc(description='Recuperar senha por id do usuário')
    def post(self):
        data = request.get_json() or {}

        id_corretor = data.get('id_corretor')
        newpass = data.get('newpass')

        if not id_corretor or not newpass:
            return {
                "error": "id_corretor e newpass são obrigatórios"
            }, 400

        if len(newpass) < 8:
            return {'error': 'A senha deve conter no mínimo 8 caracteres'}, 400

        if newpass.lower() == newpass or newpass.upper() == newpass:
            return {'error': 'A senha precisa ter letras maiúsculas e minúsculas'}, 400

        if not any(c.isalpha() for c in newpass):
            return {'error': 'A senha precisa ter pelo menos uma letra'}, 400

        if not any(c.isdigit() for c in newpass):
            return {'error': 'A senha precisa ter pelo menos um número'}, 400
        
        dados_corretor = retornar_infos(id_corretor=id_corretor)

        if not dados_corretor or "error" in dados_corretor:
            return {"error": "Usuário não encontrado"}, 404

        username = dados_corretor.get("username")
        username = normalizar_user(username)

        if not username:
            return {"error": "Username não encontrado para este usuário"}, 404

        resultado = registrar_nova_senha(username, newpass)

        if "error" in resultado:
            return {"error": resultado["error"]}, 400

        return {"ok": "Senha alterada com sucesso"}, 200



