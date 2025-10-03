from flask import request, jsonify
from flask_restx import Resource, Namespace
from app.services.analise_service import (
    analisar_imovel_detalhado,
    get_data_cache_token,
    get_precomputed_result,  # NOVO
)
from app import cache

analise_ns = Namespace('analise', description='Operações de análise de imóveiIs')

def _make_cache_key():
    token = get_data_cache_token()
    return f"analise:{request.full_path}|token:{token}"

# ---------- VENDA ----------
@analise_ns.route('/imovel/venda')
class AnalisarImovelVenda(Resource):
    @analise_ns.doc(params={
        'tipoImovel': {'description': 'Tipo do imóvel (ex: apartamento, casa)', 'required': True, 'type': 'string'},
        'bairro': {'description': 'Nome do bairro', 'required': True, 'type': 'string'},
        'nrCluster': {'description': 'Número do cluster', 'required': True, 'type': 'integer'},
        'quartos': {'description': 'Número de quartos', 'required': True, 'type': 'integer'},
        'vagas': {'description': 'Número de vagas de garagem', 'required': True, 'type': 'integer'},
        'metragem': {'description': 'Área do imóvel em m²', 'required': True, 'type': 'integer'}
    })
    # @cache.cached(timeout=3600, key_prefix=_make_cache_key)
    def get(self):
        tipo_imovel = request.args.get('tipoImovel')
        bairro = request.args.get('bairro')
        nr_cluster = int(request.args.get('nrCluster'))
        nr_quartos = int(request.args.get('quartos'))
        # Os campos abaixo podem estar desativados no front por enquanto
        nr_vagas = int(request.args.get('vagas')) if request.args.get('vagas') is not None else None
        metragem = int(request.args.get('metragem')) if request.args.get('metragem') is not None else None

        # 1) TENTA PRÉ-CALCULADO
        pre = get_precomputed_result(tipo_imovel, bairro, nr_quartos, nr_cluster, oferta="Venda")
        if pre:
            return jsonify(pre)

        # 2) FALLBACK PARA A SUA LÓGICA SENSÍVEL (inalterada)
        resultado = analisar_imovel_detalhado(
            tipo_imovel=tipo_imovel,
            bairro=bairro,
            vaga_garagem=nr_vagas,
            quartos=nr_quartos,
            metragem=metragem
        )

        venda = resultado['venda']
        if nr_cluster >= len(venda):
            return jsonify({"error": "Cluster não encontrado."}), 404
        return jsonify(venda[nr_cluster])

# ---------- ALUGUEL ----------
@analise_ns.route('/imovel/aluguel')
class AnalisarImovelAluguel(Resource):
    @analise_ns.doc(params={
        'tipoImovel': {'description': 'Tipo do imóvel (ex: apartamento, casa)', 'required': True, 'type': 'string'},
        'bairro': {'description': 'Nome do bairro', 'required': True, 'type': 'string'},
        'nrCluster': {'description': 'Número do cluster', 'required': True, 'type': 'integer'},
        'quartos': {'description': 'Número de quartos', 'required': True, 'type': 'integer'},
        'vagas': {'description': 'Número de vagas de garagem', 'required': True, 'type': 'integer'},
        'metragem': {'description': 'Área do imóvel em m²', 'required': True, 'type': 'integer'}
    })
    @cache.cached(timeout=3600, key_prefix=_make_cache_key)
    def get(self):
        tipo_imovel = request.args.get('tipoImovel')
        bairro = request.args.get('bairro')
        nr_cluster = int(request.args.get('nrCluster'))
        nr_quartos = int(request.args.get('quartos'))
        nr_vagas = int(request.args.get('vagas')) if request.args.get('vagas') is not None else None
        metragem = int(request.args.get('metragem')) if request.args.get('metragem') is not None else None
        # 1) TENTA PRÉ-CALCULADO
        pre = get_precomputed_result(tipo_imovel, bairro, nr_quartos, nr_cluster, oferta="Aluguel")
        if pre:
            return jsonify(pre)

        resultado = analisar_imovel_detalhado(
            tipo_imovel=tipo_imovel,
            bairro=bairro,
            vaga_garagem=nr_vagas,
            quartos=nr_quartos,
            metragem=metragem
        )

        aluguel = resultado['aluguel']
        if nr_cluster >= len(aluguel):
            return jsonify({"error": "Cluster não encontrado."}), 404
        return jsonify(aluguel[nr_cluster])
