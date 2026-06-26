"""Add fato_captacao/fato_saida/fato_estoque/fato_destaque (gestao de bases
corrente pelo site - substitui os scripts Bases/registrar*.py, separada do
historico congelado em eventos_imovel_legado).

Revision ID: 20260625_fato_bases
Revises: 20260625_usuario_desligado
Create Date: 2026-06-25
"""

from alembic import op
import sqlalchemy as sa


revision = "20260625_fato_bases"
down_revision = "20260625_usuario_desligado"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "fato_captacao",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("codigo_imovel", sa.String(length=50), nullable=True),
        sa.Column("captador1", sa.String(length=255), nullable=True),
        sa.Column("captador2", sa.String(length=255), nullable=True),
        sa.Column("captador3", sa.String(length=255), nullable=True),
        sa.Column("id_gerente", sa.String(length=50), nullable=True),
        sa.Column("data_entrada", sa.Date(), nullable=True),
        sa.Column("bairro_id", sa.String(length=50), nullable=True),
        sa.Column("bairro_nome", sa.String(length=255), nullable=True),
        sa.Column("tipo_id", sa.String(length=50), nullable=True),
        sa.Column("tipo_nome", sa.String(length=255), nullable=True),
        sa.Column("valor", sa.Numeric(14, 2), nullable=True),
        sa.Column("comissao_pct", sa.Numeric(6, 2), nullable=True),
        sa.Column("foco_pp", sa.Boolean(), nullable=True),
        sa.Column("foco_ac", sa.Boolean(), nullable=True),
        sa.Column("finalidade", sa.String(length=50), nullable=True),
        sa.Column("origem", sa.String(length=20), nullable=True),
        sa.Column("arquivo_origem", sa.String(length=255), nullable=True),
        sa.Column("criado_por", sa.String(length=50), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_fato_captacao_codigo_imovel", "fato_captacao", ["codigo_imovel"])
    op.create_index("ix_fato_captacao_data_entrada", "fato_captacao", ["data_entrada"])

    op.create_table(
        "fato_saida",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("codigo_imovel", sa.String(length=50), nullable=True),
        sa.Column("captador1", sa.String(length=255), nullable=True),
        sa.Column("captador2", sa.String(length=255), nullable=True),
        sa.Column("captador3", sa.String(length=255), nullable=True),
        sa.Column("id_gerente", sa.String(length=50), nullable=True),
        sa.Column("motivo", sa.Text(), nullable=True),
        sa.Column("data_saida", sa.Date(), nullable=True),
        sa.Column("origem", sa.String(length=20), nullable=True),
        sa.Column("arquivo_origem", sa.String(length=255), nullable=True),
        sa.Column("criado_por", sa.String(length=50), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_fato_saida_codigo_imovel", "fato_saida", ["codigo_imovel"])
    op.create_index("ix_fato_saida_data_saida", "fato_saida", ["data_saida"])

    op.create_table(
        "fato_estoque",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("codigo_imovel", sa.String(length=50), nullable=True),
        sa.Column("captador1", sa.String(length=255), nullable=True),
        sa.Column("captador2", sa.String(length=255), nullable=True),
        sa.Column("captador3", sa.String(length=255), nullable=True),
        sa.Column("id_gerente", sa.String(length=50), nullable=True),
        sa.Column("data_estoque", sa.Date(), nullable=True),
        sa.Column("publicacao_na_internet", sa.String(length=50), nullable=True),
        sa.Column("exclusivo", sa.String(length=50), nullable=True),
        sa.Column("categoria_df", sa.Text(), nullable=True),
        sa.Column("categoria_df_seguro", sa.Text(), nullable=True),
        sa.Column("categoria_wi", sa.Text(), nullable=True),
        sa.Column("id_anuncio_meta", sa.String(length=100), nullable=True),
        sa.Column("origem", sa.String(length=20), nullable=True),
        sa.Column("arquivo_origem", sa.String(length=255), nullable=True),
        sa.Column("criado_por", sa.String(length=50), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_fato_estoque_codigo_imovel", "fato_estoque", ["codigo_imovel"])
    op.create_index("ix_fato_estoque_data_estoque", "fato_estoque", ["data_estoque"])

    op.create_table(
        "fato_destaque",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("codigo_imovel", sa.String(length=50), nullable=True),
        sa.Column("captador1", sa.String(length=255), nullable=True),
        sa.Column("captador2", sa.String(length=255), nullable=True),
        sa.Column("captador3", sa.String(length=255), nullable=True),
        sa.Column("id_gerente", sa.String(length=50), nullable=True),
        sa.Column("data_destaque", sa.Date(), nullable=True),
        sa.Column("endereco", sa.Text(), nullable=True),
        sa.Column("bairro", sa.Text(), nullable=True),
        sa.Column("publicacao_web", sa.String(length=50), nullable=True),
        sa.Column("categoria_df", sa.Text(), nullable=True),
        sa.Column("categoria_wi", sa.Text(), nullable=True),
        sa.Column("categoria_df_seguro", sa.Text(), nullable=True),
        sa.Column("categoria_df_assinado", sa.Text(), nullable=True),
        sa.Column("valor", sa.Numeric(14, 2), nullable=True),
        sa.Column("origem", sa.String(length=20), nullable=True),
        sa.Column("arquivo_origem", sa.String(length=255), nullable=True),
        sa.Column("criado_por", sa.String(length=50), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_fato_destaque_codigo_imovel", "fato_destaque", ["codigo_imovel"])
    op.create_index("ix_fato_destaque_data_destaque", "fato_destaque", ["data_destaque"])


def downgrade():
    op.drop_table("fato_destaque")
    op.drop_table("fato_estoque")
    op.drop_table("fato_saida")
    op.drop_table("fato_captacao")
