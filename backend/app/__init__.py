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

    # Swagger na raiz: a API vive num subdomínio próprio
    # (api.inteligencia61imoveis.com.br), então `/` não disputa espaço com nada.
    # `/docs` continua funcionando por causa do redirect registrado mais abaixo.
    api = Api(
        app,
        version="1.0",
        title="API — Inteligência 61 Imóveis",
        description=(
            "Back-end do sistema da Inteligência: captação, visitas, propostas, vendas, "
            "rankings e os painéis de gerente e diretoria.\n\n"
            "**Autenticação** — toda rota exige `X-API-KEY` (chave de serviço) **ou** "
            "`Authorization: Bearer <JWT>` (login de usuário). Livres: `/health`, esta "
            "documentação e o preflight CORS.\n\n"
            "**Escopo por usuário** — várias rotas recebem `solicitante_id` e decidem o "
            "alcance pelo cadastro (gerente vê a própria equipe; diretor e administrativo "
            "veem tudo). O parâmetro não é confiável como identidade — ver doc 3.7.\n\n"
            f"**Prefixo** — todos os endpoints ficam sob `{Config.API_PREFIX}`."
        ),
        doc="/",
        authorizations={
            "ApiKey": {"type": "apiKey", "in": "header", "name": "X-API-KEY",
                       "description": "Chave de serviço (`API_SECRET_KEY`)."},
            "Bearer": {"type": "apiKey", "in": "header", "name": "Authorization",
                       "description": "Token do login: `Bearer <JWT>`."},
        },
        security=["ApiKey", "Bearer"],
    )

    from app.routes.admin_bases_routes import admin_bases_ns
    from app.routes.analise_routes import analise_ns
    from app.routes.assistente_routes import assistente_ns
    from app.routes.auth_routes import auth_ns
    from app.routes.captacao_routes import captacao_ns
    from app.routes.chat_routes import chat_ns
    from app.routes.consulta_imovel_routes import consulta_imovel_ns
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

    # A ordem aqui é a ordem das seções no Swagger — agrupada por domínio, do fluxo
    # operacional para o analítico, e não pela ordem em que os módulos foram criados.

    # Acesso e cadastro
    api.add_namespace(auth_ns, path=api_prefix)
    api.add_namespace(corretor_ns, path=api_prefix)
    api.add_namespace(equipes_ns, path=api_prefix)

    # Operação: captação -> visita -> proposta -> venda
    api.add_namespace(captacao_ns, path=api_prefix)
    api.add_namespace(assistente_ns, path=api_prefix)
    api.add_namespace(visita_ns, path=api_prefix)
    api.add_namespace(relatorio_visita, path=api_prefix)
    api.add_namespace(proposta_ns, path=api_prefix)
    api.add_namespace(vendas_ns, path=api_prefix)
    api.add_namespace(divisao_ns, path=api_prefix)
    api.add_namespace(parcerias_ns, path=api_prefix)

    # Painéis
    api.add_namespace(diretor_dashboard_ns, path=f"{api_prefix}/diretor-dashboard")
    api.add_namespace(gerente_dashboard_ns, path=f"{api_prefix}/gerente-dashboard")
    api.add_namespace(ranking_ns, path=api_prefix)

    # Bases e imóveis
    api.add_namespace(admin_bases_ns, path=api_prefix)
    api.add_namespace(consulta_imovel_ns, path=api_prefix)
    api.add_namespace(imovel_catalogo_ns, path=api_prefix)
    api.add_namespace(report_ns, path=api_prefix)

    # Análise de mercado
    api.add_namespace(analise_ns, path=api_prefix)
    api.add_namespace(mapa_ns, path=api_prefix)
    api.add_namespace(graph_ns, path=api_prefix)

    # Outros
    api.add_namespace(chat_ns, path=api_prefix)
    app.register_blueprint(meta_gerente_bp, url_prefix=api_prefix)

    # A doc morava em /docs; quem tiver o link antigo continua chegando na nova.
    @app.route("/docs")
    def _docs_legado():
        from flask import redirect

        return redirect("/", code=301)

    return app
