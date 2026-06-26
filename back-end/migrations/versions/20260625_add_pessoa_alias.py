"""Add pessoa_alias (de-para pessoa->id_usuarios) + index em usuarios.id_usuarios.

Etapa A do MAPA_BANCO.md. UNIQUE em usuarios.id_usuarios fica adiado (ha
duplicatas a resolver - ver vw_usuarios_duplicados); aqui so um index normal.

Revision ID: 20260625_pessoa_alias
Revises: 20260625_fato_bases
Create Date: 2026-06-25
"""

from alembic import op
import sqlalchemy as sa


revision = "20260625_pessoa_alias"
down_revision = "20260625_fato_bases"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "pessoa_alias",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("alias_key", sa.String(length=255), nullable=False),
        sa.Column("id_usuarios", sa.String(length=50), nullable=False),
        sa.Column("origem", sa.String(length=20), nullable=True),
        sa.Column("observacao", sa.Text(), nullable=True),
        sa.Column("criado_em", sa.DateTime(), server_default=sa.func.now(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("alias_key", name="uq_pessoa_alias_key"),
    )
    op.create_index("ix_pessoa_alias_id_usuarios", "pessoa_alias", ["id_usuarios"])
    op.create_index("ix_usuarios_id_usuarios", "usuarios", ["id_usuarios"], unique=False)


def downgrade():
    op.drop_index("ix_usuarios_id_usuarios", table_name="usuarios")
    op.drop_index("ix_pessoa_alias_id_usuarios", table_name="pessoa_alias")
    op.drop_table("pessoa_alias")
