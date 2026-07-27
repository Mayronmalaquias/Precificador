"""Add captacao_snapshot (snapshot diario da Jornada p/ dashboard de evolução).

Revision ID: 20260702_captacao_snapshot
Revises: 20260701_ranking_ocultos
Create Date: 2026-07-02
"""

from alembic import op
import sqlalchemy as sa


revision = "20260702_captacao_snapshot"
down_revision = "20260701_ranking_ocultos"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "captacao_snapshot",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("data_snapshot", sa.Date(), nullable=False),
        sa.Column("captacao_id", sa.Integer(), nullable=False),
        sa.Column("team", sa.String(length=100), nullable=True),
        sa.Column("id_corretor", sa.String(length=50), nullable=True),
        sa.Column("nome_corretor", sa.String(length=255), nullable=True),
        sa.Column("bairro", sa.Text(), nullable=True),
        sa.Column("endereco", sa.Text(), nullable=True),
        sa.Column("etapa_atual", sa.String(length=20), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("data_snapshot", "captacao_id", name="uq_captacao_snapshot_dia"),
    )
    op.create_index("ix_captacao_snapshot_data", "captacao_snapshot", ["data_snapshot"])
    op.create_index("ix_captacao_snapshot_captacao", "captacao_snapshot", ["captacao_id"])


def downgrade():
    op.drop_index("ix_captacao_snapshot_captacao", table_name="captacao_snapshot")
    op.drop_index("ix_captacao_snapshot_data", table_name="captacao_snapshot")
    op.drop_table("captacao_snapshot")
