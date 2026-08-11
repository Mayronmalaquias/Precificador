"""imovel_area: quartos, vagas e valor — dimensões do perfil de mídia.

Revision ID: 20260811_imovel_area_perfil
Revises: 20260810_proposta_detalhes
Create Date: 2026-08-11
"""
import sqlalchemy as sa
from alembic import op

revision = "20260811_imovel_area_perfil"
down_revision = "20260810_proposta_detalhes"
branch_labels = None
depends_on = None

COLUNAS = [
    ("quartos", sa.Integer()),
    ("vagas", sa.Integer()),
    ("valor", sa.Numeric(14, 2)),
]


def upgrade():
    for nome, tipo in COLUNAS:
        op.add_column("imovel_area", sa.Column(nome, tipo, nullable=True))


def downgrade():
    for nome, _ in reversed(COLUNAS):
        op.drop_column("imovel_area", nome)
