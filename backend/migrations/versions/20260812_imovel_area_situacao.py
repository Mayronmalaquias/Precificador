"""imovel_area: situação do imóvel no CRM (disponível, vendido, desativado...).

Revision ID: 20260812_imovel_situacao
Revises: 20260811_foco_auditoria
Create Date: 2026-08-12
"""
import sqlalchemy as sa
from alembic import op

revision = "20260812_imovel_situacao"
down_revision = "20260811_foco_auditoria"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("imovel_area", sa.Column("situacao", sa.String(length=40), nullable=True))
    op.create_index("ix_imovel_area_situacao", "imovel_area", ["situacao"])


def downgrade():
    op.drop_index("ix_imovel_area_situacao", table_name="imovel_area")
    op.drop_column("imovel_area", "situacao")
