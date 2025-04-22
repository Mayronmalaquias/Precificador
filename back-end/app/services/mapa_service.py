import pandas as pd
import folium
from folium.plugins import HeatMap, MarkerCluster

def gerar_mapa_anuncio_clusterizado(cluster_selecionado):
        # cluster_selecionado = 1
    cluster_selecionado = int(cluster_selecionado)
    csv_file_path = './dados/vendaC.csv'
    df = pd.read_csv(csv_file_path)

        # Verifica a presença das colunas necessárias
    if 'latitude' not in df.columns or 'longitude' not in df.columns or 'preco' not in df.columns or 'cluster' not in df.columns:
        raise ValueError("O arquivo CSV deve conter as colunas 'latitude', 'longitude', 'preco' e 'cluster'.")

        # Converte latitude e longitude para o formato correto, dividindo por 1.000.000
    df['latitude'] = df['latitude'] / 1e7
    df['longitude'] = df['longitude'] / 1e7

        # Filtra o DataFrame para o cluster especificado
    if(cluster_selecionado != 0):

        cluster_grupo1 = [1,2,3]
        cluster_grupo2 = [4,5,6]
        cluster_grupo3 = [7,8,9]
        if(cluster_selecionado in cluster_grupo1):
            cluster_grupo_mapa = cluster_grupo1
        elif(cluster_selecionado in cluster_grupo2):
            cluster_grupo_mapa = cluster_grupo2
        elif (cluster_selecionado in cluster_grupo3):
            cluster_grupo_mapa = cluster_grupo3
        df_clusterizado = df[df['cluster'].isin(cluster_grupo_mapa)].dropna(subset=['latitude', 'longitude', 'preco'])
    else:
        df_clusterizado = df.copy()
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
    legenda = """"""
    mapa.get_root().html.add_child(folium.Element(legenda))
    mapa.save("./mapas/mapa_de_calor_com_limite.html")

    return "../mapas/mapa_de_calor_com_limite.html"
    # return mapa._repr_html_()

def gerar_mapa_anuncio_completo():
    csv_file_path = './dados/dados_map.csv'
    df = pd.read_csv(csv_file_path)

    if 'latitude' not in df.columns or 'longitude' not in df.columns or 'preco' not in df.columns:
        raise ValueError("O arquivo CSV deve conter as colunas 'latitude', 'longitude' e 'preco'.")

    df_filtrado = df[['latitude', 'longitude', 'preco']].dropna()
    df_filtrado = df_filtrado.groupby(['latitude', 'longitude']).head(5)

    mapa = folium.Map(location=[-15.7942, -47.8822], zoom_start=12)

    heat_data = [[row['latitude'], row['longitude'], row['preco']] for index, row in df_filtrado.iterrows()]
    HeatMap(heat_data, min_zoom=10, max_zoom=12).add_to(mapa)

    marker_cluster = MarkerCluster().add_to(mapa)
    for index, row in df_filtrado.iterrows():
        folium.Marker(
            location=[row['latitude'], row['longitude']],
            popup=folium.Popup(
                f"""<b>Preço:</b> R$ {float(row['preco']):,.2f}<br>""",
                max_width=300
            ),
        ).add_to(marker_cluster)

    legenda = """
        """
    mapa.get_root().html.add_child(folium.Element(legenda))
    mapa.save("./mapas/mapa_de_calor_com_limite.html")
    # print(mapa._repr_html_())

    # return mapa._repr_html_()
    return "../mapas/mapa_de_calor_com_limite.html"
    
