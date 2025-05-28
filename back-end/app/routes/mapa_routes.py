from flask import request, send_file
from flask_restx import Namespace, Resource
from app.services.mapa_service import gerar_mapa_m2_completo, gerar_mapa_m2_cluterizado, gerar_mapa_anuncio_clusterizado, gerar_mapa_anuncio_completo

mapa_ns = Namespace('mapa', description='Operacoes relacionadas a mapas')

@mapa_ns.route('/mapa/carregar')
class CarregarMapa(Resource):
    @mapa_ns.doc(params ={
        'tipo': {'description': 'tipo do mapa', 'required': True, 'type': 'string'},
        'cluster' : {'description': 'cluster selecionado', 'required':True, 'type':'integer'},
        'tamanho': {'description': 'tamanho do mapa', 'required': True, 'type': 'string'}
    })
    def get(self):
        tipo_mapa = request.args.get('tipo')
        cluster_selecionado = int(request.args.get('cluster'))
        tipo_mapa_tam = request.args.get('tamanho')
        print(f"[LOG]: Cluster: {cluster_selecionado} Tipo: {type(cluster_selecionado)}")
        # df, df_map = carregar_dados()
        
        if tipo_mapa == "mapaAnuncio" or tipo_mapa == "Mapa de anuncio":
            if tipo_mapa_tam == "mapaCluster" or tipo_mapa_tam == "Mapa Clusterizado":
                mapa = gerar_mapa_anuncio_clusterizado(cluster_selecionado)
            else:
                mapa = gerar_mapa_anuncio_completo()
        else:
            if tipo_mapa_tam == "mapaCluster" or tipo_mapa_tam == "Mapa Clusterizado":
                mapa = gerar_mapa_m2_cluterizado(cluster_selecionado)
            elif tipo_mapa_tam == "mapaCompleto" or tipo_mapa_tam == "Mapa Completo":
                mapa = gerar_mapa_m2_completo(cluster_selecionado)
        # return mapa
        # return send_file('../mapas/mapa_de_calor_com_limite.html')
        return send_file(mapa)