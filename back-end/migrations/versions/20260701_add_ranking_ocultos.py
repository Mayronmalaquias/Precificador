"""Add ranking_ocultos (corretores ocultados manualmente do ranking).

Revision ID: 20260701_ranking_ocultos
Revises: 20260626_contrato_fonte
Create Date: 2026-07-01
"""

from alembic import op
import sqlalchemy as sa


revision = "20260701_ranking_ocultos"
down_revision = "20260626_contrato_fonte"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "ranking_ocultos",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("id_corretor", sa.String(length=50), nullable=False),
        sa.Column("nome", sa.String(length=255), nullable=True),
        sa.Column("criado_em", sa.DateTime(), server_default=sa.func.now(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("id_corretor", name="uq_ranking_ocultos_id_corretor"),
    )
    op.create_index("ix_ranking_ocultos_id_corretor", "ranking_ocultos", ["id_corretor"])


def downgrade():
    op.drop_index("ix_ranking_ocultos_id_corretor", table_name="ranking_ocultos")
    op.drop_table("ranking_ocultos")
