"""usuarios: link da pasta de documentos no Drive.

Revision ID: 20260811_link_documentos
Revises: 20260811_imovel_area_perfil
Create Date: 2026-08-11
"""
import sqlalchemy as sa
from alembic import op

revision = "20260811_link_documentos"
down_revision = "20260811_imovel_area_perfil"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("usuarios", sa.Column("link_documentos", sa.Text(), nullable=True))


def downgrade():
    op.drop_column("usuarios", "link_documentos")
