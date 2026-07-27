"""Drop captacoes_legado/saidas_legado/estoque_legado/destaques_legado/
destaques_mensal_legado - dado ja replicado integralmente em eventos_imovel_legado
(consolidado), confirmado contagem identica antes do drop.

Revision ID: 20260624_drop_eventos_antigas
Revises: 20260624_eventos_imovel
Create Date: 2026-06-24
"""

from alembic import op
import sqlalchemy as sa


revision = "20260624_drop_eventos_antigas"
down_revision = "20260624_eventos_imovel"
branch_labels = None
depends_on = None


def upgrade():
    # DROP TABLE remove os indices da propria tabela automaticamente.
    op.drop_table("destaques_mensal_legado")
    op.drop_table("destaques_legado")
    op.drop_table("estoque_legado")
    op.drop_table("saidas_legado")
    op.drop_table("captacoes_legado")


def downgrade():
    raise NotImplementedError(
        "Dado consolidado em eventos_imovel_legado - recriar as tabelas antigas "
        "exigiria re-popular a partir dela manualmente, sem caminho automatico de volta."
    )
