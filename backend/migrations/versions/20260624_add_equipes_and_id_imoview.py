"""Add equipes table and usuarios.id_imoview.

Revision ID: 20260624_equipes
Revises: 20260618_cliente_acao
Create Date: 2026-06-24
"""

from alembic import op
import sqlalchemy as sa


revision = "20260624_equipes"
down_revision = "20260618_cliente_acao"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "equipes",
        sa.Column("id_equipe", sa.String(length=50), nullable=False),
        sa.Column("nome", sa.String(length=100), nullable=True),
        sa.Column("email", sa.String(length=255), nullable=True),
        sa.PrimaryKeyConstraint("id_equipe"),
    )
    op.add_column("usuarios", sa.Column("id_imoview", sa.String(length=50), nullable=True))


def downgrade():
    op.drop_column("usuarios", "id_imoview")
    op.drop_table("equipes")
