# app/__init__.py
from flask import Flask
from flask_restx import Api
from flask_cors import CORS
from flask_caching import Cache
from dotenv import load_dotenv
from app.config import Config
import pandas as pd
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
engine = create_engine(Config.SQLALCHEMY_DATABASE_URI, echo=False)
SessionLocal = sessionmaker(bind=engine)
from app.models.base import Base
from app.utils.helpers import inserir_dados

# Engine e Session global

def create_app():
    load_dotenv()

    app = Flask(__name__)
    app.config.from_object(Config)
    CORS(app)
    cache = Cache(app, config={'CACHE_TYPE': 'simple'})

    # Importa os modelos
    from app.models.imovel import Imovel, ImovelVenda, ImovelAluguel

    with app.app_context():
        print("Criando tabelas com SQLAlchemy puro...")
        Base.metadata.create_all(engine)
        print("Tabelas criadas com sucesso.")
    
    inserir_dados()

    api = Api(app, version='1.0', title='API Imobiliária', description='API para análise e mapeamento de imóveis', doc='/docs')

    from app.routes.analise_routes import analise_ns
    from app.routes.mapa_routes import mapa_ns
    from app.routes.auth_routes import auth_ns
    api.add_namespace(mapa_ns, path='/')
    api.add_namespace(analise_ns, path='/')
    api.add_namespace(auth_ns, path='/' )

    @cache.cached(timeout=60)
    def carregar_dados():
        df = pd.read_csv('./dados/2024-09-06.csv')
        df_map = pd.read_csv('./dados/dados_map.csv')
        return df, df_map

    return app
