"""Proposta efetiva: detalhes do imóvel vindos da busca no Imoview.

Revision ID: 20260810_proposta_detalhes
Revises: 20260807_proposta_corretor
Create Date: 2026-08-10
"""
import sqlalchemy as sa
from alembic import op

revision = "20260810_proposta_detalhes"
down_revision = "20260807_proposta_corretor"
branch_labels = None
depends_on = None

COLUNAS = [
    ("bloco", sa.String(length=40)),
    ("complemento", sa.String(length=80)),
    ("quartos", sa.String(length=10)),
    ("vagas", sa.String(length=10)),
    ("area", sa.String(length=20)),
]


def upgrade():
    for nome, tipo in COLUNAS:
        op.add_column("proposta_efetiva", sa.Column(nome, tipo, nullable=True))


def downgrade():
    for nome, _ in reversed(COLUNAS):
        op.drop_column("proposta_efetiva", nome)
