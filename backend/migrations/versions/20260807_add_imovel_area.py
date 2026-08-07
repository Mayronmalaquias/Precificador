"""Add imovel_area (cache de metragem por código do Imoview).

Revision ID: 20260807_imovel_area
Revises: 20260807_proposta_efetiva
Create Date: 2026-08-07
"""
import sqlalchemy as sa
from alembic import op

revision = "20260807_imovel_area"
down_revision = "20260807_proposta_efetiva"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "imovel_area",
        sa.Column("codigo", sa.String(length=50), nullable=False),
        sa.Column("area", sa.Numeric(12, 2), nullable=True),
        sa.Column("area_principal", sa.Numeric(12, 2), nullable=True),
        sa.Column("area_interna", sa.Numeric(12, 2), nullable=True),
        sa.Column("area_privativa", sa.Numeric(12, 2), nullable=True),
        sa.Column("area_lote", sa.Numeric(12, 2), nullable=True),
        sa.Column("endereco", sa.Text(), nullable=True),
        sa.Column("bairro", sa.String(length=120), nullable=True),
        sa.Column("tipo", sa.String(length=80), nullable=True),
        sa.Column("origem", sa.String(length=30), nullable=True, server_default="imoview"),
        sa.Column("atualizado_em", sa.DateTime(), server_default=sa.func.now(), nullable=True),
        sa.PrimaryKeyConstraint("codigo"),
    )


def downgrade():
    op.drop_table("imovel_area")
