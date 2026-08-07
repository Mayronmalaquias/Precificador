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
        allow_headers=["Content-Type", "Authorization", "X-API-KEY"],
        methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        max_age=86400,
    )

    from app.utils.auth_middleware import register_auth_middleware
    register_auth_middleware(app)

    api = Api(
        app,
        version="1.0",
        title="API Imobiliaria",
        description="API para analise e mapeamento de imoveis",
        doc="/docs",
    )

    from app.routes.admin_bases_routes import admin_bases_ns
    from app.routes.analise_routes import analise_ns
    from app.routes.assistente_routes import assistente_ns
    from app.routes.auth_routes import auth_ns
    from app.routes.captacao_routes import captacao_ns
    from app.routes.chat_routes import chat_ns
    from app.routes.divisao_comissao_routes import divisao_ns
    from app.routes.diretor_dashboard_routes import diretor_dashboard_ns
    from app.routes.equipes_routes import equipes_ns
    from app.routes.gerentes_dash_routes import gerente_dashboard_ns
    from app.routes.graph_routes import graph_ns
    from app.routes.imovel_rel_route import imovel_catalogo_ns
    from app.routes.mapa_routes import mapa_ns
    from app.routes.parcerias_routes import parcerias_ns
    from app.routes.proposta_routes import proposta_ns
    from app.routes.ranking_routes import meta_gerente_bp, ranking_ns
    from app.routes.relatorio_visita_route import relatorio_visita
    from app.routes.report_routes import report_ns
    from app.routes.usuarios_routes import corretor_ns
    from app.routes.vendas_routes import vendas_ns
    from app.routes.visita_routes import visita_ns

    api_prefix = app.config["API_PREFIX"].rstrip("/")

    api.add_namespace(relatorio_visita, path=api_prefix)
    api.add_namespace(corretor_ns, path=api_prefix)
    api.add_namespace(imovel_catalogo_ns, path=api_prefix)
    api.add_namespace(divisao_ns, path=api_prefix)
    api.add_namespace(diretor_dashboard_ns, path=f"{api_prefix}/diretor-dashboard")
    api.add_namespace(equipes_ns, path=api_prefix)
    api.add_namespace(mapa_ns, path=api_prefix)
    api.add_namespace(gerente_dashboard_ns, path=f"{api_prefix}/gerente-dashboard")
    api.add_namespace(analise_ns, path=api_prefix)
    api.add_namespace(auth_ns, path=api_prefix)
    api.add_namespace(graph_ns, path=api_prefix)
    api.add_namespace(report_ns, path=api_prefix)
    api.add_namespace(visita_ns, path=api_prefix)
    api.add_namespace(captacao_ns, path=api_prefix)
    api.add_namespace(ranking_ns, path=api_prefix)
    api.add_namespace(parcerias_ns, path=api_prefix)
    api.add_namespace(proposta_ns, path=api_prefix)
    api.add_namespace(chat_ns, path=api_prefix)
    api.add_namespace(admin_bases_ns, path=api_prefix)
    api.add_namespace(assistente_ns, path=api_prefix)
    api.add_namespace(vendas_ns, path=api_prefix)
    app.register_blueprint(meta_gerente_bp, url_prefix=api_prefix)

    return app
