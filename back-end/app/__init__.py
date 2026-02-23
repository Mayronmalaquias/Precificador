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


# Engine e Session global

app = Flask(__name__)
app.url_map.strict_slashes = False
cache = Cache(app, config={'CACHE_TYPE': 'simple'})

def create_app():
    load_dotenv()

    app.config.from_object(Config)
    cache.init_app(app)
    CORS(
        app,
        resources={r"/*": {"origins": [
            "http://15.228.241.137",
            "http://15.228.241.137:3000",
            "http://localhost:3000",
            "http://127.0.0.1:3000",
            "http://26.126.132.200",
            "http://127.0.0.1",
            "https://inteligencia61imoveis.com.br",
            "http://inteligencia61imoveis.com.br"
        ]}},
    )
    

    api = Api(app, version='1.0', title='API Imobiliária', description='API para análise e mapeamento de imóveis', doc='/docs')

    from app.routes.analise_routes import analise_ns
    # from app.routes.mapa_routes import mapa_ns
    from app.routes.auth_routes import auth_ns
    from app.routes.graph_routes import graph_ns
    from app.routes.report_routes import report_ns
    from app.routes.visita_routes import visita_ns
    from app.routes.ranking_routes import ranking_ns
    from app.routes.divisao_comissao_routes import divisao_ns
    api.add_namespace(divisao_ns, path='/')
    # api.add_namespace(mapa_ns, path='/')
    api.add_namespace(analise_ns, path='/')
    api.add_namespace(auth_ns, path='/' )
    api.add_namespace(graph_ns, path='/')
    api.add_namespace(report_ns, path='/')
    api.add_namespace(visita_ns, path='/')
    api.add_namespace(ranking_ns, path='/')


    return app
