import pandas as pd
from unidecode import unidecode

from app import SessionLocal
from app.models.imovel import Imovel


def inserir_dados():
    session = SessionLocal()
    df = pd.read_csv("./dados/dados_map.csv")
    try:
        df["vagas"] = df["vagas"].fillna(0).astype(int)
        df["quartos"] = df["quartos"].fillna(0).astype(int)
        df["area_util"] = df["area_util"].fillna(0)
        df["valor_m2"] = df["valor_m2"].fillna(0)
        df["preco"] = df["preco"].fillna(0)

        for _, row in df.iterrows():
            if row["preco"] > 100000000 or row["valor_m2"] > 100000000:
                continue
            imovel = Imovel(
                codigo=row["codigo"],
                anunciante=row["anunciante"],
                oferta=row["oferta"],
                tipo=row["tipo"],
                area_util=row["area_util"],
                bairro=row["bairro"],
                cidade=row["cidade"],
                preco=row["preco"],
                valor_m2=row["valor_m2"],
                quartos=row["quartos"],
                vagas=row["vagas"],
                latitude=row["latitude"],
                longitude=row["longitude"],
            )
            session.add(imovel)
            session.flush()

        session.commit()
        print("Imoveis importados com sucesso.")
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def normalizar_user(username):
    if not username:
        return None
    username = username.strip()
    username = username.replace(" ", "_")
    username = username.lower()
    username = unidecode(username)
    return username
