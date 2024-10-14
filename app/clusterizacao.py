import pandas as pd
from sklearn.cluster import KMeans
import numpy as np

input_file = "./static/dados/2024-09-06.csv"

def remover_outliers_iqr(df, coluna):
    Q1 = df[coluna].quantile(0.25)
    Q3 = df[coluna].quantile(0.75)
    IQR = Q3 - Q1
    filtro = (df[coluna] >= (Q1 - 1.5 * IQR)) & (df[coluna] <= (Q3 + 1.5 * IQR))
    return df[filtro]

def calcular_rentabilidade(valor_locacao, valor_venda):
    return (valor_locacao * 12) / valor_venda if valor_venda != 0 else np.nan

def calcular_metricas_cluster(df, valor_coluna, oferta_tipo):
    metricas = {}

    if oferta_tipo == 'Venda':
        metricas['VALOR DE M² DE VENDA'] = df[valor_coluna].mean()
        metricas['VALOR DE VENDA NOMINAL'] = df['preco'].mean()
        metricas['METRAGEM MÉDIA DE VENDA'] = df['area_util'].mean()
        metricas['COEFICIENTE DE VARIAÇÃO DE VENDA'] = df[valor_coluna].std() / df[valor_coluna].mean() if df[valor_coluna].mean() != 0 else np.nan
        metricas['TAMANHO DA AMOSTRA DE VENDA'] = len(df)
    else:
        metricas['VALOR DE M² DE ALUGUEL'] = df[valor_coluna].mean()
        metricas['VALOR DE ALUGUEL NOMINAL'] = df['preco'].mean()
        metricas['METRAGEM MÉDIA DE ALUGUEL'] = df['area_util'].mean()
        metricas['COEFICIENTE DE VARIAÇÃO DE ALUGUEL'] = df[valor_coluna].std() / df[valor_coluna].mean() if df[valor_coluna].mean() != 0 else np.nan
        metricas['TAMANHO DA AMOSTRA DE ALUGUEL'] = len(df)

    return metricas

def formatar_resultados(df):
    df_formatted = df.copy()

    # Formatando os valores em reais (R$) e metros quadrados (m²)
    df_formatted['VALOR DE M² DE VENDA'] = df_formatted['VALOR DE M² DE VENDA'].apply(lambda x: f"R$ {x:,.2f} /m²")
    df_formatted['VALOR DE VENDA NOMINAL'] = df_formatted['VALOR DE VENDA NOMINAL'].apply(lambda x: f"R$ {x:,.2f}")
    df_formatted['METRAGEM MÉDIA DE VENDA'] = df_formatted['METRAGEM MÉDIA DE VENDA'].apply(lambda x: f"{x:.2f} m²")

    df_formatted['VALOR DE M² DE ALUGUEL'] = df_formatted['VALOR DE M² DE ALUGUEL'].apply(lambda x: f"R$ {x:,.2f} /m²")
    df_formatted['VALOR DE ALUGUEL NOMINAL'] = df_formatted['VALOR DE ALUGUEL NOMINAL'].apply(lambda x: f"R$ {x:,.2f}")
    df_formatted['METRAGEM MÉDIA DE ALUGUEL'] = df_formatted['METRAGEM MÉDIA DE ALUGUEL'].apply(lambda x: f"{x:.2f} m²")

    # Formatando coeficiente de variação em porcentagem
    df_formatted['COEFICIENTE DE VARIAÇÃO DE VENDA'] = df_formatted['COEFICIENTE DE VARIAÇÃO DE VENDA'].apply(lambda x: f"{x:.2%}")
    df_formatted['COEFICIENTE DE VARIAÇÃO DE ALUGUEL'] = df_formatted['COEFICIENTE DE VARIAÇÃO DE ALUGUEL'].apply(lambda x: f"{x:.2%}")

    # Formatando a rentabilidade média em porcentagem
    df_formatted['RENTABILIDADE MÉDIA'] = df_formatted['RENTABILIDADE MÉDIA'].apply(lambda x: f"{x:.2%}")

    return df_formatted

