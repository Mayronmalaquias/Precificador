from flask import Flask, request, jsonify, render_template
import pandas as pd
from clusterizacao import analisar_imovel_detalhado  # Substitua pelo nome correto do arquivo de funções
import folium  # Importando a biblioteca folium
from folium.plugins import HeatMap  # Importando o plugin HeatMap

app = Flask(__name__)

# Rota para exibir o formulário
@app.route('/', methods=['GET'])
def index():
    df = pd.read_csv('./2024-09-06.csv')
    mapa_html = gerar_mapa(df)
    return render_template('index.html', mapa_html=mapa_html)

@app.route('/analisar', methods=['POST'])
def analisar():
    params = request.form
    tipo_imovel = params.get('tipoImovel')
    bairro = params.get('bairro')
    nrCluster = int(params.get('nrCluster')) - 1  # Convertendo o valor do cluster selecionado pelo usuário para índice (0 a 8)

    # Chamar a função para analisar os dados
    resultados_df = analisar_imovel_detalhado(tipo_imovel=tipo_imovel, bairro=bairro)

    # Transpor o DataFrame para corrigir a estrutura
    resultados_df = resultados_df.T

    # Verificar a estrutura do DataFrame
    print("Estrutura do DataFrame (após transposição):", resultados_df.head())
    print("Colunas disponíveis (após transposição):", resultados_df.columns)

    if resultados_df.empty:
        return jsonify({"error": "Nenhum dado encontrado para os parâmetros selecionados."}), 404

    # Garantir que os clusters estejam ordenados pelo valor de metro quadrado (venda e aluguel)
    valorM2Venda = resultados_df.iloc[nrCluster]['VALOR DE M² DE VENDA']
    valorM2Locacao = resultados_df.iloc[nrCluster]['VALOR DE M² DE ALUGUEL']

    # Obter os valores de venda relacionados ao cluster
    valorVendaNominal = resultados_df.iloc[nrCluster]['VALOR DE VENDA NOMINAL']
    metragemMediaVenda = resultados_df.iloc[nrCluster]['METRAGEM MÉDIA DE VENDA']
    coeficienteVariacaoVenda = resultados_df.iloc[nrCluster]['COEFICIENTE DE VARIAÇÃO DE VENDA']
    tamanhoAmostraVenda = resultados_df.iloc[nrCluster]['TAMANHO DA AMOSTRA DE VENDA']

    # Obter os valores de locação relacionados ao cluster
    valorLocacaoNominal = resultados_df.iloc[nrCluster]['VALOR DE ALUGUEL NOMINAL']
    metragemMediaLocacao = resultados_df.iloc[nrCluster]['METRAGEM MÉDIA DE ALUGUEL']
    coeficienteVariacaoLocacao = resultados_df.iloc[nrCluster]['COEFICIENTE DE VARIAÇÃO DE ALUGUEL']
    tamanhoAmostraLocacao = resultados_df.iloc[nrCluster]['TAMANHO DA AMOSTRA DE ALUGUEL']

    # Obter a rentabilidade calculada
    rentabilidadeMedia = resultados_df.iloc[nrCluster]['RENTABILIDADE MÉDIA']

    # Retornar os resultados como JSON
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

def gerar_mapa(df):
    coordenadas_bairros = {
        'ASA NORTE': [-15.7625, -47.8692],
        'ASA SUL': [-15.7986, -47.8919],
        'LAGO SUL': [-15.8376, -47.8753],
        'LAGO NORTE': [-15.7300, -47.8297],
        'SUDOESTE': [-15.7895, -47.9275],
        'NOROESTE': [-15.7500, -47.9300],
        'PARK WAY': [-15.8489, -47.9382],
        'JARDIM BOTANICO': [-15.8703, -47.7965],
        # Adicionar mais coordenadas de bairros aqui...
    }

    df['latitude'] = df['bairro'].apply(lambda x: coordenadas_bairros.get(x, [0, 0])[0])
    df['longitude'] = df['bairro'].apply(lambda x: coordenadas_bairros.get(x, [0, 0])[1])

    df_filtrado = df[(df['latitude'] != 0) & (df['longitude'] != 0)]

    mapa = folium.Map(location=[-15.7942, -47.8822], zoom_start=11)

    heat_data = [[row['latitude'], row['longitude'], row['preco']] for index, row in df_filtrado.iterrows()]

    HeatMap(heat_data).add_to(mapa)

    return mapa._repr_html_()

if __name__ == '__main__':
    app.run(debug=True)
