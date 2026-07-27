"""UNIQUE em usuarios.id_usuarios (apos dedup_usuarios.sql).

Indice unico PARCIAL (ignora NULL) substituindo o index normal criado antes.
Pre-requisito: nenhum id_usuarios duplicado (ver sql/dedup_usuarios.sql + usuarios_dup_backup).

Revision ID: 20260626_uq_id_usuarios
Revises: 20260625_pessoa_alias
Create Date: 2026-06-26
"""

from alembic import op
import sqlalchemy as sa


revision = "20260626_uq_id_usuarios"
down_revision = "20260625_pessoa_alias"
branch_labels = None
depends_on = None


def upgrade():
    op.drop_index("ix_usuarios_id_usuarios", table_name="usuarios")
    op.create_index(
        "uq_usuarios_id_usuarios",
        "usuarios",
        ["id_usuarios"],
        unique=True,
        postgresql_where=sa.text("id_usuarios IS NOT NULL"),
    )


def downgrade():
    op.drop_index("uq_usuarios_id_usuarios", table_name="usuarios")
    op.create_index("ix_usuarios_id_usuarios", "usuarios", ["id_usuarios"], unique=False)
