"""Uma linha por imóvel × portal, vinda de `/Imovel/RetornarPortaisImoveis`.

Até aqui a publicação era guardada só como AGREGADO em `imovel_area`: quantos portais
ativos e o MAIOR nível de destaque entre eles. A migration `20260827_area_portais` já
registrava que uma tabela por portal seria mais fiel, e que era o caminho quando alguém
precisasse de "quantos anúncios num portal específico".

É o caso agora. O agregado engana quando se olha um portal só. Medido em 29/08/2026,
sobre os 998 imóveis de venda/disponível:

| portal                            | ativos | Simples | Destaque | Super |
|-----------------------------------|--------|---------|----------|-------|
| Facebook (Imóvel)                 |    632 |     620 |        9 |     3 |
| Facebook (Produto)                |    630 |     610 |       16 |     4 |
| OLX Brasil (ZAP, Viva Real e OLX) |    611 |     530 |       74 |     7 |
| Imóvel Web                        |    610 |     379 |      114 |   117 |
| DF imóveis                        |    609 |     551 |       58 |     0 |

O card dizia "Super destaque: 106" — quase todo Imóvel Web. **DF imóveis, que é o portal
principal da operação, não tem nenhum super destaque**, e isso era invisível no agregado.

As colunas de `imovel_area` continuam existindo: alimentam o card "Nos portais" e o
filtro de publicação, e responder "está publicado?" não precisa varrer esta tabela.

Revision ID: 20260829_imovel_portal
Revises: 20260827_area_portais
"""
from alembic import op
import sqlalchemy as sa

revision = "20260829_imovel_portal"
down_revision = "20260827_area_portais"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "imovel_portal",
        # (codigo, codigo_portal) é a chave: o Imoview devolve um registro por portal
        # para cada imóvel, e o mesmo imóvel nunca repete portal.
        sa.Column("codigo", sa.Text(), nullable=False),
        sa.Column("codigo_portal", sa.Integer(), nullable=False),
        sa.Column("nome_portal", sa.Text(), nullable=True),
        # 1 = ativo, 2 = retirado. Guardar o retirado é o que permite separar "está no
        # ar" de "já esteve no ar" — apagar a linha perderia essa diferença.
        sa.Column("situacao", sa.Integer(), nullable=True),
        sa.Column("situacao_rotulo", sa.Text(), nullable=True),
        # 1 simples, 2 destaque, 3 super destaque, 4 premiere especial, 5 premiere
        # premium, 6 triplo. Número para ordenar, rótulo para exibir.
        sa.Column("destaque_nivel", sa.Integer(), nullable=True),
        sa.Column("destaque_rotulo", sa.Text(), nullable=True),
        sa.Column("dias_publicacao", sa.Integer(), nullable=True),
        sa.Column("primeiro_envio", sa.DateTime(), nullable=True),
        sa.Column("ultimo_envio", sa.DateTime(), nullable=True),
        sa.Column("atualizado_em", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("codigo", "codigo_portal"),
    )
    # O card agrupa por portal dentro de um recorte de imóveis: o índice composto cobre
    # o caminho inteiro (filtra por situação, agrupa por portal e nível).
    op.create_index("ix_imovel_portal_codigo", "imovel_portal", ["codigo"])
    op.create_index(
        "ix_imovel_portal_agrupamento", "imovel_portal",
        ["situacao", "codigo_portal", "destaque_nivel"],
    )


def downgrade():
    op.drop_index("ix_imovel_portal_agrupamento", table_name="imovel_portal")
    op.drop_index("ix_imovel_portal_codigo", table_name="imovel_portal")
    op.drop_table("imovel_portal")
