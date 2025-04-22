import pandas as pd
from sqlalchemy import create_engine

# Configurar a conexão com o PostgreSQL
usuario = "inteligencia"
senha = "1234"
host = "localhost"  # ou o IP do servidor
banco = "database"

engine = create_engine(f'postgresql://{usuario}:{senha}@{host}:5432/{banco}')

# Carregar o CSV
caminho_csv = "./dados/dados_map.csv"
df = pd.read_csv(caminho_csv)

# Ajustando os tipos de dados conforme a estrutura do banco
df["area_util"] = pd.to_numeric(df["area_util"], errors='coerce')
df["preco"] = pd.to_numeric(df["preco"], errors='coerce')
df["valor_m2"] = pd.to_numeric(df["valor_m2"], errors='coerce')
df["latitude"] = pd.to_numeric(df["latitude"], errors='coerce')
df["longitude"] = pd.to_numeric(df["longitude"], errors='coerce')

# Enviar para o banco de dados
df.to_sql("imoveis", engine, if_exists="append", index=False)

print("CSV importado com sucesso!")
