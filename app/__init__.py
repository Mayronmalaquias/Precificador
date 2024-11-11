from flask import Flask, request, jsonify, render_template, send_file
import pandas as pd
import openai
from app.clusterizacao import analisar_imovel_detalhado, clusterizar_dados2
import folium
from folium.plugins import HeatMap, MarkerCluster
import os
from dotenv import load_dotenv
from flask_caching import Cache

def create_app():
    app = Flask(__name__,template_folder='../templates', static_folder='../static')

    csv_file_path = './static/dados/dados_map.csv'  # Substitua pelo caminho do arquivo CSV
    load_dotenv()
    openai.api_key = os.getenv('OPENAI_API_KEY')

    # Configuração do cache
    cache = Cache(app, config={'CACHE_TYPE': 'simple'})

    @cache.cached(timeout=60)
    def carregar_dados():
        df = pd.read_csv('./static/dados/2024-09-06.csv')
        df_map = pd.read_csv(csv_file_path)
        return df, df_map

    # Rota para exibir o formulário
    @app.route('/', methods=['GET'])
    def index():
        df, df_map = carregar_dados()
        return render_template('index.html')

    @app.route('/carregar_mapa', methods=['GET'])
    def carregar_mapa():
        tipo_mapa = request.args.get('tipo')
        cluster_selecionado = request.args.get('cluster')
        df, df_map = carregar_dados()
        
        if(tipo_mapa == "mapaAnuncio" or tipo_mapa == "Mapa de anuncio"):
            return gerar_mapa(cluster_selecionado)
        else:
            return gerar_mapa2(cluster_selecionado)
        # return gerar_mapa()

    @app.route('/exibir_mapa', methods=['GET'])
    def exibir_mapa():
        mapa_html_path = './static/mapa/mapa_de_calor_com_limite.html'
        return send_file(mapa_html_path)

    @app.route('/analisar', methods=['POST'])
    def analisar():
        params = request.form
        tipo_imovel = params.get('tipoImovel')
        bairro = params.get('bairro')
        nrCluster = int(params.get('nrCluster')) - 1  # Convertendo o valor do cluster selecionado pelo usuário para índice (0 a 8)
        nrQuartos = int(params.get('quartos'))
        nrVagas = int(params.get('vagas'))

        metragem = None
        if nrQuartos == 0:
            nrQuartos = None
        if nrVagas == 10:
            resultados_df = analisar_imovel_detalhado(tipo_imovel=tipo_imovel, bairro=bairro, quartos=nrQuartos, metragem=metragem)
        else:
            resultados_df = analisar_imovel_detalhado(tipo_imovel=tipo_imovel, bairro=bairro, vaga_garagem=nrVagas, quartos=nrQuartos, metragem=metragem)

        resultados_df = resultados_df.T

        if resultados_df.empty:
            return jsonify({"error": "Nenhum dado encontrado para os parâmetros selecionados."}), 404
        valorM2Venda = resultados_df.iloc[nrCluster]['VALOR DE M² DE VENDA']
        valorM2Locacao = resultados_df.iloc[nrCluster]['VALOR DE M² DE ALUGUEL']

        valorVendaNominal = resultados_df.iloc[nrCluster]['VALOR DE VENDA NOMINAL']
        metragemMediaVenda = resultados_df.iloc[nrCluster]['METRAGEM MÉDIA DE VENDA']
        coeficienteVariacaoVenda = resultados_df.iloc[nrCluster]['COEFICIENTE DE VARIAÇÃO DE VENDA']
        tamanhoAmostraVenda = resultados_df.iloc[nrCluster]['TAMANHO DA AMOSTRA DE VENDA']

        valorLocacaoNominal = resultados_df.iloc[nrCluster]['VALOR DE ALUGUEL NOMINAL']
        metragemMediaLocacao = resultados_df.iloc[nrCluster]['METRAGEM MÉDIA DE ALUGUEL']
        coeficienteVariacaoLocacao = resultados_df.iloc[nrCluster]['COEFICIENTE DE VARIAÇÃO DE ALUGUEL']
        tamanhoAmostraLocacao = resultados_df.iloc[nrCluster]['TAMANHO DA AMOSTRA DE ALUGUEL']

        rentabilidadeMedia = resultados_df.iloc[nrCluster]['RENTABILIDADE MÉDIA']

        return jsonify({
            "valorM2Venda": valorM2Venda,
            "valorVendaNominal": valorVendaNominal,
            "metragemMediaVenda": metragemMediaVenda,
            "coeficienteVariacaoVenda": coeficienteVariacaoVenda,
            "tamanhoAmostraVenda": tamanhoAmostraVenda,
            "valorM2Locacao": valorM2Locacao,
            "valorLocacaoNominal": valorLocacaoNominal,
            "metragemMediaLocacao": metragemMediaLocacao,
            "coeficienteVariacaoLocacao": coeficienteVariacaoLocacao,
            "tamanhoAmostraLocacao": tamanhoAmostraLocacao,
            "rentabilidadeMedia": rentabilidadeMedia
        })

    def gerar_mapa(cluster_selecionado):
        # cluster_selecionado = 1
        cluster_selecionado = int(cluster_selecionado)
        print(f"MIRON AQUI{cluster_selecionado} FUNCAO GERAR MAPA1")
        csv_file_path = './static/dados/vendaC.csv'
        df = pd.read_csv(csv_file_path)

        # Verifica a presença das colunas necessárias
        if 'latitude' not in df.columns or 'longitude' not in df.columns or 'preco' not in df.columns or 'cluster' not in df.columns:
            raise ValueError("O arquivo CSV deve conter as colunas 'latitude', 'longitude', 'preco' e 'cluster'.")

        # Converte latitude e longitude para o formato correto, dividindo por 1.000.000
        df['latitude'] = df['latitude'] / 1e7
        df['longitude'] = df['longitude'] / 1e7

        # Filtra o DataFrame para o cluster especificado
        df_clusterizado = df[df['cluster'] == cluster_selecionado].dropna(subset=['latitude', 'longitude', 'preco'])

        # Cria o mapa
        mapa = folium.Map(location=[-15.7942, -47.8822], zoom_start=12)

        # Adiciona os dados de calor no mapa
        heat_data = [[row['latitude'], row['longitude'], row['preco']] for index, row in df_clusterizado.iterrows()]
        HeatMap(heat_data, min_zoom=10, max_zoom=12).add_to(mapa)

        # Adiciona marcadores no mapa para cada ponto filtrado
        marker_cluster = MarkerCluster().add_to(mapa)
        for index, row in df_clusterizado.iterrows():
            folium.Marker(
                location=[row['latitude'], row['longitude']],
                popup=f"Preço: R$ {row['preco']}",
            ).add_to(marker_cluster)

        # Adiciona uma legenda ao mapa
        legenda = """
        <div style="position: fixed; 
                    bottom: 50px; left: 50px; width: 200px; height: 100px; 
                    background-color: white; border:2px solid grey; z-index:9999; font-size:14px;">
            <h4>Legenda</h4>
            <p>Quantidade de anúncios em cada agrupamento. O mapa mostra até 5 pontos por coordenada.</p>
        </div>
        """
        mapa.get_root().html.add_child(folium.Element(legenda))
        mapa.save("./static/mapas/mapa_de_calor_com_limite.html")

        return mapa._repr_html_()
    
    def gerar_mapa2(cluster_selecionado):
        # cluster_selecionado = 1
        cluster_selecionado = int(cluster_selecionado)
        print(f"MIRON AQUI{cluster_selecionado} FUNCAO GERAR MAPA2")
        csv_file_path = './static/dados/vendaC.csv'
        df = pd.read_csv(csv_file_path)

        # Verifica a presença das colunas necessárias
        if 'latitude' not in df.columns or 'longitude' not in df.columns or 'valor_m2' not in df.columns or 'cluster' not in df.columns:
            raise ValueError("O arquivo CSV deve conter as colunas 'latitude', 'longitude', 'valor_m2' e 'cluster'.")

        # Converte latitude e longitude para o formato correto, dividindo por 1.000.000
        df['latitude'] = df['latitude'] / 1e7
        df['longitude'] = df['longitude'] / 1e7

        # Filtra o DataFrame para o cluster especificado
        df_clusterizado = df[df['cluster'] == cluster_selecionado].dropna(subset=['latitude', 'longitude', 'valor_m2'])

        # Cria o mapa
        mapa = folium.Map(location=[-15.7942, -47.8822], zoom_start=12)

        # Adiciona os dados de calor no mapa, usando valor_m2 como peso para a intensidade do calor
        heat_data = [[row['latitude'], row['longitude'], row['valor_m2']] for index, row in df_clusterizado.iterrows()]
        HeatMap(heat_data, min_opacity=0.2, radius=15, blur=20, max_zoom=12).add_to(mapa)

        # Adiciona uma legenda ao mapa
        legenda = """
        <div style="position: fixed; 
                    bottom: 50px; left: 50px; width: 200px; height: 100px; 
                    background-color: white; border:2px solid grey; z-index:9999; font-size:14px;">
            <h4>Legenda</h4>
            <p>Áreas com cores mais intensas representam locais com maior valor de M².</p>
        </div>
        """
        mapa.get_root().html.add_child(folium.Element(legenda))
        mapa.save("./static/mapas/mapa_de_calor_valor_m2.html")

        return mapa._repr_html_()

    return app
