from flask import Flask
from flask_restx import Api
from flask_cors import CORS
from flask_caching import Cache
from dotenv import load_dotenv
from app.config import Config
import pandas as pd
from sqlalchemy import create_engine
from app.models.base import Base  # Arquivo com declarative_base()

def create_app():
    # Carrega variáveis de ambiente
    load_dotenv()

    app = Flask(__name__)
    app.config.from_object(Config)
    CORS(app)
    cache = Cache(app, config={'CACHE_TYPE': 'simple'})

    # Cria engine do SQLAlchemy
    engine = create_engine(app.config["SQLALCHEMY_DATABASE_URI"], echo=True)

    # Importa os modelos (para registrar no Base.metadata)
    from app.models.imovel import Imovel, ImovelVenda, ImovelAluguel

    # Cria tabelas se ainda não existirem
    with app.app_context():
        print("Criando tabelas com SQLAlchemy puro...")
        Base.metadata.create_all(engine)
        print("Tabelas criadas com sucesso.")

    # Inicializa API REST
    api = Api(
        app,
        version='1.0',
        title='API Imobiliária',
        description='API para análise e mapeamento de imóveis',
        doc='/docs'
    )

    # Importa rotas e namespaces
    from app.routes.analise_routes import analise_ns
    from app.routes.mapa_routes import mapa_ns

    api.add_namespace(mapa_ns, path='/')
    api.add_namespace(analise_ns, path='/')

    # Cache de dados de CSV (opcional)
    @cache.cached(timeout=60)
    def carregar_dados():
        df = pd.read_csv('./dados/2024-09-06.csv')
        df_map = pd.read_csv('./dados/dados_map.csv')
        return df, df_map

    return app
