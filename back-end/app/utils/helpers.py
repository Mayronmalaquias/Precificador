import pandas as pd
from sqlalchemy.orm import sessionmaker
from app.models.imovel import Imovel
from app import engine


Session = sessionmaker(bind=engine)
session = Session()

# Lê o CSV

def inserir_dados():
    df = pd.read_csv('./dados/dados_map.csv')

    # Trata os NaNs
    df['vagas'] = df['vagas'].fillna(0).astype(int)
    df['quartos'] = df['quartos'].fillna(0).astype(int)
    df['area_util'] = df['area_util'].fillna(0)
    df['valor_m2'] = df['valor_m2'].fillna(0)
    df['preco'] = df['preco'].fillna(0)
    # Insere dados
    for _, row in df.iterrows():
        if(row['preco'] > 100000000 or row['valor_m2'] > 100000000):
            continue
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
        session.add(imovel)
        session.flush()  # garante que o imovel.id seja gerado antes de usar

        # Descomente se quiser popular ImovelAluguel ou ImovelVenda no futuro
        # if row['tipo_imovel'] == 'aluguel':
        #     aluguel = ImovelAluguel(id=imovel.id, cluster=row['cluster'])
        #     session.add(aluguel)
        # elif row['tipo_imovel'] == 'venda':
        #     venda = ImovelVenda(id=imovel.id, cluster=row['cluster'])
        #     session.add(venda)

    session.commit()
    print("Imóveis importados com sucesso.")


