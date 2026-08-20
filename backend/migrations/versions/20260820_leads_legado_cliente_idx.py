"""leads_legado: índice em `cliente`, usado no casamento com os leads vivos do C2S.

A aba de leads do Relatório do Gerente passou a ler direto do Contact2Sale e precisa
reencontrar cada lead na base interna para saber se já tem acompanhamento
(`lead_c2s_service._ids_internos`, que faz `cliente IN (...)` com os nomes da página).

Sem índice, isso varria as 68 mil linhas da tabela a cada página: 10,5 s medidos, contra
0,6 s quando o Postgres já tinha o dado em cache — ou seja, a primeira consulta de cada
gerente pagava a varredura inteira.

Revision ID: 20260820_leads_cli_idx
Revises: 20260814_trello_card
Create Date: 2026-08-20
"""
from alembic import op

revision = "20260820_leads_cli_idx"
down_revision = "20260814_trello_card"
branch_labels = None
depends_on = None


def upgrade():
    op.create_index("ix_leads_legado_cliente", "leads_legado", ["cliente"])
    # O casamento é por (cliente, telefone); o composto cobre o par sem precisar voltar
    # à tabela para conferir o telefone.
    op.create_index("ix_leads_legado_cliente_telefone", "leads_legado", ["cliente", "telefone"])


def downgrade():
    op.drop_index("ix_leads_legado_cliente_telefone", table_name="leads_legado")
    op.drop_index("ix_leads_legado_cliente", table_name="leads_legado")
