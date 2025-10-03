from flask import request, jsonify
from flask_restx import Resource, Namespace
from app.services.graph_service import gerar_grafico_linha

graph_ns = Namespace('graph', description="Graficos de dados")

@graph_ns.route('/graph/graficoLinha')
class GerarGraficoLinha(Resource):
    @graph_ns.doc(description='gerar grafico linha')
    def get(self):
        """Endpoint para cadastrar um novo usuário"""
        
        return gerar_grafico_linha()