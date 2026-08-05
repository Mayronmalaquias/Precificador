"""Add motivo_sim em visitas + flags de revisao do gerente.

- visitas.motivo_sim: motivo do "Sim" (paralelo ao motivo_talvez), preenchido pelo gerente.
- gerente_visita_visualizada.viu_anexo/viu_notas/add_motivo: flags marcadas na interacao
  do gerente com a visita (importantes p/ o diretor).

Revision ID: 20260805_visita_motivo_sim_flags
Revises: 20260728_visita_revisita
Create Date: 2026-08-05
"""

from alembic import op
import sqlalchemy as sa


revision = "20260805_visita_motivo_sim_flags"
down_revision = "20260728_visita_revisita"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("visitas", sa.Column("motivo_sim", sa.Text(), nullable=True))

    for col in ("viu_anexo", "viu_notas", "add_motivo"):
        op.add_column(
            "gerente_visita_visualizada",
            sa.Column(col, sa.Boolean(), nullable=False, server_default=sa.text("false")),
        )


def downgrade():
    for col in ("add_motivo", "viu_notas", "viu_anexo"):
        op.drop_column("gerente_visita_visualizada", col)
    op.drop_column("visitas", "motivo_sim")
