import psycopg2
import pandas as pd
import matplotlib.pyplot as plt
from app.models.imovel import Imovel, ImovelAluguel, ImovelVenda
from app import SessionLocal
import io
import base64
import os

# ... (a função carregar_imoveis_venda continua a mesma) ...

def carregar_imoveis_venda():
    """
    Carrega os dados dos imóveis à venda do banco de dados,
    fazendo um join entre as tabelas Imovel e ImovelVenda.
    """
    session = SessionLocal()
    try:
        results = session.query(Imovel).all()

        dados = []
        for imovel, cluster in results:
            dados.append({
                "id": imovel.id,
                "codigo": imovel.codigo,
                "anunciante": imovel.anunciante,
                "oferta": imovel.oferta,
                "tipo": imovel.tipo,
                "area_util": imovel.area_util,
                "bairro": imovel.bairro,
                "cidade": imovel.cidade,
                "preco": imovel.preco,
                "valor_m2": imovel.valor_m2,
                "quartos": imovel.quartos,
                "vagas": imovel.vagas,
                "latitude": float(imovel.latitude) if imovel.latitude else None,
                "longitude": float(imovel.longitude) if imovel.longitude else None,
                "data_coleta": imovel.data_coleta,
                "cluster": cluster
            })
        return pd.DataFrame(dados)
    finally:
        session.close()


plt.switch_backend('Agg')

def gerar_grafico_linha():
    """
    Carrega os dados, calcula o preço médio MENSAL,
    remove outliers e gera um gráfico de LINHA minimalista, retornando-o como Base64.
    """
    try:
        df = carregar_imoveis_venda()

        if df.empty:
            return {"error": "Nenhum dado encontrado para gerar o gráfico."}

        # --- Tratamento e Limpeza dos Dados ---
        df['valor_m2'] = pd.to_numeric(df['valor_m2'], errors='coerce')
        df['data_coleta'] = pd.to_datetime(df['data_coleta'], errors='coerce')
        df.dropna(subset=['valor_m2', 'data_coleta'], inplace=True)

        media_mensal = df.groupby(df['data_coleta'].dt.to_period('M'))['valor_m2'].mean()
        
        if media_mensal.empty:
            return {"error": "Não foi possível calcular a média mensal dos preços."}
        
        df_media_mensal = media_mensal.reset_index()
        df_media_mensal.rename(columns={'data_coleta': 'mes'}, inplace=True)

        # --- Remoção de Outliers ---
        Q1 = df_media_mensal['valor_m2'].quantile(0.25)
        Q3 = df_media_mensal['valor_m2'].quantile(0.75)
        IQR = Q3 - Q1
        limite_inferior = Q1 - 1.5 * IQR
        limite_superior = Q3 + 1.5 * IQR

        df_final = df_media_mensal[(df_media_mensal['valor_m2'] >= limite_inferior) & (df_media_mensal['valor_m2'] <= limite_superior)].copy()
        
        # --- ETAPA DE DIAGNÓSTICO ---
        # Verifique os logs do seu servidor para ver esta saída.
        print("--- DADOS PARA PLOTAGEM ---")
        print(df_final)
        print("---------------------------")
        
        if df_final.empty:
            print("AVISO: df_final está vazio após a remoção de outliers. Gerando imagem em branco.")
            return {"error": "Nenhum dado restou após a remoção de valores discrepantes."}

        df_final['rotulo_mes'] = df_final['mes'].dt.strftime('%Y-%m')

        # --- Geração do Gráfico com Matplotlib ---
        fig, ax = plt.subplots(figsize=(12, 7))

        # Plota o gráfico de linha
        ax.plot(df_final['rotulo_mes'], df_final['valor_m2'], color="#e03636", linewidth=3)

        # --- AJUSTE: Definir limites do eixo Y manualmente ---
        # Isso força o Matplotlib a desenhar a linha em uma área visível.
        min_val = df_final['valor_m2'].min()
        max_val = df_final['valor_m2'].max()
        # Adiciona uma margem de 5% para a linha não tocar nas bordas
        padding = (max_val - min_val) * 0.05
        ax.set_ylim(min_val - padding, max_val + padding)

        # Remove todos os elementos visuais dos eixos
        ax.set_xticks([])
        ax.set_yticks([])
        ax.set_xlabel(None)
        ax.set_ylabel(None)
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
        ax.spines['bottom'].set_visible(False)
        ax.spines['left'].set_visible(False)
        fig.tight_layout(pad=0)

        # --- Conversão do Gráfico para Base64 ---
        buf = io.BytesIO()
        fig.savefig(buf, format='png', dpi=100, transparent=True)
        buf.seek(0)
        
        image_base64 = base64.b64encode(buf.read()).decode('utf-8')
        
        buf.close()
        plt.close(fig)

        return {"image_base64": image_base64}

    except psycopg2.Error as e:
        print(f"Erro de banco de dados: {e}")
        return {"error": "Não foi possível conectar ou buscar dados do banco de dados."}
    except Exception as e:
        print(f"Ocorreu um erro inesperado: {e}")
        return {"error": "Ocorreu um erro interno ao gerar o gráfico."}