import logging
from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

from app.config import Config
from app.models.base import Base

# Import models so Alembic can see their metadata.
from app.models import imovel, relatorio, usuarios  # noqa: F401
from app.models import equipe, visita, contrato, venda_legado, legado_diversos, estoque_legado, eventos_imovel_legado  # noqa: F401
from app.models import fato_bases  # noqa: F401
from app.models import pessoa_alias  # noqa: F401
from app.models import vendas  # noqa: F401
from app.models import ranking_oculto  # noqa: F401
from app.models import captacao_snapshot  # noqa: F401
from app.models import dfimoveis_acesso  # noqa: F401


config = context.config
config.set_main_option("sqlalchemy.url", Config.SQLALCHEMY_DATABASE_URI)

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

logger = logging.getLogger("alembic.env")
target_metadata = Base.metadata


def run_migrations_offline():
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online():
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
