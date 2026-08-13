"""imovel_area: matrícula, inscrição IPTU e data de cadastro no Imoview.

Matrícula e inscrição existiam só no Google Sheets e no Trello (gravadas no lançamento);
não havia onde consultá-las depois. `cadastrado_em` é o `datahoracadastro` do Imoview —
base da ordenação por lançamento na Consulta de Imóveis.

Revision ID: 20260813_imovel_doc
Revises: 20260812_situacao_evento
Create Date: 2026-08-13
"""
import sqlalchemy as sa
from alembic import op

revision = "20260813_imovel_doc"
down_revision = "20260812_situacao_evento"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("imovel_area", sa.Column("matricula", sa.String(length=120), nullable=True))
    op.add_column("imovel_area", sa.Column("inscricao_iptu", sa.String(length=120), nullable=True))
    op.add_column("imovel_area", sa.Column("cadastrado_em", sa.DateTime(), nullable=True))
    op.create_index("ix_imovel_area_cadastrado_em", "imovel_area", ["cadastrado_em"])


def downgrade():
    op.drop_index("ix_imovel_area_cadastrado_em", table_name="imovel_area")
    op.drop_column("imovel_area", "cadastrado_em")
    op.drop_column("imovel_area", "inscricao_iptu")
    op.drop_column("imovel_area", "matricula")
