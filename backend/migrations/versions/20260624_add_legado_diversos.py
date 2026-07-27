"""Add legado_diversos tables (Dim_*/Fato_* pequenas que faltavam + Recebido +
Relatorio_Imovel/Sessao_Usuario/App_Admins/Menu_* - ver investigacao do que faltou.

Revision ID: 20260624_legado_diversos
Revises: 20260624_vendas_legado
Create Date: 2026-06-24
"""

from alembic import op
import sqlalchemy as sa


revision = "20260624_legado_diversos"
down_revision = "20260624_vendas_legado"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "clientes_legado",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("cpf", sa.Text(), nullable=True),
        sa.Column("nome", sa.Text(), nullable=True),
        sa.Column("id_contrato", sa.Text(), nullable=True),
        sa.Column("link_drive", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "nichos_legado",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("corretor", sa.Text(), nullable=True),
        sa.Column("nome", sa.Text(), nullable=True),
        sa.Column("equipe", sa.Text(), nullable=True),
        sa.Column("gerente", sa.Text(), nullable=True),
        sa.Column("regiao", sa.Text(), nullable=True),
        sa.Column("bairro", sa.Text(), nullable=True),
        sa.Column("valor_min", sa.Text(), nullable=True),
        sa.Column("valor_max", sa.Text(), nullable=True),
        sa.Column("tipologia_1", sa.Text(), nullable=True),
        sa.Column("tipologia_2", sa.Text(), nullable=True),
        sa.Column("tipologia_3", sa.Text(), nullable=True),
        sa.Column("tipologia_4", sa.Text(), nullable=True),
        sa.Column("vaga", sa.Text(), nullable=True),
        sa.Column("n_cap_nicho", sa.Text(), nullable=True),
        sa.Column("estoque_nicho", sa.Text(), nullable=True),
        sa.Column("n_estoque_total", sa.Text(), nullable=True),
        sa.Column("vgv_venda", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "tipos_imovel_legado",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("id_tipo", sa.Text(), nullable=True),
        sa.Column("nome", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "bairros_legado",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("id_bairro", sa.Text(), nullable=True),
        sa.Column("nome", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "imoveis_legado",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("codigo", sa.Text(), nullable=True),
        sa.Column("tipo", sa.Text(), nullable=True),
        sa.Column("valor", sa.Text(), nullable=True),
        sa.Column("bairro", sa.Text(), nullable=True),
        sa.Column("foco_pp", sa.Boolean(), nullable=True),
        sa.Column("foco_ac", sa.Boolean(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "diretores_legado",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("id_diretor", sa.Text(), nullable=True),
        sa.Column("nome", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "anuncios_imovel_legado",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("id_anuncio", sa.Text(), nullable=True),
        sa.Column("cod", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "portais_legado",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("categoria", sa.Text(), nullable=True),
        sa.Column("limite", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "fontes_legado",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("codigo", sa.Text(), nullable=True),
        sa.Column("nome", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "atendimentos_legado",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("codigo", sa.Text(), nullable=True),
        sa.Column("nome", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "saidas_legado",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("codigo_imovel", sa.Text(), nullable=True),
        sa.Column("captador1", sa.Text(), nullable=True),
        sa.Column("captador2", sa.Text(), nullable=True),
        sa.Column("captador3", sa.Text(), nullable=True),
        sa.Column("id_gerente", sa.Text(), nullable=True),
        sa.Column("motivo", sa.Text(), nullable=True),
        sa.Column("data_saida", sa.Date(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "campanhas_legado",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("nome_campanha", sa.Text(), nullable=True),
        sa.Column("nome_conjunto_anuncios", sa.Text(), nullable=True),
        sa.Column("nome_anuncio", sa.Text(), nullable=True),
        sa.Column("dia", sa.Date(), nullable=True),
        sa.Column("alcance", sa.Text(), nullable=True),
        sa.Column("impressoes", sa.Text(), nullable=True),
        sa.Column("frequencia", sa.Text(), nullable=True),
        sa.Column("montante_gasto_brl", sa.Text(), nullable=True),
        sa.Column("definicao_atribuicao", sa.Text(), nullable=True),
        sa.Column("comeca_a", sa.Date(), nullable=True),
        sa.Column("termina_a", sa.Date(), nullable=True),
        sa.Column("tipo_resultado", sa.Text(), nullable=True),
        sa.Column("resultados", sa.Text(), nullable=True),
        sa.Column("custo_por_resultado", sa.Text(), nullable=True),
        sa.Column("inicio_relatorios", sa.Date(), nullable=True),
        sa.Column("fim_relatorios", sa.Date(), nullable=True),
        sa.Column("id_anuncio", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "destaques_legado",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("codigo_imovel", sa.Text(), nullable=True),
        sa.Column("captador1", sa.Text(), nullable=True),
        sa.Column("captador2", sa.Text(), nullable=True),
        sa.Column("captador3", sa.Text(), nullable=True),
        sa.Column("id_gerente", sa.Text(), nullable=True),
        sa.Column("endereco", sa.Text(), nullable=True),
        sa.Column("bairro", sa.Text(), nullable=True),
        sa.Column("publicacao_web", sa.Text(), nullable=True),
        sa.Column("categoria_df", sa.Text(), nullable=True),
        sa.Column("categoria_wi", sa.Text(), nullable=True),
        sa.Column("categoria_df_seguro", sa.Text(), nullable=True),
        sa.Column("categoria_df_assinado", sa.Text(), nullable=True),
        sa.Column("valor", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "destaques_mensal_legado",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("codigo_imovel", sa.Text(), nullable=True),
        sa.Column("captador1", sa.Text(), nullable=True),
        sa.Column("captador2", sa.Text(), nullable=True),
        sa.Column("captador3", sa.Text(), nullable=True),
        sa.Column("id_gerente", sa.Text(), nullable=True),
        sa.Column("endereco", sa.Text(), nullable=True),
        sa.Column("bairro", sa.Text(), nullable=True),
        sa.Column("publicacao_web", sa.Text(), nullable=True),
        sa.Column("categoria_df", sa.Text(), nullable=True),
        sa.Column("categoria_wi", sa.Text(), nullable=True),
        sa.Column("categoria_df_seguro", sa.Text(), nullable=True),
        sa.Column("categoria_df_assinado", sa.Text(), nullable=True),
        sa.Column("valor", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "metas_mensais_legado",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("mes", sa.Date(), nullable=True),
        sa.Column("id_gerente", sa.Text(), nullable=True),
        sa.Column("equipe", sa.Text(), nullable=True),
        sa.Column("meta_cap", sa.Text(), nullable=True),
        sa.Column("meta_vgv", sa.Text(), nullable=True),
        sa.Column("super_meta_cap", sa.Text(), nullable=True),
        sa.Column("super_meta_vgv", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "recebidos_legado",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("data", sa.Date(), nullable=True),
        sa.Column("contrato", sa.Text(), nullable=True),
        sa.Column("valor_recebido", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "relatorios_imovel_legado",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("id_relatorio", sa.Text(), nullable=True),
        sa.Column("id_imovel", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "sessoes_usuario_legado",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("id_sessao", sa.Text(), nullable=True),
        sa.Column("id_corretor", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "admins_legado",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("email", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "menus_legado",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("tipo_menu", sa.Text(), nullable=True),
        sa.Column("id_item", sa.Text(), nullable=True),
        sa.Column("titulo", sa.Text(), nullable=True),
        sa.Column("subtitulo", sa.Text(), nullable=True),
        sa.Column("icone", sa.Text(), nullable=True),
        sa.Column("deep_link", sa.Text(), nullable=True),
        sa.Column("ordem", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade():
    op.drop_table("menus_legado")
    op.drop_table("admins_legado")
    op.drop_table("sessoes_usuario_legado")
    op.drop_table("relatorios_imovel_legado")
    op.drop_table("recebidos_legado")
    op.drop_table("metas_mensais_legado")
    op.drop_table("destaques_mensal_legado")
    op.drop_table("destaques_legado")
    op.drop_table("campanhas_legado")
    op.drop_table("saidas_legado")
    op.drop_table("atendimentos_legado")
    op.drop_table("fontes_legado")
    op.drop_table("portais_legado")
    op.drop_table("anuncios_imovel_legado")
    op.drop_table("diretores_legado")
    op.drop_table("imoveis_legado")
    op.drop_table("bairros_legado")
    op.drop_table("tipos_imovel_legado")
    op.drop_table("nichos_legado")
    op.drop_table("clientes_legado")
