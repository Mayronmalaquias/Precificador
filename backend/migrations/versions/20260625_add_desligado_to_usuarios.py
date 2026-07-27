"""Add desligado flag to usuarios.

Revision ID: 20260625_usuario_desligado
Revises: 20260625_usuario_rh
Create Date: 2026-06-25
"""

from alembic import op
import sqlalchemy as sa


revision = "20260625_usuario_desligado"
down_revision = "20260625_usuario_rh"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("usuarios", sa.Column("desligado", sa.Boolean(), nullable=True))
    op.execute("UPDATE usuarios SET desligado = false WHERE desligado IS NULL")
    op.create_index("ix_usuarios_desligado", "usuarios", ["desligado"], unique=False)


def downgrade():
    op.drop_index("ix_usuarios_desligado", table_name="usuarios")
    op.drop_column("usuarios", "desligado")
