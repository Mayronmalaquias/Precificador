"""Add real FK: imoveis_legado.bairro -> bairros_legado.id_bairro,
imoveis_legado.tipo -> tipos_imovel_legado.id_tipo (validado: 100% match, sem orfao).

Revision ID: 20260624_fk_imoveis_legado
Revises: 20260624_estoque_lead
Create Date: 2026-06-24
"""

from alembic import op
import sqlalchemy as sa


revision = "20260624_fk_imoveis_legado"
down_revision = "20260624_estoque_lead"
branch_labels = None
depends_on = None


def upgrade():
    op.create_unique_constraint("uq_bairros_legado_id_bairro", "bairros_legado", ["id_bairro"])
    op.create_unique_constraint("uq_tipos_imovel_legado_id_tipo", "tipos_imovel_legado", ["id_tipo"])

    op.create_foreign_key(
        "fk_imoveis_legado_bairro", "imoveis_legado", "bairros_legado",
        ["bairro"], ["id_bairro"],
    )
    op.create_foreign_key(
        "fk_imoveis_legado_tipo", "imoveis_legado", "tipos_imovel_legado",
        ["tipo"], ["id_tipo"],
    )


def downgrade():
    op.drop_constraint("fk_imoveis_legado_tipo", "imoveis_legado", type_="foreignkey")
    op.drop_constraint("fk_imoveis_legado_bairro", "imoveis_legado", type_="foreignkey")
    op.drop_constraint("uq_tipos_imovel_legado_id_tipo", "tipos_imovel_legado", type_="unique")
    op.drop_constraint("uq_bairros_legado_id_bairro", "bairros_legado", type_="unique")
