"""Widen visitas.id_imovel to Text (1 source row has a full address typed there
instead of a short code - varchar(50) truncated it, data must not be lost).

Revision ID: 20260624_widen_id_imovel
Revises: 20260624_contratos_domain
Create Date: 2026-06-24
"""

from alembic import op
import sqlalchemy as sa


revision = "20260624_widen_id_imovel"
down_revision = "20260624_contratos_domain"
branch_labels = None
depends_on = None


def upgrade():
    op.alter_column("visitas", "id_imovel", existing_type=sa.String(length=50), type_=sa.Text())


def downgrade():
    op.alter_column("visitas", "id_imovel", existing_type=sa.Text(), type_=sa.String(length=50))
