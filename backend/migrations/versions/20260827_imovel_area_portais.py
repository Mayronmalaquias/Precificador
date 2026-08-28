"""Publicação do imóvel nos portais, vinda da API do Imoview.

`POST /Imovel/RetornarPortaisImoveis` devolve, por imóvel, a lista de portais com
situação (ativo / retirado), tipo de destaque e dias de publicação — mais os campos do
site próprio (`exibirmeusite`, `tipodestaquesite`), que não são um vínculo de portal.

Guardado como AGREGADO, não uma linha por portal. A pergunta que a tela faz é "quantos
imóveis estão publicados, e com que destaque" — para isso basta o total de portais ativos
e o maior destaque entre eles. Uma tabela `imovel_portal` seria mais fiel, e é o caminho
se um dia alguém precisar de "quantos anúncios no OLX especificamente".

`destaque_portal` guarda o MAIOR nível ativo. Um imóvel anunciado como Simples em quatro
portais e Super Destaque num quinto está, na prática, em Super Destaque — é por ele que a
operação paga, e é o que interessa contar.

Revision ID: 20260827_area_portais
Revises: 20260827_area_capt
"""
from alembic import op
import sqlalchemy as sa

revision = "20260827_area_portais"
down_revision = "20260827_area_capt"
branch_labels = None
depends_on = None

COLUNAS = (
    ("portais_ativos", sa.Integer()),
    ("portais_total", sa.Integer()),
    # Nível do CRM: 1 simples, 2 destaque, 3 super destaque, 4 premiere especial,
    # 5 premiere premium, 6 triplo. Guardo o número para ordenar e o rótulo para exibir.
    ("destaque_nivel", sa.Integer()),
    ("destaque_portal", sa.Text()),
    ("exibir_meu_site", sa.Boolean()),
    ("destaque_site", sa.Text()),
    ("portais_em", sa.DateTime()),
)


def upgrade():
    for nome, tipo in COLUNAS:
        op.add_column("imovel_area", sa.Column(nome, tipo, nullable=True))
    # A tela conta "publicados" e agrupa por destaque; os dois indexados cobrem o card.
    op.create_index("ix_imovel_area_portais_ativos", "imovel_area", ["portais_ativos"])
    op.create_index("ix_imovel_area_destaque_nivel", "imovel_area", ["destaque_nivel"])


def downgrade():
    op.drop_index("ix_imovel_area_destaque_nivel", table_name="imovel_area")
    op.drop_index("ix_imovel_area_portais_ativos", table_name="imovel_area")
    for nome, _ in reversed(COLUNAS):
        op.drop_column("imovel_area", nome)
