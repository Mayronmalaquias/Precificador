"""Histórico de mudança de situação do imóvel (base das saídas de estoque).

Revision ID: 20260812_situacao_evento
Revises: 20260812_imovel_situacao
Create Date: 2026-08-12
"""
import sqlalchemy as sa
from alembic import op

revision = "20260812_situacao_evento"
down_revision = "20260812_imovel_situacao"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "imovel_situacao_evento",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("codigo", sa.String(length=50), nullable=False),
        sa.Column("situacao_anterior", sa.String(length=40), nullable=True),
        sa.Column("situacao_nova", sa.String(length=40), nullable=True),
        sa.Column("detectado_em", sa.Date(), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=True),
    )
    op.create_index("ix_imovel_situacao_evento_codigo", "imovel_situacao_evento", ["codigo"])
    op.create_index("ix_imovel_situacao_evento_detectado_em", "imovel_situacao_evento", ["detectado_em"])
    op.create_index(
        "ix_imovel_situacao_evento_periodo", "imovel_situacao_evento",
        ["detectado_em", "situacao_anterior", "situacao_nova"],
    )


def downgrade():
    op.drop_index("ix_imovel_situacao_evento_periodo", table_name="imovel_situacao_evento")
    op.drop_index("ix_imovel_situacao_evento_detectado_em", table_name="imovel_situacao_evento")
    op.drop_index("ix_imovel_situacao_evento_codigo", table_name="imovel_situacao_evento")
    op.drop_table("imovel_situacao_evento")
