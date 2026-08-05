"""Armazena snapshots XLSX de acesso do DFImoveis.

Revision ID: 20260805_dfimoveis_acessos
Revises: 20260805_visita_motivo_sim_flags
"""
from alembic import op
import sqlalchemy as sa


revision = "20260805_dfimoveis_acessos"
down_revision = "20260805_visita_motivo_sim_flags"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "dfimoveis_acessos",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("data_relatorio", sa.Date(), nullable=False),
        sa.Column("arquivo_origem", sa.Text()), sa.Column("criado_por", sa.String(50)),
        sa.Column("endereco", sa.Text()), sa.Column("bairro", sa.Text()),
        sa.Column("codigo_busca", sa.String(100), nullable=False),
        sa.Column("negocio", sa.String(50)), sa.Column("situacao_cadastro", sa.String(50)),
        *[sa.Column(name, sa.Integer(), nullable=False, server_default="0") for name in (
            "acesso", "impressao", "emails", "telefone", "whatsapp_emails_gerados", "indique",
            "indique_whatsapp", "termo", "compartilhe_facebook", "compartilhe_google",
            "compartilhe_twitter", "atendimento_online_lancamento", "visita", "proposta")],
        sa.Column("importado_em", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("data_relatorio", "codigo_busca", name="uq_dfimoveis_relatorio_codigo"),
    )
    op.create_index("ix_dfimoveis_acessos_data_relatorio", "dfimoveis_acessos", ["data_relatorio"])
    op.create_index("ix_dfimoveis_acessos_bairro", "dfimoveis_acessos", ["bairro"])


def downgrade():
    op.drop_index("ix_dfimoveis_acessos_bairro", table_name="dfimoveis_acessos")
    op.drop_index("ix_dfimoveis_acessos_data_relatorio", table_name="dfimoveis_acessos")
    op.drop_table("dfimoveis_acessos")
