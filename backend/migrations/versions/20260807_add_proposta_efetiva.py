"""Add proposta_efetiva + proposta_efetiva_acao (propostas lançadas pelos gerentes).

Revision ID: 20260807_proposta_efetiva
Revises: 20260805_dfimoveis_acessos
Create Date: 2026-08-07
"""
import sqlalchemy as sa
from alembic import op

revision = "20260807_proposta_efetiva"
down_revision = "20260805_dfimoveis_acessos"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "proposta_efetiva",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("codigo_imovel", sa.String(length=50), nullable=True),
        sa.Column("imovel_endereco", sa.Text(), nullable=True),
        sa.Column("bairro", sa.String(length=120), nullable=True),
        sa.Column("tipo", sa.String(length=80), nullable=True),
        sa.Column("numero", sa.String(length=40), nullable=True),
        sa.Column("valor", sa.Numeric(14, 2), nullable=True),
        sa.Column("valor_permuta", sa.Numeric(14, 2), nullable=True),
        sa.Column("descricao_permuta", sa.Text(), nullable=True),
        sa.Column("forma_pagamento", sa.String(length=30), nullable=True),
        sa.Column("situacao", sa.String(length=30), nullable=False, server_default="em_analise"),
        sa.Column("team", sa.String(length=50), nullable=True),
        sa.Column("id_gerente", sa.String(length=50), nullable=True),
        sa.Column("gerente_nome", sa.String(length=255), nullable=True),
        sa.Column("cliente", sa.String(length=255), nullable=True),
        sa.Column("observacao", sa.Text(), nullable=True),
        sa.Column("data_proposta", sa.Date(), nullable=True),
        sa.Column("data_fechamento", sa.Date(), nullable=True),
        sa.Column("ultima_acao_em", sa.DateTime(), nullable=True),
        sa.Column("ativo", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("criado_por", sa.String(length=50), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_proposta_efetiva_codigo", "proposta_efetiva", ["codigo_imovel"])
    op.create_index("ix_proposta_efetiva_situacao", "proposta_efetiva", ["situacao"])
    op.create_index("ix_proposta_efetiva_team", "proposta_efetiva", ["team"])
    op.create_index("ix_proposta_efetiva_gerente", "proposta_efetiva", ["id_gerente"])
    op.create_index("ix_proposta_efetiva_data", "proposta_efetiva", ["data_proposta"])
    op.create_index("ix_proposta_efetiva_ultima_acao", "proposta_efetiva", ["ultima_acao_em"])

    op.create_table(
        "proposta_efetiva_acao",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("proposta_id", sa.Integer(), nullable=False),
        sa.Column("descricao", sa.Text(), nullable=False),
        sa.Column("situacao", sa.String(length=30), nullable=True),
        sa.Column("autor_id", sa.String(length=50), nullable=True),
        sa.Column("autor_nome", sa.String(length=255), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=True),
        sa.ForeignKeyConstraint(["proposta_id"], ["proposta_efetiva.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_proposta_acao_proposta", "proposta_efetiva_acao", ["proposta_id"])
    op.create_index("ix_proposta_acao_data", "proposta_efetiva_acao", ["created_at"])


def downgrade():
    op.drop_index("ix_proposta_acao_data", table_name="proposta_efetiva_acao")
    op.drop_index("ix_proposta_acao_proposta", table_name="proposta_efetiva_acao")
    op.drop_table("proposta_efetiva_acao")
    for indice in ("ultima_acao", "data", "gerente", "team", "situacao", "codigo"):
        op.drop_index(f"ix_proposta_efetiva_{indice}", table_name="proposta_efetiva")
    op.drop_table("proposta_efetiva")
