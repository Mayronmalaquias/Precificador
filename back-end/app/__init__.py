from dotenv import load_dotenv
from flask import Flask
from flask_cors import CORS
from flask_restx import Api

from app.config import Config
from app.database import SessionLocal, engine, remove_session
from app.extensions import cache


def create_app(config_object=Config):
    load_dotenv()

    app = Flask(__name__)
    app.url_map.strict_slashes = False
    app.config.from_object(config_object)

    cache.init_app(app)
    app.teardown_appcontext(remove_session)

    CORS(
        app,
        resources={r"/*": {"origins": app.config["CORS_ORIGINS"]}},
    )

    api = Api(
        app,
        version="1.0",
        title="API Imobiliaria",
        description="API para analise e mapeamento de imoveis",
        doc="/docs",
    )

    from app.routes.admin_bases_routes import admin_bases_ns
    from app.routes.analise_routes import analise_ns
    from app.routes.auth_routes import auth_ns
    from app.routes.captacao_routes import captacao_ns
    from app.routes.chat_routes import chat_ns
    from app.routes.divisao_comissao_routes import divisao_ns
    from app.routes.gerentes_dash_routes import gerente_dashboard_ns
    from app.routes.graph_routes import graph_ns
    from app.routes.imovel_rel_route import imovel_catalogo_ns
    from app.routes.mapa_routes import mapa_ns
    from app.routes.ranking_routes import meta_gerente_bp, ranking_ns
    from app.routes.relatorio_visita_route import relatorio_visita
    from app.routes.report_routes import report_ns
    from app.routes.usuarios_routes import corretor_ns
    from app.routes.visita_routes import visita_ns

    api_prefix = app.config["API_PREFIX"].rstrip("/")

    api.add_namespace(relatorio_visita, path=api_prefix)
    api.add_namespace(corretor_ns, path=api_prefix)
    api.add_namespace(imovel_catalogo_ns, path=api_prefix)
    api.add_namespace(divisao_ns, path=api_prefix)
    api.add_namespace(mapa_ns, path=api_prefix)
    api.add_namespace(gerente_dashboard_ns, path=f"{api_prefix}/gerente-dashboard")
    api.add_namespace(analise_ns, path=api_prefix)
    api.add_namespace(auth_ns, path=api_prefix)
    api.add_namespace(graph_ns, path=api_prefix)
    api.add_namespace(report_ns, path=api_prefix)
    api.add_namespace(visita_ns, path=api_prefix)
    api.add_namespace(captacao_ns, path=api_prefix)
    api.add_namespace(ranking_ns, path=api_prefix)
    api.add_namespace(chat_ns, path=api_prefix)
    api.add_namespace(admin_bases_ns, path=api_prefix)
    app.register_blueprint(meta_gerente_bp, url_prefix=api_prefix)

    return app
