"""Espelho local dos leads do Contact2Sale.

A tela de leads lia a API ao vivo a cada consulta filtrada, o que custava minutos: a API
do C2S nao filtra por equipe, portal nem motivo, entao qualquer recorte varria o periodo
inteiro a 10 requisicoes por minuto.

Esta tabela guarda a copia crua, atualizada de hora em hora. A chave e `id_c2s` porque
lead ja importado MUDA — situacao, etapa do funil e motivo de arquivamento sao decididos
depois da entrada, e sem a chave estavel o sync so saberia inserir.

Revision ID: 20260825_leads_c2s
Revises: 20260820_leads_cli_idx
"""
from alembic import op
import sqlalchemy as sa

revision = "20260825_leads_c2s"
down_revision = "20260820_leads_cli_idx"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "leads_c2s",
        sa.Column("id_c2s", sa.String(length=64), primary_key=True),
        sa.Column("data", sa.Date(), nullable=True),
        sa.Column("cliente", sa.Text(), nullable=True),
        sa.Column("telefone", sa.Text(), nullable=True),
        sa.Column("email", sa.Text(), nullable=True),
        sa.Column("fonte", sa.Text(), nullable=True),
        sa.Column("canal", sa.Text(), nullable=True),
        sa.Column("equipe", sa.Text(), nullable=True),
        sa.Column("corretor", sa.Text(), nullable=True),
        sa.Column("codigo_imovel", sa.Text(), nullable=True),
        sa.Column("imovel", sa.Text(), nullable=True),
        sa.Column("url", sa.Text(), nullable=True),
        sa.Column("observacao", sa.Text(), nullable=True),
        sa.Column("situacao", sa.Text(), nullable=True),
        sa.Column("situacao_alias", sa.String(length=40), nullable=True),
        sa.Column("funil", sa.Text(), nullable=True),
        sa.Column("arquivado", sa.Boolean(), nullable=True),
        sa.Column("motivo_arquivamento", sa.Text(), nullable=True),
        sa.Column("negocio_fechado", sa.Boolean(), nullable=True),
        sa.Column("valor_fechado", sa.Numeric(14, 2), nullable=True),
        sa.Column("favorito", sa.Boolean(), nullable=True),
        sa.Column("criado_em", sa.DateTime(), nullable=True),
        sa.Column("atualizado_em", sa.DateTime(), nullable=True),
        sa.Column("ultima_atividade", sa.DateTime(), nullable=True),
        sa.Column("respondido_em", sa.DateTime(), nullable=True),
        sa.Column("id_legado", sa.Integer(), nullable=True),
        sa.Column("sincronizado_em", sa.DateTime(), server_default=sa.func.now(), nullable=True),
    )
    op.create_index("ix_leads_c2s_data", "leads_c2s", ["data"])
    op.create_index("ix_leads_c2s_situacao_alias", "leads_c2s", ["situacao_alias"])
    op.create_index("ix_leads_c2s_arquivado", "leads_c2s", ["arquivado"])
    op.create_index("ix_leads_c2s_atualizado_em", "leads_c2s", ["atualizado_em"])
    op.create_index("ix_leads_c2s_id_legado", "leads_c2s", ["id_legado"])
    # A tela quase sempre pede uma janela de datas dentro de uma equipe ou de um corretor.
    op.create_index("ix_leads_c2s_data_equipe", "leads_c2s", ["data", "equipe"])
    op.create_index("ix_leads_c2s_data_corretor", "leads_c2s", ["data", "corretor"])


def downgrade():
    for nome in (
        "ix_leads_c2s_data_corretor", "ix_leads_c2s_data_equipe", "ix_leads_c2s_id_legado",
        "ix_leads_c2s_atualizado_em", "ix_leads_c2s_arquivado",
        "ix_leads_c2s_situacao_alias", "ix_leads_c2s_data",
    ):
        op.drop_index(nome, table_name="leads_c2s")
    op.drop_table("leads_c2s")
