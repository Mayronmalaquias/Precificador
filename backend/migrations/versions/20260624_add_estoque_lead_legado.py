"""Add estoque_legado (Fato_Estoque) and leads_legado (Fato_Lead) tables.

Revision ID: 20260624_estoque_lead
Revises: 20260624_legado_diversos
Create Date: 2026-06-24
"""

from alembic import op
import sqlalchemy as sa


revision = "20260624_estoque_lead"
down_revision = "20260624_legado_diversos"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "estoque_legado",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("codigo_imovel", sa.Text(), nullable=True),
        sa.Column("captador1", sa.Text(), nullable=True),
        sa.Column("captador2", sa.Text(), nullable=True),
        sa.Column("captador3", sa.Text(), nullable=True),
        sa.Column("id_gerente", sa.Text(), nullable=True),
        sa.Column("data_estoque", sa.Date(), nullable=True),
        sa.Column("publicacao_na_internet", sa.Text(), nullable=True),
        sa.Column("exclusivo", sa.Text(), nullable=True),
        sa.Column("categoria_df", sa.Text(), nullable=True),
        sa.Column("categoria_df_seguro", sa.Text(), nullable=True),
        sa.Column("categoria_wi", sa.Text(), nullable=True),
        sa.Column("id_anuncio_meta", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_estoque_legado_codigo_imovel", "estoque_legado", ["codigo_imovel"])

    op.create_table(
        "leads_legado",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("data", sa.Date(), nullable=True),
        sa.Column("fonte", sa.Text(), nullable=True),
        sa.Column("contato", sa.Text(), nullable=True),
        sa.Column("relatorio", sa.Text(), nullable=True),
        sa.Column("cliente", sa.Text(), nullable=True),
        sa.Column("telefone", sa.Text(), nullable=True),
        sa.Column("codigo_imovel", sa.Text(), nullable=True),
        sa.Column("atendimento", sa.Text(), nullable=True),
        sa.Column("equipe", sa.Text(), nullable=True),
        sa.Column("observacao", sa.Text(), nullable=True),
        sa.Column("san_observacao", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_leads_legado_data", "leads_legado", ["data"])


def downgrade():
    op.drop_table("leads_legado")
    op.drop_table("estoque_legado")
