from flask import Flask, send_file
from flask_restx import Api
import pandas as pd
from dotenv import load_dotenv
from flask_caching import Cache
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from app.routes.analise_routes import analise_ns 
from app.routes.mapa_routes import mapa_ns
from app.config import Config
from app.models import *
from flask_cors import CORS
# from app.models.imovel import Imovel


db = SQLAlchemy()
def create_app():
    app = Flask(__name__)
    CORS(app)
    app.config.from_object(Config)
    # app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://postgres:example@localhost:5432/postgres'

    db.init_app(app)
    migrate = Migrate(app, db) 
     # Ativar Flask-Migrate
    api = Api(app,
              version='1.0',
              title='API Imobiliaria',
              description='API para analise e mapeamento de imoveis',
              doc='/')

    cache = Cache(app, config={'CACHE_TYPE': 'simple'})
    load_dotenv()
    csv_file_path = './dados/dados_map.csv'

    # Carregar Dados
    @cache.cached(timeout=60)
    def carregar_dados():
        df = pd.read_csv('./dados/2024-09-06.csv')
        df_map = pd.read_csv(csv_file_path)
        return df, df_map

    # @app.route('/', methods=['GET'])
    # def index():
    #     return send_file('indexPaginaUnica.html')
    
    api.add_namespace(mapa_ns, path='/')
    api.add_namespace(analise_ns, path='/')


    return app

