from flask import request, jsonify
from flask_restx import Resource, Namespace
from app.services.analise_service import analisar_imovel_detalhado

analise_ns = Namespace('analise', description='Operacoes de análise de imóveis')

@analise_ns.route('/analise/imovel')
class AnalisarImovel(Resource):
    @analise_ns.doc(params={
        'tipoImovel': {'description': 'Tipo do imóvel (ex: apartamento, casa)', 'required': True, 'type': 'string'},
        'bairro': {'description': 'Nome do bairro', 'required': True, 'type': 'string'},
        'nrCluster': {'description': 'Número do cluster', 'required': True, 'type': 'integer'},
        'quartos': {'description': 'Número de quartos', 'required': True, 'type': 'integer'},
        'vagas': {'description': 'Número de vagas de garagem', 'required': True, 'type': 'integer'},
        'metragem': {'description': 'Área total do imóvel em m²', 'required': True, 'type': 'integer'}
    })
    def get(self):

        tipo_imovel = request.args.get('tipoImovel')
        bairro = request.args.get('bairro')
        nr_cluster = int(request.args.get('nrCluster')) # Convertendo o valor do cluster selecionado pelo usuário para índice (0 a 8)
        nr_quartos = int(request.args.get('quartos'))
        nr_vagas = int(request.args.get('vagas'))
        metragem = int(request.args.get('metragem'))


        resultados_df = analisar_imovel_detalhado(tipo_imovel=tipo_imovel, bairro=bairro, vaga_garagem=nr_vagas, quartos=nr_quartos, metragem=metragem)
        resultados_df = resultados_df.T
        print(resultados_df)

        # if resultados_df.empty:
        #     return jsonify({"error": "Nenhum dado encontrado para os parâmetros selecionados."}), 404

        return jsonify(resultados_df.iloc[nr_cluster].to_dict())
        # return jsonify({"correto": "api retornando com sucesso"})