"""Add coluna 'fonte' em contratos (distingue origem: planilha vs legado_pre2024).

Permite que contratos vire a base UNICA completa (2015->hoje) sem confundir a
sincronizacao com a planilha (que so cobre 2024+).

Revision ID: 20260626_contrato_fonte
Revises: 20260626_vendas
Create Date: 2026-06-26
"""

from alembic import op
import sqlalchemy as sa


revision = "20260626_contrato_fonte"
down_revision = "20260626_vendas"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("contratos", sa.Column("fonte", sa.String(length=20), nullable=True))
    op.create_index("ix_contratos_fonte", "contratos", ["fonte"])
    # tudo que ja existe veio da planilha
    op.execute("UPDATE contratos SET fonte = 'planilha' WHERE fonte IS NULL")


def downgrade():
    op.drop_index("ix_contratos_fonte", table_name="contratos")
    op.drop_column("contratos", "fonte")
