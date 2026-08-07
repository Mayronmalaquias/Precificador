"""Proposta efetiva: corretor responsável + visita relacionada.

Revision ID: 20260807_proposta_corretor
Revises: 20260807_imovel_area
Create Date: 2026-08-07
"""
import sqlalchemy as sa
from alembic import op

revision = "20260807_proposta_corretor"
down_revision = "20260807_imovel_area"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("proposta_efetiva", sa.Column("id_corretor", sa.String(length=50), nullable=True))
    op.add_column("proposta_efetiva", sa.Column("corretor_nome", sa.String(length=255), nullable=True))
    op.add_column("proposta_efetiva", sa.Column("id_visita", sa.String(length=50), nullable=True))
    op.create_index("ix_proposta_efetiva_corretor", "proposta_efetiva", ["id_corretor"])
    op.create_index("ix_proposta_efetiva_visita", "proposta_efetiva", ["id_visita"])


def downgrade():
    op.drop_index("ix_proposta_efetiva_visita", table_name="proposta_efetiva")
    op.drop_index("ix_proposta_efetiva_corretor", table_name="proposta_efetiva")
    op.drop_column("proposta_efetiva", "id_visita")
    op.drop_column("proposta_efetiva", "corretor_nome")
    op.drop_column("proposta_efetiva", "id_corretor")
