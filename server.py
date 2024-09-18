from flask import Flask, request, jsonify, render_template
import pandas as pd
import openai
from clusterizacao import analisar_imovel_detalhado  # Substitua pelo nome correto do arquivo de funções
import folium  # Importando a biblioteca folium
from folium.plugins import HeatMap, MarkerCluster  # Importando o plugin HeatMap
import os
from dotenv import load_dotenv
from flask_caching import Cache


app = Flask(__name__)

df = pd.read_csv('./static/dados/2024-09-06.csv')
csv_file_path = './static/dados/dados_map.csv'  # Substitua pelo caminho do arquivo CSV
df_map = pd.read_csv(csv_file_path)
load_dotenv()
openai.api_key = os.getenv('OPENAI_API_KEY')


# Configuração do cache
cache = Cache(app, config={'CACHE_TYPE': 'simple'})

@cache.cached(timeout=60)
def carregar_dados():
    df = pd.read_csv('./static/dados/2024-09-06.csv')
    df_map = pd.read_csv(csv_file_path)
    return df, df_map

# Carregar dados uma vez e usá-los a partir do cache
df, df_map = carregar_dados()

# Rota para exibir o formulário
@app.route('/', methods=['GET'])
def index():
    return render_template('index.html')

@app.route('/carregar_mapa', methods=['GET'])
def carregar_mapa():
    return gerar_mapa()

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

def gerar_mapa():
    """
    Função para gerar um mapa de calor a partir de um arquivo CSV contendo latitude, longitude e preço.
    O mapa será otimizado para mostrar clusters e limitar o número de pontos com a mesma latitude e longitude.
    
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

    # Limitar os dados para coordenadas duplicadas (mesma latitude e longitude)
    df_filtrado = df_filtrado.groupby(['latitude', 'longitude']).head(5)

    # Criar o mapa centralizado em Brasília
    mapa = folium.Map(location=[-15.7942, -47.8822], zoom_start=12)

    # Preparar os dados para o HeatMap, apenas para zoom 12 ou inferior
    heat_data = [[row['latitude'], row['longitude'], row['preco']] for index, row in df_filtrado.iterrows()]

    # Adicionar o HeatMap ao mapa (somente visível para zoom <= 12)
    HeatMap(heat_data, min_zoom=10, max_zoom=12).add_to(mapa)

    # Criar clusters para quando o zoom for menor que 10
    marker_cluster = MarkerCluster().add_to(mapa)

    # Adicionar marcadores ao cluster, limitando os marcadores por coordenada
    for index, row in df_filtrado.iterrows():
        folium.Marker(
            location=[row['latitude'], row['longitude']],
            popup=f"Preço: R$ {row['preco']}",
        ).add_to(marker_cluster)

    # Adicionar legenda personalizada
    legenda = """
    <div style="position: fixed; 
                bottom: 50px; left: 50px; width: 200px; height: 100px; 
                background-color: white; border:2px solid grey; z-index:9999; font-size:14px;
                ">
        <h4>Legenda</h4>
        <p>Quantidade de anúncios em cada agrupamento. O mapa mostra até 5 pontos por coordenada.</p>
    </div>
    """
    mapa.get_root().html.add_child(folium.Element(legenda))

    # Salvar o mapa em um arquivo HTML
    mapa.save("mapa_de_calor_com_limite.html")

    # Retornar o HTML do mapa gerado
    return mapa._repr_html_()

def prever_preco(tipo_imovel, bairro):
    resultados = analisar_imovel_detalhado(tipo_imovel=tipo_imovel, bairro=bairro)
    if not resultados.empty:
        preco_m2_venda = resultados['VALOR DE M² DE VENDA'].mean()  # Usando a média dos resultados
        return f"Baseado nos dados da 61imóveis, o valor médio do m² de venda para {tipo_imovel} no bairro {bairro} é de aproximadamente R$ {preco_m2_venda:.2f}."
    else:
        return "Desculpe, não temos dados suficientes para prever o preço desse imóvel."

# Função de interação com o ChatGPT, incluindo contexto personalizado
def chatgpt_response(message):
    try:
        response = openai.ChatCompletion.create(
            model="gpt-4",  # Usando o modelo GPT-4 ou GPT-3.5, se preferir
            messages=[{"role": "user", "content": message}],
            max_tokens=200,
            temperature=0.7
        )
        return response['choices'][0]['message']['content'].strip()
    except Exception as e:
        print(f"Erro: {e}")  # Imprimir o erro no console para verificar o problema
        return "Desculpe, o chat está indisponivel no momento."

# Função para processar perguntas específicas antes de enviar ao ChatGPT
def processar_perguntas(message):
    # Verifica se a pergunta é relacionada a previsões de preço de imóveis
    if 'preço' in message.lower() or 'custo' in message.lower():
        # Exemplo simplificado de análise: extrair dados do tipo de imóvel e bairro
        tipo_imovel = 'Apartamento'  # Padrão ou extraído da mensagem
        bairro = 'ASA SUL'  # Padrão ou extraído da mensagem
        return prever_preco(tipo_imovel, bairro)
    
    # Caso a pergunta não seja específica, delegar ao ChatGPT
    else:
        return chatgpt_response(message)

# Rota para o chatbot
@app.route('/chatbot', methods=['POST'])
def chatbot():
    data = request.get_json()
    user_message = data['message']
    response = chatgpt_response(user_message)
    return jsonify({'response': response})

if __name__ == '__main__':
    app.run(debug=True)