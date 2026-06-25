"""Add observacao and atualizado_em to divisao_comissao (matches the real
write path in ranking_service.add_divisao_comissao - Observacao/UpdatedAt).

Revision ID: 20260624_divisao_cols
Revises: 20260624_captacoes_legado
Create Date: 2026-06-24
"""

from alembic import op
import sqlalchemy as sa


revision = "20260624_divisao_cols"
down_revision = "20260624_captacoes_legado"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("divisao_comissao", sa.Column("observacao", sa.Text(), nullable=True))
    op.add_column("divisao_comissao", sa.Column("atualizado_em", sa.DateTime(), nullable=True))


def downgrade():
    op.drop_column("divisao_comissao", "atualizado_em")
    op.drop_column("divisao_comissao", "observacao")
