"""imovel_area: finalidade (Venda/Aluguel) e data da última mudança de situação.

`situacao_em` é o `datahoraultimasituacao` do Imoview — vem preenchido em 100% dos
imóveis e é o que permite contar saída de estoque **retroativamente**, sem depender do
log de transições (que só enxerga do dia da instalação em diante).

Revision ID: 20260813_imovel_fin
Revises: 20260813_imovel_doc
Create Date: 2026-08-13
"""
import sqlalchemy as sa
from alembic import op

revision = "20260813_imovel_fin"
down_revision = "20260813_imovel_doc"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("imovel_area", sa.Column("finalidade", sa.String(length=30), nullable=True))
    op.add_column("imovel_area", sa.Column("situacao_em", sa.DateTime(), nullable=True))
    op.create_index("ix_imovel_area_finalidade", "imovel_area", ["finalidade"])
    op.create_index("ix_imovel_area_situacao_em", "imovel_area", ["situacao_em"])


def downgrade():
    op.drop_index("ix_imovel_area_situacao_em", table_name="imovel_area")
    op.drop_index("ix_imovel_area_finalidade", table_name="imovel_area")
    op.drop_column("imovel_area", "situacao_em")
    op.drop_column("imovel_area", "finalidade")
