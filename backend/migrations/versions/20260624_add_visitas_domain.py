"""Add visitas domain tables (clientes_visita, parceiros_visita, visitas,
visita_cliente, visita_parceiro, avaliacoes_visita) — mirrors Modelo_Visitas xlsx.

Revision ID: 20260624_visitas_domain
Revises: 20260624_equipes
Create Date: 2026-06-24
"""

from alembic import op
import sqlalchemy as sa


revision = "20260624_visitas_domain"
down_revision = "20260624_equipes"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "clientes_visita",
        sa.Column("id_cliente", sa.String(length=50), nullable=False),
        sa.Column("nome_cliente", sa.String(length=255), nullable=True),
        sa.Column("telefone_cliente", sa.String(length=50), nullable=True),
        sa.Column("email_cliente", sa.String(length=255), nullable=True),
        sa.Column("created_by", sa.String(length=100), nullable=True),
        sa.Column("id_corretor", sa.String(length=50), nullable=True),
        sa.PrimaryKeyConstraint("id_cliente"),
    )

    op.create_table(
        "parceiros_visita",
        sa.Column("id_parceiro", sa.String(length=50), nullable=False),
        sa.Column("nome_parceiro", sa.String(length=255), nullable=True),
        sa.Column("imobiliaria", sa.String(length=255), nullable=True),
        sa.Column("id_corretor", sa.String(length=50), nullable=True),
        sa.PrimaryKeyConstraint("id_parceiro"),
    )

    op.create_table(
        "visitas",
        sa.Column("id_visita", sa.String(length=50), nullable=False),
        sa.Column("id_imovel", sa.String(length=50), nullable=True),
        sa.Column("data_visita", sa.Date(), nullable=True),
        sa.Column("id_corretor", sa.String(length=50), nullable=True),
        sa.Column("anexo_ficha_visita", sa.Text(), nullable=True),
        sa.Column("audiodescricao_cliente_visita", sa.Text(), nullable=True),
        sa.Column("link_audio", sa.Text(), nullable=True),
        sa.Column("link_imagem", sa.Text(), nullable=True),
        sa.Column("visita_com_parceiro", sa.Boolean(), nullable=True),
        sa.Column("tipo_captacao", sa.String(length=100), nullable=True),
        sa.Column("endereco_externo", sa.Text(), nullable=True),
        sa.Column("proposta", sa.String(length=100), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("created_by", sa.String(length=100), nullable=True),
        sa.Column("assinatura", sa.Text(), nullable=True),
        sa.Column("id_cliente_assinante", sa.String(length=50), nullable=True),
        sa.Column("id_parceiro", sa.String(length=50), nullable=True),
        sa.Column("imovel_nao_captado", sa.Boolean(), nullable=True),
        sa.Column("motivo_talvez", sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint("id_visita"),
        sa.ForeignKeyConstraint(["id_cliente_assinante"], ["clientes_visita.id_cliente"]),
        sa.ForeignKeyConstraint(["id_parceiro"], ["parceiros_visita.id_parceiro"]),
    )
    op.create_index("ix_visitas_id_corretor", "visitas", ["id_corretor"])
    op.create_index("ix_visitas_data_visita", "visitas", ["data_visita"])

    op.create_table(
        "visita_cliente",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("id_clientevisita_origem", sa.String(length=50), nullable=True),
        sa.Column("id_visita", sa.String(length=50), nullable=False),
        sa.Column("id_cliente", sa.String(length=50), nullable=False),
        sa.Column("papel_na_visita", sa.String(length=50), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["id_visita"], ["visitas.id_visita"]),
        sa.ForeignKeyConstraint(["id_cliente"], ["clientes_visita.id_cliente"]),
    )
    op.create_index("ix_visita_cliente_id_visita", "visita_cliente", ["id_visita"])
    op.create_index("ix_visita_cliente_id_cliente", "visita_cliente", ["id_cliente"])

    op.create_table(
        "visita_parceiro",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("id_parceirovisita_origem", sa.String(length=50), nullable=True),
        sa.Column("id_visita", sa.String(length=50), nullable=False),
        sa.Column("id_parceiro", sa.String(length=50), nullable=False),
        sa.Column("papel_na_visita", sa.String(length=50), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["id_visita"], ["visitas.id_visita"]),
        sa.ForeignKeyConstraint(["id_parceiro"], ["parceiros_visita.id_parceiro"]),
    )
    op.create_index("ix_visita_parceiro_id_visita", "visita_parceiro", ["id_visita"])

    op.create_table(
        "avaliacoes_visita",
        sa.Column("id_avaliacao", sa.String(length=50), nullable=False),
        sa.Column("id_visita", sa.String(length=50), nullable=True),
        sa.Column("id_cliente", sa.String(length=50), nullable=True),
        sa.Column("localizacao", sa.Numeric(4, 1), nullable=True),
        sa.Column("tamanho", sa.Numeric(4, 1), nullable=True),
        sa.Column("planta_imovel", sa.Numeric(4, 1), nullable=True),
        sa.Column("qualidade_acabamento", sa.Numeric(4, 1), nullable=True),
        sa.Column("estado_conservacao", sa.Numeric(4, 1), nullable=True),
        sa.Column("condominio_areacomun", sa.Numeric(4, 1), nullable=True),
        sa.Column("preco", sa.Numeric(4, 1), nullable=True),
        sa.Column("nota_geral", sa.Numeric(4, 1), nullable=True),
        sa.Column("preco_n10", sa.String(length=50), nullable=True),
        sa.Column("created_by", sa.String(length=100), nullable=True),
        sa.Column("id_parceiro", sa.String(length=50), nullable=True),
        sa.PrimaryKeyConstraint("id_avaliacao"),
        sa.ForeignKeyConstraint(["id_visita"], ["visitas.id_visita"]),
        sa.ForeignKeyConstraint(["id_cliente"], ["clientes_visita.id_cliente"]),
        sa.ForeignKeyConstraint(["id_parceiro"], ["parceiros_visita.id_parceiro"]),
    )
    op.create_index("ix_avaliacoes_visita_id_visita", "avaliacoes_visita", ["id_visita"])


def downgrade():
    op.drop_table("avaliacoes_visita")
    op.drop_table("visita_parceiro")
    op.drop_table("visita_cliente")
    op.drop_table("visitas")
    op.drop_table("parceiros_visita")
    op.drop_table("clientes_visita")