def clusterizar_dados(df, valor_coluna, oferta_tipo, n_clusters=9):
    df_oferta = df[df['oferta'] == oferta_tipo].copy()

    if not df_oferta.empty and valor_coluna in df_oferta.columns and len(df_oferta) >= n_clusters:
        X = df_oferta[[valor_coluna]].values
        kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
        df_oferta.loc[:, "cluster"] = kmeans.fit_predict(X)
        df_oferta.loc[:, 'cluster'] = df_oferta['cluster'].astype('category')

        metricas_clusters = []
        for cluster in sorted(df_oferta['cluster'].unique()):
            cluster_data = df_oferta[df_oferta['cluster'] == cluster]
            metricas = calcular_metricas_cluster(cluster_data, valor_coluna, oferta_tipo)
            metricas['Cluster'] = cluster
            metricas_clusters.append(metricas)

        metricas_df = pd.DataFrame(metricas_clusters)

        if oferta_tipo == 'Venda':
            metricas_df = metricas_df.reindex(columns=['VALOR DE M² DE VENDA', 'VALOR DE VENDA NOMINAL',
                                                       'METRAGEM MÉDIA DE VENDA', 'COEFICIENTE DE VARIAÇÃO DE VENDA',
                                                       'TAMANHO DA AMOSTRA DE VENDA'], fill_value=np.nan)
        else:
            metricas_df = metricas_df.reindex(columns=['VALOR DE M² DE ALUGUEL', 'VALOR DE ALUGUEL NOMINAL',
                                                       'METRAGEM MÉDIA DE ALUGUEL', 'COEFICIENTE DE VARIAÇÃO DE ALUGUEL',
                                                       'TAMANHO DA AMOSTRA DE ALUGUEL'], fill_value=np.nan)
        return metricas_df.reset_index(drop=True)  # Inclui o índice como coluna
    else:
        if oferta_tipo == 'Venda':
            return pd.DataFrame(columns=['VALOR DE M² DE VENDA', 'VALOR DE VENDA NOMINAL',
                                         'METRAGEM MÉDIA DE VENDA', 'COEFICIENTE DE VARIAÇÃO DE VENDA',
                                         'TAMANHO DA AMOSTRA DE VENDA'])
        else:
            return pd.DataFrame(columns=['VALOR DE M² DE ALUGUEL', 'VALOR DE ALUGUEL NOMINAL',
                                         'METRAGEM MÉDIA DE ALUGUEL', 'COEFICIENTE DE VARIAÇÃO DE ALUGUEL',
                                         'TAMANHO DA AMOSTRA DE ALUGUEL'])

def analisar_imovel_detalhado(tipo_imovel=None, bairro=None, cidade=None, cep=None, vaga_garagem=None, quadra=None, quartos=None, metragem=None):
    df = pd.read_csv(input_file, sep=",", thousands=".", decimal=",")

    # Exibir informações iniciais sobre os dados
    print(f"Total de registros no dataset: {len(df)}")

    # Filtrar os registros especificados
    filtro = pd.Series([True] * len(df))

    if tipo_imovel:
        filtro &= (df["tipo"] == tipo_imovel)
    if bairro:
        filtro &= (df["bairro"] == bairro)
    if cidade:
        filtro &= (df["cidade"] == cidade)
    if cep:
        filtro &= (df["cep"] == cep)
    if vaga_garagem is not None:
        filtro &= (df["vagas"].notnull() if vaga_garagem else df["vagas"].isnull())
    if quadra:
        filtro &= (df["quadra"] == quadra)
    if quartos:
        filtro &= (df["quartos"] == quartos)
    if metragem:
        filtro &= ((df["area_util"] >= metragem * 0.9) & (df["area_util"] <= metragem * 1.1))

    df_filtrado = df[filtro]

    # Exibir informações sobre os dados filtrados
    print(f"Total de registros após filtragem: {len(df_filtrado)}")

    # Clusterização e remoção de outliers para "Venda"
    venda_df = df_filtrado[df_filtrado['oferta'] == 'Venda'].copy()
    print(f"Total de registros de VENDA antes da remoção de outliers: {len(venda_df)}")
    if "valor_m2" in venda_df.columns:
        venda_df = remover_outliers_iqr(venda_df, "valor_m2")
    print(f"Total de registros de VENDA após remoção de outliers: {len(venda_df)}")
    metricas_venda = clusterizar_dados(venda_df, "valor_m2", "Venda")

    # Clusterização e remoção de outliers para "Aluguel"
    aluguel_df = df_filtrado[df_filtrado['oferta'] == 'Aluguel'].copy()
    print(f"Total de registros de ALUGUEL antes da remoção de outliers: {len(aluguel_df)}")
    if "valor_m2" in aluguel_df.columns:
        aluguel_df = remover_outliers_iqr(aluguel_df, "valor_m2")
    print(f"Total de registros de ALUGUEL após remoção de outliers: {len(aluguel_df)}")
    metricas_aluguel = clusterizar_dados(aluguel_df, "valor_m2", "Aluguel")

    # Ordenar os clusters de "Venda" e
        # "Aluguel" separadamente
    metricas_venda = metricas_venda.sort_values(by="VALOR DE M² DE VENDA").reset_index(drop=True)
    metricas_aluguel = metricas_aluguel.sort_values(by="VALOR DE M² DE ALUGUEL").reset_index(drop=True)

    # Garantir que ambos os DataFrames tenham o mesmo número de clusters
    max_len = max(len(metricas_venda), len(metricas_aluguel))
    metricas_venda = metricas_venda.reindex(range(max_len)).reset_index(drop=True)
    metricas_aluguel = metricas_aluguel.reindex(range(max_len)).reset_index(drop=True)

    # Combinar e alinhar as duas amostras de "Venda" e "Aluguel"
    resultados_alinhados = pd.concat([metricas_venda, metricas_aluguel], axis=1)

    # Calcular a rentabilidade média para cada linha
    resultados_alinhados['RENTABILIDADE MÉDIA'] = resultados_alinhados.apply(
        lambda row: calcular_rentabilidade(row['VALOR DE ALUGUEL NOMINAL'], row['VALOR DE VENDA NOMINAL']), axis=1
    )

    # Aplicar formatação aos resultados
    resultados_formatados = formatar_resultados(resultados_alinhados)

    # Retornar o DataFrame formatado
    return resultados_formatados.T