def gerar_mapa_m2_completo(cluster_selecionado):
    csv_file_path = './dados/vendaC.csv'
        # Carrega os dados
    df = pd.read_csv("./dados/dados_map.csv")

        # Verifica a presença das colunas necessárias
    if 'bairro' not in df.columns or 'latitude' not in df.columns or 'longitude' not in df.columns or 'valor_m2' not in df.columns:
        raise ValueError("O arquivo CSV deve conter as colunas 'regiao', 'latitude', 'longitude' e 'valor_m2'.")

        # Calcula a média de valor_m2 por região
    media_por_regiao = df.groupby('bairro')['valor_m2'].mean().reset_index()
    media_por_regiao = media_por_regiao.rename(columns={'valor_m2': 'media_valor_m2'})

        # Mescla as médias de volta ao DataFrame original
    df = df.merge(media_por_regiao, on='bairro')

        # Aplicar um peso decrescente para ajustar a intensidade ao redor das áreas mais vermelhas
        # Aqui vamos ajustar o valor com base em uma "intensidade máxima" de 10%
    df['valor_m2_ajustado'] = df.apply(
        lambda row: row['media_valor_m2'] * 0.9 if row['media_valor_m2'] < df['media_valor_m2'].max() else row['media_valor_m2'],
        axis=1
    )

        # Normaliza o valor ajustado para a faixa 0-1
    df['valor_m2_normalizado'] = (df['valor_m2_ajustado'] - df['valor_m2_ajustado'].min()) / (df['valor_m2_ajustado'].max() - df['valor_m2_ajustado'].min())

        # Cria o mapa
    mapa = folium.Map(location=[-15.7942, -47.8822], zoom_start=12)

        # Adiciona os dados de calor no mapa com o valor normalizado ajustado
    heat_data = [[row['latitude'], row['longitude'], row['valor_m2_normalizado']] for index, row in df.iterrows()]
    HeatMap(
        heat_data,
        min_opacity=0.4,
        radius=25,
        blur=20,
        max_zoom=12,
        gradient={0.2: 'blue', 0.4: 'lime', 0.6: 'yellow', 0.8: 'orange', 1: 'red'}
    ).add_to(mapa)

        # Adiciona uma legenda ao mapa
    legenda = """
        """
    mapa.get_root().html.add_child(folium.Element(legenda))
    mapa.save("./mapas/mapa_de_calor_valor_m2_ajustado.html")

    # return mapa._repr_html_()
    return "../mapas/mapa_de_calor_valor_m2_ajustado.html"
    
def gerar_mapa_m2_cluterizado(cluster_selecionado):
    csv_file_path = './dados/vendaC.csv'
        # Carrega os dados
    df = pd.read_csv("./dados/vendaC.csv")

        # Verifica se há dados após o filtro de cluster
    df['cluster'] = df['cluster'].astype(int)
    df = df[df['cluster'] == int(cluster_selecionado)].dropna(subset=['latitude', 'longitude', 'valor_m2'])
    if df.empty:
        raise ValueError(f"Nenhum dado encontrado para o cluster selecionado: {cluster_selecionado}")

        # Verifica a presença das colunas necessárias
    if 'bairro' not in df.columns or 'latitude' not in df.columns or 'longitude' not in df.columns or 'valor_m2' not in df.columns or 'cluster' not in df.columns:
        raise ValueError("O arquivo CSV deve conter as colunas 'bairro', 'latitude', 'longitude' e 'valor_m2'.")

        # Calcula a média de valor_m2 por bairro
    media_por_regiao = df.groupby('bairro')['valor_m2'].mean().reset_index()
    media_por_regiao = media_por_regiao.rename(columns={'valor_m2': 'media_valor_m2'})

    df['latitude'] = df['latitude'] / 1e7
    df['longitude'] = df['longitude'] / 1e7

        # Mescla as médias de volta ao DataFrame original
    df = df.merge(media_por_regiao, on='bairro', how='left')
    if df['media_valor_m2'].isnull().all():
        raise ValueError("Erro ao calcular a média de valor_m2 por bairro. Verifique os dados de 'bairro' e 'valor_m2'.")

        # # Aplicar um peso decrescente para ajustar a intensidade ao redor das áreas mais vermelhas
    df['valor_m2_ajustado'] = df.apply(
        lambda row: row['media_valor_m2'] * 0.9 if row['media_valor_m2'] < df['media_valor_m2'].max() else row['media_valor_m2'],
        axis=1
    )

        # # # Normaliza o valor ajustado para a faixa 0-1
        # if df['valor_m2_ajustado'].max() == df['valor_m2_ajustado'].min():
        #     raise ValueError("Todos os valores ajustados são iguais. Não é possível normalizar.")
        # df['valor_m2_normalizado'] = (df['valor_m2_ajustado'] - df['valor_m2_ajustado'].min()) / (df['valor_m2_ajustado'].max() - df['valor_m2_ajustado'].min())

        # Cria o mapa
    mapa = folium.Map(location=[-15.7942, -47.8822], zoom_start=12)

        # Adiciona os dados de calor no mapa com o valor normalizado ajustado
    heat_data = [[row['latitude'], row['longitude'], row['valor_m2']] for index, row in df.iterrows()]
    if not heat_data:
        raise ValueError("Nenhum dado de calor encontrado para plotar no mapa.")
    HeatMap(
        heat_data,
        min_opacity=0.4,
        radius=25,
        blur=20,
        max_zoom=12,
        gradient={0.2: 'blue', 0.4: 'lime', 0.6: 'yellow', 0.8: 'orange', 1: 'red'}
    ).add_to(mapa)

        # Adiciona uma legenda ao mapa
    legenda = """
        """
    mapa.get_root().html.add_child(folium.Element(legenda))
    mapa.save("./mapas/mapa_de_calor_valor_m2_ajustado.html")

    # return mapa._repr_html_()
    return "../mapas/mapa_de_calor_valor_m2_ajustado.html"