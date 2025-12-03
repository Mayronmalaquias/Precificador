from flask import request, jsonify
from flask_restx import Resource, Namespace
from app.services.auth_service import cadastrar_usuario, login

auth_ns = Namespace('auth', description="Autenticação de usuários")


@auth_ns.route('/auth/cadastro')
class CadastroUsuario(Resource):
    @auth_ns.doc(description='Cadastro de novo usuário')
    def post(self):
        """Endpoint para cadastrar um novo usuário"""
        data = request.get_json() or {}

        username  = str(data.get('username'))
        password  = data.get('password')
        team      = data.get('team')

        # novos campos
        nome      = data.get('nome')
        email     = data.get('email')
        telefone  = data.get('telefone')
        instagram = data.get('instagram')
        descricao = data.get('descricao')

        # validações básicas
        if not all([username, password, team]):
            return {'error': 'Campos username, password e team são obrigatórios'}, 400

        if len(password) < 8:
            return {'error': 'A senha deve conter no mínimo 8 caracteres'}, 400

        # aqui você poderia validar se já existe usuário/e-mail, etc.

        cadastrar_usuario(
            username=username,
            password=password,
            team=team,
            nome=nome,
            email=email,
            telefone=telefone,
            instagram=instagram,
            descricao=descricao
        )
        return {'message': 'Usuário cadastrado com sucesso'}, 201


@auth_ns.route('/auth/login')
class LoginUsuario(Resource):
    @auth_ns.doc(description='Login de usuário')
    def post(self):
        """Endpoint para login de usuário"""
        data = request.get_json() or {}

        username = data.get('username')
        password = data.get('password')

        if not all([username, password]):
            return {'error': 'Usuário e senha são obrigatórios'}, 400

        usuario = login(username, password)

        if usuario:
            # monta o objeto "usuario" que o front vai guardar
            usuario_json = {
                "username": usuario.username,
                "team": usuario.team,
                "nome": usuario.nome,
                "email": usuario.email,
                "telefone": usuario.telefone,
                "instagram": usuario.instagram,
                "descricao": usuario.descricao,
            }

            return jsonify({
                'login': True,
                'message': 'Login realizado com sucesso',
                'usuario': usuario_json
            })
        else:
            return {'error': 'Usuário ou senha incorretos'}, 401
