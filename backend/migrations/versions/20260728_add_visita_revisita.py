"""Add coluna 'revisita' em visitas (marca visita a imovel ja visitado antes).

Informacao nova capturada no "Criar visita" (checkbox), exibida no detalhe da
visita e usada como filtro na evolucao de visitas do gerente.

Revision ID: 20260728_visita_revisita
Revises: 20260721_equipes_db
Create Date: 2026-07-28
"""

from alembic import op
import sqlalchemy as sa


revision = "20260728_visita_revisita"
down_revision = "20260721_equipes_db"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "visitas",
        sa.Column("revisita", sa.Boolean(), nullable=True, server_default=sa.text("false")),
    )
    # visitas ja existentes nao sao revisita
    op.execute("UPDATE visitas SET revisita = false WHERE revisita IS NULL")


def downgrade():
    op.drop_column("visitas", "revisita")
