"""Previsao manual de fechamento e probabilidade das propostas."""
from alembic import op
import sqlalchemy as sa

revision = "20260908_proposta_previsao"
down_revision = '20260829_imovel_midia'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("proposta_efetiva", sa.Column("fechamento_7_dias", sa.Boolean(), nullable=False, server_default=sa.false()))
    op.add_column("proposta_efetiva", sa.Column("probabilidade_fechamento", sa.String(20), nullable=True))


def downgrade():
    op.drop_column("proposta_efetiva", "probabilidade_fechamento")
    op.drop_column("proposta_efetiva", "fechamento_7_dias")
