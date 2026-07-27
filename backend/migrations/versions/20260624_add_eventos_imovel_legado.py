"""Add eventos_imovel_legado (consolida captacoes_legado/saidas_legado/
estoque_legado/destaques_legado/destaques_mensal_legado, mesmo shape base).

Revision ID: 20260624_eventos_imovel
Revises: 20260624_fk_imoveis_legado
Create Date: 2026-06-24
"""

from alembic import op
import sqlalchemy as sa


revision = "20260624_eventos_imovel"
down_revision = "20260624_fk_imoveis_legado"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "eventos_imovel_legado",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("tipo_evento", sa.Text(), nullable=False),
        sa.Column("codigo_imovel", sa.Text(), nullable=True),
        sa.Column("captador1", sa.Text(), nullable=True),
        sa.Column("captador2", sa.Text(), nullable=True),
        sa.Column("captador3", sa.Text(), nullable=True),
        sa.Column("id_gerente", sa.Text(), nullable=True),
        sa.Column("data_evento", sa.Date(), nullable=True),
        sa.Column("motivo", sa.Text(), nullable=True),
        sa.Column("publicacao_na_internet", sa.Text(), nullable=True),
        sa.Column("exclusivo", sa.Text(), nullable=True),
        sa.Column("id_anuncio_meta", sa.Text(), nullable=True),
        sa.Column("endereco", sa.Text(), nullable=True),
        sa.Column("bairro", sa.Text(), nullable=True),
        sa.Column("publicacao_web", sa.Text(), nullable=True),
        sa.Column("categoria_df_assinado", sa.Text(), nullable=True),
        sa.Column("valor", sa.Text(), nullable=True),
        sa.Column("categoria_df", sa.Text(), nullable=True),
        sa.Column("categoria_df_seguro", sa.Text(), nullable=True),
        sa.Column("categoria_wi", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_eventos_imovel_legado_tipo_evento", "eventos_imovel_legado", ["tipo_evento"])
    op.create_index("ix_eventos_imovel_legado_codigo_imovel", "eventos_imovel_legado", ["codigo_imovel"])
    op.create_index("ix_eventos_imovel_legado_data_evento", "eventos_imovel_legado", ["data_evento"])


def downgrade():
    op.drop_table("eventos_imovel_legado")
