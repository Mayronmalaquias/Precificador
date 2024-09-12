from flask import Flask, request, jsonify, render_template
import pandas as pd
import openai
from clusterizacao import analisar_imovel_detalhado  # Substitua pelo nome correto do arquivo de funções
import folium  # Importando a biblioteca folium
from folium.plugins import HeatMap  # Importando o plugin HeatMap
import os
from dotenv import load_dotenv

app = Flask(__name__)

df = pd.read_csv('./static/dados/2024-09-06.csv')
load_dotenv()
openai.api_key = os.getenv('OPENAI_API_KEY')

# Rota para exibir o formulário
@app.route('/', methods=['GET'])
def index():
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