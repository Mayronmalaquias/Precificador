import pandas as pd
from sklearn.cluster import KMeans
import numpy as np

input_file = "./static/dados/dados_map.csv"

def remover_outliers_iqr(df, coluna):
    Q1 = df[coluna].quantile(0.25)
    Q3 = df[coluna].quantile(0.75)
    IQR = Q3 - Q1
    filtro = (df[coluna] >= (Q1 - 1.5 * IQR)) & (df[coluna] <= (Q3 + 1.5 * IQR))
    return df[filtro]

def calcular_rentabilidade(valor_locacao, valor_venda):
    return (valor_locacao) / valor_venda if valor_venda != 0 else np.nan

def calcular_metricas_cluster(df, valor_coluna, oferta_tipo, metragem = None):
    metricas = {}

    if oferta_tipo == 'Venda':
        metricas['VALOR DE M² DE VENDA'] = df[valor_coluna].mean()
        # metricas['VALOR DE VENDA NOMINAL'] = df['preco'].mean()
        metricas['VALOR DE VENDA NOMINAL'] = df[valor_coluna].mean() * metragem if metragem else df['preco'].mean()
        metricas['METRAGEM MÉDIA DE VENDA'] = df['area_util'].mean()
        metricas['COEFICIENTE DE VARIAÇÃO DE VENDA'] = df[valor_coluna].std() / df[valor_coluna].mean() if df[valor_coluna].mean() != 0 else np.nan
        metricas['TAMANHO DA AMOSTRA DE VENDA'] = len(df)
        if isinstance(metricas, pd.DataFrame):
    # Se já for um DataFrame, só preenche com 0 caso a coluna não exista ou tenha NaN
            if 'TAMANHO DA AMOSTRA DE VENDA' not in metricas.columns:
                metricas['TAMANHO DA AMOSTRA DE VENDA'] = len(df)  # Atribui o tamanho da amostra
            else:
                # Caso a coluna já exista, preenche com 0 se houver NaN
                metricas['TAMANHO DA AMOSTRA DE VENDA'] = metricas['TAMANHO DA AMOSTRA DE VENDA'].fillna(0)
    else:
        metricas['VALOR DE M² DE ALUGUEL'] = df[valor_coluna].mean()
        # metricas['VALOR DE ALUGUEL NOMINAL'] = df['preco'].mean()
        metricas['VALOR DE ALUGUEL NOMINAL'] =  metricas['VALOR DE M² DE ALUGUEL'] * metragem if metragem else df['preco'].mean()
        metricas['METRAGEM MÉDIA DE ALUGUEL'] = df['area_util'].mean()
        metricas['COEFICIENTE DE VARIAÇÃO DE ALUGUEL'] = df[valor_coluna].std() / df[valor_coluna].mean() if df[valor_coluna].mean() != 0 else np.nan
        metricas['TAMANHO DA AMOSTRA DE ALUGUEL'] = len(df)
        print(len(df))
        # if isinstance(metricas, pd.DataFrame):
        # # Se já for um DataFrame, só preenche com 0 caso a coluna não exista ou tenha NaN
        #     if 'TAMANHO DA AMOSTRA DE VENDA' not in metricas.columns:
        #            metricas['TAMANHO DA AMOSTRA DE VENDA'] = len(df)  # Atribui o tamanho da amostra
            # else:
            #         # Caso a coluna já exista, preenche com 0 se houver NaN
            #     metricas['TAMANHO DA AMOSTRA DE VENDA'] = metricas['TAMANHO DA AMOSTRA DE VENDA'].fillna(0)

    return metricas

def formatar_resultados(df):
    df_formatted = df.copy()

    # Formatando os valores em reais (R$) e metros quadrados (m²)
    df_formatted['VALOR DE M² DE VENDA'] = df_formatted['VALOR DE M² DE VENDA'].fillna(0).apply(lambda x: f"R$ {x:,.2f} /m²")
    df_formatted['VALOR DE VENDA NOMINAL'] = df_formatted['VALOR DE VENDA NOMINAL'].fillna(0).apply(lambda x: f"R$ {x:,.2f}")
    df_formatted['METRAGEM MÉDIA DE VENDA'] = df_formatted['METRAGEM MÉDIA DE VENDA'].fillna(0).apply(lambda x: f"{x:.2f} m²")

    df_formatted['VALOR DE M² DE ALUGUEL'] = df_formatted['VALOR DE M² DE ALUGUEL'].fillna(0).apply(lambda x: f"R$ {x:,.2f} /m²")
    df_formatted['VALOR DE ALUGUEL NOMINAL'] = df_formatted['VALOR DE ALUGUEL NOMINAL'].fillna(0).apply(lambda x: f"R$ {x:,.2f}")
    df_formatted['METRAGEM MÉDIA DE ALUGUEL'] = df_formatted['METRAGEM MÉDIA DE ALUGUEL'].fillna(0).apply(lambda x: f"{x:.2f} m²")

    # Formatando coeficiente de variação em porcentagem
    df_formatted['COEFICIENTE DE VARIAÇÃO DE VENDA'] = df_formatted['COEFICIENTE DE VARIAÇÃO DE VENDA'].fillna(0).apply(lambda x: f"{x:.2%}")
    df_formatted['COEFICIENTE DE VARIAÇÃO DE ALUGUEL'] = df_formatted['COEFICIENTE DE VARIAÇÃO DE ALUGUEL'].fillna(0).apply(lambda x: f"{x:.2%}")

    # Formatando a rentabilidade média em porcentagem
    df_formatted['RENTABILIDADE MÉDIA'] = df_formatted['RENTABILIDADE MÉDIA'].fillna(0).apply(lambda x: f"{x:.2%}")

    return df_formatted

