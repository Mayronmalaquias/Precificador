from flask import request
from flask_restx import Namespace, Resource

from app import cache
from app.services.analise_service import consultar_estudo_metricas, get_data_cache_token


analise_ns = Namespace("analise", description="Operacoes de analise de imoveis")


def _make_cache_key():
    token = get_data_cache_token()
    return f"analise:{request.full_path}|token:{token}"


def _int_arg(name, default=None):
    value = request.args.get(name)
    if value is None or value == "":
        return default
    return int(value)


def _consultar_metricas(oferta):
    resultado = consultar_estudo_metricas(
        tipo_imovel=request.args.get("tipoImovel"),
        bairro=request.args.get("bairro"),
        quartos=_int_arg("quartos", 0),
        nr_cluster=_int_arg("nrCluster", 0),
        oferta=oferta,
        vagas=_int_arg("vagas", None),
        metragem=_int_arg("metragem", None),
    )

    if not resultado:
        return {
            "error": f"Metrica de {oferta.lower()} nao encontrada para os filtros informados."
        }, 404

    return resultado, 200


@analise_ns.route("/imovel/venda")
class AnalisarImovelVenda(Resource):
    @analise_ns.doc(params={
        "tipoImovel": {"description": "Tipo do imovel", "required": True, "type": "string"},
        "bairro": {"description": "Nome do bairro", "required": True, "type": "string"},
        "nrCluster": {"description": "Condicao/cluster selecionado", "required": True, "type": "integer"},
        "quartos": {"description": "Numero de quartos", "required": True, "type": "integer"},
        "vagas": {"description": "Vagas de garagem", "required": True, "type": "integer"},
        "metragem": {"description": "Area do imovel em m2", "required": True, "type": "integer"},
    })
    # @cache.cached(timeout=3600, key_prefix=_make_cache_key)
    def get(self):
        return _consultar_metricas("Venda")


@analise_ns.route("/imovel/aluguel")
class AnalisarImovelAluguel(Resource):
    @analise_ns.doc(params={
        "tipoImovel": {"description": "Tipo do imovel", "required": True, "type": "string"},
        "bairro": {"description": "Nome do bairro", "required": True, "type": "string"},
        "nrCluster": {"description": "Condicao/cluster selecionado", "required": True, "type": "integer"},
        "quartos": {"description": "Numero de quartos", "required": True, "type": "integer"},
        "vagas": {"description": "Vagas de garagem", "required": True, "type": "integer"},
        "metragem": {"description": "Area do imovel em m2", "required": True, "type": "integer"},
    })
    # @cache.cached(timeout=3600, key_prefix=_make_cache_key)
    def get(self):
        return _consultar_metricas("Aluguel")
