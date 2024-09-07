import pandas as pd
import folium
from folium.plugins import HeatMap
import geopandas as gpd

# Exemplo de dataset (substitua pelos seus dados)
# Suponha que você tenha um DataFrame com a coluna 'bairro' e o número de anúncios por bairro

# Dataset de exemplo com bairros e número de anúncios
data = {
    'bairro': ['ASA NORTE', 'ASA SUL', 'LAGO SUL', 'LAGO NORTE', 'SUDOESTE'],
    'num_anuncios': [100, 150, 50, 75, 120]
}

df = pd.DataFrame(data)

# Suponha que temos um GeoDataFrame com as coordenadas dos bairros de Brasília
# Aqui você precisa de um arquivo com as coordenadas dos bairros ou obter um dataset de geolocalização.
# Para fins de exemplo, vamos criar um exemplo simples de coordenadas fictícias

coordinates = {
    'ASA NORTE': [-15.7625, -47.8692],
    'ASA SUL': [-15.7986, -47.8919],
    'LAGO SUL': [-15.8376, -47.8753],
    'LAGO NORTE': [-15.7300, -47.8297],
    'SUDOESTE': [-15.7895, -47.9275]
}

# Adicionando as coordenadas ao DataFrame
df['latitude'] = df['bairro'].apply(lambda x: coordinates[x][0])
df['longitude'] = df['bairro'].apply(lambda x: coordinates[x][1])

# Criando o mapa centralizado em Brasília
mapa = folium.Map(location=[-15.7942, -47.8822], zoom_start=12)

# Preparar os dados para o mapa de calor
heat_data = [[row['latitude'], row['longitude'], row['num_anuncios']] for index, row in df.iterrows()]

# Adicionando o HeatMap ao mapa
HeatMap(heat_data).add_to(mapa)

# Salvando o mapa em um arquivo HTML
mapa.save("mapa_de_calor_brasilia.html")

print("Mapa gerado: mapa_de_calor_brasilia.html")
