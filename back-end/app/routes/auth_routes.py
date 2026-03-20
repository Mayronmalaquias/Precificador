from flask import request
from flask_restx import Resource, Namespace
from app.services.auth_service import cadastrar_usuario, login

auth_ns = Namespace('auth', description="Autenticação de usuários")


@auth_ns.route('/auth/cadastro')
class CadastroUsuario(Resource):
    @auth_ns.doc(description='Cadastro de novo usuário')
    def post(self):
        data = request.get_json() or {}

        username = (data.get('username') or '').strip()
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

        username = data.get('username')
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