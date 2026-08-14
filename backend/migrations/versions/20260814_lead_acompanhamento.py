"""leads_legado: acompanhamento do lead pelo gerente (contato, visita agendada).

A tabela era só espelho do Fato_Lead (o que veio do C2S). Estas colunas são a camada
NOSSA em cima dela: o que o gerente registra depois de olhar o lead.

Revision ID: 20260814_lead_acomp
Revises: 20260813_imovel_fin
Create Date: 2026-08-14
"""
import sqlalchemy as sa
from alembic import op

revision = "20260814_lead_acomp"
down_revision = "20260813_imovel_fin"
branch_labels = None
depends_on = None


def upgrade():
    # sem_contato | whatsapp | telefone | email
    op.add_column("leads_legado", sa.Column("contato_status", sa.String(length=20), nullable=True))
    # Nulo = ninguém respondeu ainda; True/False = respondido. Sem o nulo não daria para
    # separar "não agendou" de "não olharam o lead".
    op.add_column("leads_legado", sa.Column("visita_agendada", sa.Boolean(), nullable=True))
    op.add_column("leads_legado", sa.Column("motivo_sem_visita", sa.Text(), nullable=True))
    op.add_column("leads_legado", sa.Column("proxima_acao", sa.Text(), nullable=True))
    op.add_column("leads_legado", sa.Column("acompanhamento_por", sa.String(length=50), nullable=True))
    op.add_column("leads_legado", sa.Column("acompanhamento_em", sa.DateTime(), nullable=True))
    op.create_index("ix_leads_legado_contato_status", "leads_legado", ["contato_status"])
    op.create_index("ix_leads_legado_visita_agendada", "leads_legado", ["visita_agendada"])


def downgrade():
    op.drop_index("ix_leads_legado_visita_agendada", table_name="leads_legado")
    op.drop_index("ix_leads_legado_contato_status", table_name="leads_legado")
    for coluna in ("acompanhamento_em", "acompanhamento_por", "proxima_acao",
                   "motivo_sem_visita", "visita_agendada", "contato_status"):
        op.drop_column("leads_legado", coluna)
