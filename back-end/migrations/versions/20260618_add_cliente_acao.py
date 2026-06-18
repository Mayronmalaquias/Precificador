"""Add cliente acao table.

Revision ID: 20260618_add_cliente_acao
Revises: 20260610_excl_ate
Create Date: 2026-06-18
"""

from alembic import op
import sqlalchemy as sa


revision = "20260618_cliente_acao"
down_revision = "20260610_excl_ate"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "cliente_acao",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("id_cliente", sa.String(length=100), nullable=False),
        sa.Column("id_corretor", sa.String(length=50), nullable=True),
        sa.Column("criado_por", sa.String(length=50), nullable=True),
        sa.Column("titulo", sa.String(length=255), nullable=False),
        sa.Column("descricao", sa.Text(), nullable=True),
        sa.Column("data_acao", sa.Date(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_cliente_acao_id_cliente", "cliente_acao", ["id_cliente"])
    op.create_index("ix_cliente_acao_id_corretor", "cliente_acao", ["id_corretor"])
    op.create_index("ix_cliente_acao_criado_por", "cliente_acao", ["criado_por"])
    op.create_index("ix_cliente_acao_data_acao", "cliente_acao", ["data_acao"])
    op.create_index("ix_cliente_acao_status", "cliente_acao", ["status"])


def downgrade():
    op.drop_index("ix_cliente_acao_status", table_name="cliente_acao")
    op.drop_index("ix_cliente_acao_data_acao", table_name="cliente_acao")
    op.drop_index("ix_cliente_acao_criado_por", table_name="cliente_acao")
    op.drop_index("ix_cliente_acao_id_corretor", table_name="cliente_acao")
    op.drop_index("ix_cliente_acao_id_cliente", table_name="cliente_acao")
    op.drop_table("cliente_acao")
