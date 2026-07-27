"""Tabela canonica `vendas` (Etapa B passo 2) + troca unique parcial->cheio em
usuarios.id_usuarios (necessario p/ FK das colunas *_id).

Revision ID: 20260626_vendas
Revises: 20260626_uq_id_usuarios
Create Date: 2026-06-26
"""

from alembic import op
import sqlalchemy as sa


revision = "20260626_vendas"
down_revision = "20260626_uq_id_usuarios"
branch_labels = None
depends_on = None

_FK_COLS = ["vendedor_id", "captador_id", "gerente_venda_id", "gerente_captacao_id", "diretor_id"]


def upgrade():
    # unique parcial -> unique cheio (FK exige unique nao-parcial no alvo; NULLs continuam permitidos)
    op.drop_index("uq_usuarios_id_usuarios", table_name="usuarios")
    op.create_index("uq_usuarios_id_usuarios", "usuarios", ["id_usuarios"], unique=True)

    op.create_table(
        "vendas",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("fonte", sa.String(length=20), nullable=True),
        sa.Column("id_contrato", sa.String(length=50), nullable=True),
        sa.Column("data_venda", sa.Date(), nullable=True),
        sa.Column("data_captacao", sa.Date(), nullable=True),
        sa.Column("bairro", sa.Text(), nullable=True),
        sa.Column("tipo", sa.Text(), nullable=True),
        sa.Column("codigo_imovel", sa.String(length=50), nullable=True),
        sa.Column("valor_negocio", sa.Numeric(14, 2), nullable=True),
        sa.Column("valor_comissao", sa.Numeric(14, 2), nullable=True),
        sa.Column("vendedor_nome", sa.Text(), nullable=True),
        sa.Column("vendedor_id", sa.String(length=50), nullable=True),
        sa.Column("captador_nome", sa.Text(), nullable=True),
        sa.Column("captador_id", sa.String(length=50), nullable=True),
        sa.Column("gerente_venda_nome", sa.Text(), nullable=True),
        sa.Column("gerente_venda_id", sa.String(length=50), nullable=True),
        sa.Column("gerente_captacao_nome", sa.Text(), nullable=True),
        sa.Column("gerente_captacao_id", sa.String(length=50), nullable=True),
        sa.Column("diretor_nome", sa.Text(), nullable=True),
        sa.Column("diretor_id", sa.String(length=50), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_vendas_data_venda", "vendas", ["data_venda"])
    op.create_index("ix_vendas_id_contrato", "vendas", ["id_contrato"])
    op.create_index("ix_vendas_codigo_imovel", "vendas", ["codigo_imovel"])
    for col in _FK_COLS:
        op.create_index(f"ix_vendas_{col}", "vendas", [col])
        op.create_foreign_key(f"fk_vendas_{col}", "vendas", "usuarios", [col], ["id_usuarios"])


def downgrade():
    op.drop_table("vendas")
    op.drop_index("uq_usuarios_id_usuarios", table_name="usuarios")
    op.create_index(
        "uq_usuarios_id_usuarios", "usuarios", ["id_usuarios"],
        unique=True, postgresql_where=sa.text("id_usuarios IS NOT NULL"),
    )
