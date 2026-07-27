"""Add exclusividade_ate column to captacao table.

Revision ID: 20260610_add_exclusividade_ate_captacao
Revises: 20260507_expand_user_password
Create Date: 2026-06-10
"""

from alembic import op
import sqlalchemy as sa


revision = "20260610_excl_ate"
down_revision = "20260507_expand_user_password"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("captacao", sa.Column("exclusividade_ate", sa.Date(), nullable=True))


def downgrade():
    op.drop_column("captacao", "exclusividade_ate")
