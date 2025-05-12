from flask import request, jsonify
from flask_restx import Resource, Namespace
from app.services.auth_service import cadastrar_usuario, login

auth_ns = Namespace('auth', description="Autenticação de usuários")

@auth_ns.route('/auth/cadastro')
class CadastroUsuario(Resource):
    @auth_ns.doc(description='Cadastro de novo usuário')
    def post(self):
        """Endpoint para cadastrar um novo usuário"""
        data = request.get_json()

        username = str(data.get('username'))
        password = data.get('password')
        team = data.get('team')

        if not all([username, password, team]):
            return {'error': 'Todos os campos são obrigatórios'}, 400

        if len(password) < 8:
            return {'error': 'A senha deve conter no mínimo 8 caracteres'}, 400

        cadastrar_usuario(username, password, team)
        return {'message': 'Usuário cadastrado com sucesso'}, 201


@auth_ns.route('/auth/login')
class LoginUsuario(Resource):
    @auth_ns.doc(description='Login de usuário')
    def post(self):
        """Endpoint para login de usuário"""
        data = request.get_json()

        username = data.get('username')
        password = data.get('password')

        if not all([username, password]):
            return {'error': 'Usuário e senha são obrigatórios'}, 400

        if login(username, password):
            return jsonify({'login': True, 'message': 'Login realizado com sucesso'})
        else:
            return {'error': 'Usuário ou senha incorretos'}, 401