def clusterizar_dados(df, valor_coluna, oferta_tipo, n_clusters=9, metragem=None):
    df_oferta = df[df['oferta'] == oferta_tipo].copy()
    print(len(df_oferta))
    tamanho_n = 0
    if(len(df_oferta) > 0):
        tamanho_n = 10
    # and len(df_oferta) >= n_clusters
    print(df_oferta.empty)
    print(valor_coluna in df_oferta.columns)
    print(tamanho_n >= n_clusters)
    if not df_oferta.empty and valor_coluna in df_oferta.columns and tamanho_n >= n_clusters :

        if(len(df_oferta) > 8):
            X = df_oferta[[valor_coluna]].values
            kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
            df_oferta.loc[:, "cluster"] = kmeans.fit_predict(X)
            df_oferta.loc[:, 'cluster'] = df_oferta['cluster'].astype('category')
        else:
            df_oferta.loc[:, "cluster"] = 5
            df_oferta.loc[:, "cluster"] = df_oferta["cluster"].astype("category")
        if(oferta_tipo == 'Aluguel'):
            # print(df_oferta)
            df_oferta.to_csv("./static/dados/aluguelC.csv")
        elif(oferta_tipo == 'Venda'):
            df_oferta.to_csv("./static/dados/vendaC.csv")
        else:
            print(df_oferta)
        metricas_clusters = []
        for cluster in sorted(df_oferta['cluster'].unique()):
            cluster_data = df_oferta[df_oferta['cluster'] == cluster]
            metricas = calcular_metricas_cluster(cluster_data, valor_coluna, oferta_tipo, metragem)
            # print(metricas)
            metricas['Cluster'] = cluster
            metricas_clusters.append(metricas)

        metricas_df = pd.DataFrame(metricas_clusters)
        # print(metricas_df)
        # print(metricas_df)

        if oferta_tipo == 'Venda':
            metricas_df = metricas_df.reindex(columns=['VALOR DE M² DE VENDA', 'VALOR DE VENDA NOMINAL',
                                                       'METRAGEM MÉDIA DE VENDA', 'COEFICIENTE DE VARIAÇÃO DE VENDA',
                                                       'TAMANHO DA AMOSTRA DE VENDA'], fill_value=0)
        else:
            metricas_df = metricas_df.reindex(columns=['VALOR DE M² DE ALUGUEL', 'VALOR DE ALUGUEL NOMINAL',
                                                       'METRAGEM MÉDIA DE ALUGUEL', 'COEFICIENTE DE VARIAÇÃO DE ALUGUEL',
                                                       'TAMANHO DA AMOSTRA DE ALUGUEL'], fill_value=0)
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
        if bairro == "AGUAS CLARAS":
            bairro_aguas = ["NORTE", "SUL"]
            filtro &= (df['bairro'].isin(bairro_aguas))
        else:
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
        filtro &= (df["quartos"] == quartos if (quartos < 4) else df["quartos"] >= quartos)
    
    if metragem:
        # Definir o filtro principal Aluguel
        micro_filtro = filtro.copy()  # Fazendo uma cópia do filtro atual
        micro_filtro &= ((df["area_util"] >= metragem * 0.9) & (df["area_util"] <= metragem * 1.1))
        df_filtrado_metragem = df[micro_filtro]  # Aplicar o filtro de metragem
        tamanho_amostra_aluguel = len(df_filtrado_metragem[df_filtrado_metragem['oferta'] == 'Aluguel'])

        # Definir o filtro principal Venda
        micro_filtro_venda = filtro.copy()  # Fazendo uma cópia do filtro atual
        micro_filtro_venda &= ((df["area_util"] >= metragem * 0.9) & (df["area_util"] <= metragem * 1.1))
        df_filtrado_metragem_venda = df[micro_filtro_venda]  # Aplicar o filtro de metragem
        tamanho_amostra_venda = len(df_filtrado_metragem_venda[df_filtrado_metragem_venda['oferta'] == 'Venda'])

        print(f"Valor para Aluguel após metragem: {tamanho_amostra_aluguel}")
        print(f"Valor para Venda após metragem: {tamanho_amostra_venda}")

        # Ajustar o filtro se necessário
        if tamanho_amostra_aluguel < 9 or tamanho_amostra_venda < 9:
            print("chore chorei - Ajustando filtro de metragem para 0.7 e 1.5")
            numero_interacoes = 0
            valor = 0.15
            max_interacoes = 17

            micro_filtro = filtro.copy()  # Fazendo uma cópia do filtro atual
            micro_filtro &= ((df["area_util"] >= metragem * 0.9) & (df["area_util"] <= metragem * 1.1))
            df_filtrado_metragem = df[micro_filtro]  # Aplicar o filtro de metragem
            valores_descendo_loop = len(df_filtrado_metragem[df_filtrado_metragem['oferta'] == 'Aluguel'])

            micro_filtro_venda = filtro.copy()  # Fazendo uma cópia do filtro atual
            micro_filtro_venda &= ((df["area_util"] >= metragem * 0.9) & (df["area_util"] <= metragem * 1.1))
            df_filtrado_metragem_venda = df[micro_filtro_venda]  # Aplicar o filtro de metragem
            tamanho_amostra_venda_loop = len(df_filtrado_metragem_venda[df_filtrado_metragem_venda['oferta'] == 'Venda'])

            while(((valores_descendo_loop < 9) or (tamanho_amostra_venda_loop < 9)) and numero_interacoes < max_interacoes):
                novo_micro_filtro = filtro.copy()  # Fazendo uma cópia do filtro atual

                # Aplicar a lógica da metragem
                novo_micro_filtro &= ((df["area_util"] >= metragem * (1 - valor)) & (df["area_util"] <= metragem * (1 + valor)))
                df_filtrado_metragem = df[novo_micro_filtro]  # Aplicar o filtro de metragem
                valores_descendo_loop = len(df_filtrado_metragem[df_filtrado_metragem['oferta'] == 'Aluguel'])

                micro_filtro_venda = filtro.copy()  # Fazendo uma cópia do filtro atual
                micro_filtro_venda &= ((df["area_util"] >= metragem * 0.9) & (df["area_util"] <= metragem * 1.1))
                df_filtrado_metragem_venda = df[micro_filtro_venda]  # Aplicar o filtro de metragem
                tamanho_amostra_venda_loop = len(df_filtrado_metragem_venda[df_filtrado_metragem_venda['oferta'] == 'Venda'])

                print("OLHA O TAMANHO SUBINDO: ", valores_descendo_loop)
                numero_interacoes += 1
                valor += 0.5

            filtro &= ((df["area_util"] >= metragem * (1 - valor)) & (df["area_util"] <= metragem * (1 + valor)))
        else:                
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
    metricas_venda = clusterizar_dados(venda_df, "valor_m2", "Venda", n_clusters=9,  metragem=metragem)

    # Clusterização e remoção de outliers para "Aluguel"
    aluguel_df = df_filtrado[df_filtrado['oferta'] == 'Aluguel'].copy()
    print(f"Total de registros de ALUGUEL antes da remoção de outliers: {len(aluguel_df)}")

    if "valor_m2" in aluguel_df.columns:
        aluguel_df = remover_outliers_iqr(aluguel_df, "valor_m2")
    print(f"Total de registros de ALUGUEL após remoção de outliers: {len(aluguel_df)}")
    metricas_aluguel = clusterizar_dados(aluguel_df, "valor_m2", "Aluguel", n_clusters=9,  metragem=metragem)

    # Ordenar os clusters de "Venda" e
        # "Aluguel" separadamente
    metricas_venda = metricas_venda.sort_values(by="VALOR DE M² DE VENDA").reset_index(drop=True)
    metricas_aluguel = metricas_aluguel.sort_values(by="VALOR DE M² DE ALUGUEL").reset_index(drop=True)

    # Garantir que ambos os DataFrames tenham o mesmo número de clusters
    max_len = max(len(metricas_venda), len(metricas_aluguel))
    metricas_venda = metricas_venda.reindex(range(max_len)).reset_index(drop=True)
    metricas_aluguel = metricas_aluguel.reindex(range(max_len)).reset_index(drop=True)
    # print(metricas_venda)
    # print(metricas_aluguel)

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


def clusterizar_dados2(df, valor_coluna, oferta_tipo, cluster, n_clusters=9):
    # Filtra o DataFrame para o tipo de oferta desejado
    df_oferta = df[df['oferta'] == oferta_tipo].copy()

    # Verifica se a coluna existe, o DataFrame não está vazio, e possui pelo menos n_clusters linhas
    if not df_oferta.empty and valor_coluna in df_oferta.columns and len(df_oferta) >= n_clusters:
        X = df_oferta[[valor_coluna]].values
        kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
        df_oferta.loc[:, "cluster"] = kmeans.fit_predict(X)
        df_oferta.loc[:, 'cluster'] = df_oferta['cluster'].astype('category')
        
        # Filtra para retornar apenas o cluster especificado
        # print(df_oferta)
        return df_oferta[df_oferta['cluster'] == cluster]
    else:
        # Retorna um DataFrame vazio se as condições não forem atendidas
        return df_oferta.iloc[0:0]