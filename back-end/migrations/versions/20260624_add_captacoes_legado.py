"""Add captacoes_legado table (mirrors Fato_Captacao from Base Inteligencia,
used by ranking_service.load_captacao for the captacao ranking).

Revision ID: 20260624_captacoes_legado
Revises: 20260624_widen_id_imovel
Create Date: 2026-06-24
"""

from alembic import op
import sqlalchemy as sa


revision = "20260624_captacoes_legado"
down_revision = "20260624_widen_id_imovel"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "captacoes_legado",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("codigo_imovel", sa.String(length=50), nullable=True),
        sa.Column("captador1", sa.String(length=50), nullable=True),
        sa.Column("captador2", sa.String(length=50), nullable=True),
        sa.Column("captador3", sa.String(length=50), nullable=True),
        sa.Column("id_gerente", sa.String(length=50), nullable=True),
        sa.Column("data_entrada", sa.Date(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_captacoes_legado_data_entrada", "captacoes_legado", ["data_entrada"])


def downgrade():
    op.drop_table("captacoes_legado")
