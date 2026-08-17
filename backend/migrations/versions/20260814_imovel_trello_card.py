"""imovel_area: id/url do cartão do Trello criado no lançamento.

Sem guardar o id, editar matrícula ou inscrição na Consulta de Imóveis corrigia a nossa
base e deixava o cartão do Trello com o valor antigo — o ciclo não fechava.

Revision ID: 20260814_trello_card
Revises: 20260814_lead_acomp
Create Date: 2026-08-14
"""
import sqlalchemy as sa
from alembic import op

revision = "20260814_trello_card"
down_revision = "20260814_lead_acomp"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("imovel_area", sa.Column("trello_card_id", sa.String(length=40), nullable=True))
    op.add_column("imovel_area", sa.Column("trello_card_url", sa.Text(), nullable=True))


def downgrade():
    op.drop_column("imovel_area", "trello_card_url")
    op.drop_column("imovel_area", "trello_card_id")
