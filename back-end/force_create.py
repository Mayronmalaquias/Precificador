import pandas as pd
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.models.imovel import Base, Imovel  # Você pode adicionar ImovelVenda e ImovelAluguel depois

# Conexão
DATABASE_URL = 'postgresql://inteligencia:61Imoveis!@coleta-61.ctug6oqcsj14.us-east-2.rds.amazonaws.com:5432/precificador'
engine = create_engine(DATABASE_URL)
Session = sessionmaker(bind=engine)
session = Session()

def inserir_dados():
    try:
        print("Lendo CSV...")
        df = pd.read_csv('./back-end/dados/dados_map.csv')
        print(f"{len(df)} linhas lidas com sucesso.")
    except Exception as e:
        print(f"Erro ao ler CSV: {e}")
        return

    # Preenche valores nulos
    df['vagas'] = df['vagas'].fillna(0).astype(int)
    df['quartos'] = df['quartos'].fillna(0).astype(int)
    df['area_util'] = df['area_util'].fillna(0)
    df['valor_m2'] = df['valor_m2'].fillna(0)
    df['preco'] = df['preco'].fillna(0)

    imoveis = []

    for i, row in df.iterrows():
        if row['preco'] > 100_000_000 or row['valor_m2'] > 100_000_000:
            continue

        try:
            imovel = Imovel(
                codigo=row['codigo'],
                anunciante=row['anunciante'],
                oferta=row['oferta'],
                tipo=row['tipo'],
                area_util=row['area_util'],
                bairro=row['bairro'],
                cidade=row['cidade'],
                preco=row['preco'],
                valor_m2=row['valor_m2'],
                quartos=row['quartos'],
                vagas=row['vagas'],
                latitude=row['latitude'],
                longitude=row['longitude']
            )
            imoveis.append(imovel)
        except Exception as e:
            print(f"Erro ao processar linha {i}: {e}")

        if i % 100 == 0:
            print(f"{i} registros processados...")

    try:
        print("Inserindo no banco de dados...")
        session.bulk_save_objects(imoveis)
        session.commit()
        print("Imóveis importados com sucesso.")
    except Exception as e:
        session.rollback()
        print(f"Erro ao inserir no banco: {e}")
    finally:
        session.close()

# Executa a função
