import psycopg2
import pandas as pd
import matplotlib.pyplot as plt
from app.models.imovel import Imovel, ImovelAluguel, ImovelVenda
from app import SessionLocal
import io
import base64
import os

def carregar_imoveis_venda():
    """
    Carrega os dados dos imóveis à venda do banco de dados,
    fazendo um join entre as tabelas Imovel e ImovelVenda.
    """
    session = SessionLocal()
    try:
        results = session.query(
            Imovel,
            ImovelVenda.cluster
        ).join(
            ImovelVenda, Imovel.id == ImovelVenda.id
        ).all()

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

# Desativa o aviso de "GUI is not main thread" do Matplotlib, comum em ambientes de servidor.
plt.switch_backend('Agg')

def gerar_grafico_linha():
    """
    Carrega os dados, calcula o preço médio MENSAL,
    remove outliers e gera um gráfico de COLUNAS, retornando-o como Base64.
    """
    try:
        df = carregar_imoveis_venda()

        if df.empty:
            return {"error": "Nenhum dado encontrado para gerar o gráfico."}

        # --- Tratamento e Limpeza dos Dados ---
        df['valor_m2'] = pd.to_numeric(df['valor_m2'], errors='coerce')
        df['data_coleta'] = pd.to_datetime(df['data_coleta'], errors='coerce')
        df.dropna(subset=['valor_m2', 'data_coleta'], inplace=True)

        # ### ALTERAÇÃO PRINCIPAL: Agrupar por MÊS ###
        # .dt.to_period('M') agrupa todas as datas pelo ano e mês.
        # O resultado (media_mensal) é uma Series com o mês como índice.
        media_mensal = df.groupby(df['data_coleta'].dt.to_period('M'))['valor_m2'].mean()
        
        if media_mensal.empty:
            return {"error": "Não foi possível calcular a média mensal dos preços."}
        
        # Converte a Series para um DataFrame para o tratamento de outliers
        df_media_mensal = media_mensal.reset_index()
        df_media_mensal.rename(columns={'data_coleta': 'mes'}, inplace=True)

        # --- Remoção de Outliers (agora sobre a média mensal) ---
        Q1 = df_media_mensal['valor_m2'].quantile(0.25)
        Q3 = df_media_mensal['valor_m2'].quantile(0.75)
        IQR = Q3 - Q1
        limite_inferior = Q1 - 1.5 * IQR
        limite_superior = Q3 + 1.5 * IQR

        # Filtra o DataFrame, mantendo apenas os meses com médias dentro dos limites
        # Usamos .copy() para evitar avisos de SettingWithCopyWarning
        df_final = df_media_mensal[(df_media_mensal['valor_m2'] >= limite_inferior) & (df_media_mensal['valor_m2'] <= limite_superior)].copy()

        if df_final.empty:
            return {"error": "Nenhum dado restou após a remoção de valores discrepantes."}

        # --- Preparação para o Gráfico ---
        # Converte o período do mês para uma string formatada (ex: '2025-07') para usar como rótulo no eixo X.
        df_final['rotulo_mes'] = df_final['mes'].dt.strftime('%Y-%m')

        # --- Geração do Gráfico com Matplotlib ---
        fig, ax = plt.subplots(figsize=(12, 7))

                # 1. Deixar a coluna mais fina usando o parâmetro 'width'
        bars = ax.bar(df_final['rotulo_mes'], df_final['valor_m2'], color="#942c2c", width=0.6)
        
        # 2. Adicionar o valor exato em cima de cada coluna
        for bar in bars:
            height = bar.get_height()
            
            # Formata o valor para o padrão de moeda brasileiro (ex: R$ 1.234.567,89)
            formatted_value = f'R$ {height:,.2f}'.replace(',', 'X').replace('.', ',').replace('X', '.')
            
            ax.annotate(formatted_value,
                        xy=(bar.get_x() + bar.get_width() / 2, height),
                        xytext=(0, 3),  # 3 pontos de deslocamento vertical
                        textcoords="offset points",
                        ha='center', va='bottom',
                        fontsize=18,
                        fontweight='bold')
        
        # Plota os rótulos de texto no eixo X e os preços no eixo Y
        ax.bar(df_final['rotulo_mes'], df_final['valor_m2'], color="#e03636")
        
        # Customização do Gráfico
        # ax.set_title('Evolução do Preço Médio Mensal', fontsize=16)
        ax.set_xlabel('Mês da Coleta', fontsize=12)
        ax.set_ylabel('Preço Médio (R$)', fontsize=12)
        ax.grid(True, which='major', axis='y', linestyle='--', linewidth=0.5)
        plt.xticks(rotation=45, ha="right") # Rotação e alinhamento dos rótulos
        fig.tight_layout()

        # --- Conversão do Gráfico para Base64 ---
        buf = io.BytesIO()
        fig.savefig(buf, format='png', dpi=100)
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