"""Add vendas_legado table (mirrors Fato_Venda, Base Inteligencia, dados desde 2015).

Revision ID: 20260624_vendas_legado
Revises: 20260624_divisao_cols
Create Date: 2026-06-24
"""

from alembic import op
import sqlalchemy as sa


revision = "20260624_vendas_legado"
down_revision = "20260624_divisao_cols"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "vendas_legado",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('san', sa.Text(), nullable=True),
        sa.Column('data_captacao', sa.Date(), nullable=True),
        sa.Column('data_venda', sa.Date(), nullable=True),
        sa.Column('tempo_de_venda', sa.Text(), nullable=True),
        sa.Column('bairro', sa.Text(), nullable=True),
        sa.Column('quadra', sa.Text(), nullable=True),
        sa.Column('tipo', sa.Text(), nullable=True),
        sa.Column('foco', sa.Boolean(), nullable=True),
        sa.Column('valor_do_negocio', sa.Text(), nullable=True),
        sa.Column('valor_comissao', sa.Text(), nullable=True),
        sa.Column('percentual_comissao', sa.Text(), nullable=True),
        sa.Column('valor_total_61', sa.Text(), nullable=True),
        sa.Column('participacao61', sa.Text(), nullable=True),
        sa.Column('correcao61', sa.Text(), nullable=True),
        sa.Column('correcaovgv', sa.Text(), nullable=True),
        sa.Column('nf_61_imovies', sa.Text(), nullable=True),
        sa.Column('liquido_61', sa.Text(), nullable=True),
        sa.Column('correcaovendedor1', sa.Text(), nullable=True),
        sa.Column('v1', sa.Text(), nullable=True),
        sa.Column('q1', sa.Text(), nullable=True),
        sa.Column('vendedor_1', sa.Text(), nullable=True),
        sa.Column('imobiliaria_vendedor_1', sa.Text(), nullable=True),
        sa.Column('percentual_vendedor_1', sa.Text(), nullable=True),
        sa.Column('valor_vendedor_1', sa.Text(), nullable=True),
        sa.Column('gerente_de_venda1', sa.Text(), nullable=True),
        sa.Column('percentual_gerente_venda_1', sa.Text(), nullable=True),
        sa.Column('valor_gerente_venda_1', sa.Text(), nullable=True),
        sa.Column('correcaovendedor2', sa.Text(), nullable=True),
        sa.Column('v2', sa.Text(), nullable=True),
        sa.Column('q2', sa.Text(), nullable=True),
        sa.Column('vendedor_2', sa.Text(), nullable=True),
        sa.Column('percentual_vendedor_2', sa.Text(), nullable=True),
        sa.Column('valor_vendedor_2', sa.Text(), nullable=True),
        sa.Column('gerente_de_venda2', sa.Text(), nullable=True),
        sa.Column('percentual_gerente_venda_2', sa.Text(), nullable=True),
        sa.Column('valor_gerente_venda_2', sa.Text(), nullable=True),
        sa.Column('correcaocap1', sa.Text(), nullable=True),
        sa.Column('v3', sa.Text(), nullable=True),
        sa.Column('q3', sa.Text(), nullable=True),
        sa.Column('captador_1', sa.Text(), nullable=True),
        sa.Column('imobiliaria_captador_1', sa.Text(), nullable=True),
        sa.Column('percentual_captador_1', sa.Text(), nullable=True),
        sa.Column('valor_captador_1', sa.Text(), nullable=True),
        sa.Column('gerente_de_captacao_1', sa.Text(), nullable=True),
        sa.Column('percentualgerente_de_captacao_1', sa.Text(), nullable=True),
        sa.Column('valor_gerente_de_captacao_1', sa.Text(), nullable=True),
        sa.Column('correccaocap2', sa.Text(), nullable=True),
        sa.Column('v4', sa.Text(), nullable=True),
        sa.Column('q4', sa.Text(), nullable=True),
        sa.Column('captador_2', sa.Text(), nullable=True),
        sa.Column('percentual_captador_2', sa.Text(), nullable=True),
        sa.Column('valor_captador_2', sa.Text(), nullable=True),
        sa.Column('gerente_de_captacao_2', sa.Text(), nullable=True),
        sa.Column('percentual_gerente_de_captacao_2', sa.Text(), nullable=True),
        sa.Column('valor_gerente_de_captacao_2', sa.Text(), nullable=True),
        sa.Column('origemleadvenda', sa.Text(), nullable=True),
        sa.Column('tempo_em_dias', sa.Text(), nullable=True),
        sa.Column('entradalead', sa.Date(), nullable=True),
        sa.Column('idcontrato', sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_vendas_legado_data_venda", "vendas_legado", ["data_venda"])


def downgrade():
    op.drop_table("vendas_legado")
