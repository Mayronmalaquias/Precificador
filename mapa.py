def gerar_mapa(csv_file_path):
    """
    Função para gerar um mapa de calor a partir de um arquivo CSV contendo latitude, longitude e preço.
    
    Parâmetros:
    csv_file_path (str): Caminho para o arquivo CSV que contém colunas 'latitude', 'longitude' e 'preco'.

    Retorna:
    O HTML do mapa de calor gerado.
    """
    
    # Carregar o CSV diretamente
    df = pd.read_csv(csv_file_path)
    
    # Certifique-se de que o DataFrame tem as colunas necessárias
    if 'latitude' not in df.columns or 'longitude' not in df.columns or 'preco' not in df.columns:
        raise ValueError("O arquivo CSV deve conter as colunas 'latitude', 'longitude' e 'preco'.")
    
    # Remover linhas com dados ausentes
    df_filtrado = df[['latitude', 'longitude', 'preco']].dropna()

    # Criar o mapa centralizado em Brasília
    mapa = folium.Map(location=[-15.7942, -47.8822], zoom_start=12)

    # Preparar os dados para o HeatMap
    heat_data = [[row['latitude'], row['longitude'], row['preco']] for index, row in df_filtrado.iterrows()]

    # Adicionar o HeatMap ao mapa
    HeatMap(heat_data).add_to(mapa)

    # Salvar o mapa em um arquivo HTML
    mapa.save("mapa_de_calor_brasilia.html")

    # Retornar o HTML do mapa gerado
    return mapa._repr_html_()